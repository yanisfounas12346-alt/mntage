"""SEO pack must contain actual newlines and meaningful French hashtags."""
import unittest
from tiktok_pro import seo_pack


class SeoPackTests(unittest.TestCase):
    def test_french_science_pack_is_readable(self):
        pack=seo_pack(
            "Illusion dans le miroir",
            "Pourquoi voit-on un visage étrange dans le miroir ? "
            "Le cerveau reconstruit les informations visuelles.",
            "visage miroir",
            science=True)
        self.assertIn("\n\nTITRE\n",pack)
        self.assertIn("\nHASHTAGS\n",pack)
        self.assertIn("#Visage",pack)
        self.assertIn("#Miroir",pack)
        self.assertNotIn("\\n",pack)
        self.assertIn("Le cerveau reconstruit",pack)

    def test_no_missing_script(self):
        with self.assertRaises(ValueError):
            seo_pack("Titre","")


if __name__ == "__main__":
    unittest.main()
