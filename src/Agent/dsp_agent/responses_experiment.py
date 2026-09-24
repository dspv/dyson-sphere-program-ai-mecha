"""Structured Responses API goal and tactical proposals for the offline runner.

This adapter returns data. The runner and a separate game adapter decide whether
an action may execute; no Responses API result directly changes the game.
"""

from .experiment_runner import ExperimentPlan, GoalChoice, RunnerError
from .model_planner import ModelPlannerError, call_structured_function


ACTION_KINDS = frozenset({"inspect", "inspect_entity", "move", "mine"})


class ResponsesExperimentModel:
    def __init__(self, model, allowed_actions, *, api_key=None, timeout=30, opener=None):
        if (not isinstance(allowed_actions, (set, frozenset)) or not allowed_actions
                or not allowed_actions <= ACTION_KINDS):
            raise ModelPlannerError("unsupported experiment action set")
        self.model = model
        self.allowed_actions = frozenset(allowed_actions)
        self.api_key = api_key
        self.timeout = timeout
        self.opener = opener

    def _call(self, snapshot, name, instruction, description, properties):
        arguments, _, _ = call_structured_function(
            snapshot, self.model, name, instruction, description, properties,
            api_key=self.api_key, timeout=self.timeout, opener=self.opener,
        )
        return arguments

    def choose_goal(self, observation):
        observation.validate()
        arguments = self._call(
            {"session_id": observation.session_id, "game_tick": observation.game_tick,
             "facts": observation.facts, "allowed_actions": sorted(self.allowed_actions)},
            "choose_goal",
            "Choose a feasible strategic direction and one near-term goal from observed facts. "
            "You may change goals as evidence changes. Unknown facts remain unknown. "
            "Recent checked attempts are history, not current game observations; use them "
            "to avoid repeated checks that produced no new information. "
            "Choose a near-term goal that the listed actions can advance now. "
            "Construction placement and recipe changes are unavailable in this runner. "
            "Do not claim a game action or capability has succeeded.",
            "Propose the next self-chosen goal and explain its observed feasibility.",
            {"strategic_goal": {"type": "string"},
             "near_term_goal": {"type": "string"},
             "reason": {"type": "string"}},
        )
        choice = GoalChoice(**arguments)
        try:
            choice.validate()
        except RunnerError as exc:
            raise ModelPlannerError("invalid goal proposal") from exc
        return choice

    def plan(self, observation, goal, memories):
        observation.validate()
        goal.validate()
        if not isinstance(memories, list) or len(memories) > 32:
            raise ModelPlannerError("invalid memory context")
        lessons = [{"primitive_action_outcome": memory["verdict"], "action": memory["action"],
                    "hypothesis": memory["hypothesis"], "explanation": memory["explanation"],
                    "evidence_ref": memory["evidence_ref"],
                    "observed_context": memory.get("observed_context", {}),
                    "context_similarity": memory.get("context_similarity", 0)} for memory in memories]
        arguments = self._call(
            {"session_id": observation.session_id, "game_tick": observation.game_tick,
             "facts": observation.facts,
             "goal": {"strategic": goal.strategic_goal, "near_term": goal.near_term_goal,
                      "reason": goal.reason},
             "past_checked_attempts": lessons,
             "allowed_actions": sorted(self.allowed_actions)},
            "plan_experiment",
            "Choose one small experiment for the model-chosen goal. Use only the allowed actions. "
            "Past outcomes verify only primitive action effects, not strategic goal success "
            "or the truth of a free-text hypothesis. Use checked failures as counterexamples. "
            "Recheck the observed context before applying any past action. "
            "Predict an observable result and state what would falsify it. "
            "A proposal is not evidence of success. "
            "A generic inspect only refreshes the same summary; use inspect_entity for a "
            "specific observed nearby entity. The exact entity read reports proto, recipe, "
            "cycle count, and buffers for assemblers, but not power or connection status. "
            "Use past checked attempts across goal wordings to avoid repeating an unchanged "
            "read-only check. Their achieved verdict establishes only the primitive read. "
            "For inspect, set target_id, count, and item_id to null. "
            "For inspect_entity, set target_id to an observed nearby entity ID and count "
            "and item_id to null. "
            "For move, set target_id to the observed vein ID and count and item_id to null. "
            "For mine, set target_id to the observed vein ID, count from 1 to 5, "
            "and item_id to 1001 for iron or 1002 for copper.",
            "Propose exactly one bounded tactical action and falsifiable prediction.",
            {"kind": {"type": "string", "enum": sorted(self.allowed_actions)},
             "target_id": {"type": ["integer", "null"]},
             "count": {"type": ["integer", "null"]},
             "item_id": {"type": ["integer", "null"]},
             "hypothesis": {"type": "string"},
             "prediction": {"type": "string"},
             "falsifier": {"type": "string"}},
        )
        kind = arguments["kind"]
        target_id, count, item_id = (arguments[key] for key in ("target_id", "count", "item_id"))
        if kind == "inspect":
            if any(value is not None for value in (target_id, count, item_id)):
                raise ModelPlannerError("inspection proposal has action parameters")
            args = {}
        elif kind == "inspect_entity":
            if (isinstance(target_id, bool) or not isinstance(target_id, int) or target_id <= 0
                    or count is not None or item_id is not None):
                raise ModelPlannerError("invalid entity inspection proposal")
            args = {"entity_id": target_id}
        elif kind == "move":
            if (isinstance(target_id, bool) or not isinstance(target_id, int) or target_id <= 0
                    or count is not None or item_id is not None):
                raise ModelPlannerError("invalid movement proposal")
            args = {"vein_id": target_id}
        else:
            if (isinstance(target_id, bool) or not isinstance(target_id, int) or target_id <= 0
                    or isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 5
                    or isinstance(item_id, bool) or item_id not in (1001, 1002)):
                raise ModelPlannerError("invalid mining proposal")
            args = {"vein_id": target_id, "count": count, "item_id": item_id}
        planned = ExperimentPlan({"kind": kind, "args": args}, arguments["hypothesis"],
                                 arguments["prediction"], arguments["falsifier"])
        try:
            planned.validate(self.allowed_actions)
        except RunnerError as exc:
            raise ModelPlannerError("invalid experiment proposal") from exc
        return planned
