"""Use the signed-in Codex CLI for bounded experiment proposals."""

import json
import os
import subprocess
import tempfile

from .model_planner import ModelPlannerError
from .responses_experiment import ResponsesExperimentModel


class CodexExperimentModel(ResponsesExperimentModel):
    def __init__(self, model, allowed_actions, *, command=("codex",), timeout=180, run=None):
        super().__init__(model or "Codex default", allowed_actions)
        if not command or not all(isinstance(part, str) and part for part in command):
            raise ModelPlannerError("invalid Codex command")
        self.command = tuple(command)
        self.timeout = timeout
        self.run = run or subprocess.run

    def _call(self, snapshot, name, instruction, description, properties):
        snapshot_json = json.dumps(snapshot, separators=(",", ":"), allow_nan=False)
        if len(snapshot_json.encode("utf-8")) > 64 * 1024:
            raise ModelPlannerError("snapshot is too large")
        prompt = (f"{instruction}\n{description}\nReturn one JSON object with exactly these fields: "
                  f"{json.dumps(properties, separators=(',', ':'))}. "
                  "Use null for inapplicable optional action parameters. "
                  "Do not call tools or claim that any action has occurred.\n"
                  f"Observed data:\n{snapshot_json}")
        in_wsl = os.path.basename(self.command[0]).lower() in ("wsl", "wsl.exe")
        workdir = "/tmp" if in_wsl or os.name != "nt" else tempfile.gettempdir()
        command = [*self.command, "exec", "--json", "--ephemeral", "--sandbox", "read-only",
                   "--skip-git-repo-check", "-C", workdir]
        if self.model != "Codex default":
            command.extend(["--model", self.model])
        command.append("-")
        try:
            completed = self.run(command, input=prompt, capture_output=True, text=True,
                                 timeout=self.timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ModelPlannerError("Codex CLI invocation failed") from exc
        if completed.returncode != 0:
            raise ModelPlannerError("Codex CLI did not complete")
        messages = []
        try:
            for line in completed.stdout.splitlines():
                event = json.loads(line)
                if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message":
                    messages.append(event["item"]["text"])
            if len(messages) != 1:
                raise ValueError("expected one final message")
            arguments = json.loads(messages[0])
        except (ValueError, KeyError, TypeError) as exc:
            raise ModelPlannerError("invalid Codex CLI proposal") from exc
        if not isinstance(arguments, dict) or set(arguments) != set(properties):
            raise ModelPlannerError("Codex CLI proposal failed local validation")
        return arguments
