"""Check subscription CLI proposal parsing and the local action boundary."""

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.codex_experiment import CodexExperimentModel
from dsp_agent.experiment_runner import Observation
from dsp_agent.model_planner import ModelPlannerError


def cli_reply(arguments):
    event = {"type": "item.completed", "item": {"type": "agent_message",
                                               "text": json.dumps(arguments)}}
    return SimpleNamespace(returncode=0, stdout=json.dumps(event) + "\n")


class CodexExperimentTests(unittest.TestCase):
    def test_goal_uses_read_only_signed_in_cli(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return cli_reply({"strategic_goal": "Build iron production",
                              "near_term_goal": "Inspect nearby iron",
                              "reason": "The observation lists iron veins"})

        model = CodexExperimentModel(None, {"inspect"}, run=fake_run)
        goal = model.choose_goal(Observation("session", 1, "evidence", "fingerprint", {"iron": True}))
        self.assertEqual(goal.near_term_goal, "Inspect nearby iron")
        command, kwargs = calls[0]
        self.assertIn("--ephemeral", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        self.assertNotIn("--model", command)
        self.assertIn('"iron":true', kwargs["input"])

    def test_invalid_proposal_is_rejected(self):
        model = CodexExperimentModel(None, {"inspect"},
                                     run=lambda *_args, **_kwargs: cli_reply({"unexpected": 1}))
        with self.assertRaises(ModelPlannerError):
            model.choose_goal(Observation("session", 1, "evidence", "fingerprint", {}))


if __name__ == "__main__":
    unittest.main()
