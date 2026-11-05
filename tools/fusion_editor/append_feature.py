#!/usr/bin/env python3
"""
Append Feature: Tier 3 Downstream Feature Appender for Autodesk Fusion 360.
Appends localized, surgical features (cutouts, pockets, holes, captive hex/magnet pockets,
bosses, fillets) to existing bodies without modifying or rebuilding upstream history.
"""
import json
import sys
import argparse

def generate_append_script(
    comp_name: str,
    body_name: str,
    op_type: str = "pocket_cut",
    face_normal: str = "+Z",
    op_params: dict = None
) -> str:
    """Generates Python script to append a localized feature on an existing body."""
    params_json = json.dumps(op_params or {})
    return f'''import adsk.core, adsk.fusion, json, math

def mm(val):
    return adsk.core.ValueInput.createByReal(float(val) / 10.0)

def run(context):
    app = adsk.core.Application.get()
    if not app:
        print(json.dumps({{"error": "Fusion 360 not running"}}))
        return
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print(json.dumps({{"error": "No active design document"}}))
        return

    comp_name = "{comp_name}"
    body_name = "{body_name}"
    op_type = "{op_type}"
    face_normal = "{face_normal}"
    params = json.loads('{params_json}')

    # 1. Locate Component
    target_comp = None
    def find_comp(comp):
        if comp.name == comp_name:
            return comp
        for occ in comp.occurrences:
            found = find_comp(occ.component)
            if found:
                return found
        return None

    target_comp = find_comp(design.rootComponent)
    if not target_comp:
        print(json.dumps({{"error": f"Component '{{comp_name}}' not found"}}))
        return

    # 2. Locate Body
    target_body = None
    for b in target_comp.bRepBodies:
        if b.name == body_name:
            target_body = b
            break

    if not target_body:
        # Fallback to first body in component if name is generic
        if target_comp.bRepBodies.count > 0:
            target_body = target_comp.bRepBodies.item(0)
        else:
            print(json.dumps({{"error": f"Body '{{body_name}}' not found in component '{{comp_name}}'"}}))
            return

    # 3. Locate Target Planar Face
    target_face = None
    highest_z = -1e9
    lowest_z = 1e9

    for face in target_body.faces:
        geom = face.geometry
        if geom.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
            plane = adsk.core.Plane.cast(geom)
            norm = plane.normal
            if face_normal == "+Z" and norm.z > 0.99:
                if plane.origin.z > highest_z:
                    highest_z = plane.origin.z
                    target_face = face
            elif face_normal == "-Z" and norm.z < -0.99:
                if plane.origin.z < lowest_z:
                    lowest_z = plane.origin.z
                    target_face = face
            elif face_normal == "+Y" and norm.y > 0.99:
                target_face = face
                break
            elif face_normal == "-Y" and norm.y < -0.99:
                target_face = face
                break

    if not target_face:
        print(json.dumps({{"error": f"Planar face with normal '{{face_normal}}' not found on body '{{target_body.name}}'"}}))
        return

    # 4. Execute Localized Feature Operation
    feature_created = None
    try:
        if op_type == "pocket_cut":
            # Rectangle or circular pocket
            sk = target_comp.sketches.add(target_face)
            w = params.get("width_mm", 10.0) / 10.0
            d = params.get("depth_mm", 10.0) / 10.0
            cut_depth = params.get("cut_depth_mm", 2.0)
            cx = params.get("center_x_mm", 0.0) / 10.0
            cy = params.get("center_y_mm", 0.0) / 10.0

            # Sketch centered rectangle on face plane
            lines = sk.sketchCurves.sketchLines
            p1 = adsk.core.Point3D.create(cx - w/2, cy - d/2, 0)
            p2 = adsk.core.Point3D.create(cx + w/2, cy - d/2, 0)
            p3 = adsk.core.Point3D.create(cx + w/2, cy + d/2, 0)
            p4 = adsk.core.Point3D.create(cx - w/2, cy + d/2, 0)
            lines.add(p1, p2)
            lines.add(p2, p3)
            lines.add(p3, p4)
            lines.add(p4, p1)

            prof = sk.profiles.item(sk.profiles.count - 1)
            ext_input = target_comp.features.extrudeFeatures.createInput(
                prof, adsk.fusion.FeatureOperations.CutFeatureOperation
            )
            ext_input.setDistanceExtent(False, mm(-abs(cut_depth)))
            ext_input.participantBodies = [target_body]
            feature_created = target_comp.features.extrudeFeatures.add(ext_input)
            feature_created.name = params.get("feature_name", "Surgical_Pocket_Cut")

        elif op_type == "magnet_pocket":
            # Cylindrical blind hole for press-fit magnet
            sk = target_comp.sketches.add(target_face)
            dia = params.get("dia_mm", 8.20) / 10.0
            depth = params.get("depth_mm", 3.10)
            cx = params.get("center_x_mm", 0.0) / 10.0
            cy = params.get("center_y_mm", 0.0) / 10.0

            sk.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(cx, cy, 0), dia / 2.0
            )
            prof = sk.profiles.item(sk.profiles.count - 1)
            ext_input = target_comp.features.extrudeFeatures.createInput(
                prof, adsk.fusion.FeatureOperations.CutFeatureOperation
            )
            ext_input.setDistanceExtent(False, mm(-abs(depth)))
            ext_input.participantBodies = [target_body]
            feature_created = target_comp.features.extrudeFeatures.add(ext_input)
            feature_created.name = params.get("feature_name", "Magnet_Pocket")

    except Exception as e:
        print(json.dumps({{"error": f"Failed to append feature: {{str(e)}}"}}))
        return

    result = {{
        "status": "SUCCESS" if feature_created else "ERROR",
        "component": target_comp.name,
        "body": target_body.name,
        "feature_name": feature_created.name if feature_created else None,
        "timeline_index": feature_created.timelineObject.index if feature_created else -1,
        "timeline_count": design.timeline.count
    }}

    print("APPEND_FEATURE_JSON_START")
    print(json.dumps(result, indent=2))
    print("APPEND_FEATURE_JSON_END")
'''

