"""Unit tests for safe UI-automation decisions, without actual browser clicks."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import next_request


class NextRequestTests(unittest.TestCase):
    def test_normal_request_does_not_run_checkpoint(self):
        with patch.object(next_request.gate, "checkpoint") as check:
            action=next_request.decide(9)
            self.assertEqual(action["status"],"CONTINUE")
            check.assert_not_called()

    def test_tenth_request_runs_checkpoint_and_releases_on_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            prompt=Path(folder)/"cycle_0010_next_prompt.txt"
            prompt.write_text("Tests OK. Continue.",encoding="utf-8")
            with patch.object(next_request.gate, "OUT", Path(folder)):
                with patch.object(next_request.gate, "checkpoint",return_value=True):
                    action=next_request.decide(10)
            self.assertTrue(action["allow_new_optimization"])
            self.assertIn("Tests OK",action["prompt"])

    def test_tenth_request_stops_and_requests_repair(self):
        with tempfile.TemporaryDirectory() as folder:
            prompt=Path(folder)/"cycle_0020_next_prompt.txt"
            prompt.write_text("STOP, répare le test.",encoding="utf-8")
            with patch.object(next_request.gate, "OUT", Path(folder)):
                with patch.object(next_request.gate, "checkpoint",return_value=False):
                    action=next_request.decide(20)
            self.assertEqual(action["status"],"REPAIR")
            self.assertFalse(action["allow_new_optimization"])

    def test_previous_failed_gate_blocks_the_next_batch(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"cycle_0010.json").write_text(
                json.dumps({"status":"FAIL"}),encoding="utf-8")
            (root/"cycle_0010_next_prompt.txt").write_text(
                "Réparer le moteur.",encoding="utf-8")
            with patch.object(next_request.gate,"OUT",root):
                action=next_request.decide(11)
            self.assertEqual(action["status"],"REPAIR")
            self.assertFalse(action["allow_new_optimization"])


if __name__ == "__main__":
    unittest.main()
