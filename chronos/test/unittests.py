from typing import cast
import unittest

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from chronos.blocks import (
    BoundedRAM,
    Counter,
    NeuronLocation,
    NeuronParameter,
    PacketSequencer,
    Decoder,
    Direction,
    RoundRobinArbiter,
    SecondOrderShiftDecay,
    MembranePotentialUpdater,
)
from chronos.hardware_types import Q4_12, UInt
from chronos.packets import EventPayloadFormat, Coordinate, Opcode


class ChronosQ4_12UnitTests(unittest.TestCase):
    def test_q4_12_integer_part_addition_works_as_expected(self):
        q1 = Q4_12.from_float(1.0)
        q2 = Q4_12.from_float(3.0)

        expected = Q4_12.from_float(4.0)
        self.assertEqual(q1 + q2, expected)

    def test_q4_12_integer_part_addition_with_negative_works_as_expected(self):
        q1 = Q4_12.from_float(1.0)
        q2 = Q4_12.from_float(-3.0)

        expected = Q4_12.from_float(-2.0)
        self.assertEqual(q1 + q2, expected)

    def test_q4_12_fraction_part_addition_works_as_expected(self):
        q1 = Q4_12.from_float(0.75)
        q2 = Q4_12.from_float(0.5)

        expected = Q4_12.from_float(1.25)
        self.assertEqual(q1 + q2, expected)

    def test_q4_12_fraction_part_addition_with_negative__works_as_expected(self):
        q1 = Q4_12.from_float(-0.75)
        q2 = Q4_12.from_float(0.5)

        expected = Q4_12.from_float(-0.25)
        self.assertEqual(q1 + q2, expected)

    def test_q4_12_integer_part_subtraction_works_as_expected(self):
        q1 = Q4_12.from_float(2.0)
        q2 = Q4_12.from_float(1.0)

        expected = Q4_12.from_float(1.0)
        self.assertEqual(q1 - q2, expected)

    def test_q4_12_fracation_part_subtraction_works_as_expected(self):
        q1 = Q4_12.from_float(0.5)
        q2 = Q4_12.from_float(0.125)

        expected = Q4_12.from_float(0.375)
        self.assertEqual(q1 - q2, expected)

    def test_q4_12_wraps_at_positive_max(self):
        # A maximum positive value for Q4.12, 0x7FFF
        q1 = Q4_12.from_float(7.999755859375)
        # A resolution of Q4.12
        q2 = Q4_12.from_float(0.000244140625)

        expected = Q4_12.from_float(-8)
        self.assertEqual(q1 + q2, expected)

    def test_q4_12_wraps_at_negative_min(self):
        # A minimum negative value for Q4.12, 0xFFFF
        q1 = Q4_12.from_float(-0.000244140625)
        q2 = Q4_12.from_float(0.000244140625)

        expected = Q4_12.from_float(0)
        self.assertEqual(q1 + q2, expected)


class ChronosUIntUnitTests(unittest.TestCase):
    def test_non_positive_width_uint_is_invalid(self):
        with self.assertRaises(ValueError):
            UInt(0)
        with self.assertRaises(ValueError):
            UInt(-1)

    def test_uint_addition_works_as_expected(self):
        u1 = UInt(4, 1)
        u2 = UInt(4, 2)
        expected = UInt(4, 3)

        self.assertEqual(u1 + u2, expected)

    def test_uint_addition_fails_with_different_widths(self):
        u1 = UInt(2, 1)
        u2 = UInt(3, 1)

        with self.assertRaises(ValueError):
            _ = u1 + u2

    def test_uint_subtraction_works_as_expected(self):
        u1 = UInt(4, 5)
        u2 = UInt(4, 4)
        expected = UInt(4, 1)

        self.assertEqual(u1 - u2, expected)

    def test_uint_subtraction_fails_with_different_widths(self):
        u1 = UInt(2, 1)
        u2 = UInt(3, 1)

        with self.assertRaises(ValueError):
            _ = u1 - u2

    def test_uint_wraps_as_expected_on_addition(self):
        u1 = UInt(4, 15)
        u2 = UInt(4, 2)
        expected = UInt(4, 1)

        self.assertEqual(u1 + u2, expected)

    def test_uint_wraps_as_expected_on_addition_with_longer_bits(self):
        u1 = UInt(64, 18446744073709551615)
        u2 = UInt(64, 2)
        expected = UInt(64, 1)

        self.assertEqual(u1 + u2, expected)

    def test_uint_wraps_as_expected_on_subtraction(self):
        u1 = UInt(4, 0)
        u2 = UInt(4, 1)
        expected = UInt(4, 15)

        self.assertEqual(u1 - u2, expected)

    def test_uint_wraps_as_expected_on_subtraction_with_longer_bits(self):
        u1 = UInt(64, 0)
        u2 = UInt(64, 1)
        expected = UInt(64, 18446744073709551615)

        self.assertEqual(u1 - u2, expected)


