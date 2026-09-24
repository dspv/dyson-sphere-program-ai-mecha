"""Bounded adapter from the experiment runner to verified bridge primitives.

This adapter never starts DSP. It only uses the loopback bridge when a caller
explicitly runs an experiment against an already loaded game session.
"""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

from .client import (read_entity, read_observation, read_operation, request_mine_vein,
                     request_move_to_vein)
from .bridge_verifier import verify_bridge_action
from .experiment_runner import ExperimentRunner, Observation


class BridgeExperimentError(RuntimeError):
    pass


class BridgeExperimentAdapter:
    def __init__(self, evidence_dir, *, base_url="http://127.0.0.1:38741",
                 max_polls=40, poll_interval=0.25, sleep=time.sleep,
                 observe_client=read_observation, operation_client=read_operation,
                 move_client=request_move_to_vein, mine_client=request_mine_vein,
                 entity_client=read_entity):
        if (isinstance(max_polls, bool) or not isinstance(max_polls, int)
                or not 1 <= max_polls <= 120):
            raise ValueError("max_polls must be between 1 and 120")
        if (isinstance(poll_interval, bool) or not isinstance(poll_interval, (int, float))
                or not 0 <= poll_interval <= 2):
            raise ValueError("poll_interval must be between 0 and 2 seconds")
        self.evidence_dir = Path(evidence_dir)
        self.base_url = base_url
        self.max_polls = max_polls
        self.poll_interval = poll_interval
        self.sleep = sleep
        self.observe_client = observe_client
        self.operation_client = operation_client
        self.move_client = move_client
        self.mine_client = mine_client
        self.entity_client = entity_client

    def _store(self, payload, stem):
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        destination = self.evidence_dir / (stem + "-" + digest[:16] + ".json")
        if not destination.exists():
            with tempfile.NamedTemporaryFile(dir=self.evidence_dir, prefix=".snapshot-", delete=False) as temporary:
                temporary.write(raw)
                temporary_path = Path(temporary.name)
            try:
                os.replace(temporary_path, destination)
            finally:
                temporary_path.unlink(missing_ok=True)
        return str(destination.resolve())

    def observe(self):
        payload = self.observe_client(self.base_url)
        if payload.get("status") != "ok":
            raise BridgeExperimentError("ordinary save is not loaded")
        session_id = payload.get("session_id")
        tick = payload.get("game_tick")
        planet = payload.get("planet")
        if (not isinstance(session_id, str) or re.fullmatch(r"[0-9a-f]{32}", session_id) is None
                or not isinstance(payload.get("game_version"), str) or not payload["game_version"]
                or isinstance(tick, bool) or not isinstance(tick, int) or tick < 0
                or not isinstance(planet, dict) or isinstance(planet.get("id"), bool)
                or not isinstance(planet.get("id"), int) or planet["id"] <= 0):
            raise BridgeExperimentError("loaded observation has incomplete identity")
        evidence_ref = self._store(payload, session_id + "-" + str(tick))
        facts = {name: payload.get(name) for name in (
            "game_version", "paused", "planet", "mecha_position", "inventory",
            "inhand_item", "nearby_veins", "nearby_entities", "recent_entities",
            "local_production")}
        state = {name: facts[name] for name in (
            "game_version", "paused", "planet", "mecha_position", "inventory",
            "inhand_item", "nearby_veins")}
        fingerprint = hashlib.sha256(json.dumps(
            state, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        return Observation(session_id, tick, evidence_ref, fingerprint, facts)

    def execute(self, action, before, operation_id):
        if not isinstance(before, Observation):
            raise BridgeExperimentError("before observation is required")
        before.validate()
        if (not isinstance(action, dict) or set(action) != {"kind", "args"}
                or not isinstance(action["args"], dict)):
            raise BridgeExperimentError("invalid action")
        kind, args = action["kind"], action["args"]
        if kind == "inspect":
            if args:
                raise BridgeExperimentError("inspection takes no arguments")
            return {"operation_id": operation_id, "status": "completed", "action": "inspect",
                    "session_id": before.session_id}
        if kind == "inspect_entity":
            if set(args) != {"entity_id"}:
                raise BridgeExperimentError("entity inspection requires one entity ID")
            entity_id = args["entity_id"]
            if isinstance(entity_id, bool) or not isinstance(entity_id, int) or entity_id <= 0:
                raise BridgeExperimentError("invalid entity ID")
            nearby = before.facts.get("nearby_entities")
            entities = nearby.get("entities") if isinstance(nearby, dict) else None
            if (not isinstance(entities, list) or not any(
                    isinstance(entry, dict) and entry.get("id") == entity_id for entry in entities)):
                raise BridgeExperimentError("entity was not in the bounded observation")
            detail = self.entity_client(entity_id, self.base_url)
            if (not isinstance(detail, dict) or detail.get("status") != "ok"
                    or detail.get("session_id") != before.session_id
                    or detail.get("planet_id") != before.facts["planet"]["id"]
                    or detail.get("entity_id") != entity_id
                    or isinstance(detail.get("game_tick"), bool)
                    or not isinstance(detail.get("game_tick"), int)
                    or detail["game_tick"] < before.game_tick
                    or not isinstance(detail.get("entity"), dict)):
                raise BridgeExperimentError("exact entity read changed identity")
            evidence_ref = self._store(detail, before.session_id + "-entity-" +
                                       str(entity_id) + "-" + str(detail["game_tick"]))
            return {"operation_id": operation_id, "status": "completed",
                    "action": "inspect_entity", "session_id": before.session_id,
                    "entity_id": entity_id, "entity": detail["entity"],
                    "evidence_ref": evidence_ref}
        fresh = self.observe()
        if (fresh.session_id != before.session_id
                or fresh.state_fingerprint != before.state_fingerprint):
            return {"operation_id": operation_id, "status": "rejected", "action": kind,
                    "session_id": before.session_id, "reason": "stale_snapshot",
                    "fresh_observation_ref": fresh.evidence_ref}
        if before.facts.get("paused") is not False:
            raise BridgeExperimentError("game is paused or pause status unknown")
        nearby = before.facts.get("nearby_veins")
        if not isinstance(nearby, dict) or not isinstance(nearby.get("veins"), list):
            raise BridgeExperimentError("nearby vein observation is unavailable")
        if kind == "move" and set(args) == {"vein_id"}:
            vein_id = args["vein_id"]
            item_id = None
            count = None
        elif kind == "mine" and set(args) == {"vein_id", "count", "item_id"}:
            vein_id, count, item_id = (args[key] for key in ("vein_id", "count", "item_id"))
            if (isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 5
                    or isinstance(item_id, bool) or item_id not in (1001, 1002)):
                raise BridgeExperimentError("invalid bounded mining request")
        else:
            raise BridgeExperimentError("unsupported bridge action")
        if isinstance(vein_id, bool) or not isinstance(vein_id, int) or vein_id <= 0:
            raise BridgeExperimentError("invalid vein ID")
        vein = next((entry for entry in nearby["veins"]
                     if isinstance(entry, dict) and entry.get("id") == vein_id), None)
        if vein is None:
            raise BridgeExperimentError("target vein was not in the bounded observation")
        if kind == "mine" and vein.get("product_id") != item_id:
            raise BridgeExperimentError("target vein does not yield requested ore")
        if kind == "move":
            result = self.move_client(before.session_id, vein_id, operation_id, self.base_url)
        else:
            result = self.mine_client(before.session_id, vein_id, count, operation_id,
                                      self.base_url, item_id=item_id)
        self._validate_result(result, before.session_id, operation_id, kind, vein_id, item_id, count)
        for _ in range(self.max_polls):
            if result["status"] in ("completed", "partial", "rejected"):
                return result
            self.sleep(self.poll_interval)
            result = self.operation_client(operation_id, self.base_url)
            self._validate_result(result, before.session_id, operation_id, kind, vein_id, item_id, count)
        raise BridgeExperimentError("operation still pending; reconcile its ID before another action")

    @staticmethod
    def _validate_result(result, session_id, operation_id, kind, vein_id, item_id, count):
        if (not isinstance(result, dict) or result.get("operation_id") != operation_id
                or result.get("session_id") != session_id or result.get("action") != kind
                or result.get("vein_id") != vein_id
                or result.get("status") not in ("pending", "running", "completed", "partial", "rejected")):
            raise BridgeExperimentError("bridge operation identity changed")
        if kind == "mine" and (result.get("item_id") != item_id or result.get("requested_count") != count):
            raise BridgeExperimentError("mining operation identity changed")


def make_bridge_runner(ledger, model, adapter, *, max_game_ticks=1800):
    """Wire a model provider to the bridge without starting a game session."""
    if not isinstance(adapter, BridgeExperimentAdapter):
        raise TypeError("bridge experiment adapter is required")
    allowed = model.allowed_actions
    if not allowed <= {"inspect", "inspect_entity", "move", "mine"}:
        raise ValueError("model contains an unsupported bridge action")
    return ExperimentRunner(
        ledger, adapter.observe, model.choose_goal, model.plan, adapter.execute,
        verify_bridge_action, allowed, max_game_ticks=max_game_ticks,
    )
