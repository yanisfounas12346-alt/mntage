"""Regression tests for the original offline mirror animation studio."""
import shutil
import tempfile
import unittest
from pathlib import Path

from motion_studio import (
    MotionScene, is_mirror_subject, plan_mirror_scenes,
    render_motion_scene, _background, _draw_frame,
)


SCRIPT = (
    "Imagine : tu te regardes dans un miroir. Tout est normal. "
    "Puis tu fixes ton visage sans bouger. Ton nez paraît bizarre. "
    "C'est ton cerveau qui bugue. Des chercheurs ont réalisé une expérience. "
    "Et certains ont vu des déformations étranges. Mais pourquoi ? "
    "Il reconstruit tout. Quand tu fixes longtemps, des informations disparaissent. "
    "Résultat : ton reflet devient étrange. Et le plus fou ? "
    "Tu n'as pas besoin d'un miroir hanté. Abonne-toi à Science WTF."
)


class MotionStudioTests(unittest.TestCase):
    def test_requires_relevant_subject(self):
        self.assertTrue(is_mirror_subject("Le miroir qui déforme ton visage"))
        self.assertFalse(is_mirror_subject("Pourquoi l'océan est bleu"))

    def test_narrative_beats_cover_duration_without_gaps(self):
        scenes = plan_mirror_scenes(SCRIPT, 86.0)
        self.assertEqual(scenes[0].start, 0.0)
        self.assertEqual(scenes[-1].end, 86.0)
        self.assertEqual(scenes[0].kind, "distort")  # 1-second visual hook
        self.assertEqual(scenes[1].kind, "approach")
        self.assertIn("distort", [scene.kind for scene in scenes])
        self.assertIn("experiment", [scene.kind for scene in scenes])
        for a, b in zip(scenes, scenes[1:]):
            self.assertAlmostEqual(a.end, b.start)
            self.assertGreater(a.end, a.start)

    def test_frames_actually_change_without_moving_camera(self):
        base = _background((540, 960), "distort")
        first = _draw_frame((540, 960), "distort", 0.0, 4, base)
        last = _draw_frame((540, 960), "distort", 1.0, 4, base)
        self.assertNotEqual(first.tobytes(), last.tobytes())
        self.assertEqual(first.getpixel((20, 400)), last.getpixel((20, 400)))

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg non installé")
    def test_exports_short_mp4_without_voice_or_paid_api(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "shot.mp4"
            render_motion_scene(target, MotionScene("distort", 0, 0.2),
                                fps=10, width=540, height=960)
            self.assertGreater(target.stat().st_size, 1024)


if __name__ == "__main__":
    unittest.main()
