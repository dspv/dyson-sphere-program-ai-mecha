import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Agent"))
from dsp_agent.journal import AgentJournal, JournalConflict


class JournalTests(unittest.TestCase):
    def test_repeat_key_returns_existing_operation_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episode.sqlite"
            with AgentJournal(path) as journal:
                first = journal.record_command("save-a:load-1", "build-1", {"action": "build", "args": {"x": 1}})
            with AgentJournal(path) as journal:
                second = journal.record_command("save-a:load-1", "build-1", {"args": {"x": 1}, "action": "build"})
                self.assertEqual(first, second)
                with self.assertRaises(JournalConflict):
                    journal.record_command("save-a:load-1", "build-1", {"action": "build", "args": {"x": 2}})

    def test_session_change_requires_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            with AgentJournal(Path(directory) / "episode.sqlite") as journal:
                pending, _ = journal.record_command("save-a:load-1", "a", {"action": "build"})
                completed, _ = journal.record_command("save-a:load-1", "b", {"action": "inspect"})
                journal.record_result(completed, "observed_success", {"tick": 10})
                self.assertEqual(journal.record_session_change("save-a:load-1", "save-a:load-2"), 1)
                self.assertEqual(journal.operation(pending)["status"], "needs_reconciliation")
                self.assertEqual(journal.operation(completed)["status"], "observed_success")

    def test_terminal_result_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            with AgentJournal(Path(directory) / "episode.sqlite") as journal:
                operation_id, _ = journal.record_command("session", "key", {"action": "inspect"})
                journal.record_result(operation_id, "observed_failure", {"error": "not_loaded"})
                with self.assertRaises(JournalConflict):
                    journal.record_result(operation_id, "observed_success", {"tick": 12})


if __name__ == "__main__":
    unittest.main()
