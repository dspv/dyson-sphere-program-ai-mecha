import sys
import tempfile
import sqlite3
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.experiments import ExperimentError, ExperimentLedger


class ExperimentLedgerTests(unittest.TestCase):
    def test_checked_outcome_survives_restart_and_is_retrievable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiments.sqlite"
            with ExperimentLedger(path) as ledger:
                goal = ledger.choose_goal("session-a", "reach white science", "find iron", "need ore", "obs-1")
                attempt = ledger.start_attempt("session-a", goal, "operation-1", "state-1",
                                               {"action": "inspect", "target": "iron"},
                                               "iron is nearby", "veins will appear", "no veins visible", "obs-1")
                ledger.record_verdict(attempt, "achieved", "obs-2", "iron veins appeared", "ui-1")
            with ExperimentLedger(path) as ledger:
                memory = ledger.memories("find iron")
                self.assertEqual(len(memory), 1)
                self.assertEqual(memory[0]["attempt_id"], attempt)
                self.assertEqual(memory[0]["evidence_ref"], "ui-1")
                self.assertEqual(memory[0]["prediction"], "veins will appear")
                with self.assertRaises(ExperimentError):
                    ledger.record_verdict(attempt, "failed", "obs-3", "changed mind", "ui-2")

    def test_unresolved_action_blocks_new_goal_or_action_until_reconciled(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                goal = ledger.choose_goal("session-a", "progress", "mine iron", "ore needed", "obs-1")
                attempt = ledger.start_attempt("session-a", goal, "operation-1", "state-1",
                                               {"action": "mine", "vein": 1}, "reachable", "two ore", "no ore", "obs-1")
                ledger.record_verdict(attempt, "partial", "obs-2", "order interrupted")
                with self.assertRaises(ExperimentError):
                    ledger.choose_goal("session-a", "progress", "build line", "need ingots", "obs-2")
                with self.assertRaises(ExperimentError):
                    ledger.start_attempt("session-a", goal, "operation-2", "state-2",
                                         {"action": "mine", "vein": 2}, "reachable", "two ore", "no ore", "obs-2")
                ledger.record_verdict(attempt, "failed", "obs-3", "no ore gained after interruption", "ui-3")
                self.assertEqual(ledger.memories("mine iron")[0]["verdict"], "failed")
                ledger.choose_goal("session-a", "progress", "build line", "need ingots", "obs-3")

    def test_identical_failure_needs_new_state_or_hypothesis(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                goal = ledger.choose_goal("session-a", "progress", "mine iron", "ore needed", "obs-1")
                action = {"action": "mine", "vein": 1}
                attempt = ledger.start_attempt("session-a", goal, "operation-1", "state-1", action,
                                               "reachable", "two ore", "no ore", "obs-1")
                ledger.record_verdict(attempt, "failed", "obs-2", "vein was unreachable", "ui-2")
                with self.assertRaises(ExperimentError):
                    ledger.start_attempt("session-a", goal, "operation-2", "state-1", action,
                                         "reachable", "two ore", "no ore", "obs-2")
                next_attempt = ledger.start_attempt("session-a", goal, "operation-3", "state-1", action,
                                                    "path may now be clear", "two ore", "no ore", "obs-2")
                self.assertEqual(ledger.attempt(next_attempt)["verdict"], "pending")
                self.assertEqual(len(ledger.memories("mine iron")), 1)

    def test_model_claim_without_evidence_cannot_become_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                goal = ledger.choose_goal("session-a", "progress", "find iron", "ore needed", "obs-1")
                attempt = ledger.start_attempt("session-a", goal, "operation-1", "state-1",
                                               {"action": "inspect"}, "nearby", "veins", "none", "obs-1")
                with self.assertRaises(ExperimentError):
                    ledger.record_verdict(attempt, "achieved", "obs-2", "model says it worked")
                self.assertEqual(ledger.memories("find iron"), [])

    def test_memory_from_other_game_version_is_not_supplied(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                goal = ledger.choose_goal("session-a", "progress", "find iron", "ore needed",
                                          "obs-1", game_version="build-a")
                attempt = ledger.start_attempt("session-a", goal, "operation-1", "state-1",
                                               {"kind": "inspect", "args": {}},
                                               "nearby", "veins", "none", "obs-1")
                ledger.record_verdict(attempt, "achieved", "obs-2", "veins observed", "ui-2")
                self.assertEqual(len(ledger.memories("find iron", game_version="build-a")), 1)
                self.assertEqual(ledger.memories("find iron", game_version="build-b"), [])

    def test_existing_goal_database_adds_version_column(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiments.sqlite"
            with sqlite3.connect(path) as connection:
                connection.execute(
                    "CREATE TABLE goals (goal_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, "
                    "strategic_goal TEXT NOT NULL, near_term_goal TEXT NOT NULL, reason TEXT NOT NULL, "
                    "observation_ref TEXT NOT NULL)"
                )
            with ExperimentLedger(path) as ledger:
                goal = ledger.choose_goal("session-a", "progress", "iron", "needed", "obs-1",
                                          game_version="build-a")
                self.assertIsNotNone(goal)


if __name__ == "__main__":
    unittest.main()
