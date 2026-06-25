from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import IntEnum
from random import randint

from chronos.hardware_types import Q4_12, UInt
from chronos.packets import (
    Coordinate,
    EventPayloadFormat,
    Opcode,
    Packet,
    NeuronLocation,
)
from chronos.utils import BitFieldExtractor


class SequentialModule(ABC):
    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def reset(self):
        pass


class Counter(SequentialModule):
    __bit_width: int

    __next_count: UInt
    __count: UInt

    def __init__(self, bit_width: int):
        if bit_width <= 0:
            raise ValueError(
                f"Counter bit width must be greater than 0, got {bit_width}"
            )

        self.__bit_width = bit_width
        self.reset()

    @property
    def value(self) -> UInt:
        return self.__count

    def update(self):
        self.__next_count = self.__count + UInt(self.__bit_width, 1)

    def commit(self):
        self.__count = self.__next_count

    def reset(self):
        self.__next_count = UInt(self.__bit_width)
        self.__count = UInt(self.__bit_width)


# This is a simple dual-port, write-first memory.
# That is, when written to specific memory address
# the memory returns a new 'written' data.
#
# Refer: AMD Xilinx UG473, 7 Series FPGAs Memory Resources User Guide
class BoundedRAM(SequentialModule):
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

        if bit_width <= 0:
            raise ValueError(
                f"Bit width for BoundedRAM must be positive, got {bit_width}."
            )

        self.__capacity = capacity
        self.__bit_width = bit_width
        self.__items = [
            UInt(bit_width, randint(0, 2**bit_width - 1)) for _ in range(capacity)
        ]
        self.__should_put_next_cycle = False
        self.__next_address = 0
        self.__output = self.__items[self.__next_address]

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

    def reset(self):
        # Memory itself cannot be reset,
        pass


# A chisel queue with default option.
class BoundedQueue(SequentialModule):
    # Update-dependent values
    __next_head: int
    __head: int

    __next_tail: int
    __tail: int

    __next_maybe_full: bool
    __maybe_full: bool

    # Runtime values
    __capacity: int
    __items: list[UInt]

    __is_empty: bool
    __is_full: bool

    __is_pushing: bool
    __is_popping: bool

    def __init__(self, capacity: int, bit_width: int):
        if capacity <= 0:
            raise ValueError(
                f"Only non-negative capacity is valid for queue, but got : {capacity}"
            )

        self.__capacity = capacity

        # randint() can produce float when bit_width is less than 0.
        effective_bit_width = max(bit_width, 0)
        self.__items = [
            UInt(bit_width, randint(0, 2**effective_bit_width - 1))
        ] * capacity

        self.reset()

    @property
    def capacity(self) -> int:
        return self.__capacity

    @property
    def size(self) -> int:
        ptr_diff = abs(self.__head - self.__tail)
        if self.__head == self.__tail:
            return self.__capacity if self.__maybe_full else 0
        else:
            return (
                (self.__capacity + ptr_diff) % self.__capacity
                if self.__tail > self.__head
                else ptr_diff
            )

    @property
    def empty(self) -> bool:
        return self.__is_empty

    @property
    def full(self) -> bool:
        return self.__is_full

    def __ensure_identical_bit_width(self, incoming: UInt):
        for uint in self.__items:
            if incoming.width != uint.width:
                raise ValueError(
                    f"UInt bit widths are different. Expected {uint.width} but found {incoming.width}."
                )

    def push(self, data: UInt) -> bool:
        if self.__is_full:
            return False

        self.__ensure_identical_bit_width(data)

        self.__next_head = (self.__head + 1) % self.__capacity
        self.__items[self.__head] = data
        self.__is_pushing = True

        self.__update_signals()

        return True

    def pop(self) -> tuple[bool, UInt]:
        item_at_tail = self.__items[self.__tail]
        if self.__is_empty:
            return (False, item_at_tail)  # Value is useless when empty

        self.__next_tail = (self.__tail + 1) % self.__capacity
        self.__is_popping = True

        self.__update_signals()

        return (True, item_at_tail)

    def update(self):
        pass

    def commit(self):
        self.__head = self.__next_head
        self.__tail = self.__next_tail
        self.__maybe_full = self.__next_maybe_full
        self.__is_pushing = False
        self.__is_popping = False

        self.__update_signals()

    # Chisel Queue's status signals like full/empty are combinatorial.
    def __update_signals(self):
        if self.__is_pushing != self.__is_popping:
            self.__next_maybe_full = self.__is_pushing
        ptr_match = self.__head == self.__tail

        self.__is_full = ptr_match & self.__maybe_full
        self.__is_empty = ptr_match & (not self.__maybe_full)

    def reset(self):
        self.__head = 0
        self.__next_head = 0
        self.__tail = 0
        self.__next_tail = 0
        self.__is_empty = False
        self.__is_full = False
        self.__is_pushing = False
        self.__is_popping = False
        self.__next_maybe_full = False
        self.__maybe_full = False

        self.__update_signals()


