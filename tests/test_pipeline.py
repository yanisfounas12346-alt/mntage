"""Offline regression checks: python -m unittest discover -s tests -v"""
import tempfile
import io
import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch
from stock_media import scene_queries, select_video_scenes, search_commons_videos, _download
from subtitles import write_srt, write_ass, timed_groups, write_timed_srt
from video_factory import scene_durations, validate_output, inspect_source_video

class VideoPlanningTests(unittest.TestCase):
    def test_scene_topics(self):
        q=scene_queries("Une forêt immense. Les vagues de l'océan. Les étoiles dans l'espace.",8)
        self.assertTrue(any("forest" in x for x in q))
        self.assertTrue(any("ocean" in x for x in q))
        self.assertTrue(any("space" in x for x in q))
    def test_french_queries_preserve_scene_order(self):
        q=scene_queries("La montagne domine la vallée. Une voiture passe sur la route.\\nUn ordinateur s'allume.",8)
        self.assertEqual(q,["mountain landscape","cars road","computer technology"])

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
    def test_pause_splits_subtitles(self):
        words=[{"text":"Bonjour","offset":0,"duration":1000000},
               {"text":"monde","offset":9000000,"duration":1000000}]
        self.assertEqual(len(timed_groups(words)),2)

    def test_scene_cuts_follow_speech(self):
        words=[{"text":str(i),"offset":i*10000000,"duration":4000000} for i in range(12)]
        durations=scene_durations(12.0,words,3)
        self.assertEqual(len(durations),3)
        self.assertAlmostEqual(sum(durations),12.0)
        self.assertTrue(all(d>0 for d in durations))

    def test_commons_license_and_ranking(self):
        hits={"query":{"pages":{
            "1":{"pageid":1,"title":"File:Random clip.webm","imageinfo":[{"mime":"video/webm","size":2000,"url":"https://example.org/a.webm","extmetadata":{"LicenseShortName":{"value":"CC BY 4.0"}}}]},
            "2":{"pageid":2,"title":"File:Ocean waves.webm","imageinfo":[{"mime":"video/webm","size":3000,"url":"https://example.org/b.webm","extmetadata":{"LicenseShortName":{"value":"CC0"}}}]},
            "3":{"pageid":3,"title":"File:Ocean waves restricted.webm","imageinfo":[{"mime":"video/webm","size":3000,"url":"https://example.org/c.webm","extmetadata":{"LicenseShortName":{"value":"All Rights Reserved"}}}]}
        }}}
        response=io.BytesIO(json.dumps(hits).encode("utf-8"))
        with patch("stock_media.urlopen",return_value=response):
            results=search_commons_videos("ocean waves",limit=1)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]["id"],2)

    def test_source_video_quality_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"clip.webm"
            path.write_bytes(b"video")
            metadata={"streams":[{"width":1280,"height":720}],
                      "format":{"duration":"4.5"}}
            with patch("video_factory.subprocess.run",return_value=SimpleNamespace(
                    returncode=0,stdout=json.dumps(metadata),stderr="")):
                self.assertEqual(inspect_source_video(path)["width"],1280)
                metadata["streams"][0]["height"]=240
                with self.assertRaisesRegex(RuntimeError,"trop petit"):
                    inspect_source_video(path)
                metadata["streams"][0]["height"]=720
                metadata["format"]["duration"]="0.1"
                with self.assertRaisesRegex(RuntimeError,"trop court"):
                    inspect_source_video(path)

    def test_media_download_guards(self):
        with self.assertRaisesRegex(RuntimeError,"HTTPS"):
            _download("http://example.org/video.mp4",1024)
        with patch("stock_media.urlopen") as request:
            response=request.return_value.__enter__.return_value
            response.headers={"Content-Type":"text/html"}
            with self.assertRaisesRegex(RuntimeError,"page"):
                _download("https://example.org/video.mp4",1024)
            response.headers={"Content-Type":"video/mp4","Content-Length":"2048"}
            with self.assertRaisesRegex(RuntimeError,"volumineux"):
                _download("https://example.org/video.mp4",1024)

    def test_short_video_has_no_micro_scenes(self):
        durations=scene_durations(2.0,[],1)
        self.assertEqual(len(durations),1)
        self.assertAlmostEqual(sum(durations),2.0)

    def test_export_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            video=Path(tmp)/"test.mp4"
            video.write_bytes(b"x"*2048)
            probe={"streams":[{"codec_type":"video","width":1080,"height":1920},
                              {"codec_type":"audio"}],"format":{"duration":"12.0"}}
            with patch("video_factory.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout=json.dumps(probe),stderr="")):
                validate_output(video,12.0)
                with self.assertRaisesRegex(RuntimeError,"Durée incorrecte"):
                    validate_output(video,15.0)
                with self.assertRaisesRegex(RuntimeError,"résolution"):
                    probe["streams"][0]["width"]=540
                    validate_output(video,12.0)

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
