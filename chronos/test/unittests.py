import unittest

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from chronos.blocks import (
    NeuronParameter,
    SecondOrderShiftDecay,
    MembranePotentialUpdater,
)
from chronos.hardware_types import Q4_12, UInt, BoundedMap


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


class ChronosBoundedMapUnitTests(unittest.TestCase):
    def test_map_returns_false_when_queried_non_existent_value(self):
        bounded_map = BoundedMap(4)
        is_valid, _ = bounded_map.get(0)
        self.assertFalse(is_valid)

    def test_map_returns_true_when_queried_existent_value(self):
        bounded_map = BoundedMap(4)
        expected_data = Q4_12(1)
        bounded_map.put(0, expected_data)
        is_valid, data = bounded_map.get(0)

        self.assertTrue(is_valid)
        self.assertEqual(data, expected_data)

    def test_map_returns_false_on_put_when_map_is_full(self):
        bounded_map = BoundedMap(1)
        bounded_map.put(0, Q4_12(1))
        is_valid = bounded_map.put(1, Q4_12(1))

        self.assertFalse(is_valid)

    def test_map_returns_true_on_put_when_map_is_not_full(self):
        bounded_map = BoundedMap(1)
        is_valid = bounded_map.put(0, Q4_12(1))

        self.assertTrue(is_valid)

    # Overwriting is an intended feature, as hardware doesn't do anything
    # on overwrites. However this can lead to logic bug, so one should
    # call put() cautiously.
    def test_map_returns_true_on_overwriting_put(self):
        bounded_map = BoundedMap(2)
        bounded_map.put(0, Q4_12(1))
        is_valid = bounded_map.put(0, Q4_12(1))

        self.assertTrue(is_valid)

    def test_map_returns_0_size_when_reset(self):
        bounded_map = BoundedMap(2)
        bounded_map.put(0, Q4_12(1))

        self.assertEqual(bounded_map.size, 1)
        bounded_map.reset()
        self.assertEqual(bounded_map.size, 0)


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


class ChronosNeuronCoreSubblockUnitTests(unittest.TestCase):
    def test_potential_updater_decays_per_cycle_without_input(self):
        initial = Q4_12.from_float(1.0)
        approx_decay_rate = 0.98
        k1, k2 = SecondOrderShiftDecay.find_decay_shifts(approx_decay_rate)
        spike_threshold = Q4_12.from_float(2.0)

        param = NeuronParameter(k1, k2, 4, spike_threshold)
        updater = MembranePotentialUpdater(param)

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

        param = NeuronParameter(k1, k2, 4, spike_threshold)
        updater = MembranePotentialUpdater(param)

        synaptic_weight = Q4_12.from_float(0.5)
        updater.set_membrane_potential(initial)
        updater.add_synaptic_weight_entry(0, synaptic_weight)
        updater.enqueue_spike(0)

        updater.update()
        updater.commit()

        expected = initial - (initial >> k1) - (initial >> k2) + synaptic_weight
        self.assertEqual(updater.membrane_potential, expected)

    def test_potential_updater_enqueues_outgoing_spike_packet_after_exceeding_threshold_at_next_cycle(
        self,
    ):
        initial = Q4_12.from_float(1.0)
        spike_threshold = Q4_12.from_float(1.0)

        # Set k1, k2 absurdly high so no decay would occur.
        param = NeuronParameter(16, 16, 4, spike_threshold)
        updater = MembranePotentialUpdater(param)

        updater.set_membrane_potential(initial)
        updater.update()
        updater.commit()

        # TODO: For now, it only checks the presence of packet.
        # Whenever a fanout table is introduced, this should check
        # content equivalence as well.
        self.assertNotEqual(updater.outgoing_packet, None)

        # Since it's supposed to be fire a spike, the outbound
        # spike should disappear after a cycle.
        updater.update()
        updater.commit()
        self.assertEqual(updater.outgoing_packet, None)


class ChronosNeuronCoreIntegrateTests(unittest.TestCase):
    def test_core_decays_membrane_potential_per_cycle(self):
        pass

    def test_core_adds_synaptic_weight_to_potential_after_receiving_spike(self):
        pass

    def test_core_outbound_spike_buffer_dequeue_requires_1_cycle(self):
        pass

    def test_core_enqueues_outbound_spike_at_next_cycle_when_threshold_exceeded(self):
        pass

    def test_core_enqueues_fanout_spikes_at_most_once_per_cycle_in_table_order(self):
        pass

    def test_core_never_drops_pending_fanout_spikes_during_stall(self):
        pass

    def test_core_stalls_when_downstream_router_is_not_ready(self):
        pass


class ChronosBoundaryErrorBlockUnitTests(unittest.TestCase):
    def test_error_unit_fires_error_response_to_origin_at_next_cycle(self):
        pass


if __name__ == "__main__":
    unittest.main()
