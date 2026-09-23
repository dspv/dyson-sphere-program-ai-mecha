import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.client import BridgeError, read_health


class Handler(BaseHTTPRequestHandler):
    payload = {"protocol_version": 1, "bridge_version": "0.1.0", "status": "bootstrap_only"}

    def do_GET(self):
        if self.path != "/v1/health":
            self.send_error(404)
            return
        data = json.dumps(self.payload).encode()
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
            self.assertEqual(result["bridge_version"], "0.1.0")
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


if __name__ == "__main__":
    unittest.main()
