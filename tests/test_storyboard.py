"""Fast, offline regression checks for storyboard timing and ordering."""
import unittest
from video_factory import scene_source_index, scene_durations


class StoryboardTests(unittest.TestCase):
    def test_ordered_visuals_are_contiguous(self):
        indices = [scene_source_index(i, 22, 8) for i in range(22)]
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 7)
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(set(indices), set(range(8)))

    def test_single_image(self):
        self.assertEqual([scene_source_index(i, 6, 1) for i in range(6)], [0] * 6)

    def test_no_invalid_index(self):
        with self.assertRaises(ValueError):
            scene_source_index(5, 5, 3)

    def test_durations_cover_audio(self):
        durations = scene_durations(86.64, [], 8)
        self.assertAlmostEqual(sum(durations), 86.64, places=5)
        self.assertTrue(all(d > 0 for d in durations))


if __name__ == "__main__":
    unittest.main()
