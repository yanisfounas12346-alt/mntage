"""Regression tests for the articulated, floor-contact 2D walking cycle."""
import math
import unittest
from unittest.mock import patch

from motion_director import (walk_pose, walk_pose_with_translation, articulated_knee,
                             walking_shoe_tip, THIGH_LENGTH, SHIN_LENGTH)
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

    def test_knees_keep_two_segment_lengths_through_full_gait(self):
        # No shortening/elongation under normal in-place walking.
        for sample in range(101):
            t = sample * math.tau / (100 * SPEED)
            legs = walk_pose(t)[2]
            for hip, knee, foot in legs:
                with self.subTest(t=t, hip=hip):
                    self.assertAlmostEqual(
                        math.dist(hip, knee), THIGH_LENGTH, places=5)
                    self.assertAlmostEqual(
                        math.dist(knee, foot), SHIN_LENGTH, places=5)

    def test_knee_solver_is_mirror_symmetric(self):
        # Mirroring the leg should not reverse its bend unpredictably.
        left = articulated_knee((-9, 59), (-34, 159), -1)
        right = articulated_knee((9, 59), (34, 159), 1)
        self.assertAlmostEqual(left[0], -right[0], places=6)
        self.assertAlmostEqual(left[1], right[1], places=6)
        self.assertLess(left[0], -9)
        self.assertGreater(right[0], 9)

    def test_overreach_keeps_ankle_target_and_joint_finite(self):
        # A fast move may go beyond physical reach: avoid NaN and popping.
        hip = (-9, 59)
        for x in (-185, -145, 100, 220):
            ankle = (x, 159)
            knee = articulated_knee(hip, ankle, -1)
            self.assertTrue(all(math.isfinite(value) for value in knee))
            self.assertAlmostEqual(
                math.dist(hip, knee) / math.dist(knee, ankle),
                THIGH_LENGTH / SHIN_LENGTH, places=5)
        self.assertTrue(all(math.isfinite(value) for value in
                            articulated_knee((0, 0), (0, 0), 1)))

    def test_no_joint_snap_at_full_extension_boundary(self):
        hip = (0, 0)
        radius = THIGH_LENGTH + SHIN_LENGTH
        previous = articulated_knee(hip, (20, math.sqrt((radius-.001)**2-400)), 1)
        after = articulated_knee(hip, (20, math.sqrt((radius+.001)**2-400)), 1)
        self.assertLess(math.dist(previous, after), .5)

    def test_world_planted_ankle_is_unchanged_by_knee_solver(self):
        # Solving the knee must not regress opt 4's world-space foot lock.
        scale = .83
        def root_x_at(t):
            return 50 + 70*t
        for phase in (math.pi/6, math.pi/3, 2*math.pi/3, 5*math.pi/6):
            t = phase/SPEED
            sway, bob, legs, _ = walk_pose_with_translation(
                t, root_x_at, scale=scale)
            hip, knee, foot = legs[1]  # right foot is planted
            stage_x = root_x_at(t) + scale*(sway+foot[0])
            self.assertAlmostEqual(stage_x, root_x_at(0)+34*scale, places=5)
            self.assertAlmostEqual(foot[1]+bob, 159, places=5)
            self.assertTrue(all(math.isfinite(v) for v in knee))

    def test_walking_shoes_are_flat_when_planted_and_flex_when_lifted(self):
        for phase, airborne_side in ((math.pi/2, -1), (3*math.pi/2, 1)):
            with self.subTest(phase=phase):
                t=phase/SPEED
                sway,bob,legs,stride=walk_pose(t)
                for side,leg in zip((-1,1),legs):
                    foot=leg[2]
                    toe=walking_shoe_tip(foot,side,stride)
                    if side==airborne_side:
                        self.assertLess(toe[1],foot[1]-5)
                        self.assertLess(abs(toe[0]-foot[0]),15)
                    else:
                        self.assertAlmostEqual(toe[1],foot[1],places=6)
                        self.assertAlmostEqual(toe[0],foot[0]+15*side,places=6)

    def test_swing_toe_never_penetrates_ground(self):
        for sample in range(251):
            t=sample*math.tau/(250*SPEED)
            _,bob,legs,stride=walk_pose(t)
            for side,leg in zip((-1,1),legs):
                toe=walking_shoe_tip(leg[2],side,stride)
                self.assertLessEqual(toe[1]+bob,159.000001)

    def test_toe_roll_is_periodic_and_continuous_at_contact(self):
        period=math.tau/SPEED
        for phase in (0.0,.2,1.2,math.pi,4.7,math.tau):
            t=phase/SPEED
            pose1=walk_pose(t)
            pose2=walk_pose(t+period)
            for side,leg1,leg2 in zip((-1,1),pose1[2],pose2[2]):
                before=walking_shoe_tip(leg1[2],side,pose1[3])
                after=walking_shoe_tip(leg2[2],side,pose2[3])
                self.assertAlmostEqual(before[0],after[0],places=5)
                self.assertAlmostEqual(before[1],after[1],places=5)
        epsilon=1e-4
        for phase in (0.0,math.pi,math.tau):
            positions=[]
            for offset in (-epsilon,epsilon):
                t=(phase+offset)/SPEED
                pose=walk_pose(t)
                positions.append(tuple(walking_shoe_tip(
                    leg[2],side,pose[3]) for side,leg in zip((-1,1),pose[2])))
            for a,b in zip(*positions):
                self.assertLess(math.dist(a,b),.02)

    def test_planted_toe_stays_world_locked_when_actor_moves(self):
        scale=.83
        def root_x_at(t):
            return 20+80*t+6*t*t
        for side,phases,touchdown in (
            (1,(.2,.7,1.7,2.6),0.0),
            (-1,(math.pi+.2,math.pi+.8,math.pi+1.7),math.pi/SPEED),
        ):
            for phase in phases:
                t=phase/SPEED
                sway,bob,legs,stride=walk_pose_with_translation(
                    t,root_x_at,scale=scale)
                leg=legs[0 if side==-1 else 1]
                toe=walking_shoe_tip(leg[2],side,stride)
                world_x=root_x_at(t)+scale*(sway+toe[0])
                self.assertAlmostEqual(world_x,
                    root_x_at(touchdown)+side*49*scale,places=5)
                self.assertAlmostEqual(toe[1]+bob,159,places=5)

    def test_rendered_walking_shoe_uses_the_articulated_toe(self):
        base=_background((540,960),"approach")
        options=dict(shot=0,mouth=0.0,beat_progress=.4,
                     absolute_seconds=math.pi/(2*SPEED),beat_rate=.2)
        rolled=_draw_frame((540,960),"approach",.4,3,base,**options)
        with patch("motion_director.walking_shoe_tip",
                   side_effect=lambda foot,side,stride:
                       (foot[0]+15*side,foot[1])) as fixed_shoe:
            rigid=_draw_frame((540,960),"approach",.4,3,base,**options)
        self.assertEqual(fixed_shoe.call_count,2)
        self.assertNotEqual(rolled.tobytes(),rigid.tobytes())
        self.assertEqual(rolled.getpixel((10,510)),rigid.getpixel((10,510)))

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