class ChronosBoundedRAMUnitTests(unittest.TestCase):
    def test_ram_raises_an_exception_on_non_positive_bit_width(self):
        with self.assertRaises(ValueError):
            BoundedRAM(0)
        with self.assertRaises(ValueError):
            BoundedRAM(-1)

    def test_ram_raises_an_exception_if_data_width_differs(self):
        ram = BoundedRAM(4)

        with self.assertRaises(ValueError):
            ram.put(0, UInt(2))

    def test_ram_raises_an_exception_if_capacity_is_not_positive(self):
        with self.assertRaises(ValueError):
            BoundedRAM(4, 0)
        with self.assertRaises(ValueError):
            BoundedRAM(4, -1)

    def test_ram_raises_an_exception_on_out_of_bounds_access_on_put(self):
        ram = BoundedRAM(4, 1)

        with self.assertRaises(ValueError):
            ram.put(2, UInt(4))

    def test_ram_raises_an_exception_on_out_of_bounds_access_on_get(self):
        ram = BoundedRAM(4, 1)

        with self.assertRaises(ValueError):
            ram.get(2)

    def test_ram_put_transaction_works_as_write_first_principle(self):
        ram = BoundedRAM(4)

        expected = UInt(4, 12)
        addr = 0

        ram.put(addr, expected)
        ram.update()
        ram.commit()

        # Memory is Write-first (or transparent-write),
        # so whenever write succeed, the output should be visible right away.
        self.assertEqual(expected, ram.output)

    def test_ram_put_overwrite_is_allowed(self):
        ram = BoundedRAM(4)

        initial_expected = UInt(4, 7)
        addr = 0

        ram.put(addr, initial_expected)
        ram.update()
        ram.commit()

        self.assertEqual(initial_expected, ram.output)

        overwritten_expected = UInt(4, 1)
        ram.put(addr, overwritten_expected)
        ram.update()
        ram.commit()

        self.assertEqual(overwritten_expected, ram.output)

    def test_ram_get_transaction_works_as_expected(self):
        ram = BoundedRAM(4)

        expected = UInt(4, 12)
        expected_2 = UInt(4, 7)
        addr = 0

        ram.put(addr, expected)
        ram.update()
        ram.commit()

        ram.put(addr + 1, expected_2)
        ram.update()
        ram.commit()

        ram.get(addr)
        ram.update()
        ram.commit()

        self.assertEqual(expected, ram.output)

        ram.get(addr + 1)
        ram.update()
        ram.commit()

        self.assertEqual(expected_2, ram.output)

    def test_last_request_to_ram_survives(self):
        ram = BoundedRAM(4)

        expected = UInt(4, 1)
        addr = 0

        ram.put(addr, UInt(4, 5))
        ram.put(addr, UInt(4, 7))
        ram.put(addr, expected)

        ram.update()
        ram.commit()

        self.assertEqual(expected, ram.output)


class ChronosBoundedQueueUnitTests(unittest.TestCase):
    def test_queue_rejects_non_positive_depth(self):
        pass

    def test_queue_rejects_incoming_data_with_different_bitwidth(self):
        pass

    def test_enqueue_operation_increases_queue_element_count(self):
        pass

    def test_enqueue_return_failure_if_queue_is_full(self):
        pass

    def test_dequeue_operation_decreases_queue_element_count(self):
        pass

    def test_dequeue_return_failiure_if_queue_is_empty(self):
        pass


class ChronosRouterBlockUnitTests(unittest.TestCase):
    def test_router_enqueue_becomes_visible_after_1_cycle(self):
        pass

    def test_router_dequeue_completes_after_1_cycle(self):
        pass

    def test_router_buffers_up_to_4_entries(self):
        pass

    def test_router_prefers_north_south_west_east_when_multiple_routes_exist(
        self,
    ):
        pass

    def test_router_stalls_when_downstream_router_is_not_ready(self):
        pass

    def test_router_always_routes_packet_in_a_way_reduces_manhattan_distance(self):
        pass

    def test_router_round_robin_arbiter_eventually_grants_all_contenders(self):
        pass

    def test_router_never_drops_packet(self):
        pass