@dataclass(frozen=True)
class NeuronParameter:
    k1: int
    k2: int
    neuron_addr_width: int
    spike_threshold: Q4_12
    max_fanout_spike_capacity: int


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


class MembranePotentialUpdater(SequentialModule):
    class _States(IntEnum):
        DECAY = 0
        SPIKE_RECEIVED = 1

    # Sequential components
    __weight_entry: BoundedRAM

    # Runtime settings
    __k1: int
    __k2: int

    __enqueued_spike_loc: NeuronLocation | None
    __spike_threshold: Q4_12

    # Update-dependent values
    __membrane_potential: Q4_12
    __next_membrane_potential: Q4_12

    __state: _States
    __next_state: _States

    __should_fire_spike: bool
    __next_should_fire_spike: bool

    def __init__(self, param: NeuronParameter):
        self.__k1 = param.k1
        self.__k2 = param.k2
        self.__weight_entry = BoundedRAM(Q4_12.WIDTH, param.neuron_addr_width)
        self.__spike_threshold = param.spike_threshold
        self.__enqueued_spike_loc = None
        self.__should_fire_spike = False
        self.__next_should_fire_spike = False

        self.reset()

    @property
    def membrane_potential(self) -> Q4_12:
        return self.__membrane_potential

    @property
    def should_fire_spike(self) -> bool:
        return self.__should_fire_spike

    def enqueue_spike(self, source_loc: NeuronLocation) -> bool:
        if self.__enqueued_spike_loc is None:
            self.__enqueued_spike_loc = source_loc
            return True
        return False

    def add_synaptic_weight_entry(self, source_loc: NeuronLocation, weight: Q4_12):
        self.__weight_entry.put(source_loc.to_uint().value, weight.to_uint())

    def clear_synaptic_weight_entries(self):
        self.__weight_entry.reset()

    # This overrides current membrane potential. Use with extra care.
    def set_membrane_potential(self, v: Q4_12):
        self.__membrane_potential = v

    def reset(self):
        self.clear_synaptic_weight_entries()

        self.__state = MembranePotentialUpdater._States.DECAY
        self.__next_state = MembranePotentialUpdater._States.DECAY
        self.__membrane_potential = Q4_12(0)
        self.__next_membrane_potential = Q4_12(0)

    def update(self):
        self.__weight_entry.update()

        if self.__enqueued_spike_loc is not None:
            self.__weight_entry.get(self.__enqueued_spike_loc.to_uint().value)
            self.__next_state = MembranePotentialUpdater._States.SPIKE_RECEIVED
        else:
            self.__next_state = MembranePotentialUpdater._States.DECAY

        weight_addition = Q4_12(0)
        if self.__state == MembranePotentialUpdater._States.SPIKE_RECEIVED:
            weight_addition = Q4_12.from_uint(self.__weight_entry.output)

        decayed = (
            self.__membrane_potential
            - (self.__membrane_potential >> self.__k1)
            - (self.__membrane_potential >> self.__k2)
        )

        summed = decayed + weight_addition
        if summed >= self.__spike_threshold:
            self.__next_membrane_potential = Q4_12(0)
            self.__next_should_fire_spike = True
        else:
            self.__next_membrane_potential = summed
            self.__next_should_fire_spike = False

    def commit(self):
        self.__weight_entry.commit()

        self.__membrane_potential = self.__next_membrane_potential
        self.__state = self.__next_state
        self.__should_fire_spike = self.__next_should_fire_spike
        self.__enqueued_spike_loc = None


