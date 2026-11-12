"""Regression tests for chest and shoulder weight transfer during walking."""
import math
import unittest
from unittest.mock import patch

from motion_director import (
    FOREARM_LENGTH, UPPER_ARM_LENGTH, walk_pose,
    walking_arm_pose, walking_torso_pose,
)
from motion_studio import _background, _draw_frame


SPEED = 6.2


class WalkingTorsoTests(unittest.TestCase):
    def test_chest_follows_planted_leg_not_swinging_leg(self):
        for phase, expected_support in (
            (math.pi / 2, 1), (3 * math.pi / 2, -1),
        ):
            with self.subTest(phase=phase):
                t = phase / SPEED
                shift, roll = walking_torso_pose(t)
                _, _, legs, stride = walk_pose(t)
                planted = 1 if stride > 0 else -1
                self.assertEqual(planted, expected_support)
                self.assertGreater(shift * planted, 4.9)
                self.assertTrue(math.isfinite(roll))
                self.assertAlmostEqual(
                    legs[0 if planted == -1 else 1][2][1]
                    + walk_pose(t)[1], 159, places=6,
                )

    def test_torso_and_shoulders_stay_within_subtle_limits(self):
        for sample in range(251):
            t = sample * math.tau / (250 * SPEED)
            chest, roll = walking_torso_pose(t)
            self.assertLessEqual(abs(chest), 5.000001)
            self.assertLessEqual(abs(roll), 2.400001)
            next_chest, next_roll = walking_torso_pose(t + 1 / 25)
            self.assertLess(abs(next_chest - chest), 1.3)
            self.assertLess(abs(next_roll - roll), .61)

    def test_torso_motion_is_periodic_and_contact_continuous(self):
        period = math.tau / SPEED
        for t in (.0, .11, .32, .73, 1.15):
            first = walking_torso_pose(t)
            second = walking_torso_pose(t + period)
            for a, b in zip(first, second):
                self.assertAlmostEqual(a, b, places=6)
        for phase in (0, math.pi, math.tau, 3 * math.pi):
            before = walking_torso_pose((phase - 1e-5) / SPEED)
            after = walking_torso_pose((phase + 1e-5) / SPEED)
            self.assertLess(max(abs(a-b) for a,b in zip(before,after)), .001)

    def test_attached_arms_keep_original_bone_lengths(self):
        for frame in range(121):
            t = frame * math.tau / (120 * SPEED)
            chest, roll = walking_torso_pose(t)
            for side in (-1, 1):
                original = walking_arm_pose(t, side)
                attached = tuple(
                    (x + chest, y + side * roll) for x,y in original
                )
                self.assertAlmostEqual(
                    math.dist(attached[0], attached[1]),
                    UPPER_ARM_LENGTH, places=6)
                self.assertAlmostEqual(
                    math.dist(attached[1], attached[2]),
                    FOREARM_LENGTH, places=6)
                self.assertAlmostEqual(
                    attached[0][0], 6 * side + chest, places=6)
                self.assertAlmostEqual(
                    attached[0][1], -20 + side * roll, places=6)

    def test_rendering_changes_upper_body_but_not_feet_or_set(self):
        base = _background((540, 960), "approach")
        options = dict(shot=0, mouth=0.0, beat_progress=.4,
                       absolute_seconds=math.pi/(2*SPEED), beat_rate=.2)
        dynamic = _draw_frame((540, 960), "approach", .4, 3, base, **options)
        with patch("motion_director.walking_torso_pose",
                   return_value=(0.0, 0.0)) as patched:
            rigid = _draw_frame((540, 960), "approach", .4, 3,
                                base, **options)
        patched.assert_called_once()
        self.assertNotEqual(dynamic.tobytes(), rigid.tobytes())
        # Feet, ground shadow and locked camera are exactly unchanged.
        self.assertEqual(
            dynamic.crop((0, 780, 540, 950)).tobytes(),
            rigid.crop((0, 780, 540, 950)).tobytes())
        self.assertEqual(dynamic.getpixel((10, 510)),
                         rigid.getpixel((10, 510)))

    def test_other_actions_do_not_gain_unwanted_torso_lean(self):
        base = _background((540, 960), "stare")
        with patch("motion_director.walking_torso_pose") as pose:
            _draw_frame((540, 960), "stare", .5, 2,
                        base, shot=1, mouth=.4, absolute_seconds=.7)
        pose.assert_not_called()

    def test_same_absolute_time_keeps_torso_pose_across_cuts(self):
        base = _background((540, 960), "approach")
        args = dict(shot=0, mouth=0.0, beat_progress=.32,
                    absolute_seconds=.65, beat_rate=.22)
        before = _draw_frame((540, 960), "approach", .2, 3, base, **args)
        after = _draw_frame((540, 960), "approach", .8, 3, base, **args)
        self.assertEqual(
            before.crop((0, 300, 540, 950)).tobytes(),
            after.crop((0, 300, 540, 950)).tobytes())


if __name__ == "__main__":
    unittest.main()
