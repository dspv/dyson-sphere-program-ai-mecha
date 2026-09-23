import json
import unittest
from pathlib import Path

ROADMAP = Path(__file__).resolve().parents[1] / "data" / "roadmap.json"


class RoadmapTests(unittest.TestCase):
    def test_dependency_graph_is_valid(self):
        payload = json.loads(ROADMAP.read_text())
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["status"], "desired_not_implemented")
        milestones = payload["milestones"]
        ids = [entry["id"] for entry in milestones]
        self.assertEqual(len(ids), len(set(ids)))
        visited = set()
        for entry in milestones:
            self.assertTrue(entry["done_when"])
            self.assertTrue(all(isinstance(signal, str) and signal for signal in entry["done_when"]))
            self.assertTrue(set(entry["requires"]).issubset(visited))
            visited.add(entry["id"])

    def test_titanium_precedes_logistics(self):
        milestones = {entry["id"]: entry for entry in json.loads(ROADMAP.read_text())["milestones"]}
        self.assertIn("titanium_expedition", milestones["yellow_science"]["requires"])
        self.assertIn("yellow_science", milestones["interplanetary_logistics"]["requires"])


if __name__ == "__main__":
    unittest.main()
