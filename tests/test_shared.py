import unittest
import math
import tempfile
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.cad_primitives import (
    cm, mm, make_hex_points,
    make_dfm_hex_points, calc_dfm_hex_area,
    generate_dfm_honeycomb_grid, filter_profiles_by_area
)
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

    def test_dfm_hex_points(self):
        cy, cz = 10.0, 20.0
        w_h = 5.0
        h_v = 2.0
        pts = make_dfm_hex_points(cy, cz, w_h, h_v)
        self.assertEqual(len(pts), 6)
        # Check top apex: (cy, cz + h_v + w_h)
        self.assertEqual(pts[0], (10.0, 20.0 + 2.0 + 5.0))
        # Top-left: (cy - w_h, cz + h_v)
        self.assertEqual(pts[1], (10.0 - 5.0, 20.0 + 2.0))
        # Top roof slope: dy = 5.0, dz = 5.0 -> exact 45 degrees
        d_y = pts[0][0] - pts[1][0]
        d_z = pts[0][1] - pts[1][1]
        self.assertAlmostEqual(d_z / d_y, 1.0)

    def test_dfm_hex_area(self):
        w_h = 4.0
        h_v = 1.5
        crown = 4.0
        area = calc_dfm_hex_area(w_h, h_v, crown)
        expected = 4.0 * w_h * h_v + 2.0 * w_h * crown
        self.assertAlmostEqual(area, expected)
        self.assertAlmostEqual(area, 4.0 * 4.0 * 1.5 + 2.0 * 4.0 * 4.0) # 24 + 32 = 56.0

    def test_generate_dfm_honeycomb_grid(self):
        y_bounds = (0.0, 100.0)
        z_bounds = (0.0, 50.0)
        w_h = 5.0
        h_v = 2.0
        w_strut = 2.6
        cells = generate_dfm_honeycomb_grid(y_bounds, z_bounds, w_h, h_v, w_strut, margin=2.0)
        self.assertGreater(len(cells), 0)
        # Verify row spacing delta_z = sqrt(2) * w_strut + 2 * h_v + w_h
        expected_dz = math.sqrt(2.0) * w_strut + 2.0 * h_v + w_h
        expected_dy = 2.0 * w_h + w_strut
        row_0 = [c for c in cells if c["row"] == 0]
        row_1 = [c for c in cells if c["row"] == 1]
        if len(row_0) > 1:
            self.assertAlmostEqual(row_0[1]["center"][0] - row_0[0]["center"][0], expected_dy, places=4)
        if len(row_1) > 0 and len(row_0) > 0:
            self.assertAlmostEqual(row_1[0]["center"][1] - row_0[0]["center"][1], expected_dz, places=4)
            # Verify stagger shift
            self.assertAlmostEqual(row_1[0]["center"][0] - row_0[0]["center"][0], 0.5 * expected_dy, places=4)

        # Edge cases: zero/negative dimensions or tight bounds
        self.assertEqual(generate_dfm_honeycomb_grid(y_bounds, z_bounds, 0, 2.0, 2.6), [])
        self.assertEqual(generate_dfm_honeycomb_grid(y_bounds, z_bounds, 5.0, 2.0, -1.0), [])
        self.assertEqual(generate_dfm_honeycomb_grid((0.0, 5.0), (0.0, 5.0), 10.0, 10.0, 2.0), [])

    def test_filter_profiles_by_area(self):
        class MockArea:
            def __init__(self, val):
                self.area = val
        class MockProfile:
            def __init__(self, val):
                self._area = val
            def areaProperties(self):
                return MockArea(self._area)

        profiles = [MockProfile(0.56), MockProfile(10.2), MockProfile(0.57), MockProfile(0.01)]
        filtered = filter_profiles_by_area(profiles, 0.565, tolerance=0.01)
        self.assertEqual(len(filtered), 2)

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

    def test_animate_assembly_script_generator(self):
        import importlib.util
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "skills", "to-fusion-animate", "scripts", "animate_assembly.py"))
        spec = importlib.util.spec_from_file_location("animate_assembly", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        code = mod.generate_animation_script({}, "/tmp/test_frames", num_frames=15, width=640, height=480)
        self.assertIn("def run(context):", code)
        self.assertIn("num_frames = 15", code)
        self.assertIn("/tmp/test_frames", code)
        self.assertIn("vp.saveAsImageFile", code)

if __name__ == "__main__":
    unittest.main()
