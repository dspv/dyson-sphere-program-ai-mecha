"""Bounded, read-only MCP stdio client for inspecting a Spherewright installation.

This narrow client supports protocol 2025-06-18 and sequential requests. It never
calls a mutating tool, even if a server advertises one as read-only by mistake.
"""

import json
import queue
import subprocess
import threading
import time
from pathlib import Path

PROTOCOL_VERSION = "2025-06-18"
PLAYBOOK_URI = "spherewright://agent/playbooks/opening-movement-v1"
MAX_MESSAGE_BYTES = 4 * 1024 * 1024
READ_ONLY_TOOLS = frozenset({
    "spherewright_get_status",
    "spherewright_get_session_state",
    "spherewright_get_player_state",
    "spherewright_get_progression_state",
    "spherewright_get_recipe_catalog",
    "spherewright_get_build_catalog",
    "spherewright_get_power_summary",
    "spherewright_get_overseer_summary",
    "spherewright_get_overseer_production",
    "spherewright_get_overseer_diagnostic_bundle",
    "spherewright_get_foundry_plan",
    "spherewright_list_resource_nodes",
    "spherewright_inspect_resource_node",
    "spherewright_list_factory_entities",
    "spherewright_inspect_factory_entity",
    "spherewright_get_action_result",
})


class McpError(RuntimeError):
    pass


class StdioMcpClient:
    def __init__(self, executable, timeout=10, log_path=None, args=()):
        self.executable = Path(executable)
        self.timeout = timeout
        self.args = tuple(args)
        self.log_path = Path(log_path) if log_path else None
        self.process = None
        self.log_file = None
        self.incoming = queue.Queue()
        self.request_id = 0
        self.tools = {}
        self.capabilities = {}

    def __enter__(self):
        if not self.executable.is_file():
            raise McpError("MCP executable not found: " + str(self.executable))
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_path.open("ab")
        try:
            self.process = subprocess.Popen(
                [str(self.executable), *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self.log_file if self.log_file else subprocess.DEVNULL,
                shell=False,
            )
            threading.Thread(target=self._read_loop, name="mcp-stdout", daemon=True).start()
            result = self._request("initialize", {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "dsp-ai-mecha", "version": "0.1.0"},
            })
            if result.get("protocolVersion") != PROTOCOL_VERSION:
                raise McpError("unsupported MCP protocol version")
            self.capabilities = result.get("capabilities", {})
            if not isinstance(self.capabilities, dict):
                raise McpError("invalid server capabilities")
            self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self.process is not None:
            if self.process.stdin and not self.process.stdin.closed:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            if self.process.stdout:
                self.process.stdout.close()
            self.process = None
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def _read_loop(self):
        process = self.process
        try:
            while True:
                line = process.stdout.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    self.incoming.put(McpError("MCP server closed stdout"))
                    return
                if len(line) > MAX_MESSAGE_BYTES:
                    self.incoming.put(McpError("MCP message too large"))
                    return
                try:
                    message = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    self.incoming.put(McpError("invalid MCP JSON"))
                    return
                self.incoming.put(message)
        except OSError as exc:
            self.incoming.put(McpError("MCP read failed: " + str(exc)))

    def _send(self, message):
        if self.process is None or self.process.poll() is not None:
            raise McpError("MCP server is not running")
        encoded = (json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise McpError("MCP request too large")
        try:
            self.process.stdin.write(encoded)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise McpError("MCP send failed") from exc

    def _request(self, method, params=None):
        self.request_id += 1
        request_id = self.request_id
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            request["params"] = params
        self._send(request)
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise McpError("MCP request timed out: " + method)
            try:
                message = self.incoming.get(timeout=remaining)
            except queue.Empty as exc:
                raise McpError("MCP request timed out: " + method) from exc
            if isinstance(message, Exception):
                raise message
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise McpError("invalid MCP message")
            if "method" in message:
                if message["method"] == "ping" and "id" in message:
                    self._send({"jsonrpc": "2.0", "id": message["id"], "result": {}})
                elif "id" in message:
                    self._send({"jsonrpc": "2.0", "id": message["id"],
                                "error": {"code": -32601, "message": "Method not found"}})
                continue
            if message.get("id") != request_id:
                raise McpError("unexpected MCP response ID")
            if "error" in message:
                raise McpError("MCP error: " + str(message["error"]))
            result = message.get("result")
            if not isinstance(result, dict):
                raise McpError("invalid MCP result")
            return result

    def list_tools(self):
        if "tools" not in self.capabilities:
            raise McpError("server does not advertise tools")
        tools = {}
        cursor = None
        for _ in range(20):
            result = self._request("tools/list", {"cursor": cursor} if cursor else {})
            page = result.get("tools")
            if not isinstance(page, list):
                raise McpError("invalid tool list")
            for tool in page:
                if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                    raise McpError("invalid tool descriptor")
                tools[tool["name"]] = tool
            cursor = result.get("nextCursor")
            if not cursor:
                self.tools = tools
                return tools
            if not isinstance(cursor, str):
                raise McpError("invalid tool cursor")
        raise McpError("too many tool pages")

    def call_read_only(self, name, arguments=None):
        if name not in READ_ONLY_TOOLS:
            raise McpError("tool is not in the read-only allowlist")
        if name not in self.tools:
            raise McpError("tool was not advertised by server")
        result = self._request("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            raise McpError("tool returned an error: " + str(result.get("content", [])))
        return result

    def read_playbook(self):
        if "resources" not in self.capabilities:
            raise McpError("server does not advertise resources")
        result = self._request("resources/read", {"uri": PLAYBOOK_URI})
        contents = result.get("contents")
        if not isinstance(contents, list) or not contents:
            raise McpError("playbook resource is empty")
        text_blocks = [item.get("text") for item in contents if isinstance(item, dict)
                       and item.get("uri") == PLAYBOOK_URI and isinstance(item.get("text"), str)]
        if not text_blocks:
            raise McpError("playbook text is unavailable")
        return "\n".join(text_blocks)
