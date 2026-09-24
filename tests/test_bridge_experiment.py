import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.bridge_experiment import BridgeExperimentAdapter, BridgeExperimentError, make_bridge_runner
from dsp_agent.experiment_runner import ExperimentPlan, ExperimentRunner, GoalChoice, RunnerError
from dsp_agent.experiments import ExperimentLedger


SESSION = "a" * 32


def observation(tick=100, *, session=SESSION):
    return {"protocol_version": 1, "status": "ok", "session_id": session,
            "game_version": "0.10.35.29088", "game_tick": tick, "paused": False,
            "planet": {"id": 102, "name": "Ancha II"},
            "mecha_position": {"x": 1.0, "y": 2.0, "z": 3.0},
            "inventory": {"complete": True, "items": []},
            "nearby_veins": {"veins": [{"id": 7, "product_id": 1001, "amount": 100}]}}


def operation(operation_id, status="pending", *, session=SESSION):
    return {"operation_id": operation_id, "status": status, "session_id": session,
            "action": "mine", "vein_id": 7, "item_id": 1001, "requested_count": 2}


class BridgeExperimentTests(unittest.TestCase):
    def test_mining_polls_one_operation_and_keeps_private_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            submissions = []
            polls = []
            adapter = BridgeExperimentAdapter(
                Path(directory) / "episodes", poll_interval=0, sleep=lambda _: None,
                observe_client=lambda base: observation(),
                mine_client=lambda session, vein, count, operation_id, base, *, item_id:
                    (submissions.append((session, vein, count, operation_id, item_id))
                     or operation(operation_id)),
                operation_client=lambda operation_id, base:
                    (polls.append(operation_id) or operation(operation_id, "completed")),
            )
            before = adapter.observe()
            result = adapter.execute({"kind": "mine", "args": {"vein_id": 7, "count": 2, "item_id": 1001}},
                                     before, "operation-1")
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(submissions), 1)
            self.assertEqual(polls, ["operation-1"])
            self.assertEqual(json.loads(Path(before.evidence_ref).read_text()), observation())
            self.assertEqual(before.state_fingerprint, adapter.observe().state_fingerprint)

    def test_unobserved_or_mismatched_vein_is_never_submitted(self):
        with tempfile.TemporaryDirectory() as directory:
            submissions = []
            adapter = BridgeExperimentAdapter(
                directory, observe_client=lambda base: observation(),
                mine_client=lambda *args, **kwargs: submissions.append(args),
            )
            before = adapter.observe()
            for vein_id, item_id in ((999, 1001), (7, 1002)):
                with self.assertRaises(BridgeExperimentError):
                    adapter.execute({"kind": "mine", "args": {"vein_id": vein_id,
                                                              "count": 2, "item_id": item_id}},
                                    before, "operation-2")
            self.assertEqual(submissions, [])

    def test_changed_world_rejects_plan_before_post(self):
        with tempfile.TemporaryDirectory() as directory:
            observations = iter((observation(100), observation(110)))
            submissions = []

            def next_observation(base):
                payload = next(observations)
                if payload["game_tick"] == 110:
                    payload["nearby_veins"]["veins"][0]["amount"] = 98
                return payload

            adapter = BridgeExperimentAdapter(
                directory, observe_client=next_observation,
                mine_client=lambda *args, **kwargs: submissions.append(args),
            )
            before = adapter.observe()
            result = adapter.execute({"kind": "mine", "args": {"vein_id": 7,
                                                                  "count": 2, "item_id": 1001}},
                                     before, "operation-3")
            self.assertEqual(result["status"], "rejected")
            self.assertEqual(result["reason"], "stale_snapshot")
            self.assertEqual(submissions, [])

    def test_poll_exhaustion_leaves_runner_unknown_for_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            submissions = []
            adapter = BridgeExperimentAdapter(
                Path(directory) / "episodes", max_polls=2, poll_interval=0, sleep=lambda _: None,
                observe_client=lambda base: observation(),
                mine_client=lambda session, vein, count, operation_id, base, *, item_id:
                    (submissions.append(operation_id) or operation(operation_id)),
                operation_client=lambda operation_id, base: operation(operation_id, "running"),
            )
            with ExperimentLedger(Path(directory) / "ledger.sqlite") as ledger:
                runner = ExperimentRunner(
                    ledger, adapter.observe,
                    lambda before: GoalChoice("build an iron line", "get iron", "need ore"),
                    lambda before, goal, memories: ExperimentPlan(
                        {"kind": "mine", "args": {"vein_id": 7, "count": 2, "item_id": 1001}},
                        "reachable", "two ore", "no ore"),
                    adapter.execute, lambda *_: None, {"mine"},
                )
                with self.assertRaisesRegex(RunnerError, "reconciliation"):
                    runner.run_once()
                self.assertEqual(len(submissions), 1)
                with self.assertRaisesRegex(ValueError, "unresolved"):
                    runner.run_once()
                self.assertEqual(len(submissions), 1)

    def test_invalid_session_cannot_be_used_in_snapshot_path(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = BridgeExperimentAdapter(
                directory, observe_client=lambda base: observation(session="../escape"),
            )
            with self.assertRaises(BridgeExperimentError):
                adapter.observe()
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_wired_runner_checks_mining_readback_before_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            before = observation(100)
            fresh = observation(101)
            after = observation(150)
            after["inventory"]["items"] = [{"item_id": 1001, "count": 2}]
            after["nearby_veins"]["veins"][0]["amount"] = 98
            snapshots = iter((before, fresh, after))

            def mined(session, vein, count, operation_id, base, *, item_id):
                return {"operation_id": operation_id, "status": "completed", "session_id": session,
                        "action": "mine", "vein_id": vein, "item_id": item_id,
                        "requested_count": count, "planet_id": 102,
                        "inventory_before": 0, "inventory_now": 2,
                        "vein_amount_before": 100, "vein_amount_now": 98}

            adapter = BridgeExperimentAdapter(
                Path(directory) / "episodes", observe_client=lambda base: next(snapshots),
                mine_client=mined,
            )

            class FakeModel:
                allowed_actions = frozenset({"mine"})

                def choose_goal(self, seen):
                    return GoalChoice("build iron line", "get iron", "ore needed")

                def plan(self, seen, goal, memories):
                    return ExperimentPlan({"kind": "mine", "args": {"vein_id": 7,
                                                                       "count": 2, "item_id": 1001}},
                                          "reachable", "two ore", "no ore")

            with ExperimentLedger(Path(directory) / "ledger.sqlite") as ledger:
                result = make_bridge_runner(ledger, FakeModel(), adapter).run_once()
                self.assertEqual(result["verdict"], "achieved")
                self.assertEqual(result["game_version"], "0.10.35.29088")
                self.assertEqual(len(ledger.memories("get iron", game_version="0.10.35.29088")), 1)


if __name__ == "__main__":
    unittest.main()
