"""Tests for the ten-request quality gate; no network or Git modifications."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import checkpoint as gate


class CheckpointTests(unittest.TestCase):
    def test_skips_other_iteration_numbers(self):
        with patch("sys.argv", ["checkpoint.py", "--iteration", "9"]):
            with patch.object(gate, "checkpoint") as run:
                self.assertEqual(gate.main(), 0)
                run.assert_not_called()

    def test_every_tenth_iteration_invokes_gate(self):
        with patch("sys.argv", ["checkpoint.py", "--iteration", "10", "--no-pull"]):
            with patch.object(gate, "checkpoint", return_value=True) as run:
                self.assertEqual(gate.main(), 0)
                run.assert_called_once_with(10, pull=False)

    def test_failed_gate_writes_repair_prompt_and_result(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(gate, "OUT", Path(folder)):
                report, prompt = gate._write_results(
                    20, [{
                        "step": "tests unitaires", "command": ["python", "-m", "unittest"],
                        "ok": False, "output": "AssertionError: failed",
                        "duration_seconds": 1.3, "exit_code": 1,
                    }], False,
                )
                payload = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(payload["status"], "FAIL")
                message = prompt.read_text(encoding="utf-8")
                self.assertIn("Ne commence PAS une nouvelle fonctionnalité", message)
                self.assertIn("AssertionError", message)
                self.assertIn("python tools/checkpoint.py --iteration 20", message)

    def test_successful_gate_requests_next_optimization(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(gate, "OUT", Path(folder)):
                _, prompt = gate._write_results(10, [], True)
                self.assertIn("TOUS LES TESTS ONT REUSSI",
                              prompt.read_text(encoding="utf-8"))

    def test_failure_exits_nonzero(self):
        with patch("sys.argv", ["checkpoint.py", "--iteration", "10", "--no-pull"]):
            with patch.object(gate, "checkpoint", return_value=False):
                self.assertEqual(gate.main(), 1)


if __name__ == "__main__":
    unittest.main()
