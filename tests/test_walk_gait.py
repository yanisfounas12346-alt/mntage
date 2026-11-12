"""Regression tests for the articulated, floor-contact 2D walking cycle."""
import math
import unittest

from motion_director import walk_pose, walk_pose_with_translation
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

    def test_stationary_animated_root_preserves_existing_gait(self):
        # Opt 4 should not alter the already-tested in-place stride from opt 3.
        for t in (0.0, .08, .21, .49, .65, .91, 1.27):
            original = walk_pose(t)
            anchored = walk_pose_with_translation(t, lambda _: 120, scale=.83)
            self.assertAlmostEqual(original[0], anchored[0], places=6)
            self.assertAlmostEqual(original[1], anchored[1], places=6)
            for old_leg, new_leg in zip(original[2], anchored[2]):
                for old_joint, new_joint in zip(old_leg, new_leg):
                    for a, b in zip(old_joint, new_joint):
                        self.assertAlmostEqual(a, b, places=5)

    def test_stance_ankles_are_fixed_in_stage_while_root_translates(self):
        scale = .83
        def root_x_at(t):
            return 20 + 80*t + 6*t*t
        for side, phases, touchdown in (
            (1, (0.2, 0.7, 1.7, 2.6), 0.0),
            (-1, (math.pi+.2, math.pi+.8, math.pi+1.7,
                  math.tau-.2), math.pi/SPEED),
        ):
            for phase in phases:
                with self.subTest(side=side, phase=phase):
                    t = phase/SPEED
                    sway, bob, legs, _ = walk_pose_with_translation(
                        t, root_x_at, scale=scale)
                    ankle = legs[0 if side == -1 else 1][2]
                    stage_x = root_x_at(t) + scale*(sway+ankle[0])
                    self.assertAlmostEqual(
                        stage_x, root_x_at(touchdown)+side*34*scale, places=5)
                    self.assertAlmostEqual(ankle[1]+bob, 159, places=6)

    def test_swing_feet_advance_without_backtracking_for_translating_actor(self):
        scale = .83
        root_x_at = lambda t: 25 + 95*t
        for side, start in ((-1, 0), (1, math.pi)):
            world_x = []
            for fraction in (0.01, .2, .5, .8, .99):
                t = (start+math.pi*fraction)/SPEED
                sway, _, legs, _ = walk_pose_with_translation(
                    t, root_x_at, scale=scale)
                ankle = legs[0 if side == -1 else 1][2]
                world_x.append(root_x_at(t)+scale*(sway+ankle[0]))
            self.assertEqual(world_x, sorted(world_x))
            self.assertGreater(world_x[-1]-world_x[0], 20)

    def test_touchdown_is_continuous_while_root_is_advancing(self):
        root_x_at = lambda t: 23 + 80*t + 4*t*t
        epsilon = 0.0001
        for boundary in (0, math.pi, math.tau, 3*math.pi):
            with self.subTest(boundary=boundary):
                frames = []
                for phase in (boundary-epsilon, boundary+epsilon):
                    t = phase/SPEED
                    sway, bob, legs, _ = walk_pose_with_translation(t, root_x_at)
                    frames.append(tuple(
                        (root_x_at(t)+sway+leg[2][0], bob+leg[2][1])
                        for leg in legs
                    ))
                for prev, nxt in zip(frames[0], frames[1]):
                    self.assertAlmostEqual(prev[0], nxt[0], delta=.001)
                    self.assertAlmostEqual(prev[1], nxt[1], delta=.001)

    def test_approach_actor_pose_is_deterministic_across_shot_cuts(self):
        # Different local progress values do not change the walking pose
        # when the absolute time, narrative beat and beat speed match.
        base = _background((540, 960), "approach")
        args = dict(shot=0, mouth=0.0, beat_progress=.32,
                    absolute_seconds=.65, beat_rate=.22)
        before = _draw_frame((540, 960), "approach", .2, 3, base, **args)
        after = _draw_frame((540, 960), "approach", .8, 3, base, **args)
        self.assertEqual(
            before.crop((0, 300, 540, 950)).tobytes(),
            after.crop((0, 300, 540, 950)).tobytes()
        )

    def test_approach_beat_speed_affects_ground_contact_not_root_position(self):
        base = _background((540, 960), "approach")
        kw = dict(shot=0, mouth=0, beat_progress=.3, absolute_seconds=.4)
        slow = _draw_frame((540, 960), "approach", .3, 2, base,
                           beat_rate=.1, **kw)
        quick = _draw_frame((540, 960), "approach", .3, 2, base,
                            beat_rate=.55, **kw)
        self.assertNotEqual(slow.tobytes(), quick.tobytes())
        self.assertEqual(slow.getpixel((10, 510)), quick.getpixel((10, 510)))

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
