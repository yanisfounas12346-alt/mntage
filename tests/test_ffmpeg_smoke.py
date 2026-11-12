"""Offline FFmpeg smoke test: verifies real vertical video + audio encoding."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_factory import inspect_source_video, validate_output


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "FFmpeg and ffprobe not installed")
class FFmpegSmokeTests(unittest.TestCase):
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
