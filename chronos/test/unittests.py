import unittest

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from chronos.blocks import NeuronParameter, NeuronCore, SecondOrderShiftDecay
from chronos.hardware_types import Q4_12


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


class ChronosCoreBlockUnitTests(unittest.TestCase):
    def test_core_decays_membrane_potential_per_cycle(self):
        initial = Q4_12.from_float(1.0)
        approx_decay_rate = 0.98
        k1, k2 = SecondOrderShiftDecay.find_decay_shifts(approx_decay_rate)

        param = NeuronParameter(k1, k2)
        core = NeuronCore(param)

        core.set_membrane_potential(initial)
        core.update()
        core.commit()

        expected = initial - (initial >> k1) - (initial >> k2)
        self.assertEqual(core.membrane_potential, expected)

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
