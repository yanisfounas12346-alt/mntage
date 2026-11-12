"""SEO pack must contain actual newlines and meaningful French hashtags."""
import unittest
from tiktok_pro import seo_pack, seo_editorial_checks


class SeoPackTests(unittest.TestCase):
    def test_french_science_pack_is_readable(self):
        pack=seo_pack(
            "Illusion dans le miroir",
            "Pourquoi voit-on un visage étrange dans le miroir ? "
            "Le cerveau reconstruit les informations visuelles.",
            "visage miroir",
            science=True)
        self.assertIn("\n\nTITRE ACTUEL\n",pack)
        self.assertIn("\nHASHTAGS\n",pack)
        self.assertIn("#Visage",pack)
        self.assertIn("#Miroir",pack)
        self.assertNotIn("\\n",pack)
        self.assertIn("Le cerveau reconstruit",pack)

    def test_editorial_checks_identify_generic_title_and_missing_keyword(self):
        checks=seo_editorial_checks("Mon premier Short",
            "Imagine un visage étrange dans un miroir.", "illusion du miroir")
        self.assertFalse(checks["title_specific"])
        self.assertFalse(checks["keyword_in_title"])
        self.assertFalse(checks["keyword_in_script"])

    def test_search_title_does_not_claim_trending_topic(self):
        pack=seo_pack("Un visage qui change", "Ton reflet semble bizarre.",
                      "illusion du miroir", science=True)
        self.assertIn("TITRE ORIENTÉ RECHERCHE",pack)
        self.assertIn("Illusion du miroir",pack)
        self.assertNotIn("tendance vérifiée",pack.lower())

    def test_no_missing_script(self):
        with self.assertRaises(ValueError):
            seo_pack("Titre","")


if __name__ == "__main__":
    unittest.main()