def parse_append_output(raw_output: str) -> dict:
    """Parses JSON from append script execution."""
    if "APPEND_FEATURE_JSON_START" in raw_output:
        start = raw_output.find("APPEND_FEATURE_JSON_START") + len("APPEND_FEATURE_JSON_START")
        end = raw_output.find("APPEND_FEATURE_JSON_END", start)
        return json.loads(raw_output[start:end].strip())
    try:
        return json.loads(raw_output)
    except Exception:
        return {"error": "Failed to parse script output", "raw": raw_output}

def append_feature_in_place(
    mcp_client=None,
    comp_name: str = "",
    body_name: str = "",
    op_type: str = "pocket_cut",
    face_normal: str = "+Z",
    op_params: dict = None
) -> dict:
    """Entrypoint to execute feature append programmatically."""
    script = generate_append_script(comp_name, body_name, op_type, face_normal, op_params)
    if mcp_client:
        res = mcp_client.execute_api_script(script)
        return parse_append_output(res)
    return {"script": script}

def main():
    parser = argparse.ArgumentParser(description="Fusion 360 Localized Feature Appender (Tier 3)")
    parser.add_argument("--comp", required=True, help="Target component name")
    parser.add_argument("--body", default="Body1", help="Target body name")
    parser.add_argument("--op", default="pocket_cut", choices=["pocket_cut", "magnet_pocket"])
    parser.add_argument("--normal", default="+Z", help="Target face normal (+Z, -Z, +Y, -Y)")
    parser.add_argument("--params", default="{}", help="JSON string of feature parameters")
    args = parser.parse_args()

    params = json.loads(args.params)
    script = generate_append_script(args.comp, args.body, args.op, args.normal, params)
    print(script)

if __name__ == "__main__":
    main()
