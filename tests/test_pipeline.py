"""Offline regression checks: python -m unittest discover -s tests -v"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from stock_media import scene_queries, select_video_scenes
from subtitles import write_srt, write_ass, timed_groups, write_timed_srt

class VideoPlanningTests(unittest.TestCase):
    def test_scene_topics(self):
        q=scene_queries("Une forêt immense. Les vagues de l'océan. Les étoiles dans l'espace.",8)
        self.assertTrue(any("forest" in x for x in q))
        self.assertTrue(any("ocean" in x for x in q))
        self.assertTrue(any("space" in x for x in q))
    def test_unique_clips(self):
        clips=[{"id":1,"url":"a"},{"id":2,"url":"b"}]
        with patch("stock_media.search_videos",return_value=clips):
            selected,missing=select_video_scenes("Une forêt. Un océan.",8)
        self.assertEqual([v["id"] for v in selected],[1,2])
        self.assertFalse(missing)
    def test_real_word_timing(self):
        words=[
            {"text":"Bonjour","offset":1000000,"duration":2000000},
            {"text":"le","offset":3500000,"duration":1000000},
            {"text":"monde","offset":5000000,"duration":2500000},
        ]
        groups=timed_groups(words)
        self.assertEqual(len(groups),1)
        self.assertAlmostEqual(groups[0][0],0.1)
        self.assertAlmostEqual(groups[0][1],0.75)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"timed.srt"
            write_timed_srt(words,path)
            self.assertIn("00:00:00,100 --> 00:00:00,750",path.read_text(encoding="utf-8"))
    def test_short_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            srt=Path(tmp)/"test.srt"
            ass=Path(tmp)/"test.ass"
            text="Un deux trois quatre cinq six sept huit neuf."
            write_srt(text,8,srt)
            write_ass(text,8,ass)
            self.assertIn("00:00:00,000 -->",srt.read_text(encoding="utf-8"))
            self.assertIn("Un deux trois quatre",srt.read_text(encoding="utf-8"))
            self.assertIn("Style: Caption",ass.read_text(encoding="utf-8-sig"))
if __name__=="__main__":unittest.main()
