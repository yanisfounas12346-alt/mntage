"""Walking-arm regression tests: natural alternating movement and fixed lengths."""
import math
import unittest
from unittest.mock import patch

from motion_director import (
    FOREARM_LENGTH, UPPER_ARM_LENGTH, walking_arm_pose,
)
from motion_studio import _background, _draw_frame


SPEED = 6.2


class WalkingArmTests(unittest.TestCase):
    def test_upper_and_forearm_lengths_are_constant(self):
        for i in range(121):
            t = math.tau*i/(120*SPEED)
            for side in (-1, 1):
                shoulder, elbow, wrist = walking_arm_pose(t, side)
                with self.subTest(frame=i, side=side):
                    self.assertAlmostEqual(
                        math.dist(shoulder, elbow), UPPER_ARM_LENGTH, places=6)
                    self.assertAlmostEqual(
                        math.dist(elbow, wrist), FOREARM_LENGTH, places=6)

    def test_arm_swing_is_opposite_on_left_and_right(self):
        for phase in (math.pi/2 + .2, 3*math.pi/2 + .2):
            t = phase/SPEED
            left = walking_arm_pose(t, -1)[-1]
            right = walking_arm_pose(t, 1)[-1]
            with self.subTest(phase=phase):
                self.assertGreater(abs(left[1] - right[1]), 20)
                self.assertAlmostEqual(left[1] + right[1], 42, places=5)
        first = math.pi/2 + .2
        left_up = walking_arm_pose((first+math.pi)/SPEED, -1)[-1]
        right_up = walking_arm_pose(first/SPEED, 1)[-1]
        self.assertLess(left_up[1], 12)
        self.assertLess(right_up[1], 12)

    def test_half_cycle_mirrors_opposite_arm(self):
        half_period = math.pi/SPEED
        for t in (0, .11, .27, .43, .8, 1.21):
            left = walking_arm_pose(t, -1)
            right_later = walking_arm_pose(t+half_period, 1)
            for left_point, right_point in zip(left, right_later):
                self.assertAlmostEqual(left_point[0], -right_point[0], places=6)
                self.assertAlmostEqual(left_point[1], right_point[1], places=6)

    def test_elbows_remain_outside_torso_and_motion_is_smooth(self):
        step = 1/25
        for i in range(26):
            t = i*step
            for side in (-1, 1):
                first = walking_arm_pose(t, side)
                second = walking_arm_pose(t+step, side)
                self.assertGreater(side*first[1][0], 20)
                self.assertTrue(all(math.isfinite(value)
                    for point in first for value in point))
                self.assertLess(
                    max(math.dist(a, b) for a, b in zip(first, second)), 14)

    def test_cycle_continuity_at_boundaries(self):
        period = math.tau/SPEED
        for side in (-1, 1):
            for t in (0, .1, .3, .8):
                before = walking_arm_pose(t, side)
                after = walking_arm_pose(t + period, side)
                for a, b in zip(before, after):
                    self.assertAlmostEqual(a[0], b[0], places=5)
                    self.assertAlmostEqual(a[1], b[1], places=5)
            for boundary in (0, period/2, period):
                before = walking_arm_pose(boundary-1e-5, side)
                after = walking_arm_pose(boundary+1e-5, side)
                self.assertLess(
                    max(math.dist(a, b) for a,b in zip(before, after)), .005)

    def test_animation_renders_new_arms_without_moving_camera(self):
        base = _background((540, 960), "approach")
        options = dict(shot=0, mouth=0, beat_progress=.4,
                       absolute_seconds=(math.pi/2+.2)/SPEED, beat_rate=.2)
        articulated = _draw_frame(
            (540, 960), "approach", .4, 3, base, **options)
        with patch("motion_director.walking_arm_pose",
                   side_effect=lambda t, side: (
                       (6*side, -20), (37*side, -8), (57*side, 25))) as mocked:
            rigid = _draw_frame(
                (540, 960), "approach", .4, 3, base, **options)
        self.assertEqual(mocked.call_count, 2)
        self.assertNotEqual(articulated.tobytes(), rigid.tobytes())
        self.assertEqual(articulated.getpixel((10, 510)),
                         rigid.getpixel((10, 510)))

    def test_nonwalking_actions_do_not_invoke_arm_solver(self):
        base = _background((540, 960), "stare")
        with patch("motion_director.walking_arm_pose") as mocked:
            _draw_frame((540, 960), "stare", .5, 2, base,
                        shot=1, mouth=0.0, absolute_seconds=.5)
        mocked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
