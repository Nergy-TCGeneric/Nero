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

    def __str__(self) -> str:
        return f"{self.to_float()}"

    def __repr__(self) -> str:
        return str(self)
