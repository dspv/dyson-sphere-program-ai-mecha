"""Durable promotion of strategy versions from paired, verified episode scores."""

import json
import sqlite3
from pathlib import Path

from .reward import RewardError, RewardPolicy


class LearningError(ValueError):
    pass


class StrategyMemory:
    def __init__(self, path):
        location = Path(path)
        location.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(location))
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS active_strategies (
                goal TEXT PRIMARY KEY,
                strategy_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS comparisons (
                experiment_id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                baseline_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );
            """
        )

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def active(self, goal):
        row = self.connection.execute(
            "SELECT strategy_id FROM active_strategies WHERE goal = ?", (goal,)
        ).fetchone()
        return row[0] if row else None

    def consider(self, goal, experiment_id, policy, baseline, candidate):
        if (not isinstance(goal, str) or not goal or not isinstance(experiment_id, str)
                or not experiment_id or not isinstance(policy, RewardPolicy)):
            raise LearningError("goal, experiment ID, and reward policy are required")
        try:
            decision = policy.compare(baseline, candidate)
        except RewardError as exc:
            raise LearningError(str(exc)) from exc
        baseline_id = baseline[0].strategy_id
        candidate_id = candidate[0].strategy_id
        evidence = json.dumps({
            "baseline": [self._card(card) for card in baseline],
            "candidate": [self._card(card) for card in candidate],
        }, sort_keys=True, separators=(",", ":"))
        result = json.dumps(decision, sort_keys=True, separators=(",", ":"))
        with self.connection:
            prior = self.connection.execute(
                "SELECT goal, baseline_id, candidate_id, evidence_json, result_json "
                "FROM comparisons WHERE experiment_id = ?", (experiment_id,)
            ).fetchone()
            if prior is not None:
                if prior[:4] != (goal, baseline_id, candidate_id, evidence):
                    raise LearningError("experiment ID already names different evidence")
                return json.loads(prior[4])
            active = self.active(goal)
            if active is not None and active != baseline_id:
                raise LearningError("baseline is not the active strategy")
            if active is None:
                self.connection.execute("INSERT INTO active_strategies VALUES (?, ?)", (goal, baseline_id))
            self.connection.execute(
                "INSERT INTO comparisons VALUES (?, ?, ?, ?, ?, ?)",
                (experiment_id, goal, baseline_id, candidate_id, evidence, result),
            )
            if decision["promote"]:
                self.connection.execute(
                    "UPDATE active_strategies SET strategy_id = ? WHERE goal = ?",
                    (candidate_id, goal),
                )
        return decision

    @staticmethod
    def _card(card):
        return {
            "episode_id": card.episode_id,
            "strategy_id": card.strategy_id,
            "trial_key": card.trial_key,
            "game_version": card.game_version,
            "white_rate_numerator": card.white_rate_per_tick.numerator,
            "white_rate_denominator": card.white_rate_per_tick.denominator,
            "progress_points": card.progress_points,
            "elapsed_ticks": card.elapsed_ticks,
        }
