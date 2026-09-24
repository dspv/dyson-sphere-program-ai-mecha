"""Evaluate game-measured production windows without guessing a rate target."""

from dataclasses import dataclass


class EvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class ProductionSample:
    session_id: str
    save_copy_id: str
    checkpoint_sha256: str
    game_version: str
    planet_id: int
    entity_id: int
    item_id: int
    recipe_id: int
    game_tick: int
    produced_total: int
    source: str

    def validate(self):
        if (not self.session_id or not self.save_copy_id or not self.game_version
                or len(self.checkpoint_sha256) != 64
                or any(character not in "0123456789abcdef" for character in self.checkpoint_sha256)
                or self.planet_id <= 0 or self.entity_id <= 0 or self.item_id <= 0
                or self.recipe_id <= 0):
            raise EvidenceError("production identity is incomplete")
        if self.game_tick < 0 or self.produced_total < 0:
            raise EvidenceError("negative tick or count")
        if self.source != "game_production_counter":
            raise EvidenceError("sample is not a game production counter")


class ProductionVerifier:
    """Require positive item production in consecutive measured game-time windows.

    Caller supplies a positive window duration and count from the experiment
    configuration. The adapter must supply a cumulative counter for one exact
    game entity and item; inventory changes are not accepted as production.
    """

    def __init__(self, window_ticks, required_windows):
        if not isinstance(window_ticks, int) or window_ticks <= 0:
            raise EvidenceError("window_ticks must be positive")
        if not isinstance(required_windows, int) or required_windows <= 1:
            raise EvidenceError("required_windows must exceed one")
        self.window_ticks = window_ticks
        self.required_windows = required_windows
        self.baseline = None
        self.last = None
        self.windows = []

    def observe(self, sample):
        if not isinstance(sample, ProductionSample):
            raise EvidenceError("expected a production sample")
        sample.validate()
        if self.last is None:
            self.baseline = sample
            self.last = sample
            return self.status()
        identity = (sample.session_id, sample.save_copy_id, sample.checkpoint_sha256,
                    sample.game_version, sample.planet_id, sample.entity_id,
                    sample.item_id, sample.recipe_id)
        prior_identity = (self.last.session_id, self.last.save_copy_id,
                          self.last.checkpoint_sha256, self.last.game_version,
                          self.last.planet_id, self.last.entity_id,
                          self.last.item_id, self.last.recipe_id)
        if identity != prior_identity:
            raise EvidenceError("production identity changed")
        if sample.game_tick <= self.last.game_tick:
            raise EvidenceError("game tick did not advance")
        if sample.produced_total < self.last.produced_total:
            raise EvidenceError("production counter moved backwards")
        self.last = sample
        elapsed = sample.game_tick - self.baseline.game_tick
        if elapsed < self.window_ticks:
            return self.status()
        delta = sample.produced_total - self.baseline.produced_total
        self.windows.append({
            "start_tick": self.baseline.game_tick,
            "end_tick": sample.game_tick,
            "produced": delta,
        })
        self.baseline = sample
        return self.status()

    def status(self):
        consecutive = 0
        for window in reversed(self.windows):
            if window["produced"] <= 0:
                break
            consecutive += 1
        return {
            "confirmed": consecutive >= self.required_windows,
            "consecutive_positive_windows": consecutive,
            "required_windows": self.required_windows,
            "windows": list(self.windows),
        }
