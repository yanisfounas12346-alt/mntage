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

    @staticmethod
    def _media_step(command, output="", ok=True):
        return {
            "step": command[0], "command": command, "ok": ok,
            "exit_code": 0 if ok else 1,
            "duration_seconds": .01, "output": output,
        }

    def test_media_gate_checks_real_commands_and_ass_filter(self):
        def fake_run(label, command, timeout, **kwargs):
            if "-filters" in command:
                self.assertEqual(kwargs["output_limit"], 100000)
                output = "Filters:\n ... ass V->V Render ASS subtitles.\n"
            else:
                output = "version confirmed"
            return self._media_step(command, output)
        with patch.object(gate, "_run", side_effect=fake_run) as runner:
            steps = gate._check_media_tools()
        self.assertTrue(all(step["ok"] for step in steps))
        self.assertEqual(
            [step["command"] for step in steps],
            [["ffmpeg", "-version"], ["ffprobe", "-version"],
             ["ffmpeg", "-hide_banner", "-filters"]],
        )
        self.assertEqual(runner.call_count, 3)

    def test_media_gate_rejects_build_without_ass_filter(self):
        def fake_run(label, command, timeout, **kwargs):
            return self._media_step(
                command,
                "Filters:\n ... subtitles V->V Burn text.\n"
                if "-filters" in command else "version confirmed")
        with patch.object(gate, "_run", side_effect=fake_run):
            steps = gate._check_media_tools()
        self.assertFalse(steps[-1]["ok"])
        self.assertEqual(steps[-1]["exit_code"], 1)
        self.assertIn("filtre 'ass' est absent", steps[-1]["output"])

    def test_media_gate_rejects_broken_ffprobe_even_with_ass(self):
        def fake_run(label, command, timeout, **kwargs):
            ok = command[0] != "ffprobe"
            text = " ... ass V->V available" if "-filters" in command else ""
            return self._media_step(command, text, ok)
        with patch.object(gate, "_run", side_effect=fake_run):
            steps = gate._check_media_tools()
        self.assertFalse(steps[1]["ok"])
        self.assertTrue(steps[0]["ok"])
        self.assertTrue(steps[2]["ok"])

    def test_media_gate_blocks_when_encoder_cannot_start(self):
        def fake_run(label, command, timeout, **kwargs):
            return self._media_step(command, "FileNotFoundError", ok=False)
        with patch.object(gate, "_run", side_effect=fake_run) as runner:
            steps = gate._check_media_tools()
        self.assertEqual(runner.call_count, 2)
        self.assertFalse(steps[0]["ok"])
        self.assertFalse(steps[-1]["ok"])
        self.assertIn("non vérifiable", steps[-1]["output"])

    def test_checkpoint_fails_closed_and_writes_report_on_missing_ass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in gate.SOURCE_FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# placeholder\n", encoding="utf-8")
            missing = self._media_step(
                ["ffmpeg", "-hide_banner", "-filters"], "filtre ASS absent", False)
            with patch.object(gate, "ROOT", root), patch.object(gate, "OUT", root/"results"):
                with patch.object(gate, "_check_media_tools", return_value=[missing]):
                    with patch.object(gate, "_run", return_value=self._media_step(
                        ["python", "test"], "OK", True)):
                        self.assertFalse(gate.checkpoint(10, pull=False))
            report = json.loads(
                (root/"results"/"cycle_0010.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["iteration"], 10)
            self.assertTrue(any(not item["ok"] for item in report["steps"]))
            prompt = (root/"results"/"cycle_0010_next_prompt.txt").read_text(
                encoding="utf-8")
            self.assertIn("Ne commence PAS une nouvelle fonctionnalité", prompt)

    def test_failure_exits_nonzero(self):
        with patch("sys.argv", ["checkpoint.py", "--iteration", "10", "--no-pull"]):
            with patch.object(gate, "checkpoint", return_value=False):
                self.assertEqual(gate.main(), 1)


if __name__ == "__main__":
    unittest.main()