class PacketSequencer(SequentialModule):
    # TODO: Stub value, should be configruable via NeuronParameter.
    TIMESTAMP_WIDTH = 8

    class _States(IntEnum):
        IDLE = 0
        SEQUENCING = 1

    # Sequential components
    __memory: BoundedRAM
    __time_recorder: Counter

    # Runtime settings
    __capacity: int
    __position: Coordinate
    __local_position: Coordinate

    # Update-dependent values
    __next_entry_count: int
    __entry_count: int

    __next_head: int
    __head: int

    __next_state: _States
    __state: _States

    __outgoing_packet: Packet

    # dest_addr_width here is neuron address width + local address width.
    def __init__(self, capacity: int, loc: NeuronLocation):

        self.__position = loc.position
        self.__local_position = loc.local_position

        # Since source addr width = dest addr width, we can infer
        # required bit width here.
        dest_addr_width = loc.position.width + loc.local_position.width
        self.__capacity = capacity
        self.__memory = BoundedRAM(dest_addr_width, capacity)
        self.__time_recorder = Counter(PacketSequencer.TIMESTAMP_WIDTH)
        self.reset()

    @property
    def capacity(self) -> int:
        return self.__capacity

    @property
    def size(self) -> int:
        return self.__entry_count

    @property
    def is_busy(self) -> bool:
        return self.__state == PacketSequencer._States.SEQUENCING

    @property
    def outgoing_packet(self) -> Packet:
        return self.__outgoing_packet

    def add_destination_entry(self, dest: NeuronLocation):
        if self.__entry_count >= self.__capacity:
            raise ValueError(
                f"Buffer overflow occured: entry count {self.__entry_count} exceeded capacity {self.__capacity}"
            )

        concated_bit_width = dest.position.width + dest.local_position.width
        concated = UInt(
            concated_bit_width,
            (dest.local_position.to_uint().value << dest.position.width)
            + dest.position.to_uint().value,
        )

        self.__memory.put(self.__entry_count, concated)
        self.__next_entry_count = self.__entry_count + 1

    def enqueue_sequencing_request(self) -> bool:
        if self.__state == PacketSequencer._States.IDLE:
            self.__next_state = PacketSequencer._States.SEQUENCING
            self.__next_head = 0
            return True

        return False

    def update(self):
        self.__memory.update()
        self.__time_recorder.update()

        end_of_sequence = self.__head >= self.__entry_count - 1

        # Advance the head, if it's sequencing.
        if self.__state == PacketSequencer._States.SEQUENCING:
            self.__memory.get(self.__head)
            if end_of_sequence:
                self.__next_head = 0
                self.__next_state = PacketSequencer._States.IDLE
            else:
                self.__next_head = self.__head + 1
                self.__next_state = PacketSequencer._States.SEQUENCING

    def commit(self):
        self.__memory.commit()
        self.__time_recorder.commit()

        self.__entry_count = self.__next_entry_count
        self.__head = self.__next_head
        self.__state = self.__next_state

        # Extracting the coordinate
        dest_as_uint = self.__memory.output
        extractor = BitFieldExtractor(dest_as_uint.value, dest_as_uint.width)
        destination = Coordinate.from_uint(
            extractor.next(self.__position.width),
            self.__position.width // 2,
        )
        local_dest = Coordinate.from_uint(
            extractor.next(self.__local_position.width),
            self.__local_position.width // 2,
        )

        # According to sNPU Architecture, spike opcode is 5'b00000.
        # Payload is don't care, so use it as is.
        event_format = EventPayloadFormat(Opcode.SPIKE)

        self.__outgoing_packet = Packet(
            self.__position,
            destination,
            self.__local_position,
            local_dest,
            self.__time_recorder.value,
            event_format,
        )

    def reset(self):
        self.__memory.reset()
        self.__time_recorder.reset()

        self.__next_entry_count = 0
        self.__entry_count = 0
        self.__next_head = 0
        self.__head = 0
        self.__next_state = PacketSequencer._States.IDLE
        self.__state = PacketSequencer._States.IDLE


