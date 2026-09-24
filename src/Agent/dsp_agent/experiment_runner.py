"""One model-directed experiment over injected observation and action adapters.

The runner has no default game adapter. A caller must provide observation,
decision, execution, and verification functions. It never awards success from
the model's own explanation or from an action response alone.
"""

import uuid
from dataclasses import dataclass


class RunnerError(RuntimeError):
    pass


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise RunnerError(name + " must be nonempty text of at most 2000 characters")


@dataclass(frozen=True)
class Observation:
    session_id: str
    game_tick: int
    evidence_ref: str
    state_fingerprint: str
    facts: dict

    def validate(self):
        for name in ("session_id", "evidence_ref", "state_fingerprint"):
            _text(getattr(self, name), name)
        if isinstance(self.game_tick, bool) or not isinstance(self.game_tick, int) or self.game_tick < 0:
            raise RunnerError("game tick must be nonnegative")
        if not isinstance(self.facts, dict):
            raise RunnerError("observation facts must be an object")


@dataclass(frozen=True)
class GoalChoice:
    strategic_goal: str
    near_term_goal: str
    reason: str

    def validate(self):
        for name in ("strategic_goal", "near_term_goal", "reason"):
            _text(getattr(self, name), name)


@dataclass(frozen=True)
class ExperimentPlan:
    action: dict
    hypothesis: str
    prediction: str
    falsifier: str

    def validate(self, allowed_actions):
        for name in ("hypothesis", "prediction", "falsifier"):
            _text(getattr(self, name), name)
        if (not isinstance(self.action, dict) or set(self.action) != {"kind", "args"}
                or not isinstance(self.action["kind"], str)
                or self.action["kind"] not in allowed_actions
                or not isinstance(self.action["args"], dict)):
            raise RunnerError("action is not in the allowed tool set")


@dataclass(frozen=True)
class Verification:
    verdict: str
    explanation: str
    evidence_ref: str | None = None

    def validate(self):
        if self.verdict not in ("achieved", "failed", "partial", "unknown"):
            raise RunnerError("invalid verifier verdict")
        _text(self.explanation, "explanation")
        if self.verdict in ("achieved", "failed"):
            _text(self.evidence_ref, "verification evidence reference")


class ExperimentRunner:
    def __init__(self, ledger, observe, choose_goal, plan, execute, verify,
                 allowed_actions, *, max_game_ticks=1800):
        if (not isinstance(allowed_actions, (set, frozenset)) or not allowed_actions
                or any(not isinstance(name, str) or not name for name in allowed_actions)):
            raise RunnerError("allowed actions must be a nonempty set")
        if (isinstance(max_game_ticks, bool) or not isinstance(max_game_ticks, int)
                or not 1 <= max_game_ticks <= 36000):
            raise RunnerError("invalid game tick budget")
        self.ledger = ledger
        self.observe = observe
        self.choose_goal = choose_goal
        self.plan = plan
        self.execute = execute
        self.verify = verify
        self.allowed_actions = frozenset(allowed_actions)
        self.max_game_ticks = max_game_ticks

    def run_once(self):
        """Record one decision and one action; return its stored ledger record."""
        before = self.observe()
        if not isinstance(before, Observation):
            raise RunnerError("observer did not return an Observation")
        before.validate()
        goal = self.choose_goal(before)
        if not isinstance(goal, GoalChoice):
            raise RunnerError("model did not return a GoalChoice")
        goal.validate()
        game_version = before.facts.get("game_version")
        memories = self.ledger.memories(goal.near_term_goal, game_version=game_version)
        planned = self.plan(before, goal, memories)
        if not isinstance(planned, ExperimentPlan):
            raise RunnerError("model did not return an ExperimentPlan")
        planned.validate(self.allowed_actions)
        goal_id = self.ledger.choose_goal(before.session_id, goal.strategic_goal,
                                          goal.near_term_goal, goal.reason, before.evidence_ref,
                                          game_version=game_version)
        operation_id = uuid.uuid4().hex
        attempt_id = self.ledger.start_attempt(
            before.session_id, goal_id, operation_id, before.state_fingerprint,
            planned.action, planned.hypothesis, planned.prediction,
            planned.falsifier, before.evidence_ref,
        )
        try:
            action_result = self.execute(planned.action, before, operation_id)
        except Exception as exc:
            self.ledger.record_verdict(attempt_id, "unknown", before.evidence_ref,
                                       "action adapter raised " + type(exc).__name__)
            raise RunnerError("action outcome needs reconciliation: " + attempt_id) from exc
        if (not isinstance(action_result, dict) or action_result.get("operation_id") != operation_id
                or action_result.get("status") not in ("completed", "partial", "rejected")):
            self.ledger.record_verdict(attempt_id, "unknown", before.evidence_ref,
                                       "action adapter returned no terminal matching result")
            raise RunnerError("action outcome needs reconciliation: " + attempt_id)
        try:
            after = self.observe()
            if not isinstance(after, Observation):
                raise RunnerError("observer did not return an Observation")
            after.validate()
        except Exception as exc:
            self.ledger.record_verdict(attempt_id, "unknown", before.evidence_ref,
                                       "fresh observation unavailable")
            raise RunnerError("observation needs reconciliation: " + attempt_id) from exc
        if after.session_id != before.session_id or after.game_tick < before.game_tick:
            self.ledger.record_verdict(attempt_id, "unknown", after.evidence_ref,
                                       "session or game tick changed unexpectedly")
            raise RunnerError("session changed; reconcile attempt: " + attempt_id)
        if after.game_tick - before.game_tick > self.max_game_ticks:
            self.ledger.record_verdict(attempt_id, "partial", after.evidence_ref,
                                       "game tick budget exceeded")
            return self.ledger.attempt(attempt_id)
        try:
            decision = self.verify(before, after, planned, action_result)
            if not isinstance(decision, Verification):
                raise RunnerError("verifier did not return a Verification")
            decision.validate()
        except Exception as exc:
            self.ledger.record_verdict(attempt_id, "unknown", after.evidence_ref,
                                       "verification unavailable")
            raise RunnerError("verification needs reconciliation: " + attempt_id) from exc
        self.ledger.record_verdict(attempt_id, decision.verdict, after.evidence_ref,
                                   decision.explanation, decision.evidence_ref)
        return self.ledger.attempt(attempt_id)
