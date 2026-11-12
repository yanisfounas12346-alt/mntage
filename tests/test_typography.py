"""Regression tests for Windows typography used in animated science scenes."""
import unittest
from PIL import Image
from motion_studio import _display_font, _Painter


class TypographyTests(unittest.TestCase):
    def test_font_is_reused_across_thousands_of_frames(self):
        self.assertIs(_display_font(46), _display_font(46))

    def test_larger_export_has_larger_legible_letters(self):
        label = "SCIENCE WTF"
        smaller = _display_font(23)
        bigger = _display_font(46)
        small_box = smaller.getbbox(label)
        big_box = bigger.getbbox(label)
        small_width = small_box[2] - small_box[0]
        big_width = big_box[2] - big_box[0]
        self.assertGreater(small_width, 0)
        self.assertGreater(big_width, small_width * 1.5)

    def test_typography_renders_at_native_and_export_scale(self):
        for dimensions in ((540, 960), (1080, 1920)):
            with self.subTest(dimensions=dimensions):
                image = Image.new("RGB", dimensions, (13, 23, 38))
                painter = _Painter(image)
                painter.text((270, 250), "SCIENCE WTF", size=20)
                # Verify the label changed pixels inside its expected region.
                area = image.crop((
                    dimensions[0] // 4, dimensions[1] // 5,
                    3 * dimensions[0] // 4, dimensions[1] // 3,
                ))
                self.assertTrue(any(
                    pixel != (13, 23, 38) for pixel in area.getdata()
                ))


if __name__ == "__main__":
    unittest.main()
