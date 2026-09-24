"""Inspect the local bridge and issue explicit, bounded game orders."""

import argparse
import json
import sys
from pathlib import Path
from .bridge_experiment import BridgeExperimentAdapter, BridgeExperimentError, make_bridge_runner
from .client import BridgeError, read_build_preview, read_entity, read_health, read_observation, read_operation, request_mine_vein, request_move_to_vein
from .experiment_runner import RunnerError
from .experiments import ExperimentError, ExperimentLedger
from .mcp_stdio import McpError, StdioMcpClient
from .model_planner import ModelPlannerError
from .responses_experiment import ResponsesExperimentModel


def main(argv=None):
    parser = argparse.ArgumentParser(description="DSP bridge diagnostics and bounded orders")
    commands = parser.add_subparsers(dest="command")
    health = commands.add_parser("health", help="Read the project bootstrap endpoint")
    health.add_argument("--bridge", default="http://127.0.0.1:38741")
    observe = commands.add_parser("observe", help="Read bounded game observation")
    observe.add_argument("--bridge", default="http://127.0.0.1:38741")
    entity = commands.add_parser("entity", help="Read one exact game entity and its assembler state")
    entity.add_argument("--bridge", default="http://127.0.0.1:38741")
    entity.add_argument("--entity-id", type=int, required=True)
    preview = commands.add_parser("build-preview", help="Read the current UI construction preview")
    preview.add_argument("--bridge", default="http://127.0.0.1:38741")
    move = commands.add_parser("move-to-vein", help="Order a walking mecha to one nearby vein")
    move.add_argument("--bridge", default="http://127.0.0.1:38741")
    move.add_argument("--session-id", required=True)
    move.add_argument("--vein-id", type=int, required=True)
    move.add_argument("--operation-id", required=True, help="Stable UUID hex; reuse only to poll the same request")
    mine = commands.add_parser("mine-vein", help="Mine at most five iron or copper ore through a normal order")
    mine.add_argument("--bridge", default="http://127.0.0.1:38741")
    mine.add_argument("--session-id", required=True)
    mine.add_argument("--vein-id", type=int, required=True)
    mine.add_argument("--count", type=int, required=True)
    mine.add_argument("--item-id", type=int, choices=(1001, 1002), default=1001)
    mine.add_argument("--operation-id", required=True, help="Stable UUID hex; reuse only to poll the same request")
    operation = commands.add_parser("operation", help="Read a movement result without retrying it")
    operation.add_argument("--bridge", default="http://127.0.0.1:38741")
    operation.add_argument("--operation-id", required=True)
    experiment = commands.add_parser("experiment-once", help="Ask a model for one goal and one checked experiment")
    experiment.add_argument("--bridge", default="http://127.0.0.1:38741")
    experiment.add_argument("--model", required=True)
    experiment.add_argument("--data-dir", required=True, help="Private local directory for the ledger and raw observations")
    experiment.add_argument("--allow-game-write", action="store_true",
                            help="Allow one guarded walking or mining order; default is read-only inspection")
    spherewright = commands.add_parser("spherewright-probe", help="Inspect Spherewright MCP without game writes")
    spherewright.add_argument("--exe", required=True, help="Path to Spherewright.Mcp.exe")
    spherewright.add_argument("--log", help="Optional local stderr log path")
    args = parser.parse_args(argv)
    try:
        if args.command in (None, "health"):
            result = read_health(args.bridge if args.command else "http://127.0.0.1:38741")
        elif args.command == "observe":
            result = read_observation(args.bridge)
        elif args.command == "entity":
            result = read_entity(args.entity_id, args.bridge)
        elif args.command == "build-preview":
            result = read_build_preview(args.bridge)
        elif args.command == "move-to-vein":
            result = request_move_to_vein(args.session_id, args.vein_id, args.operation_id, args.bridge)
        elif args.command == "mine-vein":
            result = request_mine_vein(args.session_id, args.vein_id, args.count, args.operation_id,
                                       args.bridge, item_id=args.item_id)
        elif args.command == "operation":
            result = read_operation(args.operation_id, args.bridge)
        elif args.command == "experiment-once":
            allowed = {"inspect", "move", "mine"} if args.allow_game_write else {"inspect"}
            data_dir = Path(args.data_dir).resolve()
            model = ResponsesExperimentModel(args.model, allowed)
            ledger = ExperimentLedger(data_dir / "ledger.sqlite3")
            adapter = BridgeExperimentAdapter(data_dir / "observations", base_url=args.bridge,
                                              max_polls=120, poll_interval=0.5)
            result = make_bridge_runner(ledger, model, adapter).run_once()
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
    except (BridgeError, BridgeExperimentError, ExperimentError, RunnerError,
            ModelPlannerError, McpError, OSError) as exc:
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