class ChronosRoundRobinArbiterUnitTests(unittest.TestCase):
    def test_arbiter_should_grant_no_one_if_there_is_no_request(self):
        arbiter = RoundRobinArbiter()
        arbiter.update()
        arbiter.commit()

        self.assertEqual(arbiter.grant, None)

    def test_arbiter_should_grant_incoming_request_at_next_cycle(self):
        arbiter = RoundRobinArbiter()
        arbiter.put_request_from_direction(Direction.NORTH)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, Direction.NORTH)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, None)

    def test_arbiter_should_eventually_grant_all_incoming_and_pending_requests(self):
        arbiter = RoundRobinArbiter()

        # Push all and see if they're all eventually granted, one by one.
        for direction in Direction:
            arbiter.put_request_from_direction(direction)

        def check_grant_at(arbiter: RoundRobinArbiter, direction: Direction):
            arbiter.update()
            arbiter.commit()
            self.assertEqual(arbiter.grant, direction)

        for direction in Direction:
            check_grant_at(arbiter, direction)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, None)

    def test_arbiter_should_grant_different_request_when_multiple_request_exist_and_previous_request_comes_again(
        self,
    ):
        arbiter = RoundRobinArbiter()
        arbiter.put_request_from_direction(Direction.NORTH)
        arbiter.put_request_from_direction(Direction.SOUTH)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, Direction.NORTH)

        # Push north request once again and see if it's not selected at next cycle.
        arbiter.put_request_from_direction(Direction.NORTH)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, Direction.SOUTH)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, Direction.NORTH)

    def test_arbiter_should_reject_putting_multiple_identical_request_at_once(self):
        arbiter = RoundRobinArbiter()
        self.assertTrue(arbiter.put_request_from_direction(Direction.NORTH))
        self.assertFalse(arbiter.put_request_from_direction(Direction.NORTH))

        arbiter.update()
        arbiter.commit()
        self.assertTrue(arbiter.put_request_from_direction(Direction.NORTH))
        self.assertFalse(arbiter.put_request_from_direction(Direction.NORTH))


class ChronosDecoderUnitTests(unittest.TestCase):
    def test_decoder_outputs_west_when_packet_needs_to_move_left(self):
        # (2, 2) -> (1, 2)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 1), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.WEST}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_east_when_packet_needs_to_move_right(self):
        # (2, 2) -> (3, 2)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 3), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.EAST}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_north_when_packet_needs_to_move_up(self):
        # (2, 2) -> (2, 3)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 3))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.NORTH}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_south_when_packet_needs_to_move_down(self):
        # (2, 2) -> (2, 1)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 1))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.SOUTH}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_west_and_north_when_packet_can_move_to_left_or_up(self):
        # (2, 2) -> (1, 3)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 1), UInt(4, 3))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.WEST, Direction.NORTH}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_west_and_south_when_packet_can_move_to_left_or_down(self):
        # (2, 2) -> (1, 1)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 1), UInt(4, 1))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.WEST, Direction.SOUTH}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_east_and_north_when_packet_can_move_to_right_or_up(self):
        # (2, 2) -> (3, 3)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 3), UInt(4, 3))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.EAST, Direction.NORTH}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_east_and_south_when_packet_can_move_to_right_or_down(self):
        # (2, 2) -> (3, 1)
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 3), UInt(4, 1))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.EAST, Direction.SOUTH}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_local_0_when_packet_can_move_to_neuron_at_0_0(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.LOCAL0}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_local_1_when_packet_can_move_to_neuron_at_0_1(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 1), UInt(1, 0))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.LOCAL1}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_local_2_when_packet_can_move_to_neuron_at_1_0(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 1))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.LOCAL2}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_local_3_when_packet_can_move_to_neuron_at_1_1(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 1), UInt(1, 1))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.LOCAL3}
        self.assertEqual(decoder.decode(dest_loc), expected)


class ChronosCounterUnitTests(unittest.TestCase):
    def test_counter_triggers_exception_on_non_positive_width(self):
        with self.assertRaises(ValueError):
            Counter(0)
        with self.assertRaises(ValueError):
            Counter(-1)

    def test_counter_correctly_increases_on_each_cycle(self):
        counter = Counter(2)
        self.assertEqual(counter.value, UInt(2, 0))

        counter.update()
        counter.commit()
        self.assertEqual(counter.value, UInt(2, 1))

        counter.update()
        counter.commit()
        self.assertEqual(counter.value, UInt(2, 2))

        counter.update()
        counter.commit()
        self.assertEqual(counter.value, UInt(2, 3))

        # Wrapping around is an intended behaviour.
        counter.update()
        counter.commit()
        self.assertEqual(counter.value, UInt(2, 0))


