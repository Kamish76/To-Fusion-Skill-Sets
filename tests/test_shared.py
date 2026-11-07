import unittest
import math
import tempfile
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.cad_primitives import cm, mm, make_hex_points
from shared.hardware_library import MAKERS_SUPPLY_M3_STACKUP
from shared.scene_animator import clamp, smoothstep

class TestSharedLibrary(unittest.TestCase):
    def test_unit_conversion(self):
        self.assertAlmostEqual(cm(10.0), 1.0)
        self.assertAlmostEqual(cm(250.0), 25.0)
        self.assertAlmostEqual(mm(2.5), 25.0)

    def test_make_hex_points(self):
        pts = make_hex_points(0, 0, 5.7) # AF = 5.7 cm
        self.assertEqual(len(pts), 6)
        # Test distance from center to vertices: r = AF / (2 * cos(30 deg))
        expected_r = (5.7 / 2.0) / math.cos(math.pi / 6.0)
        for x, y in pts:
            self.assertAlmostEqual(math.hypot(x, y), expected_r, places=4)

    def test_makers_supply_m3_stackup(self):
        s = MAKERS_SUPPLY_M3_STACKUP
        self.assertEqual(s["bar_web_thickness_mm"], 5.0)
        self.assertEqual(s["outer_counterbore_dia_mm"], 6.2)
        self.assertEqual(s["outer_counterbore_depth_mm"], 1.5)
        self.assertEqual(s["inner_hex_nut_af_mm"], 5.7)
        self.assertEqual(s["inner_hex_nut_depth_mm"], 2.4)
        self.assertEqual(s["through_bore_dia_mm"], 3.3)
        self.assertEqual(s["washer_outer_dia_mm"], 9.5)
        self.assertEqual(s["washer_thickness_mm"], 1.8)

    def test_animation_easing(self):
        self.assertEqual(clamp(-5, 0, 10), 0)
        self.assertEqual(clamp(15, 0, 10), 10)
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertAlmostEqual(smoothstep(0.0, 1.0, 0.0), 0.0)
        self.assertAlmostEqual(smoothstep(0.0, 1.0, 1.0), 1.0)
        self.assertAlmostEqual(smoothstep(0.0, 1.0, 0.5), 0.5)

if __name__ == "__main__":
    unittest.main()
