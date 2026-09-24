"""Check the CLI's game-write boundary before any real model or bridge call."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.__main__ import main


class ExperimentCliTests(unittest.TestCase):
    def test_write_actions_require_explicit_flag(self):
        allowed_sets = []

        class FakeModel:
            def __init__(self, _model, allowed, **_kwargs):
                allowed_sets.append(allowed)

        class FakeRunner:
            def run_once(self):
                return {"verdict": "achieved"}

        with tempfile.TemporaryDirectory() as directory:
            with (patch("dsp_agent.__main__.CodexExperimentModel", FakeModel),
                  patch("dsp_agent.__main__.ExperimentLedger"),
                  patch("dsp_agent.__main__.BridgeExperimentAdapter"),
                  patch("dsp_agent.__main__.make_bridge_runner", return_value=FakeRunner()),
                  contextlib.redirect_stdout(io.StringIO())):
                for extra in ([], ["--allow-game-write"]):
                    code = main(["experiment-once", "--data-dir", directory, *extra])
                    self.assertEqual(code, 0)
        self.assertEqual(allowed_sets, [{"inspect", "inspect_entity"},
                                        {"inspect", "inspect_entity", "move", "mine"}])

    def test_bounded_run_stops_after_non_achieved_attempt(self):
        class FakeModel:
            def __init__(self, _model, _allowed, **_kwargs):
                pass

        class FakeRunner:
            def __init__(self):
                self.calls = 0

            def run_once(self):
                self.calls += 1
                return {"verdict": "achieved" if self.calls == 1 else "partial"}

        runner = FakeRunner()
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with (patch("dsp_agent.__main__.CodexExperimentModel", FakeModel),
                  patch("dsp_agent.__main__.ExperimentLedger"),
                  patch("dsp_agent.__main__.BridgeExperimentAdapter"),
                  patch("dsp_agent.__main__.make_bridge_runner", return_value=runner),
                  contextlib.redirect_stdout(output)):
                code = main(["experiment-run", "--data-dir", directory, "--max-attempts", "5"])
        self.assertEqual(code, 0)
        self.assertEqual(runner.calls, 2)
        self.assertEqual(json.loads(output.getvalue())["stopped_on"], "partial")


if __name__ == "__main__":
    unittest.main()
