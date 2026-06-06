from dataclasses import dataclass, field

from chronos.utils import BitFieldExtractor


class Q4_12:
    WIDTH = 16
    FRAC = 12
    SCALE = 1 << FRAC

    def __init__(self, raw: int):
        self.raw = raw & self.__mask()

    def __mask(self) -> int:
        return (1 << self.WIDTH) - 1

    def __to_signed(self, x: int) -> int:
        x &= self.__mask()
        sign = 1 << (self.WIDTH - 1)
        return (x ^ sign) - sign

    @classmethod
    def from_float(cls, x: float):
        return cls(round(x * cls.SCALE))

    @classmethod
    def from_uint(cls, x: "UInt"):
        return cls(x.value)

    def signed_raw(self) -> int:
        return self.__to_signed(self.raw)

    def to_float(self) -> float:
        return self.signed_raw() / self.SCALE

    def to_uint(self) -> "UInt":
        return UInt(self.WIDTH, self.signed_raw())

    def __add__(self, other):
        return Q4_12(self.signed_raw() + other.signed_raw())

    def __sub__(self, other):
        return Q4_12(self.signed_raw() - other.signed_raw())

    def __rshift__(self, num):
        return Q4_12(self.signed_raw() >> num)

    def __lshift__(self, num):
        return Q4_12(self.signed_raw() << num)

    def __eq__(self, other):
        return isinstance(other, Q4_12) and self.raw == other.raw

    def __lt__(self, other):
        return isinstance(other, Q4_12) and self.raw < other.raw

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        return not self < other and not self == other

    def __ge__(self, other):
        return not self < other

    def __str__(self) -> str:
        return f"{self.to_float()}"

    def __repr__(self) -> str:
        return str(self)


# N-bit unsigned int in hardware.
@dataclass(frozen=True, slots=True)
class UInt:
    width: int
    raw: int = 0

    def __post_init__(self):
        if self.width <= 0:
            raise ValueError("UInt width must be positive.")
        object.__setattr__(self, "raw", self.raw & self.mask)

    @property
    def value(self) -> int:
        return self.raw

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1

    # Any arithmetic operations must be done with identical width.
    # This is to ensure no stupid mistake, with an inconveneient tradeoff.
    @staticmethod
    def __check_width_equivalence(this: "UInt", other: "UInt") -> None:
        if this.width != other.width:
            raise ValueError(
                f"UInt bit width does not match, got {this.width} and {other.width} bits."
            )

    def __add__(self, other: "UInt") -> "UInt":
        UInt.__check_width_equivalence(self, other)
        return UInt(self.width, self.value + other.value)

    def __sub__(self, other: "UInt") -> "UInt":
        UInt.__check_width_equivalence(self, other)
        return UInt(self.width, self.value - other.value)

    def __eq__(self, other):
        return isinstance(other, UInt) and self.value == other.value

    def __str__(self) -> str:
        return f"{self.value}<{self.width}>"

    def __repr__(self) -> str:
        return str(self)


class Opcode:
    SPIKE = UInt(5, 0)


@dataclass(frozen=True)
class Coordinate:
    x: UInt
    y: UInt

    @classmethod
    def from_uint(cls, v: UInt, addr_width: int):
        if v.width != addr_width * 2:
            raise ValueError(
                f"UInt width is expected to be {addr_width * 2} bits for coordinate, "
                f"but got {v.width} bits instead"
            )

        extractor = BitFieldExtractor(v.value, 2 * addr_width)
        x = UInt(addr_width, extractor.next(addr_width))
        y = UInt(addr_width, extractor.next(addr_width))
        return cls(x, y)

    # LSB is x, packed as [y, x]
    def to_uint(self) -> UInt:
        return UInt(self.width, (self.y.value << self.x.width) + self.x.value)

    @property
    def width(self) -> int:
        return self.x.width + self.y.width


