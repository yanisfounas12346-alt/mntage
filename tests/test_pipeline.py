"""Offline regression checks: python -m unittest discover -s tests -v"""
import tempfile
import subprocess
import io
import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch
from stock_media import scene_queries, select_video_scenes, search_commons_videos, search_videos, search_pixabay_videos, _download, download_videos, download_commons_scenes
from subtitles import write_srt, write_ass, timed_groups, write_timed_srt
from video_factory import scene_durations, validate_output, inspect_source_video, _run, make_video, duration_seconds, validate_image_dimensions

class QueueNarrationTests(unittest.TestCase):
    def test_voice_rate_saved_and_read_from_queue(self):
        import job_store
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(job_store,"DB",Path(tmp)/"queue.sqlite3"):
            job_id=job_store.enqueue("Titre","Bonjour","Éco","fr-FR-DeniseNeural",True,"+10%")
            job=job_store.next_job()
            self.assertEqual(job["id"],job_id)
            self.assertEqual(job["voice_rate"],"+10%")

    def test_failed_job_can_be_retried_without_losing_voice_rate(self):
        import job_store
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(job_store,"DB",Path(tmp)/"queue.sqlite3"):
            job_id=job_store.enqueue("Titre","Bonjour","Éco","fr-FR-DeniseNeural",True,"+5%")
            self.assertFalse(job_store.retry_failed(job_id))
            job_store.next_job()
            job_store.finish(job_id,error="Erreur temporaire")
            self.assertTrue(job_store.retry_failed(job_id))
            self.assertFalse(job_store.retry_failed(job_id))
            job=job_store.next_job()
            self.assertEqual(job["voice_rate"],"+5%")
            self.assertIsNone(job["error"])

    def test_manual_recovery_only_resets_running_job(self):
        import job_store
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(job_store,"DB",Path(tmp)/"queue.sqlite3"):
            job_id=job_store.enqueue("Titre","Bonjour","Éco","fr-FR-DeniseNeural",True,"+10%")
            self.assertFalse(job_store.recover_interrupted(job_id))
            job_store.next_job()
            self.assertTrue(job_store.recover_interrupted(job_id))
            self.assertFalse(job_store.recover_interrupted(job_id))
            recovered=job_store.next_job()
            self.assertEqual(recovered["voice_rate"],"+10%")

    def test_next_job_claims_each_task_once(self):
        import job_store
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(job_store,"DB",Path(tmp)/"queue.sqlite3"):
            first=job_store.enqueue("Premier","Bonjour","Éco","fr-FR-DeniseNeural",True)
            second=job_store.enqueue("Deuxième","Salut","Éco","fr-FR-DeniseNeural",True)
            self.assertEqual(job_store.next_job()["id"],first)
            self.assertIsNone(job_store.next_job())  # first render still active
            job_store.finish(first,video="first.mp4")
            self.assertEqual(job_store.next_job()["id"],second)
            self.assertIsNone(job_store.next_job())

    def test_concurrent_sessions_claim_only_one_render(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        import job_store
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(job_store,"DB",Path(tmp)/"queue.sqlite3"):
            for index in range(4):
                job_store.enqueue(f"Vidéo {index}","Bonjour","Éco","fr-FR-DeniseNeural",True)
            barrier=Barrier(4)
            def claim(_):
                barrier.wait(timeout=10)
                return job_store.next_job()
            with ThreadPoolExecutor(max_workers=4) as executor:
                results=list(executor.map(claim,range(4)))
            claimed=[job for job in results if job is not None]
            self.assertEqual(len(claimed),1)
            self.assertEqual(claimed[0]["status"],"queued")
            self.assertEqual(sum(job["status"]=="running" for job in job_store.jobs()),1)

    def test_cancel_only_pending_jobs(self):
        import job_store
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(job_store,"DB",Path(tmp)/"queue.sqlite3"):
            first=job_store.enqueue("Annuler","Texte","Éco","fr-FR-DeniseNeural",True)
            self.assertTrue(job_store.cancel_queued(first))
            self.assertFalse(job_store.cancel_queued(first))
            self.assertIsNone(job_store.next_job())
            second=job_store.enqueue("Garder","Texte","Éco","fr-FR-DeniseNeural",True)
            self.assertEqual(job_store.next_job()["id"],second)
            self.assertFalse(job_store.cancel_queued(second))

    def test_existing_database_gets_voice_rate_default(self):
        import sqlite3
        import job_store
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"old.sqlite3"
            with sqlite3.connect(db) as con:
                con.execute("""CREATE TABLE jobs (
                    id INTEGER PRIMARY KEY, created TEXT NOT NULL, title TEXT NOT NULL,
                    script TEXT NOT NULL, mode TEXT NOT NULL, voice TEXT NOT NULL,
                    captions INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                    video TEXT, error TEXT, views INTEGER NOT NULL DEFAULT 0,
                    revenue REAL NOT NULL DEFAULT 0, costs REAL NOT NULL DEFAULT 0,
                    youtube_url TEXT)""")
            with patch.object(job_store,"DB",db):
                with job_store.connect() as con:
                    columns=[row[1] for row in con.execute("PRAGMA table_info(jobs)")]
                self.assertIn("voice_rate",columns)

class VideoPlanningTests(unittest.TestCase):
    def test_pexels_avoids_oversized_files(self):
        payload={"videos":[{"id":7,"video_files":[
            {"file_type":"video/mp4","link":"https://example.org/huge.mp4",
             "size":55*1024*1024,"width":1080,"height":1920},
            {"file_type":"video/mp4","link":"https://example.org/small.mp4",
             "size":20*1024*1024,"width":720,"height":1280}]}]}
        with patch("stock_media._api",return_value=payload):
            clips=search_videos("forest")
        self.assertEqual(clips[0]["url"],"https://example.org/small.mp4")

    def test_pixabay_avoids_oversized_files(self):
        payload={"hits":[{"id":9,"videos":{
            "medium":{"url":"https://example.org/huge.mp4","size":55*1024*1024},
            "small":{"url":"https://example.org/small.mp4","size":12*1024*1024}}}]}
        with tempfile.TemporaryDirectory() as tmp, \
             patch("stock_media.os.environ.get",return_value="test-key"), \
             patch("stock_media.json.load",return_value=payload), \
             patch("stock_media.urlopen",return_value=io.BytesIO(b"{}")):
            import os
            previous=os.getcwd()
            try:
                os.chdir(tmp)
                clips=search_pixabay_videos("forest")
            finally:
                os.chdir(previous)
        self.assertEqual(clips[0]["url"],"https://example.org/small.mp4")

    def test_invalid_media_redirect_url_rejected(self):
        response=io.BytesIO(b"video")
        response.headers={"Content-Type":"video/mp4"}
        response.geturl=lambda: None
        with patch("stock_media.urlopen",return_value=response):
            with self.assertRaisesRegex(RuntimeError,"URL finale"):
                _download("https://example.org/clip.mp4",1024)

    def test_insecure_media_redirect_rejected(self):
        response=io.BytesIO(b"video")
        response.headers={"Content-Type":"video/mp4"}
        response.geturl=lambda: "http://example.org/clip.mp4"
        with patch("stock_media.urlopen",return_value=response):
            with self.assertRaisesRegex(RuntimeError,"Redirection"):
                _download("https://example.org/clip.mp4",1024)

    def test_invalid_audio_duration_rejected(self):
        for value in ("0", "nan", "inf", "-1", "not-a-number"):
            with self.subTest(value=value):
                with patch("video_factory.subprocess.run",
                           return_value=SimpleNamespace(stdout=value,returncode=0)):
                    with self.assertRaises(RuntimeError):
                        duration_seconds(Path("voice.mp3"))

    def test_corrupt_png_payload_rejected_before_voice(self):
        from PIL import Image
        image=Image.new("RGB",(64,64),"red")
        stream=io.BytesIO()
        image.save(stream,format="PNG")
        damaged=bytearray(stream.getvalue())
        position=damaged.index(b"IDAT")+8
        damaged[position] ^= 0x01  # Invalid PNG chunk checksum, valid header.
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Image 1 invalide"):
                make_video("test","Bonjour",[bytes(damaged)])
        voice.assert_not_called()

    def test_music_requires_actual_mp3_stream(self):
        from video_factory import validate_music_audio
        with patch("video_factory.subprocess.run",
                   return_value=SimpleNamespace(returncode=0,stdout='{"streams": []}')):
            with self.assertRaisesRegex(ValueError,"sans piste audio"):
                validate_music_audio(Path("fake.mp3"))
        with patch("video_factory.subprocess.run",
                   return_value=SimpleNamespace(returncode=0,stdout='{"streams":[{"codec_type":"audio","codec_name":"aac"}]}')):
            with self.assertRaisesRegex(ValueError,"véritable fichier MP3"):
                validate_music_audio(Path("fake.mp3"))
        with patch("video_factory.subprocess.run",
                   return_value=SimpleNamespace(returncode=0,stdout='{"streams":[{"codec_type":"audio","codec_name":"mp3"}]}')):
            validate_music_audio(Path("valid.mp3"))

    def test_empty_music_rejected_before_voice(self):
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"musique MP3"):
                make_video("test","Bonjour",[b"image"],music=b"")
        voice.assert_not_called()

    def test_invalid_music_rejected_before_voice(self):
        from PIL import Image
        image=Image.new("RGB",(32,32),"red")
        buffer=io.BytesIO()
        image.save(buffer,format="PNG")
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.duration_seconds",side_effect=RuntimeError("invalid audio")), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Musique MP3 invalide"):
                make_video("test","Bonjour",[buffer.getvalue()],music=b"not an mp3")
        voice.assert_not_called()

    def test_invalid_mp4_rejected_before_voice(self):
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.inspect_source_video",side_effect=RuntimeError("Flux vidéo absent")), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Clip MP4 1 invalide"):
                make_video("test","Bonjour",[],video_bytes=[b"not an mp4"])
        voice.assert_not_called()

    def test_all_mp4_clips_are_checked_before_voice(self):
        calls=[]
        def inspect(path):
            calls.append(path.name)
            if path.name=="source_001.mp4":
                raise RuntimeError("Clip illisible")
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.inspect_source_video",side_effect=inspect), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Clip MP4 2 invalide"):
                make_video("test","Bonjour",[],video_bytes=[b"first",b"second"])
        self.assertEqual(calls,["source_000.mp4","source_001.mp4"])
        voice.assert_not_called()

    def test_corrupt_image_rejected_before_voice(self):
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Image 1 invalide"):
                make_video("test","Bonjour",[b"not an image"])
        voice.assert_not_called()

    def test_empty_uploaded_media_rejected_before_voice(self):
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"visuel importé est vide"):
                make_video("test","Bonjour",[b""])
            with self.assertRaisesRegex(ValueError,"visuel importé est vide"):
                make_video("test","Bonjour",[],video_bytes=[b""])
        voice.assert_not_called()

    def test_rejects_oversized_video_before_voice(self):
        with patch("video_factory.require_ffmpeg"), \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Chaque clip MP4"):
                make_video("test","Bonjour",[],video_bytes=[b"x"*(100*1024*1024+1)])
        voice.assert_not_called()

    def test_rejects_decompressed_images_over_pixel_budget(self):
        validate_image_dimensions(4000,4000)
        with self.assertRaisesRegex(ValueError,"40 mégapixels"):
            validate_image_dimensions(10000,5000)
        with self.assertRaises(ValueError):
            validate_image_dimensions(0,100)

    def test_rejects_oversized_images_before_voice_or_ffmpeg(self):
        with patch("video_factory.require_ffmpeg") as ffmpeg, \
             patch("video_factory.synthesize") as voice:
            with self.assertRaisesRegex(ValueError,"Chaque image"):
                make_video("test","Bonjour",[b"x"*(20*1024*1024+1)])
        voice.assert_not_called()

    def test_failed_render_removes_partial_output(self):
        async def fake_voice(script,destination,voice,rate):
            destination.write_bytes(b"audio")
            return []
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            def fail_render(args,timeout=1800):
                (folder/"test-12345678.mp4").write_bytes(b"partial")
                raise RuntimeError("FFmpeg failed")
            with patch("video_factory.OUT",folder), \
                 patch("video_factory.uuid4",return_value=SimpleNamespace(hex="12345678abcdef")), \
                 patch("video_factory.require_ffmpeg"), \
                 patch("video_factory.synthesize",side_effect=fake_voice), \
                 patch("video_factory.duration_seconds",return_value=2.0), \
                 patch("video_factory.inspect_source_video"), \
                 patch("video_factory._run",side_effect=fail_render):
                with self.assertRaisesRegex(RuntimeError,"FFmpeg failed"):
                    make_video("test","Bonjour",[ ],video_bytes=[b"clip"],captions=False)
            self.assertFalse((folder/"test-12345678.mp4").exists())

    def test_ffmpeg_timeout_is_reported(self):
        with patch("video_factory.subprocess.run",side_effect=subprocess.TimeoutExpired(["ffmpeg"],3)):
            with self.assertRaisesRegex(RuntimeError,"délai"):
                _run(["ffmpeg","-version"],timeout=3)

    def test_scene_topics(self):
        q=scene_queries("Une forêt immense. Les vagues de l'océan. Les étoiles dans l'espace.",8)
        self.assertTrue(any("forest" in x for x in q))
        self.assertTrue(any("ocean" in x for x in q))
        self.assertTrue(any("space" in x for x in q))
    def test_french_queries_preserve_scene_order(self):
        q=scene_queries("La montagne domine la vallée. Une voiture passe sur la route.\nUn ordinateur s'allume.",8)
        self.assertEqual(q,["mountain landscape","cars road","computer technology"])

    def test_irregular_french_plurals_select_animal_footage(self):
        self.assertEqual(scene_queries("Les animaux traversent la plaine.")[0],
                         "wildlife animals")
        self.assertEqual(scene_queries("Des chevaux courent dans les champs.")[0],
                         "wildlife animals")

    def test_no_false_keyword_matches(self):
        self.assertNotEqual(scene_queries("Le premier jour sera difficile.")[0],"ocean waves")
        self.assertEqual(scene_queries("La mer est calme.")[0],"ocean waves")

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

    def test_commons_accepts_visual_synonyms(self):
        hits={"query":{"pages":{
            "1":{"pageid":1,"title":"File:Alps sunrise.webm","imageinfo":[
                {"mime":"video/webm","size":2000,"url":"https://example.org/alps.webm",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"}}}]},
            "2":{"pageid":2,"title":"File:Random celebration.webm","imageinfo":[
                {"mime":"video/webm","size":2000,"url":"https://example.org/random.webm",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"}}}]}}}}
        with patch("stock_media.urlopen",return_value=io.BytesIO(json.dumps(hits).encode())):
            results=search_commons_videos("mountain landscape",limit=6)
        self.assertEqual([item["id"] for item in results],[1])

    def test_commons_matches_specific_animal_titles(self):
        hits={"query":{"pages":{
            "1":{"pageid":1,"title":"File:Horse running.webm","imageinfo":[
                {"mime":"video/webm","size":2000,"url":"https://example.org/horse.webm",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"}}}]},
            "2":{"pageid":2,"title":"File:Industrial machinery.webm","imageinfo":[
                {"mime":"video/webm","size":2000,"url":"https://example.org/machine.webm",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"}}}]}}}}
        with patch("stock_media.urlopen",return_value=io.BytesIO(json.dumps(hits).encode())):
            results=search_commons_videos("wildlife animals",limit=6)
        self.assertEqual([item["id"] for item in results],[1])

    def test_commons_rejects_unrelated_titles(self):
        hits={"query":{"pages":{
            "1":{"pageid":1,"title":"File:Random celebration.webm","imageinfo":[
                {"mime":"video/webm","size":2000,"url":"https://example.org/a.webm",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"}}}]},
            "2":{"pageid":2,"title":"File:Forest trees.webm","imageinfo":[
                {"mime":"video/webm","size":2000,"url":"https://example.org/b.webm",
                 "extmetadata":{"LicenseShortName":{"value":"CC0"}}}]}}}}
        with patch("stock_media.urlopen",return_value=io.BytesIO(json.dumps(hits).encode())):
            results=search_commons_videos("forest trees",limit=6)
        self.assertEqual([item["id"] for item in results],[2])

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

    def test_invalid_video_durations_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"clip.mp4"
            path.write_bytes(b"x"*2048)
            for invalid in ("nan","inf","-inf","invalid"):
                with self.subTest(value=invalid):
                    source={"streams":[{"width":1280,"height":720}],
                            "format":{"duration":invalid}}
                    with patch("video_factory.subprocess.run",return_value=SimpleNamespace(
                            returncode=0,stdout=json.dumps(source),stderr="")):
                        with self.assertRaises(RuntimeError):
                            inspect_source_video(path)
                    exported={"streams":[{"codec_type":"video","width":1080,"height":1920},
                                         {"codec_type":"audio"}],
                              "format":{"duration":invalid}}
                    with patch("video_factory.subprocess.run",return_value=SimpleNamespace(
                            returncode=0,stdout=json.dumps(exported),stderr="")):
                        with self.assertRaises(RuntimeError):
                            validate_output(path,5.0)

    def test_source_duration_falls_back_to_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"source.webm"
            path.write_bytes(b"video")
            metadata={"streams":[{"width":1280,"height":720,"duration":"N/A"}],
                      "format":{"duration":"3.25"}}
            with patch("video_factory.subprocess.run",return_value=SimpleNamespace(
                    returncode=0,stdout=json.dumps(metadata),stderr="")):
                self.assertAlmostEqual(inspect_source_video(path)["duration"],3.25)

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

    def test_commons_broadens_after_corrupt_results(self):
        broken={"id":1,"url":"https://example.org/broken.webm"}
        good={"id":2,"url":"https://example.org/good.webm"}
        def search(query,limit):
            return [broken] if query=="mountain landscape" else [broken,good]
        with patch("stock_media.scene_queries",return_value=["mountain landscape"]), \
             patch("stock_media.search_commons_videos",side_effect=search), \
             patch("stock_media._download",return_value=b"video") as download, \
             patch("stock_media._valid_video_payload",side_effect=[False,True]):
            found,clips,missing=download_commons_scenes("La montagne.",limit=1)
        self.assertEqual(found[0]["id"],2)
        self.assertEqual(download.call_count,2)
        self.assertEqual(missing,[])

    def test_commons_fallback_uses_subject_not_generic_modifier(self):
        clip={"id":42,"url":"https://example.org/space.webm"}
        def search(query,limit):
            return [clip] if query=="space" else []
        with patch("stock_media.scene_queries",return_value=["outer space stars"]), \
             patch("stock_media.search_commons_videos",side_effect=search) as lookup, \
             patch("stock_media._download",return_value=b"video"), \
             patch("stock_media._valid_video_payload",return_value=True):
            found,clips,missing=download_commons_scenes("Les étoiles.",limit=1)
        self.assertEqual(found[0]["id"],42)
        self.assertEqual([call.args[0] for call in lookup.call_args_list],
                         ["outer space stars","space"])
        self.assertFalse(missing)

    def test_commons_broadens_empty_search(self):
        clip={"id":3,"url":"https://example.org/mountain.webm"}
        def search(query,limit):
            return [] if query=="mountain landscape" else [clip]
        with patch("stock_media.scene_queries",return_value=["mountain landscape"]), \
             patch("stock_media.search_commons_videos",side_effect=search) as search_mock, \
             patch("stock_media._download",return_value=b"video"), \
             patch("stock_media._valid_video_payload",return_value=True):
            found,clips,missing=download_commons_scenes("La montagne.",limit=1)
        self.assertEqual(found[0]["id"],3)
        self.assertEqual(search_mock.call_count,2)
        self.assertEqual(missing,[])

    def test_commons_retries_corrupt_clip(self):
        options=[
            {"id":1,"url":"https://example.org/corrupt.webm"},
            {"id":2,"url":"https://example.org/valid.webm"}]
        with patch("stock_media.scene_queries",return_value=["forest trees"]), \
             patch("stock_media.search_commons_videos",return_value=options), \
             patch("stock_media._download",return_value=b"video"), \
             patch("stock_media._valid_video_payload",side_effect=[False,True]):
            found,clips,missing=download_commons_scenes("Une forêt.",limit=1)
        self.assertEqual(found[0]["id"],2)
        self.assertEqual(len(clips),1)
        self.assertEqual(missing,[])

    def test_commons_retries_failed_clip(self):
        options=[
            {"id":1,"url":"https://example.org/broken.webm"},
            {"id":2,"url":"https://example.org/good.webm"}]
        def fetch(url,limit):
            if "broken" in url:
                raise RuntimeError("HTTP 404")
            return b"valid-video"
        with patch("stock_media.scene_queries",return_value=["forest trees"]), \
             patch("stock_media.search_commons_videos",return_value=options), \
             patch("stock_media._download",side_effect=fetch), \
             patch("stock_media._valid_video_payload",return_value=True):
            found,clips,missing=download_commons_scenes("Une forêt.",limit=1)
        self.assertEqual(found[0]["id"],2)
        self.assertEqual(clips,[b"valid-video"])
        self.assertFalse(missing)

    def test_download_videos_limits_each_source(self):
        with patch("stock_media._download",return_value=b"video") as download:
            clips=download_videos([{"url":"https://example.org/a.mp4"}])
        self.assertEqual(clips,[b"video"])
        self.assertEqual(download.call_args.args[1],35*1024*1024)

    def test_media_download_guards(self):
        with self.assertRaisesRegex(RuntimeError,"HTTPS"):
            _download("http://example.org/video.mp4",1024)
        with patch("stock_media.urlopen") as request:
            response=request.return_value.__enter__.return_value
            response.geturl.return_value="https://example.org/video.mp4"
            response.headers={"Content-Type":"text/html"}
            with self.assertRaisesRegex(RuntimeError,"page"):
                _download("https://example.org/video.mp4",1024)
            response.headers={"Content-Type":"video/mp4","Content-Length":"2048"}
            with self.assertRaisesRegex(RuntimeError,"volumineux"):
                _download("https://example.org/video.mp4",1024)

    def test_scene_planning_rejects_nonfinite_duration(self):
        for duration in (float("nan"),float("inf"),float("-inf"),0.0,-2.0):
            with self.subTest(duration=duration):
                with self.assertRaises(ValueError):
                    scene_durations(duration,[],3)

    def test_scene_cut_rhythm_and_total_duration(self):
        words=[{"offset":int(t*10000000),"duration":1000000}
               for t in (1.8,3.9,6.1,8.2,10.1,12.2,14.1,16.1)]
        durations=scene_durations(18.0,words,3)
        self.assertAlmostEqual(sum(durations),18.0)
        self.assertTrue(all(1.0<=d<=6.0 for d in durations),durations)

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
