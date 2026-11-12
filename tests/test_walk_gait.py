"""Regression tests for the articulated, floor-contact 2D walking cycle."""
import math
import unittest

from motion_director import walk_pose
from motion_studio import _background, _draw_frame


SPEED = 6.2


class WalkGaitTests(unittest.TestCase):
    def test_alternating_swing_keeps_other_foot_on_floor(self):
        for phase, moving_index in (
            (math.pi / 2, 0),
            (3 * math.pi / 2, 1),
        ):
            with self.subTest(phase=phase):
                sway, bob, legs, stride = walk_pose(phase / SPEED)
                self.assertEqual(len(legs), 2)
                airborne = legs[moving_index][2]
                grounded = legs[1 - moving_index][2]
                # World y is actor bob + local foot y: contact never floats.
                self.assertAlmostEqual(grounded[1] + bob, 159.0, places=5)
                self.assertLess(airborne[1] + bob, 140)
                self.assertGreater(abs(airborne[0] - grounded[0]), 1)
                self.assertGreater(abs(stride), .99)

    def test_stance_ankle_does_not_slide_against_body_sway(self):
        # The animated root sways, but the planted shoe stays at one X.
        for phase in (math.pi/8, math.pi/4, math.pi/2, 3*math.pi/4,
                      7*math.pi/8, 9*math.pi/8, 5*math.pi/4,
                      3*math.pi/2, 7*math.pi/4, 15*math.pi/8):
            with self.subTest(phase=phase):
                sway, bob, legs, stride = walk_pose(phase/SPEED)
                planted = 1 if stride > 0 else 0
                shoe = legs[planted][2]
                expected_x = 34 if planted == 1 else -34
                self.assertAlmostEqual(shoe[0] + sway, expected_x, places=6)
                self.assertAlmostEqual(shoe[1] + bob, 159.0, places=6)

    def test_foot_contacts_have_no_horizontal_snap(self):
        # Both ankles approach each stance transition smoothly.
        epsilon = 0.001
        for phase in (0.0, math.pi, math.tau):
            with self.subTest(phase=phase):
                for offset in (-epsilon, epsilon):
                    sway, _, legs, _ = walk_pose((phase + offset)/SPEED)
                    self.assertAlmostEqual(legs[0][2][0] + sway, -34,
                                           delta=0.0001)
                    self.assertAlmostEqual(legs[1][2][0] + sway, 34,
                                           delta=0.0001)

    def test_foot_still_advances_during_airborne_swing(self):
        for phase, moving_index, resting_x in (
            (math.pi/2, 0, -34),
            (3*math.pi/2, 1, 34),
        ):
            with self.subTest(phase=phase):
                sway, bob, legs, _ = walk_pose(phase/SPEED)
                airborne = legs[moving_index][2]
                self.assertGreater(airborne[0] + sway, resting_x + 20)
                self.assertLess(airborne[1] + bob, 140)

    def test_knee_bends_when_leg_is_airborne(self):
        _, _, stance, _ = walk_pose(0.0)
        _, _, swing, _ = walk_pose(math.pi / (2 * SPEED))
        # The knee rises during a swing instead of remaining rigid.
        self.assertLess(swing[0][1][1], stance[0][1][1] - 5)

    def test_ground_foot_has_fixed_world_height_across_many_frames(self):
        for frame in range(26):
            t = frame / 25.0
            _, bob, legs, stride = walk_pose(t)
            grounded_index = 1 if stride > 0 else 0
            self.assertAlmostEqual(legs[grounded_index][2][1] + bob, 159.0, places=4)

    def test_cycle_is_periodic_and_does_not_teleport_at_landing(self):
        period = math.tau / SPEED
        for t in (0.01, .13, .3, .47):
            a = walk_pose(t)
            b = walk_pose(t + period)
            self.assertAlmostEqual(a[0], b[0], places=6)
            self.assertAlmostEqual(a[1], b[1], places=6)
            for leg_a, leg_b in zip(a[2], b[2]):
                for joint_a, joint_b in zip(leg_a, leg_b):
                    for xa, xb in zip(joint_a, joint_b):
                        self.assertAlmostEqual(xa, xb, places=6)
        for t in (.0, .3, .5, .9):
            a = walk_pose(t)[2]
            b = walk_pose(t + 1 / 25)[2]
            max_delta = max(
                math.dist(pa, pb)
                for leg_a, leg_b in zip(a, b)
                for pa, pb in zip(leg_a, leg_b)
            )
            self.assertLess(max_delta, 15)

    def test_approach_actually_changes_pose_while_camera_remains_locked(self):
        bg = _background((540, 960), "approach")
        first = _draw_frame(
            (540, 960), "approach", .4, 3, bg,
            shot=0, mouth=0, beat_progress=.4, absolute_seconds=.25,
        )
        second = _draw_frame(
            (540, 960), "approach", .4, 3, bg,
            shot=0, mouth=0, beat_progress=.4, absolute_seconds=.62,
        )
        self.assertNotEqual(first.tobytes(), second.tobytes())
        # Same stage coordinate far from the actor is invariant.
        self.assertEqual(first.getpixel((10, 510)), second.getpixel((10, 510)))


if __name__ == "__main__":
    unittest.main()
