#!/usr/bin/env python3
"""
Unit and integration tests for Fusion In-Place Editing Tool Suite and CAD-ICM Model Scaffolder.
"""
import unittest
import tempfile
import json
from pathlib import Path

from tools.fusion_editor.timeline_doctor import (
    generate_health_script,
    parse_doctor_output,
    format_health_table,
)
from tools.fusion_editor.inspect_model import (
    generate_inspect_script,
    parse_inspect_output,
    format_inspect_table,
)
from tools.fusion_editor.edit_parameter import (
    generate_param_edit_script,
    parse_edit_output,
)
from tools.fusion_editor.rollback_edit import (
    generate_rollback_script,
    parse_rollback_output,
)
from tools.fusion_editor.append_feature import (
    generate_append_script,
    parse_append_output,
)
from tools.scaffold_model import scaffold_model_directory
from tools.log_model_edit import log_edit

class TestFusionEditorTools(unittest.TestCase):

    def test_timeline_doctor_script_and_parser(self):
        script = generate_health_script()
        self.assertIn("timeline = design.timeline", script)
        self.assertIn("TIMELINE_DOCTOR_JSON_START", script)

        sample_json = """
        TIMELINE_DOCTOR_JSON_START
        {
            "status": "HEALTHY",
            "total": 10,
            "healthy": 10,
            "warnings": [],
            "errors": []
        }
        TIMELINE_DOCTOR_JSON_END
        """
        report = parse_doctor_output(sample_json)
        self.assertEqual(report["status"], "HEALTHY")
        self.assertEqual(report["total"], 10)

        table = format_health_table(report)
        self.assertIn("🟢 HEALTHY", table)
        self.assertIn("| 10 | 10 | 0 | 0 |", table)

    def test_inspect_model_script_and_parser(self):
        script = generate_inspect_script("TestComp")
        self.assertIn("INSPECT_MODEL_JSON_START", script)
        self.assertIn("rootComponent", script)

        sample_manifest = """
        INSPECT_MODEL_JSON_START
        {
            "document_name": "TestDoc",
            "timeline_summary": {"total": 5, "feature_types": {"ExtrudeFeature": 3}},
            "user_parameters": [{"name": "L_mm", "expression": "100 mm", "value_mm": 100.0}],
            "model_parameters_count": 2,
            "hierarchy": {
                "occurrence_name": "Root",
                "bodies": [{"name": "Body1", "bbox_mm": {"width_x": 10, "depth_y": 20, "height_z": 30}, "face_count": 6}],
                "children": []
            }
        }
        INSPECT_MODEL_JSON_END
        """
        manifest = parse_inspect_output(sample_manifest)
        self.assertEqual(manifest["document_name"], "TestDoc")
        table = format_inspect_table(manifest)
        self.assertIn("TestDoc", table)
        self.assertIn("Body1", table)

    def test_edit_parameter_script_generation(self):
        script_param = generate_param_edit_script(param_name="Slot_Width", new_expression="15.0 mm")
        self.assertIn('param_name = "Slot_Width"', script_param)
        self.assertIn('new_expr = "15.0 mm"', script_param)
        self.assertIn("PARAM_EDIT_JSON_START", script_param)

        script_feat = generate_param_edit_script(
            comp_name="Slider",
            feature_name="Extrude10",
            feature_prop="distance",
            new_expression="4.5 mm"
        )
        self.assertIn('comp_name = "Slider"', script_feat)
        self.assertIn('feature_name = "Extrude10"', script_feat)

        sample_res = """
        PARAM_EDIT_JSON_START
        {
            "status": "SUCCESS",
            "target_type": "Parameter",
            "target_name": "Slot_Width",
            "previous_expression": "12.0 mm",
            "applied_expression": "15.0 mm"
        }
        PARAM_EDIT_JSON_END
        """
        parsed = parse_edit_output(sample_res)
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertEqual(parsed["applied_expression"], "15.0 mm")

    def test_rollback_edit_script_generation(self):
        script = generate_rollback_script(
            target_name="Extrude2",
            action_type="modify_extrude",
            action_params={"distance_mm": 50.0}
        )
        self.assertIn('target_name = "Extrude2"', script)
        self.assertIn("target_obj.rollTo(False)", script)
        self.assertIn("timeline.moveToEnd()", script)

    def test_append_feature_script_generation(self):
        script = generate_append_script(
            comp_name="TopSlider",
            body_name="Body1",
            op_type="magnet_pocket",
            face_normal="+Z",
            op_params={"dia_mm": 8.20, "depth_mm": 3.10}
        )
        self.assertIn('comp_name = "TopSlider"', script)
        self.assertIn('body_name = "Body1"', script)
        self.assertIn("CutFeatureOperation", script)

    def test_scaffold_model_and_audit_logging(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = scaffold_model_directory(
                name="Test_Widget",
                envelope="120 x 80 x 40 mm",
                category="Prototype",
                repo_root=tmp_dir,
                description="Test widget for CAD-ICM unit verification."
            )
            p = Path(model_path)
            self.assertTrue((p / "CONTEXT.md").exists())
            self.assertTrue((p / "SPEC.md").exists())
            self.assertTrue((p / "DECISIONS.md").exists())
            self.assertTrue((p / "TIMELINE.md").exists())
            self.assertTrue((p / "README.md").exists())
            self.assertTrue((p / "assets" / "references").is_dir())
            self.assertTrue((p / "assets" / "renders").is_dir())

            # Test logging edit
            log_edit(
                model_dir_str=model_path,
                prompt="Widen central slot from 10mm to 12mm",
                tier=1,
                comp="Main_Body",
                target="Slot_Width",
                before="10.0 mm",
                after="12.0 mm",
                status="HEALTHY",
                adr_title="Wider Slot for Cables",
                adr_context="Cables were binding in 10mm slot.",
                adr_decision="Enlarged slot to 12mm."
            )

            # Verify TIMELINE.md content
            timeline_text = (p / "TIMELINE.md").read_text(encoding="utf-8")
            self.assertIn("Tier 1 (Parametric Edit)", timeline_text)
            self.assertIn("10.0 mm", timeline_text)
            self.assertIn("12.0 mm", timeline_text)

            # Verify DECISIONS.md ADR content
            decisions_text = (p / "DECISIONS.md").read_text(encoding="utf-8")
            self.assertIn("ADR-002: Wider Slot for Cables", decisions_text)
            self.assertIn("Enlarged slot to 12mm", decisions_text)

if __name__ == "__main__":
    unittest.main()
