import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Agent"))
from dsp_agent.learning import LearningError, StrategyMemory
from dsp_agent.reward import EpisodeResult, ProductionWindow, RewardPolicy, SignalProof

POLICY = RewardPolicy(ROOT / "data" / "reward-policy.json")


def card(strategy, trial, improved=False):
    proofs = (SignalProof("iron_ingot_output_sustained", "entity_counter", "private-episode:" + trial,
                          (ProductionWindow(10, 1), ProductionWindow(10, 1))),) if improved else ()
    return POLICY.score(EpisodeResult("episode-" + strategy + trial, strategy, trial,
                                      "test-game", True, 100, (), proofs))


class LearningTests(unittest.TestCase):
    def test_promotion_persists_and_replay_is_idempotent(self):
        old = [card("baseline", "a"), card("baseline", "b")]
        new = [card("candidate", "a", True), card("candidate", "b")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "learning.sqlite"
            with StrategyMemory(path) as memory:
                result = memory.consider("white", "experiment-1", POLICY, old, new)
                self.assertTrue(result["promote"])
                self.assertEqual(memory.active("white"), "candidate")
            with StrategyMemory(path) as memory:
                self.assertEqual(memory.consider("white", "experiment-1", POLICY, old, new), result)
                self.assertEqual(memory.active("white"), "candidate")
                with self.assertRaises(LearningError):
                    memory.consider("white", "experiment-1", POLICY, old, [new[0], card("candidate", "b", True)])

    def test_regression_cannot_replace_active_strategy(self):
        old = [card("baseline", "a"), card("baseline", "b")]
        new = [card("candidate", "a", True), card("candidate", "b")]
        with tempfile.TemporaryDirectory() as directory:
            with StrategyMemory(Path(directory) / "learning.sqlite") as memory:
                memory.consider("white", "experiment-1", POLICY, old, new)
                worse = [card("worse", "a"), card("worse", "b")]
                current = [card("candidate", "a", True), card("candidate", "b")]
                decision = memory.consider("white", "experiment-2", POLICY, current, worse)
                self.assertFalse(decision["promote"])
                self.assertEqual(memory.active("white"), "candidate")
                with self.assertRaises(LearningError):
                    memory.consider("white", "experiment-3", POLICY, old, worse)


if __name__ == "__main__":
    unittest.main()
