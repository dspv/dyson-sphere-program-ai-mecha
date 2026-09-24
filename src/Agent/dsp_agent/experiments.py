"""Local ledger for model-chosen goals and checked tactical experiments.

This module records decisions and verifier results. It never executes game tools
or treats a model explanation as proof of an observed outcome.
"""

import json
import sqlite3
import uuid
from pathlib import Path


class ExperimentError(ValueError):
    pass


def _required(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ExperimentError(name + " is required")
    return value


def _json(value):
    if not isinstance(value, dict):
        raise ExperimentError("action must be an object")
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ExperimentError("action must contain JSON values") from exc


def context_from_facts(facts):
    """Keep a small observed applicability summary, without inferred facts."""
    if not isinstance(facts, dict):
        raise ExperimentError("observation facts must be an object")
    planet = facts.get("planet")
    inventory = facts.get("inventory")
    veins = facts.get("nearby_veins")
    entities = facts.get("nearby_entities")
    inhand = facts.get("inhand_item")

    def ids(container, entries, key):
        values = container.get(entries) if isinstance(container, dict) else None
        if not isinstance(values, list):
            return []
        return sorted({entry[key] for entry in values
                       if isinstance(entry, dict) and isinstance(entry.get(key), int)
                       and not isinstance(entry[key], bool) and entry[key] > 0})

    return {
        "planet_id": planet.get("id") if isinstance(planet, dict) else None,
        "inventory_item_ids": ids(inventory, "items", "item_id"),
        "nearby_resource_item_ids": ids(veins, "veins", "product_id"),
        "nearby_entity_proto_ids": ids(entities, "entities", "proto_id"),
        "inhand_item_id": inhand.get("item_id") if isinstance(inhand, dict) else None,
    }


def _context_similarity(current, past):
    if not current or not past:
        return 0
    score = 0
    if current.get("planet_id") is not None and current.get("planet_id") == past.get("planet_id"):
        score += 1
    if current.get("inhand_item_id") is not None and current.get("inhand_item_id") == past.get("inhand_item_id"):
        score += 1
    for key, weight in (("nearby_resource_item_ids", 3),
                        ("nearby_entity_proto_ids", 2), ("inventory_item_ids", 1)):
        left, right = set(current.get(key) or []), set(past.get(key) or [])
        if left and right:
            score += weight * len(left & right) / len(left | right)
    return score


class ExperimentLedger:
    """Persist goals, attempted actions, and external verification decisions."""

    def __init__(self, path):
        location = Path(path)
        location.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(location))
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                strategic_goal TEXT NOT NULL,
                near_term_goal TEXT NOT NULL,
                reason TEXT NOT NULL,
                observation_ref TEXT NOT NULL,
                game_version TEXT
            );
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL REFERENCES goals(goal_id),
                operation_id TEXT NOT NULL UNIQUE,
                state_fingerprint TEXT NOT NULL,
                action_json TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                prediction TEXT NOT NULL,
                falsifier TEXT NOT NULL,
                before_ref TEXT NOT NULL,
                context_json TEXT,
                verdict TEXT NOT NULL DEFAULT 'pending',
                after_ref TEXT,
                evidence_ref TEXT,
                explanation TEXT
            );
            """
        )
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(goals)")}
        if "game_version" not in columns:
            self.connection.execute("ALTER TABLE goals ADD COLUMN game_version TEXT")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(attempts)")}
        if "context_json" not in columns:
            self.connection.execute("ALTER TABLE attempts ADD COLUMN context_json TEXT")

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def choose_goal(self, session_id, strategic_goal, near_term_goal, reason, observation_ref,
                    game_version=None):
        values = [_required(value, name) for value, name in (
            (session_id, "session ID"), (strategic_goal, "strategic goal"),
            (near_term_goal, "near-term goal"), (reason, "reason"),
            (observation_ref, "observation reference"))]
        if game_version is not None:
            _required(game_version, "game version")
        with self.connection:
            if self.connection.execute(
                "SELECT 1 FROM attempts a JOIN goals g ON a.goal_id = g.goal_id "
                "WHERE g.session_id = ? AND a.verdict IN ('pending', 'partial', 'unknown') LIMIT 1",
                (session_id,),
            ).fetchone():
                raise ExperimentError("unresolved attempt requires reconciliation")
            goal_id = uuid.uuid4().hex
            self.connection.execute(
                "INSERT INTO goals (goal_id, session_id, strategic_goal, near_term_goal, reason, "
                "observation_ref, game_version) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (goal_id, *values, game_version),
            )
        return goal_id

    def start_attempt(self, session_id, goal_id, operation_id, state_fingerprint,
                      action, hypothesis, prediction, falsifier, before_ref, context=None):
        for value, name in ((session_id, "session ID"), (goal_id, "goal ID"),
                            (operation_id, "operation ID"), (state_fingerprint, "state fingerprint"),
                            (hypothesis, "hypothesis"), (prediction, "prediction"),
                            (falsifier, "falsifier"), (before_ref, "before reference")):
            _required(value, name)
        encoded = _json(action)
        encoded_context = _json({} if context is None else context)
        with self.connection:
            goal = self.connection.execute("SELECT session_id FROM goals WHERE goal_id = ?", (goal_id,)).fetchone()
            if goal is None or goal[0] != session_id:
                raise ExperimentError("goal does not belong to this session")
            if self.connection.execute(
                "SELECT 1 FROM attempts a JOIN goals g ON a.goal_id = g.goal_id "
                "WHERE g.session_id = ? AND a.verdict IN ('pending', 'partial', 'unknown') LIMIT 1",
                (session_id,),
            ).fetchone():
                raise ExperimentError("unresolved attempt requires reconciliation")
            if self.connection.execute(
                "SELECT 1 FROM attempts a JOIN goals g ON a.goal_id = g.goal_id "
                "WHERE g.session_id = ? AND a.state_fingerprint = ? AND a.action_json = ? "
                "AND a.hypothesis = ? AND a.verdict = 'failed' LIMIT 1",
                (session_id, state_fingerprint, encoded, hypothesis),
            ).fetchone():
                raise ExperimentError("identical failed experiment needs changed state or hypothesis")
            if self.connection.execute("SELECT 1 FROM attempts WHERE operation_id = ?", (operation_id,)).fetchone():
                raise ExperimentError("operation ID already used")
            attempt_id = uuid.uuid4().hex
            self.connection.execute(
                "INSERT INTO attempts (attempt_id, goal_id, operation_id, state_fingerprint, "
                "action_json, hypothesis, prediction, falsifier, before_ref, context_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (attempt_id, goal_id, operation_id, state_fingerprint, encoded,
                 hypothesis, prediction, falsifier, before_ref, encoded_context),
            )
        return attempt_id

    def record_verdict(self, attempt_id, verdict, after_ref, explanation, evidence_ref=None):
        _required(attempt_id, "attempt ID")
        _required(after_ref, "after reference")
        _required(explanation, "explanation")
        if verdict not in ("achieved", "failed", "partial", "unknown"):
            raise ExperimentError("invalid verdict")
        if verdict in ("achieved", "failed"):
            _required(evidence_ref, "evidence reference")
        with self.connection:
            row = self.connection.execute("SELECT verdict FROM attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
            if row is None:
                raise KeyError(attempt_id)
            if row[0] not in ("pending", "partial", "unknown"):
                raise ExperimentError("verified verdict is immutable")
            self.connection.execute(
                "UPDATE attempts SET verdict = ?, after_ref = ?, evidence_ref = ?, explanation = ? "
                "WHERE attempt_id = ?",
                (verdict, after_ref, evidence_ref, explanation, attempt_id),
            )

    def attempt(self, attempt_id):
        row = self.connection.execute(
            "SELECT a.operation_id, a.goal_id, g.session_id, g.strategic_goal, g.near_term_goal, "
            "g.game_version, "
            "a.state_fingerprint, a.action_json, a.hypothesis, a.prediction, a.falsifier, "
            "a.before_ref, a.context_json, a.verdict, a.after_ref, a.evidence_ref, a.explanation "
            "FROM attempts a JOIN goals g ON a.goal_id = g.goal_id WHERE a.attempt_id = ?",
            (attempt_id,),
        ).fetchone()
        if row is None:
            raise KeyError(attempt_id)
        keys = ("operation_id", "goal_id", "session_id", "strategic_goal", "near_term_goal",
                "game_version",
                "state_fingerprint", "action", "hypothesis", "prediction", "falsifier",
                "before_ref", "observed_context", "verdict", "after_ref", "evidence_ref", "explanation")
        result = dict(zip(keys, row))
        result["action"] = json.loads(result["action"])
        result["observed_context"] = json.loads(result["observed_context"] or "{}")
        result["attempt_id"] = attempt_id
        return result

    def memories(self, near_term_goal, limit=8, *, game_version=None, context=None):
        _required(near_term_goal, "near-term goal")
        if game_version is not None:
            _required(game_version, "game version")
        if context is not None and not isinstance(context, dict):
            raise ExperimentError("memory context must be an object")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 32:
            raise ExperimentError("memory limit must be between 1 and 32")
        query = (
            "SELECT a.attempt_id FROM attempts a JOIN goals g ON a.goal_id = g.goal_id "
            "WHERE g.near_term_goal = ? AND a.verdict IN ('achieved', 'failed') "
            "AND a.evidence_ref IS NOT NULL"
        )
        parameters = [near_term_goal]
        if game_version is not None:
            query += " AND g.game_version = ?"
            parameters.append(game_version)
        query += " ORDER BY a.rowid DESC LIMIT 128"
        rows = self.connection.execute(query, parameters).fetchall()
        ranked = []
        for recency, row in enumerate(rows):
            memory = self.attempt(row[0])
            similarity = _context_similarity(context, memory["observed_context"])
            memory["context_similarity"] = similarity
            ranked.append((similarity, -recency, memory))
        ranked.sort(key=lambda candidate: (candidate[0], candidate[1]), reverse=True)
        return [candidate[2] for candidate in ranked[:limit]]
