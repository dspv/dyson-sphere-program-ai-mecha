"""Bounded loopback client for bridge observations and guarded game actions."""

import json
import uuid
from urllib import error, parse, request


class BridgeError(RuntimeError):
    pass


def _request(base_url, path, timeout, max_bytes, method="GET"):
    parsed = parse.urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise BridgeError("bridge address must use loopback HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise BridgeError("bridge address must be a plain loopback origin")
    url = base_url.rstrip("/") + path
    try:
        body = b"" if method == "POST" else None
        with request.urlopen(request.Request(url, data=body, method=method), timeout=timeout) as response:
            data = response.read(max_bytes)
            if response.read(1):
                raise BridgeError("oversized bridge response")
    except (error.URLError, TimeoutError) as exc:
        raise BridgeError("bridge unavailable: " + str(exc)) from exc
    try:
        payload = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc:
        raise BridgeError("invalid bridge JSON") from exc
    if not isinstance(payload, dict) or payload.get("protocol_version") != 1:
        raise BridgeError("unsupported bridge protocol")
    return payload


def _read(base_url, path, timeout, max_bytes):
    return _request(base_url, path, timeout, max_bytes)


def _operation_id(value):
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise BridgeError("operation ID must be a UUID") from exc
    if parsed.hex != value:
        raise BridgeError("operation ID must use 32 lowercase hex digits")
    return value


def read_health(base_url="http://127.0.0.1:38741", timeout=3):
    payload = _read(base_url, "/v1/health", timeout, 4096)
    if payload.get("status") not in ("bootstrap_only", "observer_unverified", "stage_b_unverified", "stage_c_experimental"):
        raise BridgeError("unexpected bridge status")
    if not isinstance(payload.get("bridge_version"), str):
        raise BridgeError("missing bridge version")
    return payload


def request_move_to_vein(session_id, vein_id, operation_id, base_url="http://127.0.0.1:38741", timeout=3):
    _operation_id(operation_id)
    _operation_id(session_id)
    if isinstance(vein_id, bool) or not isinstance(vein_id, int) or vein_id <= 0:
        raise BridgeError("vein ID must be a positive integer")
    query = parse.urlencode({"operation_id": operation_id, "session_id": session_id, "vein_id": vein_id})
    payload = _request(base_url, "/v1/move-to-vein?" + query, timeout, 8192, "POST")
    if payload.get("operation_id") != operation_id or payload.get("status") not in ("pending", "running", "completed", "partial", "rejected"):
        raise BridgeError("invalid movement response")
    return payload


def request_mine_vein(session_id, vein_id, count, operation_id, base_url="http://127.0.0.1:38741", timeout=3, *, item_id=1001):
    _operation_id(operation_id)
    _operation_id(session_id)
    if isinstance(vein_id, bool) or not isinstance(vein_id, int) or vein_id <= 0:
        raise BridgeError("vein ID must be a positive integer")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1 or count > 5:
        raise BridgeError("mining count must be between 1 and 5")
    if item_id not in (1001, 1002) or isinstance(item_id, bool):
        raise BridgeError("only iron and copper ore are supported")
    parameters = {"operation_id": operation_id, "session_id": session_id, "vein_id": vein_id, "count": count}
    if item_id != 1001:
        parameters["item_id"] = item_id
    query = parse.urlencode(parameters)
    payload = _request(base_url, "/v1/mine-vein?" + query, timeout, 8192, "POST")
    if (payload.get("operation_id") != operation_id or payload.get("action") != "mine"
            or payload.get("item_id") != item_id
            or payload.get("status") not in ("pending", "running", "completed", "partial", "rejected")):
        raise BridgeError("invalid mining response")
    return payload


def read_operation(operation_id, base_url="http://127.0.0.1:38741", timeout=3):
    _operation_id(operation_id)
    query = parse.urlencode({"operation_id": operation_id})
    payload = _read(base_url, "/v1/operation?" + query, timeout, 8192)
    if payload.get("operation_id") != operation_id or payload.get("status") not in ("pending", "running", "completed", "partial", "rejected"):
        raise BridgeError("invalid operation response")
    return payload


def read_observation(base_url="http://127.0.0.1:38741", timeout=3):
    payload = _read(base_url, "/v1/observe", timeout, 65536)
    if payload.get("status") not in ("ok", "not_loaded"):
        raise BridgeError("observation failed: " + str(payload.get("error", "unknown")))
    if not isinstance(payload.get("game_version"), str):
        raise BridgeError("missing game version")
    if payload["status"] == "ok":
        if not isinstance(payload.get("session_id"), str) or not isinstance(payload.get("game_tick"), int):
            raise BridgeError("missing loaded session identity")
        for key in ("inventory", "nearby_entities", "recent_entities", "nearby_veins"):
            value = payload.get(key)
            if value is not None and not isinstance(value, dict):
                raise BridgeError("invalid " + key)
    return payload


def read_entity(entity_id, base_url="http://127.0.0.1:38741", timeout=3):
    if isinstance(entity_id, bool) or not isinstance(entity_id, int) or entity_id <= 0:
        raise BridgeError("entity ID must be a positive integer")
    query = parse.urlencode({"entity_id": entity_id})
    payload = _read(base_url, "/v1/entity?" + query, timeout, 8192)
    if payload.get("status") not in ("ok", "not_loaded"):
        raise BridgeError("entity read failed: " + str(payload.get("error", "unknown")))
    if payload["status"] == "ok":
        if (payload.get("entity_id") != entity_id or not isinstance(payload.get("session_id"), str)
                or isinstance(payload.get("planet_id"), bool) or not isinstance(payload.get("planet_id"), int)
                or isinstance(payload.get("game_tick"), bool) or not isinstance(payload.get("game_tick"), int)):
            raise BridgeError("invalid entity identity")
        entity = payload.get("entity")
        if entity is not None and not isinstance(entity, dict):
            raise BridgeError("invalid entity data")
    return payload


def read_build_preview(base_url="http://127.0.0.1:38741", timeout=3):
    payload = _read(base_url, "/v1/build-preview", timeout, 4096)
    if payload.get("status") not in ("ok", "not_loaded"):
        raise BridgeError("build preview read failed: " + str(payload.get("error", "unknown")))
    if payload["status"] == "ok":
        count = payload.get("preview_count")
        if (not isinstance(payload.get("session_id"), str)
                or isinstance(payload.get("planet_id"), bool) or not isinstance(payload.get("planet_id"), int)
                or isinstance(payload.get("game_tick"), bool) or not isinstance(payload.get("game_tick"), int)
                or not isinstance(payload.get("active"), bool)
                or isinstance(count, bool) or not isinstance(count, int) or count < 0):
            raise BridgeError("invalid build preview identity")
        preview = payload.get("single_preview")
        if (preview is not None and (count != 1 or not payload["active"] or not isinstance(preview, dict)
                or isinstance(preview.get("item_id"), bool)
                or (preview.get("item_id") is not None and
                    (not isinstance(preview["item_id"], int) or preview["item_id"] <= 0))
                or not isinstance(preview.get("position"), dict)
                or not isinstance(preview.get("condition"), str)
                or isinstance(preview.get("cover_object_id"), bool)
                or not isinstance(preview.get("cover_object_id"), int)
                or not isinstance(preview.get("connection_node"), bool))):
            raise BridgeError("invalid single build preview")
    return payload
