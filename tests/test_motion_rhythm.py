"""Regression tests for fast, story-driven 2D editing and word-level lip motion."""
import unittest
from motion_studio import MotionScene, plan_mirror_scenes, mouth_open_at, _background, _draw_frame


SCRIPT = (
    "Imagine : tu te regardes dans un miroir. Tout est normal. "
    "Puis tu fixes ton visage sans bouger. Ton nez paraît bizarre. "
    "C'est ton cerveau qui bugue. Des chercheurs ont étudié une expérience. "
    "Et certains ont vu des déformations étranges. Mais pourquoi ? "
    "Il reconstruit tout. Quand tu fixes longtemps, des informations disparaissent. "
    "Résultat : ton reflet devient étrange. Et le plus fou ? "
    "Tu n'as pas besoin d'un miroir hanté. Abonne-toi à Science WTF."
)


class MotionRhythmTests(unittest.TestCase):
    def test_no_shot_over_3_25_seconds(self):
        shots = plan_mirror_scenes(SCRIPT, 86.0)
        self.assertGreater(len(shots), 20)
        self.assertLessEqual(max(s.end - s.start for s in shots), 3.251)
        self.assertEqual(shots[0].start, 0.0)
        self.assertEqual(shots[-1].end, 86.0)
        for first, second in zip(shots, shots[1:]):
            self.assertAlmostEqual(first.end, second.start)

    def test_mouth_uses_word_boundaries_without_changing_audio(self):
        words = [{"offset": 10_000_000, "duration": 3_000_000, "text": "bonjour"}]
        self.assertEqual(mouth_open_at(0.5, words), 0.0)
        self.assertGreater(mouth_open_at(1.2, words), 0.2)
        self.assertEqual(mouth_open_at(1.8, words), 0.0)

    def test_all_four_shot_compositions_render(self):
        base = _background((540, 960), "distort")
        shots = [_draw_frame((540, 960), "distort", 0.45, 2.8, base,
                             shot=i, mouth=0.9) for i in range(4)]
        self.assertEqual(len({im.tobytes() for im in shots}), 4)


if __name__ == "__main__":
    unittest.main()
