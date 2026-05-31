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

class BoundedMap:
    __capacity : int
    __items: dict[int, Q4_12] # neuron id -> weight

    def __init__(self, capacity = 4):
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

    def get(self, neuron_id: int) -> tuple[bool, Q4_12]:
        if neuron_id not in self.__items:
            return (False, None)
        return (True, self.__items[neuron_id])

    def reset(self):
        self.__items = {}
