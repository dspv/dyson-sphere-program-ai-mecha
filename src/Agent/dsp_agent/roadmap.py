"""Select the next desired milestone from explicit observed evidence."""

import json
from pathlib import Path


class RoadmapError(ValueError):
    pass


class RoadmapPlanner:
    def __init__(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("status") != "desired_not_implemented":
            raise RoadmapError("unsupported roadmap schema or status")
        self.milestones = data.get("milestones")
        if not isinstance(self.milestones, list) or not self.milestones:
            raise RoadmapError("roadmap has no milestones")
        prior = set()
        all_signals = set()
        for milestone in self.milestones:
            if not isinstance(milestone, dict):
                raise RoadmapError("invalid milestone")
            identifier = milestone.get("id")
            requires = milestone.get("requires")
            done_when = milestone.get("done_when")
            if not isinstance(identifier, str) or not identifier or identifier in prior:
                raise RoadmapError("duplicate or empty milestone ID")
            if (not isinstance(requires, list) or not all(isinstance(item, str) for item in requires)
                    or len(requires) != len(set(requires)) or not set(requires).issubset(prior)):
                raise RoadmapError("milestone prerequisites must precede it")
            if not isinstance(done_when, list) or not done_when or not all(
                isinstance(signal, str) and signal for signal in done_when
            ):
                raise RoadmapError("milestone requires evidence signals")
            prior.add(identifier)
            all_signals.update(done_when)
        self.signal_names = frozenset(all_signals)

    def evaluate(self, evidence):
        if not isinstance(evidence, dict):
            raise RoadmapError("evidence must be an object")
        unknown_keys = set(evidence) - self.signal_names
        if unknown_keys:
            raise RoadmapError("unknown evidence signal: " + sorted(unknown_keys)[0])
        if any(value is not True and value is not False and value is not None
               for value in evidence.values()):
            raise RoadmapError("evidence values must be true, false, or null")
        completed = set()
        states = []
        current = None
        for milestone in self.milestones:
            missing = [signal for signal in milestone["done_when"] if evidence.get(signal) is not True]
            waiting_for = [name for name in milestone["requires"] if name not in completed]
            if not missing and not waiting_for:
                completed.add(milestone["id"])
                state = "complete"
            elif waiting_for:
                state = "waiting_for_prerequisite"
            else:
                state = "ready_for_work"
                if current is None:
                    current = milestone["id"]
            states.append({
                "id": milestone["id"],
                "state": state,
                "waiting_for": waiting_for,
                "missing_evidence": missing,
                "unknown_evidence": [signal for signal in missing if evidence.get(signal) is None],
            })
        return {"current_milestone": current, "all_complete": len(completed) == len(self.milestones),
                "milestones": states}