class ChronosPotentialUpdaterUnitTests(unittest.TestCase):
    def test_potential_updater_decays_per_cycle_without_input(self):
        initial = Q4_12.from_float(1.0)
        approx_decay_rate = 0.98
        k1, k2 = SecondOrderShiftDecay.find_decay_shifts(approx_decay_rate)
        spike_threshold = Q4_12.from_float(2.0)

        param = NeuronParameter(k1, k2, 4, spike_threshold, 1)
        updater = MembranePotentialUpdater(param)
        updater.reset()

        updater.set_membrane_potential(initial)
        updater.update()
        updater.commit()

        expected = initial - (initial >> k1) - (initial >> k2)
        self.assertEqual(updater.membrane_potential, expected)

    def test_potential_updater_increases_potential_at_incoming_spike(self):
        initial = Q4_12.from_float(1.0)
        approx_decay_rate = 0.97
        k1, k2 = SecondOrderShiftDecay.find_decay_shifts(approx_decay_rate)
        spike_threshold = Q4_12.from_float(2.0)

        param = NeuronParameter(k1, k2, 4, spike_threshold, 1)
        updater = MembranePotentialUpdater(param)
        updater.reset()

        source_neuron_loc = Coordinate(UInt(1, 1), UInt(1, 0))
        source_local_loc = Coordinate(UInt(1, 0), UInt(1, 1))
        source_loc = NeuronLocation(source_neuron_loc, source_local_loc)

        # Cycle 0: Adding synaptic weight.
        synaptic_weight = Q4_12.from_float(0.5)
        updater.add_synaptic_weight_entry(source_loc, synaptic_weight)
        updater.update()
        updater.commit()

        # Cycle 1: Inject an incoming spike, with weight = 0.5
        updater.set_membrane_potential(initial)
        updater.enqueue_spike(source_loc)
        updater.update()
        updater.commit()

        # Check if potential was decayed as expected first.
        first_expected = initial - (initial >> k1) - (initial >> k2)
        self.assertEqual(updater.membrane_potential, first_expected)

        # Cycle 2:  Observe if synaptic weight was added as expected.
        updater.update()
        updater.commit()

        last_expected = (
            first_expected
            - (first_expected >> k1)
            - (first_expected >> k2)
            + synaptic_weight
        )
        self.assertEqual(updater.membrane_potential, last_expected)

    def test_potential_updater_should_notify_after_exceeding_threshold_at_next_cycle(
        self,
    ):
        initial = Q4_12.from_float(1.0)
        spike_threshold = Q4_12.from_float(1.0)

        # Set k1, k2 absurdly high so no decay would occur.
        param = NeuronParameter(16, 16, 4, spike_threshold, 1)
        updater = MembranePotentialUpdater(param)

        updater.set_membrane_potential(initial)
        updater.update()
        updater.commit()

        # Cycle 0: Notify the downstream that Vmem
        # has exceeded the threshold.
        self.assertTrue(updater.should_fire_spike)

        # Cycle 1: Silence the notification.
        updater.update()
        updater.commit()
        self.assertFalse(updater.should_fire_spike)


