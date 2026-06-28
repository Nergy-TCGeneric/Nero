from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import randint
from typing import Self


class HasWidth(ABC):
    @property
    @abstractmethod
    def width(self) -> int:
        pass

    @classmethod
    @abstractmethod
    def randomized(cls, width: int) -> Self:
        pass


class Q4_12(HasWidth):
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

    @property
    def width(self) -> int:
        return self.WIDTH

    @classmethod
    def from_float(cls, x: float):
        return cls(round(x * cls.SCALE))

    @classmethod
    def from_uint(cls, x: "UInt"):
        return cls(x.value)

    @classmethod
    def randomized(cls, width: int) -> Self:
        return cls(randint(0, (1 << cls.WIDTH) - 1))

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
class UInt(HasWidth):
    bit_width: int
    raw: int = 0

    def __post_init__(self):
        if self.bit_width <= 0:
            raise ValueError("UInt width must be positive.")
        object.__setattr__(self, "raw", self.raw & self.mask)

    @property
    def width(self) -> int:
        return self.bit_width

    @property
    def value(self) -> int:
        return self.raw

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1

    @classmethod
    def randomized(cls, width: int) -> Self:
        return cls(width, randint(0, (1 << width) - 1))

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

    def __lt__(self, other):
        return isinstance(other, UInt) and self.value < other.value

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        return not self < other and not self == other

    def __ge__(self, other):
        return not self < other

    def __str__(self) -> str:
        return f"{self.value}<{self.width}>"

    def __repr__(self) -> str:
        return str(self)
