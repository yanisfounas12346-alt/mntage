"""Three-request supervised GUI pilot, fully tested without a browser or network."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import pilot_3
from tools import session_handoff as handoff


class PilotThreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        for obj, field, val in (
            (pilot_3, "PILOT_FILE", root / "pilot.json"),
            (handoff, "STATE_FILE", root / "session.json"),
            (handoff, "HANDOFF_FILE", root / "resume.txt"),
            (handoff.gate, "OUT", root / "checkpoints"),
        ):
            p = patch.object(obj, field, val)
            p.start()
            self.addCleanup(p.stop)

    def test_three_confirmed_changes_then_stop_even_after_restart(self):
        pilot = pilot_3.PilotSession()
        self.assertEqual(pilot.progress(), (0, 3))
        for n in range(3):
            action = pilot.prepare()
            self.assertEqual(action["status"], "SEND")
            self.assertEqual(action["iteration"], n + 1)
            result = pilot.confirm(
                action["request_id"], f"Correction réelle {n + 1}",
                f"012345{n}a", verifier=lambda sha: None,
            )
            self.assertIn(result["status"], ("RECORDED", "CHECKPOINT_REQUIRED"))
        self.assertEqual(pilot.progress(), (3, 3))
        restarted = pilot_3.PilotSession()
        self.assertEqual(restarted.prepare()["status"], "DONE")
        self.assertEqual(handoff.load()["completed"], 3)
        self.assertEqual(len(handoff.load()["history"]), 3)

    def test_pending_does_not_send_again(self):
        pilot = pilot_3.PilotSession()
        first = pilot.prepare()
        same = pilot.prepare()
        self.assertEqual(same["status"], "PENDING_REVIEW")
        self.assertFalse(same["allow_send"])
        self.assertEqual(first["request_id"], same["request_id"])

    def test_commit_must_be_real_for_validated_action(self):
        pilot = pilot_3.PilotSession()
        action = pilot.prepare()
        with self.assertRaises(ValueError):
            pilot.confirm(action["request_id"], "Résumé", "bad-commit")
        self.assertEqual(handoff.load()["completed"], 0)
        self.assertEqual(handoff.load()["pending"]["request_id"], action["request_id"])

    def test_same_old_commit_cannot_be_reused_for_two_optimizations(self):
        pilot = pilot_3.PilotSession()
        first = pilot.prepare()
        pilot.confirm(first["request_id"], "Premier correctif", "abcdef12",
                      verifier=lambda sha: None)
        second = pilot.prepare()
        with self.assertRaises(ValueError):
            pilot.confirm(second["request_id"], "Second correctif factice",
                          "ABCDEF12", verifier=lambda sha: None)
        self.assertEqual(handoff.load()["completed"], 1)

    def test_invalid_commit_is_rejected_before_git_fetch(self):
        with patch.object(pilot_3.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                pilot_3._verify_remote_commit("malformed")
            run.assert_not_called()

    def test_every_tenth_request_blocks_new_requests_on_failed_gate(self):
        state = handoff.initial()
        state["completed"] = 9
        handoff.save(state)
        pilot = pilot_3.PilotSession()
        action = pilot.prepare()
        self.assertEqual(action["iteration"], 10)
        pilot.confirm(action["request_id"], "Vérifié", "01234567",
                      verifier=lambda sha: None)
        blocked = pilot.prepare()
        self.assertEqual(blocked["status"], "CHECKPOINT_REQUIRED")
        self.assertFalse(blocked["allow_send"])
        path = handoff.gate.OUT / "cycle_0010.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"iteration": 10, "status": "PASS"}), encoding="utf-8")
        permitted = pilot.prepare()
        self.assertEqual(permitted["status"], "SEND")
        self.assertEqual(permitted["iteration"], 11)

    def test_corrupt_pilot_metadata_never_resets_counter(self):
        pilot_3.PILOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        pilot_3.PILOT_FILE.write_text("{missing}", encoding="utf-8")
        with self.assertRaises(ValueError):
            pilot_3.PilotSession()

    def test_failed_result_blocks_further_requests(self):
        pilot = pilot_3.PilotSession()
        action = pilot.prepare()
        pilot.confirm(action["request_id"], "Tests cassés", "",
                      result="failed")
        self.assertEqual(pilot.prepare()["status"], "REPAIR")
        self.assertEqual(handoff.load()["completed"], 1)


if __name__ == "__main__":
    unittest.main()
