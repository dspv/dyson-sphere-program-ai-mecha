import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.client import BridgeError, read_health, read_observation, read_operation, request_mine_vein, request_move_to_vein


class Handler(BaseHTTPRequestHandler):
    payload = {"protocol_version": 1, "bridge_version": "0.2.0", "status": "observer_unverified"}
    observation = {"protocol_version": 1, "status": "not_loaded", "game_version": "0.10.35", "session_id": None}
    operation_id = "0123456789abcdef0123456789abcdef"

    def do_POST(self):
        if self.path.startswith("/v1/mine-vein?"):
            self._send({"protocol_version": 1, "operation_id": self.operation_id, "action": "mine", "status": "pending"})
            return
        if not self.path.startswith("/v1/move-to-vein?"):
            self.send_error(404)
            return
        self._send({"protocol_version": 1, "operation_id": self.operation_id, "status": "pending"})

    def do_GET(self):
        if self.path.startswith("/v1/operation?"):
            self._send({"protocol_version": 1, "operation_id": self.operation_id, "status": "partial", "reason": "order_interrupted"})
            return
        if self.path not in ("/v1/health", "/v1/observe"):
            self.send_error(404)
            return
        self._send(self.payload if self.path == "/v1/health" else self.observation)

    def _send(self, payload):
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


class ClientTests(unittest.TestCase):
    def test_valid_health(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = read_health("http://127.0.0.1:" + str(server.server_port))
            self.assertEqual(result["bridge_version"], "0.2.0")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_reject_remote_origin(self):
        with self.assertRaises(BridgeError):
            read_health("http://example.com")

    def test_reject_credentials(self):
        with self.assertRaises(BridgeError):
            read_health("http://user:password@127.0.0.1:38741")

    def test_observation_requires_session_identity_when_loaded(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_port)
            self.assertEqual(read_observation(base)["status"], "not_loaded")
            Handler.observation = {"protocol_version": 1, "status": "ok", "game_version": "0.10.35", "game_tick": 42}
            with self.assertRaises(BridgeError):
                read_observation(base)
        finally:
            Handler.observation = {"protocol_version": 1, "status": "not_loaded", "game_version": "0.10.35", "session_id": None}
            server.shutdown()
            server.server_close()
            thread.join()

    def test_movement_uses_stable_operation_id_and_reports_partial(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_port)
            session = "fedcba9876543210fedcba9876543210"
            operation_id = Handler.operation_id
            self.assertEqual(request_move_to_vein(session, 1, operation_id, base)["status"], "pending")
            self.assertEqual(read_operation(operation_id, base)["reason"], "order_interrupted")
            with self.assertRaises(BridgeError):
                request_move_to_vein(session, 0, operation_id, base)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_mining_count_is_bounded_before_request(self):
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_port)
            session = "fedcba9876543210fedcba9876543210"
            operation_id = Handler.operation_id
            self.assertEqual(request_mine_vein(session, 1, 5, operation_id, base)["status"], "pending")
            for count in (0, 6, True):
                with self.assertRaises(BridgeError):
                    request_mine_vein(session, 1, count, operation_id, base)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
