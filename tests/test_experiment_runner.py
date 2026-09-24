import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.experiments import ExperimentLedger
from dsp_agent.experiment_runner import (ExperimentPlan, ExperimentRunner,
                                         GoalChoice, Observation, RunnerError, Verification)


def observation(tick, state="same", session="session-a"):
    return Observation(session, tick, "obs-" + str(tick), state, {"iron_veins": 1})


class ExperimentRunnerTests(unittest.TestCase):
    def test_model_goal_and_memory_change_next_experiment(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                observations = iter((observation(10), observation(20), observation(30), observation(40)))
                seen_memories = []
                seen_history = []
                actions = []

                def plan(before, goal, memories):
                    seen_memories.append(memories)
                    hypothesis = "walking is enough" if not memories else "mining is required"
                    kind = "move" if not memories else "mine"
                    return ExperimentPlan({"kind": kind, "args": {"vein_id": 1}},
                                          hypothesis, "ore appears", "no ore appears")

                def execute(action, before, operation_id):
                    actions.append(action["kind"])
                    return {"operation_id": operation_id, "status": "completed"}

                def verify(before, after, planned, result):
                    if planned.action["kind"] == "move":
                        return Verification("failed", "walking moved mecha but gave no ore", "ui-no-ore")
                    return Verification("achieved", "ore appeared in the visible inventory", "ui-two-ore")

                def choose_goal(before):
                    seen_history.append(before.facts["recent_checked_attempts"])
                    near_term = "get iron" if not seen_history[-1] else "extract ore"
                    return GoalChoice("build an iron line", near_term, "ore is a prerequisite")

                runner = ExperimentRunner(
                    ledger, lambda: next(observations),
                    choose_goal,
                    plan, execute, verify, {"move", "mine"},
                )
                first = runner.run_once()
                second = runner.run_once()
                self.assertEqual((first["verdict"], second["verdict"]), ("failed", "achieved"))
                self.assertEqual(actions, ["move", "mine"])
                self.assertEqual(seen_memories[0], [])
                self.assertEqual(seen_memories[1][0]["explanation"],
                                 "walking moved mecha but gave no ore")
                self.assertEqual(seen_history[0], [])
                self.assertEqual(seen_history[1][0]["verdict"], "failed")
                self.assertEqual(seen_memories[1][0]["near_term_goal"], "get iron")

    def test_unlisted_action_never_reaches_executor(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                calls = []
                runner = ExperimentRunner(
                    ledger, lambda: observation(10),
                    lambda before: GoalChoice("progress", "iron", "needed"),
                    lambda before, goal, memories: ExperimentPlan(
                        {"kind": "spawn_item", "args": {}}, "fast", "ore", "none"),
                    lambda *_: calls.append("executed"), lambda *_: None, {"mine"},
                )
                with self.assertRaises(RunnerError):
                    runner.run_once()
                self.assertEqual(calls, [])

    def test_adapter_failure_is_unknown_and_blocks_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                runner = ExperimentRunner(
                    ledger, lambda: observation(10),
                    lambda before: GoalChoice("progress", "iron", "needed"),
                    lambda before, goal, memories: ExperimentPlan(
                        {"kind": "mine", "args": {"vein_id": 1}}, "reachable", "ore", "none"),
                    lambda *_: (_ for _ in ()).throw(TimeoutError("lost response")),
                    lambda *_: None, {"mine"},
                )
                with self.assertRaisesRegex(RunnerError, "reconciliation"):
                    runner.run_once()
                with self.assertRaisesRegex(ValueError, "unresolved"):
                    runner.run_once()

    def test_session_change_prevents_verification_and_next_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            with ExperimentLedger(Path(directory) / "experiments.sqlite") as ledger:
                observations = iter((observation(10), observation(11, session="session-b")))
                verified = []
                runner = ExperimentRunner(
                    ledger, lambda: next(observations),
                    lambda before: GoalChoice("progress", "iron", "needed"),
                    lambda before, goal, memories: ExperimentPlan(
                        {"kind": "mine", "args": {"vein_id": 1}}, "reachable", "ore", "none"),
                    lambda action, before, operation_id: {"operation_id": operation_id, "status": "completed"},
                    lambda *_: verified.append("called"), {"mine"},
                )
                with self.assertRaisesRegex(RunnerError, "session changed"):
                    runner.run_once()
                self.assertEqual(verified, [])


if __name__ == "__main__":
    unittest.main()
