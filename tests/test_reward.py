import sys
import unittest
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "Agent"))
from dsp_agent.reward import (EpisodeResult, ProductionWindow, RewardError, RewardPolicy,
                              SignalProof, WhiteThroughput)

POLICY = RewardPolicy(ROOT / "data" / "reward-policy.json")


def proof(name, source=None):
    return SignalProof(name, source or ("entity_counter" if name.endswith("_output_sustained")
                                       else "visible_game_observation"), "episode:test",
                       (ProductionWindow(10, 1), ProductionWindow(10, 2))
                       if name.endswith("_output_sustained") else ())


def episode(strategy="baseline", trial="copy-1", start=(), end=(), white=None, ticks=100):
    return EpisodeResult("episode-" + strategy + trial, strategy, trial, "test-game", True,
                         ticks, tuple(start), tuple(end), white)


class RewardTests(unittest.TestCase):
    def test_two_mined_ore_have_no_production_reward(self):
        card = POLICY.score(episode())
        self.assertEqual(card.progress_points, 0)
        self.assertEqual(card.white_rate_per_tick, 0)

    def test_later_verified_output_gets_more_one_time_points(self):
        ore = POLICY.score(episode(end=[proof("iron_ore_flow_observed")]))
        ingot = POLICY.score(episode(end=[proof("iron_ingot_output_sustained")]))
        circuit = POLICY.score(episode(end=[proof("circuit_output_sustained")]))
        self.assertLess(ore.progress_points, ingot.progress_points)
        self.assertLess(ingot.progress_points, circuit.progress_points)
        repeated = POLICY.score(episode(start=[proof("iron_ingot_output_sustained")],
                                        end=[proof("iron_ingot_output_sustained")]))
        self.assertEqual(repeated.progress_points, 0)

    def test_white_throughput_is_primary_and_needs_sustained_attributed_output(self):
        white = WhiteThroughput("entity_counter", "episode:test", (
            ProductionWindow(10, 1), ProductionWindow(10, 2)))
        card = POLICY.score(episode(end=[proof("white_matrix_output_sustained")], white=white))
        self.assertEqual(card.white_rate_per_tick, Fraction(3, 20))
        self.assertGreater(card.rank, POLICY.score(episode(end=[proof("green_matrix_output_sustained")])).rank)
        with self.assertRaises(RewardError):
            POLICY.score(episode(end=[proof("white_matrix_output_sustained")],
                                 white=replace(white, source="planet_aggregate")))
        with self.assertRaises(RewardError):
            POLICY.score(episode(end=[proof("white_matrix_output_sustained")],
                                 white=replace(white, windows=(ProductionWindow(10, 1),))))
        with self.assertRaises(RewardError):
            POLICY.score(episode(end=[proof("white_matrix_output_sustained")]))

    def test_rejects_unverified_and_nonordinary_evidence(self):
        with self.assertRaises(RewardError):
            POLICY.score(episode(end=[proof("iron_ingot_output_sustained", "inventory")]))
        with self.assertRaises(RewardError):
            POLICY.score(replace(episode(), ordinary_mode=False))

    def test_pairwise_promotion_requires_improvement_without_regression(self):
        baseline = [POLICY.score(episode(trial="a")), POLICY.score(episode(trial="b"))]
        candidate = [POLICY.score(episode(strategy="candidate", trial="a",
                                          end=[proof("iron_ingot_output_sustained")])),
                     POLICY.score(episode(strategy="candidate", trial="b"))]
        self.assertTrue(POLICY.compare(baseline, candidate)["promote"])
        regressed = [candidate[0], replace(candidate[1], elapsed_ticks=101)]
        self.assertFalse(POLICY.compare(baseline, regressed)["promote"])
        with self.assertRaises(RewardError):
            POLICY.compare(baseline[:1], candidate[:1])
        with self.assertRaises(RewardError):
            POLICY.compare(baseline, [candidate[0], replace(candidate[1], trial_key="other")])


if __name__ == "__main__":
    unittest.main()
