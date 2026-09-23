import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.mcp_stdio import McpError, StdioMcpClient

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fake_mcp_server.py"


class McpStdioTests(unittest.TestCase):
    def test_handshake_tools_resource_and_read(self):
        with StdioMcpClient(sys.executable, args=[str(FIXTURE)]) as client:
            tools = client.list_tools()
            self.assertIn("spherewright_get_status", tools)
            self.assertIn("spherewright_commit_build", tools)
            self.assertEqual(client.read_playbook(), "Read before acting.")
            status = client.call_read_only("spherewright_get_status")
            self.assertTrue(status["structuredContent"]["status"]["bridgeConnected"])

    def test_write_tool_is_rejected_locally(self):
        with StdioMcpClient(sys.executable, args=[str(FIXTURE)]) as client:
            client.list_tools()
            with self.assertRaises(McpError):
                client.call_read_only("spherewright_commit_build", {"planToken": "x"})
            self.assertTrue(client.call_read_only("spherewright_get_status"))

    def test_unadvertised_tool_is_rejected(self):
        with StdioMcpClient(sys.executable, args=[str(FIXTURE)]) as client:
            client.list_tools()
            with self.assertRaises(McpError):
                client.call_read_only("spherewright_get_player_state")


if __name__ == "__main__":
    unittest.main()
