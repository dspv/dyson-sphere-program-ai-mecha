"""Inspect local bridge transports without issuing gameplay actions."""

import argparse
import json
import sys
from .client import BridgeError, read_health
from .mcp_stdio import McpError, StdioMcpClient


def main(argv=None):
    parser = argparse.ArgumentParser(description="DSP bridge read-only diagnostics")
    commands = parser.add_subparsers(dest="command")
    health = commands.add_parser("health", help="Read the project bootstrap endpoint")
    health.add_argument("--bridge", default="http://127.0.0.1:38741")
    spherewright = commands.add_parser("spherewright-probe", help="Inspect Spherewright MCP without game writes")
    spherewright.add_argument("--exe", required=True, help="Path to Spherewright.Mcp.exe")
    spherewright.add_argument("--log", help="Optional local stderr log path")
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "health"):
            result = read_health(args.bridge if args.command else "http://127.0.0.1:38741")
        else:
            with StdioMcpClient(args.exe, log_path=args.log) as client:
                tools = client.list_tools()
                playbook = client.read_playbook()
                status = client.call_read_only("spherewright_get_status")
                content = status.get("content", [])
                if not isinstance(content, list):
                    raise McpError("malformed MCP status content")
                summary = next((block.get("text") for block in content
                                if isinstance(block, dict) and isinstance(block.get("text"), str)), None)
                bridge = _nested_dict(status, "structuredContent", "status")
                session = client.call_read_only("spherewright_get_session_state")
                game = _nested_dict(session, "structuredContent", "result")
                result = {
                    "mcp_connected": True,
                    "tool_count": len(tools),
                    "tool_names": sorted(tools),
                    "playbook_available": bool(playbook),
                    "status_summary": summary,
                    "bridge": {key: bridge.get(key) for key in ("bridgeConnected", "pluginVersion", "gameVersion", "gameLoaded", "writeHealth")},
                    "game": {key: game.get(key) for key in ("gameLoaded", "ownedBySpherewright", "accessRestricted", "gameVersion", "peacefulMode", "sandboxMode", "localPlanetId", "writesAllowed")},
                }
    except (BridgeError, McpError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _nested_dict(value, *keys):
    for key in keys:
        if not isinstance(value, dict):
            raise McpError("malformed MCP tool response")
        value = value.get(key)
    if not isinstance(value, dict):
        raise McpError("malformed MCP tool response")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
