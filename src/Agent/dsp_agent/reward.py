"""Offline reward scoring for verified, comparable DSP episodes.

The scorer consumes evidence; it cannot turn an unverified bridge value into
game proof. White-matrix throughput is the primary objective. Intermediate
signals yield one-time progress points, never points per produced item.
"""

import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


class RewardError(ValueError):
    pass


PRODUCTION_SOURCES = frozenset({"entity_counter", "attributed_clean_save_counter"})
OTHER_SOURCES = frozenset({"visible_game_observation"})


@dataclass(frozen=True)
class ProductionWindow:
    game_ticks: int
    produced: int

    def validate(self):
        if (isinstance(self.game_ticks, bool) or not isinstance(self.game_ticks, int)
                or self.game_ticks <= 0 or isinstance(self.produced, bool)
                or not isinstance(self.produced, int) or self.produced <= 0):
            raise RewardError("every sustained production window must be positive")


@dataclass(frozen=True)
class SignalProof:
    name: str
    source: str
    evidence_id: str
    windows: tuple[ProductionWindow, ...] = ()

    def validate(self):
        if (not isinstance(self.name, str) or not self.name
                or not isinstance(self.evidence_id, str) or not self.evidence_id
                or not isinstance(self.windows, tuple)):
            raise RewardError("signal and evidence ID are required")
        production = self.name.endswith("_output_sustained")
        allowed = PRODUCTION_SOURCES if production else OTHER_SOURCES
        if self.source not in allowed:
            raise RewardError("signal has an unsupported evidence source")
        if production:
            if len(self.windows) < 2:
                raise RewardError("sustained output needs multiple production windows")
            for window in self.windows:
                if not isinstance(window, ProductionWindow):
                    raise RewardError("invalid production window")
                window.validate()
        elif self.windows:
            raise RewardError("nonproduction signal cannot claim output windows")


@dataclass(frozen=True)
class WhiteThroughput:
    source: str
    evidence_id: str
    windows: tuple[ProductionWindow, ...]

    def rate_per_tick(self):
        if (self.source not in PRODUCTION_SOURCES or not isinstance(self.evidence_id, str)
                or not self.evidence_id or not isinstance(self.windows, tuple)
                or len(self.windows) < 2):
            raise RewardError("white throughput needs attributed, multi-window game evidence")
        for window in self.windows:
            if not isinstance(window, ProductionWindow):
                raise RewardError("invalid white production window")
            window.validate()
        return Fraction(sum(window.produced for window in self.windows),
                        sum(window.game_ticks for window in self.windows))


@dataclass(frozen=True)
class EpisodeResult:
    episode_id: str
    strategy_id: str
    trial_key: str
    game_version: str
    ordinary_mode: bool
    elapsed_ticks: int
    start_proofs: tuple[SignalProof, ...]
    end_proofs: tuple[SignalProof, ...]
    white_throughput: WhiteThroughput | None = None


@dataclass(frozen=True)
class RewardCard:
    episode_id: str
    strategy_id: str
    trial_key: str
    game_version: str
    white_rate_per_tick: Fraction
    progress_points: int
    elapsed_ticks: int

    @property
    def rank(self):
        return (self.white_rate_per_tick, self.progress_points, -self.elapsed_ticks)


class RewardPolicy:
    def __init__(self, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("status") != "policy_parameters_not_game_measurements":
            raise RewardError("unsupported reward policy")
        self.points = data.get("signal_points")
        self.minimum_paired_trials = data.get("minimum_paired_trials")
        if (not isinstance(self.points, dict) or not self.points
                or any(not isinstance(name, str) or not name or isinstance(value, bool)
                       or not isinstance(value, int) or value <= 0
                       for name, value in self.points.items())
                or isinstance(self.minimum_paired_trials, bool)
                or not isinstance(self.minimum_paired_trials, int)
                or self.minimum_paired_trials < 2
                or "white_matrix_output_sustained" not in self.points):
            raise RewardError("invalid reward policy values")

    def score(self, episode):
        if (not isinstance(episode, EpisodeResult)
                or not all(isinstance(value, str) and value for value in (
                    episode.episode_id, episode.strategy_id, episode.trial_key, episode.game_version))):
            raise RewardError("episode identity is incomplete")
        if episode.ordinary_mode is not True:
            raise RewardError("only ordinary-mode episodes can be scored")
        if (isinstance(episode.elapsed_ticks, bool) or not isinstance(episode.elapsed_ticks, int)
                or episode.elapsed_ticks <= 0):
            raise RewardError("elapsed game ticks must be positive")
        start = self._proof_names(episode.start_proofs)
        end = self._proof_names(episode.end_proofs)
        progress = sum(self.points[name] for name in end) - sum(self.points[name] for name in start)
        white_rate = Fraction(0)
        if "white_matrix_output_sustained" in end:
            if episode.white_throughput is None:
                raise RewardError("sustained white signal needs measured throughput")
            white_proof = next(proof for proof in episode.end_proofs
                               if proof.name == "white_matrix_output_sustained")
            if (white_proof.source != episode.white_throughput.source
                    or white_proof.evidence_id != episode.white_throughput.evidence_id
                    or white_proof.windows != episode.white_throughput.windows):
                raise RewardError("white throughput does not match its signal proof")
            white_rate = episode.white_throughput.rate_per_tick()
        elif episode.white_throughput is not None:
            raise RewardError("white throughput needs a sustained white signal")
        return RewardCard(episode.episode_id, episode.strategy_id, episode.trial_key,
                          episode.game_version, white_rate, progress, episode.elapsed_ticks)

    def _proof_names(self, proofs):
        if not isinstance(proofs, tuple):
            raise RewardError("proofs must be a tuple")
        names = set()
        for proof in proofs:
            if not isinstance(proof, SignalProof):
                raise RewardError("invalid signal proof")
            proof.validate()
            if proof.name not in self.points or proof.name in names:
                raise RewardError("unknown or duplicate reward signal")
            names.add(proof.name)
        return names

    def compare(self, baseline, candidate):
        """Promote only if paired trials show improvement and no regression."""
        if not isinstance(baseline, (list, tuple)) or not isinstance(candidate, (list, tuple)):
            raise RewardError("paired trial collections are required")
        if len(baseline) < self.minimum_paired_trials or len(candidate) != len(baseline):
            raise RewardError("insufficient paired trials")
        if any(not isinstance(card, RewardCard) for card in (*baseline, *candidate)):
            raise RewardError("invalid reward card")
        old = {card.trial_key: card for card in baseline}
        new = {card.trial_key: card for card in candidate}
        if len(old) != len(baseline) or len(new) != len(candidate) or set(old) != set(new):
            raise RewardError("trial keys must pair exactly once")
        versions = {card.game_version for card in (*baseline, *candidate)}
        old_ids = {card.strategy_id for card in baseline}
        new_ids = {card.strategy_id for card in candidate}
        if (len(versions) != 1 or len(old_ids) != 1 or len(new_ids) != 1
                or old_ids == new_ids):
            raise RewardError("strategy or game version mismatch")
        improvements = [new[key].rank > old[key].rank for key in old]
        regressions = [new[key].rank < old[key].rank for key in old]
        return {"promote": any(improvements) and not any(regressions),
                "improved_trials": sum(improvements), "regressed_trials": sum(regressions),
                "paired_trials": len(old)}
