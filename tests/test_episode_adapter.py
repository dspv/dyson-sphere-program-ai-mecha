import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.evidence import EvidenceError, ProductionSample
from dsp_agent.episode_adapter import episode_from_record, iron_sample_from_entity, sample_record
from dsp_agent.reward import RewardPolicy


POLICY = RewardPolicy(Path(__file__).resolve().parents[1] / "data" / "reward-policy.json")
HASH = "a" * 64


def record(counts, *, ui=True):
    samples = [ProductionSample(session_id="session-a", save_copy_id="new-game-trial-a",
               checkpoint_sha256=HASH, game_version="0.10.35.29057", planet_id=102,
               entity_id=10, item_id=1101, recipe_id=1, game_tick=index * 120,
               produced_total=count, source="game_production_counter")
               for index, count in enumerate(counts)]
    return {"episode_id": "episode-a", "strategy_id": "baseline", "trial_key": "checkpoint-a",
            "game_version": "0.10.35.29057", "ordinary_mode": True,
            "save_copy_id": "new-game-trial-a", "checkpoint_sha256": HASH,
            "session_id": "session-a", "planet_id": 102, "entity_id": 10, "item_id": 1101,
            "elapsed_ticks": 240, "signal_name": "iron_ingot_output_sustained",
            "evidence_id": "private:episode-a", "window_ticks": 120,
            "required_windows": 2, "window_ui_refs": ["ui:120", "ui:240"] if ui else ["", ""],
            "automated_input_ui_refs": ["ui:belt:120", "ui:belt:240"],
            "samples": [sample_record(sample) for sample in samples]}


class EpisodeAdapterTests(unittest.TestCase):
    def test_verified_machine_windows_earn_one_bounded_capability(self):
        result = episode_from_record(record([0, 2, 5]))
        self.assertEqual(result.end_proofs[0].windows[0].produced, 2)
        self.assertEqual(POLICY.score(result).progress_points, 2)

    def test_idle_or_unpowered_machine_earns_no_output(self):
        self.assertEqual(POLICY.score(episode_from_record(record([0, 0, 0]))).progress_points, 0)
        self.assertEqual(POLICY.score(episode_from_record(record([0, 1, 1]))).progress_points, 0)

    def test_manual_ore_and_planet_total_cannot_be_adapted(self):
        stale = record([0, 0, 0])
        stale["samples"][1]["produced_total"] = 5
        stale["samples"][1]["source"] = "inventory"
        with self.assertRaises(EvidenceError):
            episode_from_record(stale)
        manually_fed = record([0, 2, 5])
        manually_fed.pop("automated_input_ui_refs")
        with self.assertRaises(EvidenceError):
            episode_from_record(manually_fed)
        self.assertEqual(POLICY.score(episode_from_record(record([0, 0, 0]))).progress_points, 0)

    def test_live_entity_counter_requires_exact_checked_recipe_and_identity(self):
        payload = {"protocol_version": 1, "status": "ok", "session_id": "session-a", "planet_id": 102,
                   "entity_id": 3, "game_tick": 750188,
                   "entity": {"proto_id": 2302,
                              "assembler": {"recipe_id": 1, "cycle_count": 112,
                                            "extra_cycle_count": 0,
                                            "inputs": [{"item_id": 1001, "per_cycle": 1,
                                                        "buffered": 0}],
                                            "outputs": [{"item_id": 1101, "per_cycle": 1,
                                                         "buffered": 62}]}}}
        sample = iron_sample_from_entity(payload, save_copy_id="new-game-trial-a",
                                         checkpoint_sha256=HASH,
                                         game_version="0.10.35.29057")
        self.assertEqual((sample.entity_id, sample.produced_total), (3, 112))
        updated_sample = iron_sample_from_entity(payload, save_copy_id="new-game-trial-a",
                                                 checkpoint_sha256=HASH,
                                                 game_version="0.10.35.29088")
        self.assertEqual(updated_sample.game_version, "0.10.35.29088")
        with self.assertRaises(EvidenceError):
            iron_sample_from_entity(payload, save_copy_id="new-game-trial-a",
                                    checkpoint_sha256=HASH, game_version="0.10.35.29100")
        payload["entity"]["assembler"]["recipe_id"] = 2
        with self.assertRaises(EvidenceError):
            iron_sample_from_entity(payload, save_copy_id="new-game-trial-a",
                                    checkpoint_sha256=HASH, game_version="0.10.35.29057")

    def test_recipe_save_and_ui_identity_are_required(self):
        wrong_recipe = record([0, 1, 2])
        wrong_recipe["samples"][0]["recipe_id"] = 2
        with self.assertRaises(EvidenceError):
            episode_from_record(wrong_recipe)
        wrong_copy = record([0, 1, 2])
        wrong_copy["samples"][1]["save_copy_id"] = "another-copy"
        with self.assertRaises(EvidenceError):
            episode_from_record(wrong_copy)
        with self.assertRaises(EvidenceError):
            episode_from_record(record([0, 1, 2], ui=False))

    def test_early_item_farming_cannot_beat_verified_downstream_progress(self):
        early = POLICY.score(episode_from_record(record([0, 20, 40])))
        self.assertEqual(early.progress_points, 2)
        self.assertEqual(early.white_rate_per_tick, 0)
        downstream = replace(early, progress_points=3)
        self.assertGreater(downstream.rank, early.rank)


if __name__ == "__main__":
    unittest.main()
