from dataclasses import dataclass
from chronos.hardware_types import Q4_12


@dataclass
class NeuronParameter:
    k1: int
    k2: int


class SecondOrderShiftDecay:
    @staticmethod
    def find_decay_shifts(v: float, k_min=1, k_max=31) -> tuple[int, int]:
        assert 0 < v <= 1

        best_error = float("inf")
        best_k1, best_k2 = 0, 0

        for k1 in range(k_min, k_max + 1):
            for k2 in range(k1, k_max + 1):
                approx_v = 1.0 - (2.0**-k1) - (2.0**-k2)
                error = abs(v - approx_v)

                if error < best_error:
                    best_error = error
                    best_k1 = k1
                    best_k2 = k2

        return (best_k1, best_k2)


class NeuronCore:
    __membrane_potential: Q4_12
    __next_membrane_potential: Q4_12

    __k1: int
    __k2: int

    def __init__(self, param: NeuronParameter):
        self.__k1 = param.k1
        self.__k2 = param.k2
        self.reset()

    @property
    def membrane_potential(self) -> Q4_12:
        return self.__membrane_potential

    # This overrides current membrane potential. Use with extra care.
    def set_membrane_potential(self, v: Q4_12):
        self.__membrane_potential = v

    def reset(self):
        self.__membrane_potential = Q4_12(0)
        self.__next_membrane_potential = Q4_12(0)

    def update(self):
        self.__next_membrane_potential = (
            self.__membrane_potential
            - (self.__membrane_potential >> self.__k1)
            - (self.__membrane_potential >> self.__k2)
        )

    def commit(self):
        self.__membrane_potential = self.__next_membrane_potential