# Refer sNPU Architecture, 7. Event and Response
# Bit field for details.
@dataclass(frozen=True)
class ResponsePayloadFormat:
    WIDTH = 24

    payload_valid: bool = False
    response_code: UInt = field(default_factory=lambda: UInt(2))
    payload: UInt = field(default_factory=lambda: UInt(16))

    @classmethod
    def from_uint(cls, x: UInt):
        if x.width != cls.WIDTH:
            raise ValueError(
                f"UInt width is expected to be {cls.WIDTH} bits for response payload, "
                f"but got {x.width} bits instead"
            )

        extractor = BitFieldExtractor(x.value, ResponsePayloadFormat.WIDTH)
        _ = extractor.next(1)  # Type
        payload_valid = bool(extractor.next(1))
        response_code = UInt(2, extractor.next(2))
        _ = extractor.next(4)  # Reserved
        payload = UInt(16, extractor.next(16))

        return cls(payload_valid, response_code, payload)

    def __post_init__(self):
        if self.response_code.width != 2:
            raise ValueError("Response code width must be 2, according to the spec.")
        if self.payload.width != 16:
            raise ValueError("Payload width must be 16, according to the spec.")

    @property
    def width(self) -> int:
        return ResponsePayloadFormat.WIDTH


# Refer sNPU Architecture, 7. Event and Response
# Bit field for details.
@dataclass(frozen=True)
class EventPayloadFormat:
    WIDTH = 24

    event_type: UInt = field(default_factory=lambda: UInt(5))
    payload: UInt = field(default_factory=lambda: UInt(16))

    @classmethod
    def from_uint(cls, x: UInt):
        if x.width != cls.WIDTH:
            raise ValueError(
                "UInt width is expected to be 24 bits for event payload, "
                f"but got {x.width} bits instead"
            )

        extractor = BitFieldExtractor(x.value, EventPayloadFormat.WIDTH)
        _ = extractor.next(1)  # Type
        event_type = UInt(5, extractor.next(5))
        _ = extractor.next(2)  # Reserved
        payload = UInt(16, extractor.next(16))

        return cls(event_type, payload)

    def __post_init__(self):
        if self.event_type.width != 5:
            raise ValueError("Event type width must be 5, according to the spec.")
        if self.payload.width != 16:
            raise ValueError("Payload width must be 16, according to the spec.")

    @property
    def width(self) -> int:
        return EventPayloadFormat.WIDTH


@dataclass(frozen=True)
class Packet:
    source: Coordinate
    destination: Coordinate
    source_local: Coordinate
    dest_local: Coordinate
    timestamp: UInt
    format: EventPayloadFormat | ResponsePayloadFormat

    @classmethod
    def from_uint(
        cls,
        x: UInt,
        addr_width: int,
        local_width: int,
        timestamp_width: int,
        is_response: bool,
    ):
        # Both EventPayloadFOrmat and ResponsePayloadFormat share the same bit width,
        # so pick one of them.
        packet_bit_width = (
            2 * addr_width
            + 2 * local_width
            + timestamp_width
            + EventPayloadFormat.WIDTH
        )
        extractor = BitFieldExtractor(x.value, packet_bit_width)

        source = Coordinate.from_uint(
            UInt(2 * addr_width, extractor.next(2 * addr_width)), addr_width
        )
        destination = Coordinate.from_uint(
            UInt(2 * addr_width, extractor.next(2 * addr_width)), addr_width
        )
        source_local = Coordinate.from_uint(
            UInt(2 * local_width, extractor.next(2 * local_width)), local_width
        )
        dest_local = Coordinate.from_uint(
            UInt(2 * local_width, extractor.next(2 * local_width)), local_width
        )
        timestamp = UInt(timestamp_width, extractor.next(timestamp_width))
        format_as_uint = UInt(
            EventPayloadFormat.WIDTH, extractor.next(EventPayloadFormat.WIDTH)
        )

        format = (
            ResponsePayloadFormat.from_uint(format_as_uint)
            if is_response
            else EventPayloadFormat.from_uint(format_as_uint)
        )

        return cls(
            source,
            destination,
            source_local,
            dest_local,
            timestamp,
            format,
        )

    @property
    def width(self) -> int:
        return (
            self.source.width
            + self.destination.width
            + self.source_local.width
            + self.dest_local.width
            + self.timestamp.width
            + EventPayloadFormat.WIDTH
        )
