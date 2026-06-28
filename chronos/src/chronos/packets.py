from dataclasses import dataclass, field
from typing import Self

from chronos.hardware_types import UInt, HasWidth
from chronos.utils import BitFieldExtractor


class Opcode:
    SPIKE = UInt(5, 0)


@dataclass(frozen=True)
class Coordinate(HasWidth):
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
        x = extractor.next(addr_width)
        y = extractor.next(addr_width)
        return cls(x, y)

    # LSB is x, packed as [y, x]
    def to_uint(self) -> UInt:
        return UInt(self.width, (self.y.value << self.x.width) + self.x.value)

    @property
    def width(self) -> int:
        return self.x.width + self.y.width

    @classmethod
    def randomized(cls, width: int) -> Self:
        uint_x = UInt.randomized(width)
        uint_y = UInt.randomized(width)
        return cls(uint_x, uint_y)


@dataclass(frozen=True)
class NeuronLocation(HasWidth):
    position: Coordinate
    local_position: Coordinate

    def to_uint(self) -> UInt:
        pos_as_uint = self.position.to_uint()
        local_pos_as_uint = self.local_position.to_uint()
        concated_width = self.position.width + self.local_position.width

        return UInt(
            concated_width,
            local_pos_as_uint.value << self.position.width + pos_as_uint.value,
        )

    @property
    def width(self) -> int:
        return self.position.width + self.local_position.width

    @classmethod
    def randomized(cls, width: int) -> Self:
        pos = Coordinate.randomized(width)
        local_pos = Coordinate.randomized(1)
        return cls(pos, local_pos)


# Refer sNPU Architecture, 7. Event and Response
# Bit field for details.
@dataclass(frozen=True)
class ResponsePayloadFormat(HasWidth):
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
        payload_valid = bool(extractor.next(1).value)
        response_code = extractor.next(2)
        _ = extractor.next(4)  # Reserved
        payload = extractor.next(16)

        return cls(payload_valid, response_code, payload)

    def __post_init__(self):
        if self.response_code.width != 2:
            raise ValueError("Response code width must be 2, according to the spec.")
        if self.payload.width != 16:
            raise ValueError("Payload width must be 16, according to the spec.")

    @property
    def width(self) -> int:
        return ResponsePayloadFormat.WIDTH

    @classmethod
    def randomized(cls, width: int) -> Self:
        del width  # Both field has fixed width according to sNPU Architecture.

        resp_uint = UInt.randomized(2)
        payload_uint = UInt.randomized(16)
        return cls(False, resp_uint, payload_uint)


# Refer sNPU Architecture, 7. Event and Response
# Bit field for details.
@dataclass(frozen=True)
class EventPayloadFormat(HasWidth):
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
        event_type = extractor.next(5)
        _ = extractor.next(2)  # Reserved
        payload = extractor.next(16)

        return cls(event_type, payload)

    def __post_init__(self):
        if self.event_type.width != 5:
            raise ValueError("Event type width must be 5, according to the spec.")
        if self.payload.width != 16:
            raise ValueError("Payload width must be 16, according to the spec.")

    @property
    def width(self) -> int:
        return EventPayloadFormat.WIDTH

    @classmethod
    def randomized(cls, width: int) -> Self:
        del width  # Both field has fixed width according to sNPU Architecture.

        event_type = UInt.randomized(5)
        payload_uint = UInt.randomized(16)
        return cls(event_type, payload_uint)


@dataclass(frozen=True)
class Packet(HasWidth):
    source: Coordinate
    destination: Coordinate
    source_local: Coordinate
    dest_local: Coordinate
    timestamp: UInt
    format: EventPayloadFormat | ResponsePayloadFormat

    @classmethod
    # Creates spike packet in a simple way. Assumes 8-bit timestamp.
    # Both location follows format: (x, y, local_x, local_y).
    # NOTE: This doesn't check overflow.
    def create_spike_packet(
        cls,
        addr_width: int,
        source_loc: tuple[int, int, int, int],
        dest_loc: tuple[int, int, int, int],
        timestamp: int,
    ) -> "Packet":
        src_loc = Coordinate(
            UInt(addr_width, source_loc[0]),
            UInt(addr_width, source_loc[1]),
        )
        src_local_loc = Coordinate(
            UInt(addr_width, source_loc[2]), UInt(addr_width, source_loc[3])
        )
        dst_loc = Coordinate(
            UInt(addr_width, dest_loc[0]), UInt(addr_width, dest_loc[1])
        )
        dst_local_loc = Coordinate(
            UInt(addr_width, dest_loc[2]), UInt(addr_width, dest_loc[3])
        )
        stamp = UInt(8, timestamp)
        format = EventPayloadFormat(Opcode.SPIKE)

        return cls(src_loc, dst_loc, src_local_loc, dst_local_loc, stamp, format)

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

        source = Coordinate.from_uint(extractor.next(2 * addr_width), addr_width)
        destination = Coordinate.from_uint(extractor.next(2 * addr_width), addr_width)
        src_local = Coordinate.from_uint(extractor.next(2 * local_width), local_width)
        dest_local = Coordinate.from_uint(extractor.next(2 * local_width), local_width)
        timestamp = extractor.next(timestamp_width)
        format_as_uint = extractor.next(EventPayloadFormat.WIDTH)

        format = (
            ResponsePayloadFormat.from_uint(format_as_uint)
            if is_response
            else EventPayloadFormat.from_uint(format_as_uint)
        )

        return cls(
            source,
            destination,
            src_local,
            dest_local,
            timestamp,
            format,
        )

    @property
    def source_location(self) -> NeuronLocation:
        return NeuronLocation(self.source, self.source_local)

    @property
    def destination_location(self) -> NeuronLocation:
        return NeuronLocation(self.destination, self.dest_local)

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
