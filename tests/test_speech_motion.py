"""Offline lip-sync and frame-timing regression tests."""
import math
from array import array
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

from speech_motion import SpeechMotion, speech_motion_from_pcm, analyze_speech_audio
from motion_studio import plan_mirror_scenes, MotionScene, render_motion_scene


def sample_audio(rate=8000):
    """Half second silence, 0.6s speech-like tone, then 0.4s silence."""
    samples = [0] * (rate // 2)
    samples += [int(11000 * math.sin(2 * math.pi * 180 * i / rate))
                for i in range(round(rate * 0.6))]
    samples += [0] * round(rate * .4)
    return array("h", samples).tobytes()


class SpeechMotionTests(unittest.TestCase):
    def test_voice_moves_mouth_and_silence_closes_it(self):
        track=speech_motion_from_pcm(sample_audio())
        self.assertEqual(track.at(.20),0.0)
        self.assertGreater(track.at(.75),.6)
        self.assertEqual(track.at(1.40),0.0)

    def test_loud_speech_articulates_instead_of_holding_open_mouth(self):
        track=SpeechMotion((1.0,)*100)
        poses=[track.mouth_at(t) for t in (.10,.20,.30,.40,.50,.60)]
        self.assertGreater(max(poses)-min(poses),.4)
        quiet=SpeechMotion((0.0,)*100)
        self.assertEqual(quiet.mouth_at(.4),0.0)

    def test_empty_audio_and_invalid_input(self):
        self.assertEqual(speech_motion_from_pcm(b"").at(1.0),0.0)
        with self.assertRaises(ValueError):
            speech_motion_from_pcm(b"x")

    def test_subframe_interpolation_and_bounds(self):
        track=SpeechMotion((0.0,1.0,0.0))
        self.assertAlmostEqual(track.at(.01),.5)
        self.assertEqual(track.at(-1),0.0)
        self.assertEqual(track.at(100),0.0)

    @unittest.skipUnless(shutil.which("ffmpeg"),"FFmpeg non disponible")
    def test_decode_real_audio_container_without_voice_modification(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"synthetic.wav"
            with wave.open(str(path),"wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(sample_audio())
            track=analyze_speech_audio(path)
            self.assertGreater(track.at(.75),.6)
            self.assertEqual(track.at(.2),0.0)

    def test_cut_frame_rounding_has_no_cumulative_drift(self):
        script=(
            "Imagine tu te regardes dans un miroir. Puis tu fixes ton visage sans bouger. "
            "Ton nez devient étrange. C'est ton cerveau qui bugue. Des chercheurs "
            "ont réalisé une expérience. Et certains ont vu des déformations étranges. "
            "Mais pourquoi ? Il reconstruit ce que tu vois. Quand tu fixes longtemps "
            "tu perds les détails. Résultat : ton reflet semble flippant. "
            "Le plus fou ? Pas besoin d'un miroir hanté. Abonne-toi à Science WTF."
        )
        total=86.64
        scenes=plan_mirror_scenes(script,total)
        for fps in (25,30):
            frame_lengths=[round(s.end*fps)-round(s.start*fps) for s in scenes]
            self.assertGreater(min(frame_lengths),0)
            self.assertEqual(sum(frame_lengths),round(total*fps))


if __name__=="__main__":
    unittest.main()
