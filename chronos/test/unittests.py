from typing import cast
import unittest

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from chronos.blocks import (
    BoundedRAM,
    BoundedQueue,
    Counter,
    NeuronParameter,
    PacketSequencer,
    Decoder,
    Crossbar8x8,
    Direction,
    RoundRobinArbiter,
    SecondOrderShiftDecay,
    MembranePotentialUpdater,
)
from chronos.hardware_types import Q4_12, UInt
from chronos.packets import (
    EventPayloadFormat,
    Coordinate,
    Opcode,
    NeuronLocation,
    Packet,
)


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
        with self.assertRaises(ValueError):
            BoundedQueue[UInt](-1, 1)
        with self.assertRaises(ValueError):
            BoundedQueue[UInt](0, 1)

    def test_queue_rejects_non_positive_bit_width(self):
        with self.assertRaises(ValueError):
            BoundedQueue[UInt](1, -1)
        with self.assertRaises(ValueError):
            BoundedQueue[UInt](1, 0)

    def test_queue_rejects_incoming_data_with_different_bitwidth(self):
        queue = BoundedQueue[UInt](2, 1)
        with self.assertRaises(ValueError):
            queue.push(UInt(2, 1))

    def test_enqueue_operation_increases_queue_element_count(self):
        queue = BoundedQueue[UInt](2, 4)
        self.assertEqual(queue.size, 0)

        queue.push(UInt(4, 1))
        queue.update()
        queue.commit()

        self.assertEqual(queue.size, 1)

    def test_enqueue_return_failure_if_queue_is_full(self):
        queue = BoundedQueue[UInt](1, 4)

        self.assertTrue(queue.push(UInt(4, 1)))
        queue.update()
        queue.commit()

        self.assertFalse(queue.push(UInt(4, 1)))

    def test_dequeue_operation_decreases_queue_element_count(self):
        queue = BoundedQueue[UInt](1, 4)
        expected = UInt(4, 1)

        self.assertTrue(queue.push(expected))

        queue.update()
        queue.commit()
        self.assertEqual(queue.size, 1)

        popped_result = queue.pop()
        self.assertTrue(popped_result[0])
        self.assertEqual(popped_result[1], expected)

        queue.update()
        queue.commit()
        self.assertEqual(queue.size, 0)

    def test_dequeue_return_failiure_if_queue_is_empty(self):
        queue = BoundedQueue[UInt](1, 4)
        self.assertEqual(queue.size, 0)

        popped_result = queue.pop()
        self.assertFalse(popped_result[0])


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


