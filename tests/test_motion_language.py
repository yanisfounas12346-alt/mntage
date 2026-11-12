"""Visual consistency and rhythm regression checks for six-shot 2D animation."""
import unittest

from motion_studio import _background, _draw_frame, plan_mirror_scenes


SCRIPT = (
    "Imagine : tu te regardes dans un miroir. Tout est normal. "
    "Puis tu fixes ton visage sans bouger. Ton nez paraît bizarre. "
    "C'est ton cerveau qui bugue. Des chercheurs ont réalisé une expérience. "
    "Et certains ont rapporté des déformations étranges. Mais pourquoi ? "
    "Il reconstruit ce que tu vois. Quand tu fixes longtemps, des informations "
    "disparaissent. Résultat : ton reflet devient étrange. Et le plus fou ? "
    "Pas besoin d'un miroir hanté. Abonne-toi à Science WTF."
)


class MotionLanguageTests(unittest.TestCase):
    def test_six_different_compositions_for_mirror_and_science(self):
        for kind in ("distort", "brain", "experiment"):
            with self.subTest(kind=kind):
                background = _background((540, 960), kind)
                frames = [
                    _draw_frame((540, 960), kind, .64, 3, background,
                                shot=i, mouth=.4, beat_progress=.64)
                    for i in range(6)
                ]
                self.assertEqual(len({im.tobytes() for im in frames}), 6)

    def test_no_camera_motion_in_same_shot(self):
        background = _background((540, 960), "distort")
        first = _draw_frame((540, 960), "distort", 0, 3, background, shot=4)
        last = _draw_frame((540, 960), "distort", 1, 3, background, shot=4)
        # Pixels far from the animated content stay locked in place.
        self.assertEqual(first.getpixel((10, 510)), last.getpixel((10, 510)))

    def test_short_shots_cover_narration(self):
        for duration in (42.3, 86.64, 110.0):
            with self.subTest(duration=duration):
                shots = plan_mirror_scenes(SCRIPT, duration)
                self.assertAlmostEqual(shots[0].start, 0)
                self.assertAlmostEqual(shots[-1].end, duration)
                self.assertLessEqual(max(s.end - s.start for s in shots), 3.251)
                self.assertTrue(set(range(6)).issubset({s.shot for s in shots}))
                for a, b in zip(shots, shots[1:]):
                    self.assertAlmostEqual(a.end, b.start)

    def test_story_context_changes_artwork(self):
        frames = []
        for kind in ("brain", "distort", "experiment"):
            base = _background((540, 960), kind)
            frames.append(_draw_frame((540, 960), kind, .5, 3, base,
                                      shot=4).tobytes())
        self.assertEqual(len(set(frames)), 3)


if __name__ == "__main__":
    unittest.main()
