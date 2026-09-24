import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.bridge_verifier import verify_bridge_action
from dsp_agent.experiment_runner import ExperimentPlan, Observation


def observed(tick, inventory_count, vein_amount, position):
    return Observation(
        "session-a", tick, "snapshot-" + str(tick), "state-" + str(tick),
        {"planet": {"id": 102}, "mecha_position": position,
         "inventory": {"complete": True, "items": [{"item_id": 1001, "count": inventory_count}]},
         "nearby_veins": {"veins": [{"id": 7, "amount": vein_amount, "product_id": 1001}]}},
    )


class BridgeVerifierTests(unittest.TestCase):
    def test_mining_needs_both_operation_counters_and_fresh_readback(self):
        before = observed(10, 0, 100, {"x": 0, "y": 0, "z": 0})
        after = observed(20, 2, 98, {"x": 2, "y": 0, "z": 0})
        plan = ExperimentPlan({"kind": "mine", "args": {"vein_id": 7, "count": 2, "item_id": 1001}},
                              "reachable", "two ore", "no ore")
        result = {"status": "completed", "session_id": "session-a", "planet_id": 102,
                  "inventory_before": 0, "inventory_now": 2,
                  "vein_amount_before": 100, "vein_amount_now": 98}
        self.assertEqual(verify_bridge_action(before, after, plan, result).verdict, "achieved")
        missing = observed(20, 0, 100, {"x": 2, "y": 0, "z": 0})
        self.assertEqual(verify_bridge_action(before, missing, plan, result).verdict, "unknown")

    def test_move_needs_fresh_position_near_target(self):
        before = observed(10, 0, 100, {"x": 0, "y": 0, "z": 0})
        after = observed(20, 0, 100, {"x": 9, "y": 0, "z": 0})
        plan = ExperimentPlan({"kind": "move", "args": {"vein_id": 7}},
                              "path clear", "near vein", "still far")
        result = {"status": "completed", "session_id": "session-a", "planet_id": 102,
                  "target_position": {"x": 10, "y": 0, "z": 0}}
        self.assertEqual(verify_bridge_action(before, after, plan, result).verdict, "achieved")
        stalled = observed(20, 0, 100, {"x": 0, "y": 0, "z": 0})
        self.assertEqual(verify_bridge_action(before, stalled, plan, result).verdict, "unknown")

    def test_rejection_is_recorded_as_a_failed_primitive_only(self):
        before = observed(10, 0, 100, {"x": 0, "y": 0, "z": 0})
        after = observed(11, 0, 100, {"x": 0, "y": 0, "z": 0})
        plan = ExperimentPlan({"kind": "mine", "args": {"vein_id": 7, "count": 2, "item_id": 1001}},
                              "reachable", "ore", "none")
        verdict = verify_bridge_action(before, after, plan,
                                       {"status": "rejected", "reason": "player_busy"})
        self.assertEqual(verdict.verdict, "failed")
        self.assertEqual(verdict.evidence_ref, "snapshot-11")


if __name__ == "__main__":
    unittest.main()