class ChronosPacketSequencerUnitTests(unittest.TestCase):
    def test_packet_sequencer_triggers_overflow_exception_on_adding_entry_when_full(
        self,
    ):
        source_pos = Coordinate(UInt(4, 0), UInt(4, 0))
        source_local_pos = Coordinate(UInt(1, 0), UInt(1, 0))
        source_loc = NeuronLocation(source_pos, source_local_pos)

        sequencer = PacketSequencer(1, source_loc)

        first_dest_pos = Coordinate(UInt(4, 0), UInt(4, 1))
        first_dest_local_pos = Coordinate(UInt(1, 0), UInt(1, 0))
        first_dest_loc = NeuronLocation(first_dest_pos, first_dest_local_pos)

        sequencer.add_destination_entry(first_dest_loc)
        sequencer.update()
        sequencer.commit()

        # Doesn't matter if value duplicates. Point is, this operation
        # will make buffer overflow.
        with self.assertRaises(ValueError):
            sequencer.add_destination_entry(first_dest_loc)

    def test_packet_sequencer_fires_a_packet_after_request_enqueue(self):
        source_pos = Coordinate(UInt(4, 0), UInt(4, 0))
        source_local_pos = Coordinate(UInt(1, 0), UInt(1, 0))
        source_loc = NeuronLocation(source_pos, source_local_pos)

        sequencer = PacketSequencer(2, source_loc)

        first_dest_pos = Coordinate(UInt(4, 0), UInt(4, 1))
        first_dest_local_pos = Coordinate(UInt(1, 0), UInt(1, 0))
        first_dest_loc = NeuronLocation(first_dest_pos, first_dest_local_pos)

        sequencer.add_destination_entry(first_dest_loc)
        sequencer.update()
        sequencer.commit()

        # Cycle 0 : Enqueue the sequencing request.
        sequencer.enqueue_sequencing_request()
        sequencer.update()
        sequencer.commit()

        self.assertTrue(sequencer.is_busy)

        # Cycle 1 : Iterate through the table.
        sequencer.update()
        sequencer.commit()

        packet = sequencer.outgoing_packet
        self.assertEqual(packet.source, source_pos)
        self.assertEqual(packet.destination, first_dest_pos)
        self.assertEqual(packet.source_local, source_local_pos)
        self.assertEqual(packet.dest_local, first_dest_local_pos)
        self.assertEqual(packet.timestamp, UInt(PacketSequencer.TIMESTAMP_WIDTH, 3))
        self.assertTrue(isinstance(packet.format, EventPayloadFormat))

        event_packet = cast(EventPayloadFormat, packet.format)
        self.assertEqual(event_packet.event_type, Opcode.SPIKE)

        sequencer.update()
        sequencer.commit()

        self.assertFalse(sequencer.is_busy)

    def test_packet_sequencer_fires_packets_one_by_one_in_added_order(self):
        source_pos = Coordinate(UInt(4, 0), UInt(4, 0))
        source_local_pos = Coordinate(UInt(1, 0), UInt(1, 0))
        source_loc = NeuronLocation(source_pos, source_local_pos)

        sequencer = PacketSequencer(2, source_loc)

        first_dest_pos = Coordinate(UInt(4, 0), UInt(4, 1))
        first_dest_local_pos = Coordinate(UInt(1, 0), UInt(1, 0))
        first_dest_loc = NeuronLocation(first_dest_pos, first_dest_local_pos)

        sequencer.add_destination_entry(first_dest_loc)
        sequencer.update()
        sequencer.commit()

        second_dest_pos = Coordinate(UInt(4, 4), UInt(4, 7))
        second_dest_local_pos = Coordinate(UInt(1, 1), UInt(1, 0))
        second_dest_loc = NeuronLocation(second_dest_pos, second_dest_local_pos)

        sequencer.add_destination_entry(second_dest_loc)
        sequencer.update()
        sequencer.commit()

        # Cycle 0 : Enqueue the sequencing request.
        sequencer.enqueue_sequencing_request()
        sequencer.update()
        sequencer.commit()

        self.assertTrue(sequencer.is_busy)

        # Cycle 1 : Iterate through the table.
        sequencer.update()
        sequencer.commit()

        packet = sequencer.outgoing_packet

        self.assertEqual(packet.source, source_pos)
        self.assertEqual(packet.destination, first_dest_pos)
        self.assertEqual(packet.source_local, source_local_pos)
        self.assertEqual(packet.dest_local, first_dest_local_pos)
        self.assertEqual(packet.timestamp, UInt(PacketSequencer.TIMESTAMP_WIDTH, 4))
        self.assertTrue(isinstance(packet.format, EventPayloadFormat))

        event_packet = cast(EventPayloadFormat, packet.format)
        self.assertEqual(event_packet.event_type, Opcode.SPIKE)

        sequencer.update()
        sequencer.commit()

        self.assertFalse(sequencer.is_busy)
        packet = sequencer.outgoing_packet

        self.assertEqual(packet.source, source_pos)
        self.assertEqual(packet.destination, second_dest_pos)
        self.assertEqual(packet.source_local, source_local_pos)
        self.assertEqual(packet.dest_local, second_dest_local_pos)
        self.assertEqual(packet.timestamp, UInt(PacketSequencer.TIMESTAMP_WIDTH, 5))
        self.assertTrue(isinstance(packet.format, EventPayloadFormat))

        event_packet = cast(EventPayloadFormat, packet.format)
        self.assertEqual(event_packet.event_type, Opcode.SPIKE)


class ChronosNeuronCoreIntegrateTests(unittest.TestCase):
    def test_core_never_drops_pending_fanout_spikes_during_stall(self):
        pass

    def test_core_stalls_when_downstream_router_is_not_ready(self):
        pass


class ChronosBoundaryErrorBlockUnitTests(unittest.TestCase):
    def test_error_unit_fires_error_response_to_origin_at_next_cycle(self):
        pass


if __name__ == "__main__":
    unittest.main()
