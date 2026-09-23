import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.model_planner import ModelPlannerError, propose_next_step


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def response(arguments):
    return FakeResponse(json.dumps({
        "id": "resp_test", "status": "completed", "usage": {"total_tokens": 12},
        "output": [{"type": "function_call", "name": "propose_next_step",
                    "arguments": json.dumps(arguments)}],
    }).encode())


class ModelPlannerTests(unittest.TestCase):
    def test_proposal_is_bounded_and_key_stays_in_header(self):
        captured = {}

        def open_request(http_request, timeout):
            captured["payload"] = json.loads(http_request.data)
            captured["authorization"] = http_request.get_header("Authorization")
            return response({"operation": "inspect", "reason": "Need production data", "target": "iron"})

        proposal = propose_next_step({"production": None}, "test-model", api_key="test-secret",
                                     opener=open_request)
        self.assertEqual(proposal.operation, "inspect")
        self.assertEqual(proposal.total_tokens, 12)
        self.assertEqual(captured["payload"]["store"], False)
        self.assertEqual(captured["payload"]["tools"][0]["strict"], True)
        self.assertEqual(captured["authorization"], "Bearer test-secret")
        self.assertNotIn("test-secret", json.dumps(captured["payload"]))

    def test_rejects_unapproved_operation(self):
        with self.assertRaises(ModelPlannerError):
            propose_next_step({}, "test-model", api_key="test-secret", opener=lambda *_args, **_kwargs:
                              response({"operation": "commit_build", "reason": "build", "target": None}))
        with self.assertRaises(ModelPlannerError):
            propose_next_step({}, "test-model", api_key="test-secret", opener=lambda *_args, **_kwargs:
                              response({"operation": ["inspect"], "reason": "inspect", "target": None}))

    def test_requires_key_before_network_call(self):
        with self.assertRaises(ModelPlannerError):
            propose_next_step({}, "test-model", api_key="")


if __name__ == "__main__":
    unittest.main()