class ChronosCrossbar8x8UnitTests(unittest.TestCase):
    def __push_all_recipient_ready(self, crossbar: Crossbar8x8):
        for dir in Direction:
            self.assertTrue(crossbar.push_ready(dir))

    # A shortcut of creating spike packet.
    def __create_spike_packet(
        self, source_loc: tuple[int, int], dest_loc: tuple[int, int, int, int]
    ) -> Packet:
        return Packet.create_spike_packet(
            4, (source_loc[0], source_loc[1], 0, 0), dest_loc, 0
        )

    def __create_destination_coordinate(
        self, source: tuple[int, int], direction: Direction
    ) -> tuple[int, int, int, int]:
        if direction == Direction.NORTH:
            return (source[0], source[1] + 1, 0, 0)
        elif direction == Direction.EAST:
            return (source[0] + 1, source[1], 0, 0)
        elif direction == Direction.WEST:
            return (source[0] - 1, source[1], 0, 0)
        elif direction == Direction.SOUTH:
            return (source[0], source[1] - 1, 0, 0)
        elif direction == Direction.LOCAL0:
            return (source[0], source[1], 0, 0)
        elif direction == Direction.LOCAL1:
            return (source[0], source[1], 0, 1)
        elif direction == Direction.LOCAL2:
            return (source[0], source[1], 1, 0)
        elif direction == Direction.LOCAL3:
            return (source[0], source[1], 1, 1)

    def __check_packet_forwarding_to(
        self,
        crossbar: Crossbar8x8,
        router_loc: tuple[int, int],
        source_loc: tuple[int, int],
        direction: Direction,
    ):
        self.__push_all_recipient_ready(crossbar)

        dest_coord = self.__create_destination_coordinate(router_loc, direction)
        packet = self.__create_spike_packet(source_loc, dest_coord)

        self.assertTrue(crossbar.push_packet(packet, direction))
        self.__check_outgoing_packet_of(crossbar, direction, packet)

        crossbar.update()
        crossbar.commit()

    def __check_outgoing_packet_of(
        self,
        crossbar: Crossbar8x8,
        direction: Direction,
        expected_packet: Packet | None,
    ):
        for dir in Direction:
            if dir == direction:
                self.assertEqual(crossbar.get_outbound_packet_of(dir), expected_packet)
            else:
                self.assertEqual(crossbar.get_outbound_packet_of(dir), None)

    def test_crossbar_one_request_going_one_recipient_once_should_be_forwarded_correctly(
        self,
    ):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        crossbar = Crossbar8x8(router_loc)

        # (2, 1) -> (2, 3), with locals all (0, 0)
        packet = Packet.create_spike_packet(4, (2, 1, 0, 0), (2, 3, 0, 0), 0)

        # Scenario: Recipient is ready, requster fires a request.
        # Expected to forward packet SOUTH -> NORTH at the same cycle.
        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.assertTrue(crossbar.push_packet(packet, Direction.SOUTH))
        self.__check_outgoing_packet_of(crossbar, Direction.NORTH, packet)

    def test_crossbar_request_stalls_if_recipient_is_not_ready_in_given_cycle(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        crossbar = Crossbar8x8(router_loc)

        # (2, 1) -> (2, 3)
        packet = Packet.create_spike_packet(4, (2, 1, 0, 0), (2, 3, 0, 0), 0)

        # Scenario: Recipient is NOT ready, requester fires a request.
        # Expected NOT to forward packet SOUTH -> NORTH, until recipient is ready.
        self.assertTrue(crossbar.push_packet(packet, Direction.SOUTH))
        self.assertEqual(crossbar.get_outbound_packet_of(Direction.NORTH), None)

        crossbar.update()
        crossbar.commit()

        # No transactions were made, means it's stalled.
        self.assertFalse(crossbar.push_packet(packet, Direction.SOUTH))
        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.__check_outgoing_packet_of(crossbar, Direction.NORTH, packet)

        crossbar.update()
        crossbar.commit()

        self.assertEqual(crossbar.get_outbound_packet_of(Direction.NORTH), None)

    def test_crossbar_request_stalls_if_it_was_not_granted_in_given_cycle(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        crossbar = Crossbar8x8(router_loc)

        # Scenario: Recipient is ready and two requesters are competing to
        # fire their request to identical receiver. Let's say these come
        # from router (2, 1) and 0-th neuron at router (2, 2).
        packet = Packet.create_spike_packet(4, (2, 1, 0, 0), (2, 3, 0, 0), 0)
        another_packet = Packet.create_spike_packet(4, (2, 2, 0, 0), (2, 3, 0, 0), 0)

        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.assertTrue(crossbar.push_packet(packet, Direction.SOUTH))
        self.assertTrue(crossbar.push_packet(another_packet, Direction.LOCAL0))

        # Cardinal ones go first, then local.
        self.__check_outgoing_packet_of(crossbar, Direction.NORTH, packet)
        crossbar.update()
        crossbar.commit()

        # Local 0 didn't make it last turn, so left stalled
        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.assertFalse(crossbar.push_packet(another_packet, Direction.LOCAL0))

        # Local
        self.__check_outgoing_packet_of(crossbar, Direction.NORTH, another_packet)
        crossbar.update()
        crossbar.commit()

        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.assertEqual(crossbar.get_outbound_packet_of(Direction.NORTH), None)

    def test_router_forward_packets_according_to_XY_routing_scheme(
        self,
    ):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        crossbar = Crossbar8x8(router_loc)

        # Scenario: Recipient is ready and requster and recipient
        # are placed diagnoally; that is, two path is possible:
        # NORTH and EAST as it's going from (2, 1) to (3, 3).
        packet = Packet.create_spike_packet(4, (2, 1, 0, 0), (3, 3, 0, 0), 0)

        # According to sNPU Architecture, when shipping packet through
        # cardinal direction it should follow fixed priority:
        # East > West > North > South, where East has highest priority.
        #
        # However in this case we assume East was somehow blocked.
        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.assertTrue(crossbar.push_packet(packet, Direction.SOUTH))

        # No port should be forwarding any incoming packets.
        self.__check_outgoing_packet_of(crossbar, Direction.NORTH, None)

        crossbar.update()
        crossbar.commit()

        # After that, assuming two paths are now available again.
        # According to XY routing, packet must go through east,
        # not north.
        self.assertTrue(crossbar.push_ready(Direction.NORTH))
        self.assertTrue(crossbar.push_ready(Direction.EAST))
        self.__check_outgoing_packet_of(crossbar, Direction.EAST, packet)

        crossbar.update()
        crossbar.commit()

        self.assertEqual(crossbar.get_outbound_packet_of(Direction.EAST), None)

    def test_crossbar_one_request_going_multiple_recipient_through_cardinal_direction_should_be_forwarded_correctly(
        self,
    ):
        router_loc = (2, 2)
        rloc = Coordinate(UInt(4, router_loc[0]), UInt(4, router_loc[1]))
        crossbar = Crossbar8x8(rloc)

        # Scenario: All recipient is ready, requester fires a request toward EVERY recipient.
        # Expected to forward packet SOUTH -> NORTH/EAST/WEST/SOUTH
        # throughout the 8 cycles.
        for direction in Direction.cardinal_directions():
            coord = self.__create_destination_coordinate(router_loc, direction)

            # Re-mapping because original has 4 element, but this needs only 2
            requester_loc = (coord[0], coord[1])
            self.__check_packet_forwarding_to(
                crossbar, router_loc, requester_loc, direction
            )

    def test_crossbar_one_request_going_multiple_recipient_toward_local_should_be_forwarded_correctly(
        self,
    ):
        router_loc = (2, 2)
        rloc = Coordinate(UInt(4, router_loc[0]), UInt(4, router_loc[1]))
        crossbar = Crossbar8x8(rloc)

        # Scenario: All recipient is ready, requester fires a request toward EVERY recipient.
        # Expected to forward packet SELF -> LOCAL0/LOCAL1/LOCAL2/LOCAL3
        # throughout the 8 cycles.
        requester_loc = (2, 2)
        for direction in Direction.local_directions():
            self.__check_packet_forwarding_to(
                crossbar, router_loc, requester_loc, direction
            )

    def test_crossbar_one_request_going_identical_recipient_multiple_times_should_be_forwarded_correctly(
        self,
    ):
        router_loc = (2, 2)
        rloc = Coordinate(UInt(4, router_loc[0]), UInt(4, router_loc[1]))
        crossbar = Crossbar8x8(rloc)

        # Scenario: Recipient is ready all the time, requester fires packet
        # to identical recipient repeatedly.

        # Repeat firing request to identical spot 8 times. see if it works as intended.
        requester_loc = (2, 3)
        for direction in Direction:
            for _ in range(8):
                self.__check_packet_forwarding_to(
                    crossbar, router_loc, requester_loc, direction
                )

    def test_crossbar_multiple_request_going_one_recipient_once_should_be_forwarded_correctly(
        self,
    ):
        router_loc = (2, 2)
        rloc = Coordinate(UInt(4, router_loc[0]), UInt(4, router_loc[1]))
        crossbar = Crossbar8x8(rloc)

        # Scenario: A recipient is ready. EVERY requesters fire a request toward a recipient.
        # Expected to forward packet NORTH/EAST/WEST/SOUTH/LOCAL0/LOCAL1/LOCAL2/LOCAL3 -> EAST
        # throughout the 8 cycles.

        def push_all_request_packets(
            router_loc: tuple[int, int],
            recipient_loc: tuple[int, int, int, int],
            from_direction: Direction,
        ) -> Packet:
            source_loc = self.__create_destination_coordinate(
                router_loc, from_direction
            )
            packet = self.__create_spike_packet(
                (source_loc[0], source_loc[1]), recipient_loc
            )
            self.assertTrue(crossbar.push_packet(packet, from_direction))

            return packet

        recipient_loc = (3, 2, 0, 0)

        generated_packets = []
        for dir in Direction:
            generated_packets.append(
                push_all_request_packets(router_loc, recipient_loc, dir)
            )

        for dir in Direction:
            self.assertTrue(crossbar.push_ready(Direction.EAST))
            self.assertEqual(
                crossbar.get_outbound_packet_of(Direction.EAST),
                generated_packets[dir],
            )
            crossbar.update()
            crossbar.commit()

    def test_crossbar_multiple_request_going_multiple_recipients_once_should_be_forwarded_correctly(
        self,
    ):
        router_loc = (2, 2)
        rloc = Coordinate(UInt(4, router_loc[0]), UInt(4, router_loc[1]))
        crossbar = Crossbar8x8(rloc)

        # Scenario: Every recipient is ready. Every requester
        # fires a request toward themselves, resembling
        # a massive autapse.

        self.__push_all_recipient_ready(crossbar)

        for dir in Direction:
            dest_coord = self.__create_destination_coordinate(router_loc, dir)
            packet = self.__create_spike_packet(
                (dest_coord[0], dest_coord[1]), dest_coord
            )
            self.assertTrue(crossbar.push_packet(packet, dir))
            self.assertEqual(crossbar.get_outbound_packet_of(dir), packet)

        crossbar.update()
        crossbar.commit()

        for dir in Direction:
            self.assertEqual(crossbar.get_outbound_packet_of(dir), None)


class ChronosRoundRobinArbiterUnitTests(unittest.TestCase):
    def test_arbiter_should_grant_no_one_if_there_is_no_request(self):
        arbiter = RoundRobinArbiter()
        arbiter.update()
        arbiter.commit()

        self.assertEqual(arbiter.grant, None)

    def test_arbiter_should_grant_incoming_request_at_same_cycle(self):
        arbiter = RoundRobinArbiter()
        arbiter.put_request_from_direction(Direction.NORTH)
        self.assertEqual(arbiter.grant, Direction.NORTH)

        arbiter.update()
        arbiter.commit()
        self.assertEqual(arbiter.grant, None)

    def test_arbiter_should_eventually_grant_all_incoming_and_pending_requests(self):
        arbiter = RoundRobinArbiter()

        # Push all and see if they're all eventually granted, one by one.
        def pack_all_requests(arbiter: RoundRobinArbiter):
            for direction in Direction:
                self.assertTrue(arbiter.put_request_from_direction(direction))

        def check_grant_at(arbiter: RoundRobinArbiter, direction: Direction):
            self.assertEqual(arbiter.grant, direction)
            arbiter.update()
            arbiter.commit()

        for direction in Direction:
            pack_all_requests(arbiter)
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

        self.assertEqual(arbiter.grant, Direction.NORTH)
        arbiter.update()
        arbiter.commit()

        arbiter.put_request_from_direction(Direction.NORTH)
        arbiter.put_request_from_direction(Direction.SOUTH)

        self.assertEqual(arbiter.grant, Direction.SOUTH)
        arbiter.update()
        arbiter.commit()

        arbiter.put_request_from_direction(Direction.NORTH)

        self.assertEqual(arbiter.grant, Direction.NORTH)
        arbiter.update()
        arbiter.commit()

        self.assertEqual(arbiter.grant, None)

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
        dest_local_loc = Coordinate(UInt(1, 0), UInt(1, 1))
        dest_loc = NeuronLocation(dest_neuron_loc, dest_local_loc)

        expected = {Direction.LOCAL1}
        self.assertEqual(decoder.decode(dest_loc), expected)

    def test_decoder_outputs_local_2_when_packet_can_move_to_neuron_at_1_0(self):
        router_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        decoder = Decoder(router_loc)

        dest_neuron_loc = Coordinate(UInt(4, 2), UInt(4, 2))
        dest_local_loc = Coordinate(UInt(1, 1), UInt(1, 0))
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
