"""Guard visual storytelling improvements against accidental regressions."""
import unittest

from motion_studio import _background, _draw_frame, plan_mirror_scenes


SCRIPT = (
    "Imagine : tu te regardes dans un miroir. "
    "Puis tu fixes ton visage sans bouger. Ton nez paraît bizarre. "
    "C'est ton cerveau qui bugue. Des chercheurs ont réalisé une expérience. "
    "Et certains ont rapporté des déformations étranges. Mais pourquoi ? "
    "Il reconstruit ce que tu vois. Quand tu fixes longtemps, ton regard change. "
    "Résultat : ton propre reflet se déforme. Et le plus fou ? "
    "Pas besoin d'un miroir hanté. Abonne-toi à Science WTF."
)


class ProfessionalMotionTests(unittest.TestCase):
    def test_storyboard_is_contiguous_and_short(self):
        scenes=plan_mirror_scenes(SCRIPT,86.0)
        self.assertGreater(len(scenes),20)
        self.assertLessEqual(max(s.end-s.start for s in scenes),3.251)
        self.assertAlmostEqual(sum(s.end-s.start for s in scenes),86.0)

    def test_mouth_animation_is_visible(self):
        base=_background((540,960),"stare")
        shut=_draw_frame((540,960),"stare",0.6,3.0,base,shot=1,mouth=0.0)
        open_mouth=_draw_frame((540,960),"stare",0.6,3.0,base,shot=1,mouth=1.0)
        self.assertNotEqual(shut.tobytes(),open_mouth.tobytes())

    def test_distorted_reflection_changes_when_time_progresses(self):
        base=_background((540,960),"distort")
        early=_draw_frame((540,960),"distort",0.03,3.0,base,shot=2,mouth=0.3)
        late=_draw_frame((540,960),"distort",0.9,3.0,base,shot=2,mouth=0.3)
        self.assertNotEqual(early.tobytes(),late.tobytes())

    def test_narrative_context_is_distinct(self):
        kinds=["experiment","distort","brain","reveal"]
        render=[]
        for kind in kinds:
            base=_background((540,960),kind)
            render.append(_draw_frame((540,960),kind,.54,2.8,base,shot=0,mouth=.2).tobytes())
        self.assertEqual(len(set(render)),len(kinds))

    def test_camera_background_stays_fixed(self):
        base=_background((540,960),"distort")
        start=_draw_frame((540,960),"distort",0,3,base,shot=2,mouth=0)
        end=_draw_frame((540,960),"distort",1,3,base,shot=2,mouth=0)
        self.assertEqual(start.getpixel((14,640)),end.getpixel((14,640)))


if __name__=="__main__":
    unittest.main()