class NeuronCore(SequentialModule):
    __potential_updater: MembranePotentialUpdater
    __sequencer: PacketSequencer

    @property
    def outgoing_packet(self) -> Packet:
        return self.__sequencer.outgoing_packet

    @property
    def is_firing_packet(self) -> bool:
        return self.__sequencer.is_busy

    def __init__(self, loc: NeuronLocation, param: NeuronParameter):
        self.__potential_updater = MembranePotentialUpdater(param)
        self.__sequencer = PacketSequencer(param.max_fanout_spike_capacity, loc)

    def enqueue_packet(self, spike_packet: Packet) -> bool:
        incoming_loc = NeuronLocation(spike_packet.source, spike_packet.source_local)
        return self.__potential_updater.enqueue_spike(incoming_loc)

    def add_synaptic_weight_entry(self, source_loc: NeuronLocation, weight: Q4_12):
        self.__potential_updater.add_synaptic_weight_entry(source_loc, weight)

    def clear_synaptic_weight_entries(self):
        self.__potential_updater.clear_synaptic_weight_entries()

    def add_destination_entry(self, dest: NeuronLocation):
        self.__sequencer.add_destination_entry(dest)

    def reset(self):
        self.__potential_updater.reset()
        self.__sequencer.reset()

    # TODO: Should emulate stall behaviour if there's a pending sequencing request.
    def update(self):
        self.__potential_updater.update()
        if self.__potential_updater.should_fire_spike:
            self.__sequencer.enqueue_sequencing_request()
        self.__sequencer.update()

    def commit(self):
        self.__potential_updater.commit()
        self.__sequencer.commit()


# A direction, encoded with priority.
class Direction(IntEnum):
    EAST = 0
    WEST = 1
    NORTH = 2
    SOUTH = 3
    LOCAL0 = 4
    LOCAL1 = 5
    LOCAL2 = 6
    LOCAL3 = 7

    @classmethod
    def cardinal_directions(cls) -> set["Direction"]:
        return {cls.EAST, cls.WEST, cls.NORTH, cls.SOUTH}

    @classmethod
    def local_directions(cls) -> set["Direction"]:
        return {cls.LOCAL0, cls.LOCAL1, cls.LOCAL2, cls.LOCAL3}


# This is a combinatorial sub-block.
class Decoder:
    __router_loc: Coordinate

    def __init__(self, router_loc: Coordinate):
        self.__router_loc = router_loc

    def decode(self, dest_loc: NeuronLocation) -> set[Direction]:
        available = set[Direction]()

        dest_neuron_loc = dest_loc.position
        dest_local_loc = dest_loc.local_position
        toward_local = dest_neuron_loc == self.__router_loc

        # TODO: Assumes 4 neurons attached to a router,
        # i.e, local address spans from (0, 0) to (1, 1).
        if toward_local:
            if dest_local_loc.x == UInt(
                dest_local_loc.width, 0
            ) and dest_local_loc.y == UInt(dest_local_loc.width, 0):
                available.add(Direction.LOCAL0)
            elif dest_local_loc.x == UInt(
                dest_local_loc.width, 0
            ) and dest_local_loc.y == UInt(dest_local_loc.width, 1):
                available.add(Direction.LOCAL1)
            elif dest_local_loc.x == UInt(
                dest_local_loc.width, 1
            ) and dest_local_loc.y == UInt(dest_local_loc.width, 0):
                available.add(Direction.LOCAL2)
            elif dest_local_loc.x == UInt(
                dest_local_loc.width, 1
            ) and dest_local_loc.y == UInt(dest_local_loc.width, 1):
                available.add(Direction.LOCAL3)
        else:
            if self.__router_loc.x < dest_neuron_loc.x:
                available.add(Direction.EAST)
            elif self.__router_loc.x > dest_neuron_loc.x:
                available.add(Direction.WEST)
            if self.__router_loc.y < dest_neuron_loc.y:
                available.add(Direction.NORTH)
            elif self.__router_loc.y > dest_neuron_loc.y:
                available.add(Direction.SOUTH)

        return available


# Arbiter is a mix of combinatorial part and
# sequential one(mask register). Grant is
# computed immediately as soon as request
# or mask was changed.
class RoundRobinArbiter(SequentialModule):
    __grant: Direction | None

    __mask: Direction | None
    __next_mask: Direction | None

    __pending_requests: set[Direction]

    def __init__(self):
        self.reset()

    @property
    def grant(self) -> Direction | None:
        return self.__grant

    def reset(self):
        self.__grant = None
        self.__pending_requests = set()
        self.__mask = None
        self.__next_mask = None

    def put_request_from_direction(self, direction: Direction) -> bool:
        if direction in self.__pending_requests:
            return False

        self.__pending_requests.add(direction)
        self.__update_grant()
        return True

    def __update_grant(self):
        if self.__mask is None:
            self.__grant = min(self.__pending_requests, default=None)
        else:
            self.__grant = min(
                (req for req in self.__pending_requests if req > self.__mask),
                default=min(self.__pending_requests, default=None),
            )

    def update(self):
        # Whole comparison is based on their priority.
        if self.__mask is None:
            self.__next_mask = min(self.__pending_requests, default=None)
        else:
            # Wrap to lowest one if none of requests can be granted with this state.
            self.__next_mask = min(
                (req for req in self.__pending_requests if req > self.__mask),
                default=min(self.__pending_requests, default=None),
            )

    def commit(self):
        self.__mask = self.__next_mask
        self.__pending_requests = set()
        self.__update_grant()


