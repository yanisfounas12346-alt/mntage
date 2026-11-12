"""Offline FFmpeg smoke test: verifies real vertical video + audio encoding."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_factory import inspect_source_video, validate_output, make_video
from unittest.mock import patch
from subtitles import write_ass


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and ffprobe not installed")
class FFmpegSmokeTests(unittest.TestCase):
    def test_full_pipeline_with_offline_voice(self):
        """Exercise make_video end-to-end without network or Edge TTS."""
        async def fake_synthesize(script, destination, voice, rate):
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=2",
                 "-c:a","libmp3lame",str(destination)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            if result.returncode:
                raise RuntimeError(result.stderr[-1000:])
            return [{"text":"Bonjour","offset":0,"duration":9000000},
                    {"text":"monde","offset":10000000,"duration":9000000}]
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            source=work/"source.mp4"
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-f","lavfi","-i","color=c=blue:s=640x640:r=25:d=2",
                 "-c:v","libx264","-preset","ultrafast","-crf","30",str(source)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr[-1000:])
            with patch("video_factory.OUT",work), \
                 patch("video_factory.synthesize",side_effect=fake_synthesize):
                output=make_video("offline-test","Bonjour monde",[],
                                  video_bytes=[source.read_bytes()],captions=True)
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".srt").is_file())
            self.assertIn("Bonjour monde",output.with_suffix(".srt").read_text(encoding="utf-8"))
            validate_output(output,2.0)

    def test_burned_in_subtitles_with_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            write_ass("Bonjour monde",1.2,work/"captions.ass")
            target=work/"captioned.mp4"
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-f","lavfi","-i","color=c=black:s=1080x1920:r=25:d=1.2",
                 "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=1.2",
                 "-vf","ass=captions.ass",
                 "-map","0:v:0","-map","1:a:0",
                 "-c:v","libx264","-preset","ultrafast","-crf","30",
                 "-pix_fmt","yuv420p","-c:a","aac","-shortest",str(target)]
            result=subprocess.run(cmd,cwd=str(work),capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr[-1000:])
            validate_output(target,1.2)

    def test_two_scene_concat_with_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)
            segments=[]
            for i,color in enumerate(("red","blue")):
                segment=work/f"scene_{i}.mp4"
                cmd=["ffmpeg","-hide_banner","-loglevel","error","-y",
                     "-f","lavfi","-i",f"color=c={color}:s=1080x1920:r=25:d=0.6",
                     "-c:v","libx264","-preset","ultrafast","-crf",str(26+i),
                     "-pix_fmt","yuv420p",str(segment)]
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stderr[-1000:])
                segments.append(segment)
            playlist=work/"clips.txt"
            playlist.write_text("".join(f"file '{p.name}'\n" for p in segments))
            target=work/"combined.mp4"
            cmd=["ffmpeg","-hide_banner","-loglevel","error","-y",
                 "-f","concat","-safe","0","-i",str(playlist),
                 "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=1.2",
                 "-map","0:v:0","-map","1:a:0","-t","1.2",
                 "-c:v","libx264","-preset","ultrafast","-crf","30",
                 "-pix_fmt","yuv420p","-c:a","aac",str(target)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr[-1000:])
            validate_output(target,1.2)

    def test_synthetic_vertical_mp4_with_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"smoke.mp4"
            command=[
                "ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","lavfi","-i","color=c=black:s=1080x1920:r=25:d=1",
                "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=1",
                "-map","0:v:0","-map","1:a:0",
                "-c:v","libx264","-preset","ultrafast","-crf","30",
                "-c:a","aac","-shortest",str(target)]
            result=subprocess.run(command,capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stderr[-1000:])
            validate_output(target,1.0)
            source=inspect_source_video(target)
            self.assertEqual(source["height"],1920)
            self.assertGreater(source["duration"],0.5)


if __name__=="__main__":
    unittest.main()
