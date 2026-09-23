import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.client import BridgeError, read_health, read_observation


class Handler(BaseHTTPRequestHandler):
    payload = {"protocol_version": 1, "bridge_version": "0.2.0", "status": "observer_unverified"}
    observation = {"protocol_version": 1, "status": "not_loaded", "game_version": "0.10.35", "session_id": None}

    def do_GET(self):
        if self.path not in ("/v1/health", "/v1/observe"):
            self.send_error(404)
            return
        data = json.dumps(self.payload if self.path == "/v1/health" else self.observation).encode()
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


if __name__ == "__main__":
    unittest.main()
