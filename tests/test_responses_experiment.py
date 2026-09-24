import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.experiment_runner import GoalChoice, Observation
from dsp_agent.model_planner import ModelPlannerError
from dsp_agent.responses_experiment import ResponsesExperimentModel


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def response(name, arguments):
    return FakeResponse(json.dumps({
        "id": "response-test", "status": "completed",
        "output": [{"type": "function_call", "name": name,
                    "arguments": json.dumps(arguments)}],
    }).encode())


class ResponsesExperimentTests(unittest.TestCase):
    def test_model_chooses_goal_then_uses_checked_failure_in_plan(self):
        requests = []

        def opener(http_request, timeout):
            payload = json.loads(http_request.data)
            requests.append(payload)
            self.assertEqual(http_request.get_header("Authorization"), "Bearer fake-key")
            name = payload["tools"][0]["name"]
            if name == "choose_goal":
                return response(name, {"strategic_goal": "make iron ingots",
                                       "near_term_goal": "get ore", "reason": "iron is nearby"})
            return response(name, {"kind": "mine", "target_id": 1, "count": 2,
                                   "item_id": 1001, "hypothesis": "mining is needed",
                                   "prediction": "two ore in inventory", "falsifier": "no ore gained"})

        model = ResponsesExperimentModel("configured-model", {"inspect", "move", "mine"},
                                         api_key="fake-key", opener=opener)
        observed = Observation("session-a", 10, "obs-10", "state-a", {"nearby_iron": True})
        goal = model.choose_goal(observed)
        plan = model.plan(observed, goal, [{"verdict": "failed", "action": {"kind": "move"},
                                           "hypothesis": "walking is enough", "explanation": "no ore gained",
                                           "evidence_ref": "ui-1"}])
        self.assertEqual(goal.near_term_goal, "get ore")
        self.assertEqual(plan.action, {"kind": "mine", "args": {"vein_id": 1, "count": 2, "item_id": 1001}})
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(item["store"] is False for item in requests))
        self.assertTrue(all(item["parallel_tool_calls"] is False for item in requests))
        self.assertTrue(all(item["tools"][0]["strict"] is True for item in requests))
        self.assertNotIn("fake-key", json.dumps(requests))
        context = json.loads(requests[1]["input"][1]["content"])
        self.assertEqual(context["past_checked_attempts"][0]["explanation"], "no ore gained")

    def test_invalid_mining_parameters_are_rejected_locally(self):
        model = ResponsesExperimentModel(
            "configured-model", {"mine"}, api_key="fake-key",
            opener=lambda *_args, **_kwargs: response(
                "plan_experiment", {"kind": "mine", "target_id": 1, "count": 500,
                                    "item_id": 1001, "hypothesis": "ore exists",
                                    "prediction": "ore", "falsifier": "none"}),
        )
        with self.assertRaises(ModelPlannerError):
            model.plan(Observation("session-a", 10, "obs-10", "state-a", {}),
                       GoalChoice("progress", "ore", "needed"), [])

    def test_exact_entity_inspection_maps_observed_id(self):
        model = ResponsesExperimentModel(
            "configured-model", {"inspect_entity"}, api_key="fake-key",
            opener=lambda *_args, **_kwargs: response(
                "plan_experiment", {"kind": "inspect_entity", "target_id": 19,
                                    "count": None, "item_id": None,
                                    "hypothesis": "recipe may be unset",
                                    "prediction": "recipe ID zero", "falsifier": "recipe ID positive"}),
        )
        plan = model.plan(Observation("session-a", 10, "obs-10", "state-a", {}),
                          GoalChoice("progress", "inspect smelter", "need state"), [])
        self.assertEqual(plan.action, {"kind": "inspect_entity", "args": {"entity_id": 19}})


if __name__ == "__main__":
    unittest.main()
