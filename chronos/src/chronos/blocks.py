from dataclasses import dataclass
from chronos.hardware_types import Q4_12, EventPacket, UInt


# This is a simple dual-port, write-first memory.
# That is, when written to specific memory address
# the memory returns a new 'written' data.
#
# Refer: AMD Xilinx UG473, 7 Series FPGAs Memory Resources User Guide
class BoundedRAM:
    __capacity: int
    __bit_width: int
    __items: list[UInt]

    __data_to_put_next_cycle: UInt
    __next_address: int
    __should_put_next_cycle: bool

    __output: UInt

    def __init__(self, bit_width: int, capacity: int = 4):
        if capacity <= 0:
            raise ValueError(
                f"Only non-negative capacity is valid for RAM, but got : {capacity}"
            )

        self.__capacity = capacity
        self.__bit_width = bit_width
        self.__items = [
            UInt(bit_width) for _ in range(capacity)
        ]  # TODO: Initialize with random UInt later
        self.__should_put_next_cycle = False

    @property
    def capacity(self) -> int:
        return self.__capacity

    @property
    def output(self) -> UInt:
        return self.__output

    def __ensure_identical_bit_width(self, incoming_data: UInt):
        if incoming_data.width != self.__bit_width:
            raise ValueError(
                f"Incoming UInt bit width, {incoming_data.width} bits does not match"
                f" with declared RAM bit width: {self.__bit_width} bits."
            )

        if len(self.__items) == 0:
            return

        for uint in self.__items:
            if self.__bit_width != uint.width:
                raise ValueError(
                    f"UInt bit widths are different. RAM bit width is {self.__bit_width} bits,"
                    f" but contains {uint.width} bits data."
                )

    def put(self, addr: int, data: UInt):
        self.__ensure_identical_bit_width(data)
        if addr < 0 or addr >= self.capacity:
            raise ValueError(f"Out of bound access for address : {addr}")

        self.__data_to_put_next_cycle = data
        self.__next_address = addr
        self.__should_put_next_cycle = True

    def get(self, addr: int):
        if addr < 0 or addr >= self.capacity:
            raise ValueError(f"Out of bound access for address : {addr}")

        # Both operations are mutually exclusive. Last request wins.
        if self.__should_put_next_cycle is True:
            self.__should_put_next_cycle = False
        self.__next_address = addr

    # Handled by get() and put() instead.
    def update(self):
        pass

    def commit(self):
        if self.__should_put_next_cycle:
            self.__items[self.__next_address] = self.__data_to_put_next_cycle
        self.__output = self.__items[self.__next_address]


# TODO: Can be implemented with BoundedRAM later.
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

    __fanout_table: list[UInt]
    __outbound_spike_packet: EventPacket | None
    __next_outbound_spike_packet: EventPacket | None

    def __init__(self, param: NeuronParameter):
        self.__k1 = param.k1
        self.__k2 = param.k2
        self.__weight_entry = BoundedMap(param.weight_capacity)
        self.__spike_threshold = param.spike_threshold
        self.__outbound_spike_packet = None
        self.__next_outbound_spike_packet = None
        self.__fanout_table = []

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
# TODO: Can be implemented with BoundedRAM later.
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

