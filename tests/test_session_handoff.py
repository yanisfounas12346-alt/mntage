"""Tests: resume state survives process restarts and fail-closed checkpoints."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from tools import session_handoff as handoff


class SessionHandoffTests(unittest.TestCase):
    def setUp(self):
        self.folder=TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root=Path(self.folder.name)
        self._state_patch=patch.object(handoff,"STATE_FILE",self.root/"session.json")
        self._gate_patch=patch.object(handoff.gate,"OUT",self.root/"checkpoints")
        self._handoff_patch=patch.object(handoff,"HANDOFF_FILE",self.root/"resume_prompt.txt")
        self._state_patch.start()
        self._gate_patch.start()
        self._handoff_patch.start()
        self.addCleanup(self._state_patch.stop)
        self.addCleanup(self._gate_patch.stop)
        self.addCleanup(self._handoff_patch.stop)

    def test_persists_counter_and_does_not_send_pending_twice(self):
        s=handoff.initial()
        first=handoff.begin(s)
        self.assertEqual(first["iteration"],1)
        persisted=handoff.load()
        repeat=handoff.begin(persisted)
        self.assertEqual(repeat["status"],"PENDING_REVIEW")
        self.assertFalse(repeat["allow_send"])
        self.assertEqual(persisted["completed"],0)
        handoff.complete(persisted,first["request_id"],
                         "Amélioration du personnage",commit="abc123",
                         focus="Rendre les gestes plus naturels",result="validated")
        reloaded=handoff.load()
        self.assertEqual(reloaded["completed"],1)
        self.assertIsNone(reloaded["pending"])
        self.assertIn("abc123",handoff.make_handoff(reloaded))
        self.assertIn("Rendre les gestes",handoff.make_handoff(reloaded))

    def test_handoff_file_is_refreshed_after_every_change(self):
        s=handoff.initial()
        handoff.save(s)
        first=handoff.begin(s)
        text=handoff.HANDOFF_FILE.read_text(encoding="utf-8")
        self.assertIn(first["request_id"],text)
        handoff.complete(s,first["request_id"],"Première amélioration vérifiée")
        updated=handoff.HANDOFF_FILE.read_text(encoding="utf-8")
        self.assertIn("DEMANDES CONFIRMÉES : 1/600",updated)
        self.assertNotIn("EN COURS, ID",updated)

    def test_old_100_request_cycle_migrates_without_losing_work(self):
        state = handoff.initial()
        state["goal"] = 100
        state["completed"] = 17
        state["last_commit"] = "deadbeef"
        state["history"] = [{"number": 17, "summary": "Ancien résultat",
                             "result": "validated", "commit": "deadbeef"}]
        state["pending"] = {"request_id": "existing-id", "iteration": 18,
                            "prompt": "Correction non terminée"}
        handoff.save(state)
        migrated = handoff.load()
        self.assertEqual(migrated["goal"], 600)
        self.assertEqual(migrated["completed"], 17)
        self.assertEqual(migrated["pending"]["request_id"], "existing-id")
        self.assertEqual(len(migrated["history"]), 1)
        self.assertEqual(handoff.load()["goal"], 600)
        self.assertIn("17/600", handoff.HANDOFF_FILE.read_text(encoding="utf-8"))

    def test_rejects_wrong_request_id_and_does_not_increment(self):
        s=handoff.initial()
        handoff.begin(s)
        with self.assertRaises(ValueError):
            handoff.complete(s,"wrong","Ne doit pas compter")
        self.assertEqual(handoff.load()["completed"],0)

    def test_tenth_request_blocks_until_successful_checkpoint(self):
        s=handoff.initial()
        s["completed"]=9
        handoff.save(s)
        action=handoff.begin(s)
        handoff.complete(s,action["request_id"],"Neuvième correction terminée")
        self.assertEqual(s["completed"],10)
        self.assertEqual(handoff.begin(s)["status"],"CHECKPOINT_REQUIRED")
        path=handoff.gate.OUT/"cycle_0010.json"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps({"iteration":10,"status":"FAIL"}),encoding="utf-8")
        self.assertEqual(handoff.begin(s)["status"],"REPAIR")
        path.write_text(json.dumps({"iteration":10,"status":"PASS"}),encoding="utf-8")
        next_action=handoff.begin(s)
        self.assertEqual(next_action["status"],"SEND")
        self.assertEqual(next_action["iteration"],11)

    def test_repair_cannot_be_counted_as_optimization(self):
        s=handoff.initial()
        action=handoff.begin(s)
        handoff.complete(s,action["request_id"],"Régression détectée",result="failed")
        self.assertEqual(handoff.begin(s)["status"],"REPAIR")
        with patch.object(handoff.gate,"checkpoint",return_value=True):
            result=handoff.checkpoint(s,force=True,pull=False)
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(s["completed"],1)
        self.assertEqual(handoff.begin(s)["iteration"],2)

    def test_resume_warnings_for_in_flight_request(self):
        s=handoff.initial()
        action=handoff.begin(s)
        text=handoff.make_handoff(handoff.load())
        self.assertIn(action["request_id"],text)
        self.assertIn("Ne PAS réenvoyer",text)
        self.assertIn("30 EUR/mois",text)
        self.assertIn("QUALITY_GATE_100.md",text)

    def test_corrupted_state_does_not_reset_progress(self):
        handoff.STATE_FILE.write_text("not json",encoding="utf-8")
        with self.assertRaises(ValueError):
            handoff.load()


if __name__=="__main__":
    unittest.main()
