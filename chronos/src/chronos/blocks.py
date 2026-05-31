from dataclasses import dataclass
from chronos.hardware_types import Q4_12, BoundedMap, EventPacket, UInt


@dataclass(frozen=True)
class NeuronParameter:
    k1: int
    k2: int
    weight_capacity: int
    spike_threshold: Q4_12


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


class MembranePotentialUpdater:
    __membrane_potential: Q4_12
    __next_membrane_potential: Q4_12

    __k1: int
    __k2: int

    __weight_entry: BoundedMap
    __enqueued_spike_id: int = -1
    __spike_threshold: Q4_12

    __outbound_spike_packet: EventPacket | None
    __next_outbound_spike_packet: EventPacket | None

    def __init__(self, param: NeuronParameter):
        self.__k1 = param.k1
        self.__k2 = param.k2
        self.__weight_entry = BoundedMap(param.weight_capacity)
        self.__spike_threshold = param.spike_threshold
        self.__outbound_spike_packet = None
        self.__next_outbound_spike_packet = None

    @property
    def membrane_potential(self) -> Q4_12:
        return self.__membrane_potential

    @property
    def outgoing_packet(self) -> EventPacket | None:
        return self.__outbound_spike_packet

    def enqueue_spike(self, neuron_id: int) -> bool:
        if self.__enqueued_spike_id == -1:
            self.__enqueued_spike_id = neuron_id
            return True
        return False

    def add_synaptic_weight_entry(self, neuron_id: int, weight: Q4_12) -> bool:
        return self.__weight_entry.put(neuron_id, weight)

    def clear_synaptic_weight_entries(self):
        self.__weight_entry.reset()

    # This overrides current membrane potential. Use with extra care.
    def set_membrane_potential(self, v: Q4_12):
        self.__membrane_potential = v

    def reset(self):
        self.__membrane_potential = Q4_12(0)
        self.__next_membrane_potential = Q4_12(0)

    def update(self):
        self.__next_outbound_spike_packet = None
        decayed = (
            self.__membrane_potential
            - (self.__membrane_potential >> self.__k1)
            - (self.__membrane_potential >> self.__k2)
        )

        weight_addition = Q4_12(0)
        if self.__enqueued_spike_id != -1:
            _, weight_addition = self.__weight_entry.get(self.__enqueued_spike_id)
            self.__enqueued_spike_id = -1

        # TODO: Need spike fanout table later.
        summed = decayed + weight_addition
        if summed >= self.__spike_threshold:
            self.__next_membrane_potential = Q4_12(0)
            self.__next_outbound_spike_packet = EventPacket(UInt(5, 0), UInt(16, 0))
        else:
            self.__next_membrane_potential = decayed + weight_addition

    def commit(self):
        self.__membrane_potential = self.__next_membrane_potential
        self.__outbound_spike_packet = self.__next_outbound_spike_packet


class NeuronCore:
    __potential_updater: MembranePotentialUpdater

    def __init__(self, param: NeuronParameter):
        self.__potential_updater = MembranePotentialUpdater(param)

    def reset(self):
        self.__potential_updater.reset()

    def update(self):
        self.__potential_updater.update()

    def commit(self):
        self.__potential_updater.commit()
