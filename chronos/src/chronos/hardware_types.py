from dataclasses import dataclass, field


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

    def signed_raw(self) -> int:
        return self.__to_signed(self.raw)

    def to_float(self) -> float:
        return self.signed_raw() / self.SCALE

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
class UInt:
    __width: int
    __raw: int

    def __init__(self, width: int, raw: int = 0):
        assert width > 0
        self.__width = width
        self.__raw = raw & self.__mask()

    @property
    def value(self) -> int:
        return self.__raw

    def __mask(self) -> int:
        return (1 << self.__width) - 1

    def __add__(self, other):
        return UInt(self.value + other.value)

    def __sub__(self, other):
        return UInt(self.value - other.value)

    def __eq__(self, other):
        return isinstance(other, UInt) and self.value == other.value

    def __str__(self) -> str:
        return f"{self.value}<{self.__width}>"

    def __repr__(self) -> str:
        return str(self)

class BoundedMap:
    __capacity: int
    __items: dict[int, Q4_12]  # neuron id -> weight

    def __init__(self, capacity=4):
        assert capacity > 0
        self.__capacity = capacity
        self.__items = {}

    @property
    def size(self) -> int:
        return len(self.__items)

    @property
    def capacity(self) -> int:
        return self.__capacity

    def put(self, neuron_id: int, weight: Q4_12) -> bool:
        if self.size >= self.__capacity:
            return False
        self.__items[neuron_id] = weight
        return True

    def get(self, neuron_id: int) -> tuple[bool, Q4_12 | None]:
        if neuron_id not in self.__items:
            return (False, None)
        return (True, self.__items[neuron_id])

    def reset(self):
        self.__items = {}


@dataclass(frozen=True)
class ResponsePacket:
    payload_valid: bool = False
    response_code: UInt = field(default_factory=lambda: UInt(2))
    payload: UInt = field(default_factory=lambda: UInt(16))

    def __post_init__(self):
        if self.response_code.width != 2:
            raise ValueError("Response code width must be 2, according to the spec.")
        if self.payload.width != 16:
            raise ValueError("Payload width must be 16, according to the spec.")


@dataclass(frozen=True)
class EventPacket:
    event_type: UInt = field(default_factory=lambda: UInt(5))
    payload: UInt = field(default_factory=lambda: UInt(16))

    def __post_init__(self):
        if self.event_type.width != 5:
            raise ValueError("Event type width must be 5, according to the spec.")
        if self.payload.width != 16:
            raise ValueError("Payload width must be 16, according to the spec.")
