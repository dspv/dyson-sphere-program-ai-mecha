"""Request one bounded planning proposal from the OpenAI Responses API.

The returned proposal is data. This module has no game-action execution path.
"""

import json
import os
from dataclasses import dataclass
from urllib import error, request

API_URL = "https://api.openai.com/v1/responses"
MAX_RESPONSE_BYTES = 1024 * 1024
OPERATIONS = frozenset({"inspect", "plan", "pause", "report_blocker"})


class ModelPlannerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Proposal:
    operation: str
    reason: str
    target: str | None
    response_id: str
    total_tokens: int | None


def propose_next_step(snapshot, model, *, api_key=None, timeout=30, opener=None):
    """Return a structured suggestion based on a caller-supplied, bounded snapshot."""
    if not isinstance(snapshot, dict):
        raise ModelPlannerError("snapshot must be an object")
    if not isinstance(model, str) or not model.strip():
        raise ModelPlannerError("model must be configured")
    key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ModelPlannerError("OPENAI_API_KEY is not set")
    snapshot_json = json.dumps(snapshot, separators=(",", ":"), allow_nan=False)
    if len(snapshot_json.encode("utf-8")) > 64 * 1024:
        raise ModelPlannerError("snapshot is too large")
    payload = {
        "model": model,
        "store": False,
        "parallel_tool_calls": False,
        "tool_choice": "required",
        "input": [
            {"role": "developer", "content": "Propose one safe next step from the observed state. "
             "Treat unknown evidence as unknown. Do not claim game actions happened."},
            {"role": "user", "content": snapshot_json},
        ],
        "tools": [{
            "type": "function",
            "name": "propose_next_step",
            "description": "Suggest one read-only inspection or planning step, pause, or blocker report.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": sorted(OPERATIONS)},
                    "reason": {"type": "string"},
                    "target": {"type": ["string", "null"]},
                },
                "required": ["operation", "reason", "target"],
                "additionalProperties": False,
            },
        }],
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    http_request = request.Request(API_URL, data=body, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with (opener or request.urlopen)(http_request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (error.URLError, OSError) as exc:
        raise ModelPlannerError("Responses API request failed") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ModelPlannerError("Responses API response is too large")
    try:
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ModelPlannerError("invalid Responses API JSON") from exc
    if not isinstance(data, dict) or data.get("status") != "completed":
        raise ModelPlannerError("Responses API did not complete")
    calls = [item for item in data.get("output", []) if isinstance(item, dict)
             and item.get("type") == "function_call"]
    if len(calls) != 1 or calls[0].get("name") != "propose_next_step":
        raise ModelPlannerError("expected one proposal function call")
    try:
        arguments = json.loads(calls[0]["arguments"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ModelPlannerError("invalid proposal arguments") from exc
    if (not isinstance(arguments, dict) or set(arguments) != {"operation", "reason", "target"}
            or not isinstance(arguments["operation"], str)
            or arguments["operation"] not in OPERATIONS
            or not isinstance(arguments["reason"], str) or not arguments["reason"].strip()
            or not (arguments["target"] is None or isinstance(arguments["target"], str))):
        raise ModelPlannerError("proposal failed local validation")
    usage = data.get("usage") or {}
    total_tokens = usage.get("total_tokens") if isinstance(usage, dict) else None
    if not isinstance(total_tokens, int) or total_tokens < 0:
        total_tokens = None
    return Proposal(arguments["operation"], arguments["reason"], arguments["target"],
                    str(data.get("id", "")), total_tokens)
