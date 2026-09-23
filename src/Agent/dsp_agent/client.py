"""Strict read-only bridge client. Gameplay actions are not implemented yet."""

import json
from urllib import error, parse, request


class BridgeError(RuntimeError):
    pass


def _read(base_url, path, timeout, max_bytes):
    parsed = parse.urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise BridgeError("bridge address must use loopback HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise BridgeError("bridge address must be a plain loopback origin")
    url = base_url.rstrip("/") + path
    try:
        with request.urlopen(request.Request(url, method="GET"), timeout=timeout) as response:
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


def read_health(base_url="http://127.0.0.1:38741", timeout=3):
    payload = _read(base_url, "/v1/health", timeout, 4096)
    if payload.get("status") not in ("bootstrap_only", "observer_unverified"):
        raise BridgeError("unexpected bridge status")
    if not isinstance(payload.get("bridge_version"), str):
        raise BridgeError("missing bridge version")
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
        for key in ("inventory", "nearby_entities", "nearby_veins"):
            value = payload.get(key)
            if value is not None and not isinstance(value, dict):
                raise BridgeError("invalid " + key)
    return payload
