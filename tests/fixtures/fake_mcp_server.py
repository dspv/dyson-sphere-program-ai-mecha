"""Tiny MCP peer for testing the client transport; never used as game evidence."""

import json
import sys


def send(message):
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    method = message.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": {"name": "fake-spherewright", "version": "test"},
        }
    elif method == "tools/list":
        result = {"tools": [
            {"name": "spherewright_get_status", "inputSchema": {"type": "object"}},
            {"name": "spherewright_get_session_state", "inputSchema": {"type": "object"}},
            {"name": "spherewright_commit_build", "inputSchema": {"type": "object"}},
        ]}
    elif method == "resources/read":
        result = {"contents": [{"uri": "spherewright://agent/playbooks/opening-movement-v1",
                                "mimeType": "text/plain", "text": "Read before acting."}]}
    elif method == "tools/call":
        if message["params"]["name"] == "spherewright_commit_build":
            result = {"isError": True, "content": [{"type": "text", "text": "unexpected write"}]}
        elif message["params"]["name"] == "spherewright_get_session_state":
            result = {"isError": False, "structuredContent": {"success": True, "result": {"gameLoaded": False}},
                      "content": [{"type": "text", "text": "session"}]}
        else:
            result = {"isError": False, "structuredContent": {"success": True,
                       "status": {"bridgeConnected": True, "gameVersion": "test", "pluginVersion": "test"}},
                      "content": [{"type": "text", "text": "connected"}]}
    else:
        send({"jsonrpc": "2.0", "id": message["id"],
              "error": {"code": -32601, "message": "Method not found"}})
        continue
    send({"jsonrpc": "2.0", "id": message["id"], "result": result})
