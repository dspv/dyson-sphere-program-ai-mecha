import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Agent"))
from dsp_agent.roadmap import RoadmapError, RoadmapPlanner


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = RoadmapPlanner(ROOT / "data" / "roadmap.json")

    def test_unknown_does_not_count_as_done(self):
        result = self.planner.evaluate({})
        self.assertEqual(result["current_milestone"], "starter_industry")
        self.assertEqual(result["milestones"][0]["state"], "ready_for_work")
        self.assertIn("iron_ingot_output_sustained", result["milestones"][0]["unknown_evidence"])

    def test_next_milestone_after_starter_industry(self):
        evidence = {"iron_ore_flow_observed": True, "iron_ingot_output_sustained": True}
        self.assertEqual(self.planner.evaluate(evidence)["current_milestone"], "blue_science")

    def test_invalid_signal_is_rejected(self):
        with self.assertRaises(RoadmapError):
            self.planner.evaluate({"free_iron_spawned": True})


if __name__ == "__main__":
    unittest.main()
