import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.evidence import EvidenceError, ProductionSample, ProductionVerifier


def sample(tick, total, session="save:load-1", source="game_production_counter"):
    return ProductionSample(session, 104, 10, 1101, tick, total, source)


class ProductionEvidenceTests(unittest.TestCase):
    def test_requires_multiple_positive_windows(self):
        verifier = ProductionVerifier(window_ticks=10, required_windows=2)
        self.assertFalse(verifier.observe(sample(0, 0))["confirmed"])
        self.assertFalse(verifier.observe(sample(10, 2))["confirmed"])
        self.assertTrue(verifier.observe(sample(20, 5))["confirmed"])

    def test_idle_window_breaks_streak(self):
        verifier = ProductionVerifier(window_ticks=10, required_windows=2)
        for tick, total in [(0, 0), (10, 1), (20, 1), (30, 2)]:
            status = verifier.observe(sample(tick, total))
        self.assertFalse(status["confirmed"])
        self.assertEqual(status["consecutive_positive_windows"], 1)

    def test_session_and_counter_reset_are_rejected(self):
        verifier = ProductionVerifier(window_ticks=10, required_windows=2)
        verifier.observe(sample(0, 5))
        with self.assertRaises(EvidenceError):
            verifier.observe(sample(10, 6, session="save:load-2"))
        with self.assertRaises(EvidenceError):
            verifier.observe(sample(10, 4))

    def test_inventory_is_not_production_evidence(self):
        verifier = ProductionVerifier(window_ticks=10, required_windows=2)
        with self.assertRaises(EvidenceError):
            verifier.observe(sample(0, 10, source="inventory"))


if __name__ == "__main__":
    unittest.main()
