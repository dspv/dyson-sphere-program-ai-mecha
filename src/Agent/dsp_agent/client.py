"""Strict read-only bridge client. Gameplay actions are not implemented yet."""

import json
from urllib import error, parse, request


class BridgeError(RuntimeError):
    pass


def read_health(base_url="http://127.0.0.1:38741", timeout=3):
    parsed = parse.urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise BridgeError("bridge address must use loopback HTTP")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise BridgeError("bridge address must be a plain loopback origin")
    url = base_url.rstrip("/") + "/v1/health"
    try:
        with request.urlopen(request.Request(url, method="GET"), timeout=timeout) as response:
            data = response.read(4096)
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
    if payload.get("status") != "bootstrap_only":
        raise BridgeError("unexpected bridge status")
    if not isinstance(payload.get("bridge_version"), str):
        raise BridgeError("missing bridge version")
    return payload
