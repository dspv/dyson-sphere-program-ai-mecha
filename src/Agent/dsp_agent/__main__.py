"""Inspect the local bridge and issue explicit, bounded game orders."""

import argparse
import json
import sys
from .client import BridgeError, read_health, read_observation, read_operation, request_mine_vein, request_move_to_vein
from .mcp_stdio import McpError, StdioMcpClient


def main(argv=None):
    parser = argparse.ArgumentParser(description="DSP bridge diagnostics and bounded orders")
    commands = parser.add_subparsers(dest="command")
    health = commands.add_parser("health", help="Read the project bootstrap endpoint")
    health.add_argument("--bridge", default="http://127.0.0.1:38741")
    observe = commands.add_parser("observe", help="Read bounded game observation")
    observe.add_argument("--bridge", default="http://127.0.0.1:38741")
    move = commands.add_parser("move-to-vein", help="Order a walking mecha to one nearby vein")
    move.add_argument("--bridge", default="http://127.0.0.1:38741")
    move.add_argument("--session-id", required=True)
    move.add_argument("--vein-id", type=int, required=True)
    move.add_argument("--operation-id", required=True, help="Stable UUID hex; reuse only to poll the same request")
    mine = commands.add_parser("mine-vein", help="Mine at most five iron ore through a normal order")
    mine.add_argument("--bridge", default="http://127.0.0.1:38741")
    mine.add_argument("--session-id", required=True)
    mine.add_argument("--vein-id", type=int, required=True)
    mine.add_argument("--count", type=int, required=True)
    mine.add_argument("--operation-id", required=True, help="Stable UUID hex; reuse only to poll the same request")
    operation = commands.add_parser("operation", help="Read a movement result without retrying it")
    operation.add_argument("--bridge", default="http://127.0.0.1:38741")
    operation.add_argument("--operation-id", required=True)
    spherewright = commands.add_parser("spherewright-probe", help="Inspect Spherewright MCP without game writes")
    spherewright.add_argument("--exe", required=True, help="Path to Spherewright.Mcp.exe")
    spherewright.add_argument("--log", help="Optional local stderr log path")
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "health"):
            result = read_health(args.bridge if args.command else "http://127.0.0.1:38741")
        elif args.command == "observe":
            result = read_observation(args.bridge)
        elif args.command == "move-to-vein":
            result = request_move_to_vein(args.session_id, args.vein_id, args.operation_id, args.bridge)
        elif args.command == "mine-vein":
            result = request_mine_vein(args.session_id, args.vein_id, args.count, args.operation_id, args.bridge)
        elif args.command == "operation":
            result = read_operation(args.operation_id, args.bridge)
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