# The flow is fully combinatorial, but arbiter changes its
# state throughout the time. To maintain hierarchy I marked
# crossbar as a SequentialModule as well.
class Crossbar8x8(SequentialModule):
    __decoders: list[Decoder]
    __arbiters: list[RoundRobinArbiter]

    __inbound_packets: list[Packet | None]
    __outbound_packets: list[Packet | None]

    __requests: set[Direction]
    __readys: set[Direction]

    __transacted_map: dict[Direction, Direction]

    def __init__(self, router_loc: Coordinate):
        self.__decoders = [Decoder(router_loc) for _ in Direction]
        self.__arbiters = [RoundRobinArbiter() for _ in Direction]

        self.__inbound_packets = [None for _ in Direction]
        self.__outbound_packets = [None for _ in Direction]

        self.__readys = set()
        self.__requests = set()

        self.reset()

    def get_outbound_packet_of(self, from_direction: Direction) -> Packet | None:
        return self.__outbound_packets[from_direction]

    def push_packet(self, packet: Packet, from_direction: Direction) -> bool:
        if from_direction in self.__requests:
            return False

        self.__requests.add(from_direction)
        self.__inbound_packets[from_direction] = packet
        self.__update_outbound_packet()
        return True

    def push_ready(self, from_direction: Direction) -> bool:
        self.__readys.add(from_direction)
        self.__update_outbound_packet()
        return True

    def __update_outbound_packet(self):
        granted_map: dict[Direction, Direction] = dict()
        decoded_map: dict[Direction, Direction] = dict()

        # Given packets from each ingress port, decode first
        for incoming_request in self.__requests:
            packet = self.__inbound_packets[incoming_request]
            assert packet is not None

            decoded_vector = self.__decoders[incoming_request].decode(
                packet.destination_location
            )
            assert len(decoded_vector) > 0

            # Pick up the first one, based on priority.
            decoded = min(decoded_vector)
            self.__arbiters[decoded].put_request_from_direction(incoming_request)
            decoded_map[incoming_request] = decoded

        # And from arbiters, use grant to gate upstream ready.
        # Iterating ready set is enough as grant without ready
        # is effectively equivalent to "Don't pass".
        for incoming_ready in self.__readys:
            granted = self.__arbiters[incoming_ready].grant

            if granted is not None:
                granted_map[incoming_ready] = granted

        # From requester's perspective (since they cannot be withdrawn)
        # if they got a corresponding grant, forward their packet to
        # specified destination.
        for requester_dir, decoded_dir in decoded_map.items():
            if decoded_dir not in granted_map:
                continue
            if granted_map[decoded_dir] != requester_dir:
                continue

            self.__transacted_map[decoded_dir] = requester_dir
            self.__outbound_packets[decoded_dir] = self.__inbound_packets[requester_dir]

    def reset(self):
        for arbiter in self.__arbiters:
            arbiter.reset()

        self.__transacted_map = dict()

    def update(self):
        for arbiter in self.__arbiters:
            arbiter.update()

    def commit(self):
        for arbiter in self.__arbiters:
            arbiter.commit()

        # Nullify every outgoing packets, effectively make them
        # start over. This is to emulate data being invalid
        # after successful VALID-READY transaction.
        for direction in Direction:
            # Drop corresponding VALID-READY.
            if direction in self.__transacted_map:
                granted_input = self.__transacted_map[direction]
                self.__readys.remove(direction)
                self.__requests.remove(granted_input)
            self.__outbound_packets[direction] = None

        self.__transacted_map = dict()


class Router(SequentialModule):
    def reset(self):
        pass

    def update(self):
        pass

    def commit(self):
        pass
