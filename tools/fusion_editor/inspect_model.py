#!/usr/bin/env python3
"""
Inspect Model: Deep introspection engine for active Autodesk Fusion 360 models.
Extracts component trees, bodies, bounding boxes, user & model parameters, timeline
features, and planar face spatial coordinates.
"""
import json
import sys
import argparse

def generate_inspect_script(target_comp: str = "", find_face: str = "") -> str:
    """Generates Fusion 360 API Python script for deep introspection."""
    return f'''import adsk.core, adsk.fusion, json, math

def run(context):
    app = adsk.core.Application.get()
    if not app:
        print(json.dumps({{"error": "Fusion 360 not running"}}))
        return
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print(json.dumps({{"error": "No active design document"}}))
        return

    doc_name = design.parentDocument.name if design.parentDocument else "Untitled"
    root = design.rootComponent

    # 1. User & Driving Parameters
    user_params = []
    for p in design.userParameters:
        user_params.append({{
            "name": p.name,
            "expression": p.expression,
            "value_mm": p.value * 10.0,
            "unit": p.unit,
            "comment": p.comment
        }})

    model_params = []
    for p in design.allParameters:
        if p not in design.userParameters:
            model_params.append({{
                "name": p.name,
                "expression": p.expression,
                "value_mm": p.value * 10.0,
                "unit": p.unit
            }})

    # 2. Timeline Breakdown
    timeline = design.timeline
    timeline_summary = {{"total": timeline.count, "feature_types": {{}}}}
    for i in range(timeline.count):
        obj = timeline.item(i)
        t_name = obj.entity.objectType if obj.entity else "TimelineGroup"
        short_type = t_name.split("::")[-1]
        timeline_summary["feature_types"][short_type] = timeline_summary["feature_types"].get(short_type, 0) + 1

    # 3. Component & Body Hierarchy
    def inspect_comp(comp, occ_name="Root"):
        info = {{
            "occurrence_name": occ_name,
            "component_name": comp.name,
            "bodies": [],
            "sketches": [],
            "features_summary": {{
                "extrudes": comp.features.extrudeFeatures.count,
                "revolves": comp.features.revolveFeatures.count,
                "fillets": comp.features.filletFeatures.count,
                "chamfers": comp.features.chamferFeatures.count,
                "holes": comp.features.holeFeatures.count
            }},
            "children": []
        }}
        for b in comp.bRepBodies:
            bbox = b.boundingBox
            min_pt = bbox.minPoint
            max_pt = bbox.maxPoint
            dx = (max_pt.x - min_pt.x) * 10.0
            dy = (max_pt.y - min_pt.y) * 10.0
            dz = (max_pt.z - min_pt.z) * 10.0
            b_info = {{
                "name": b.name,
                "is_visible": b.isLightBulbOn,
                "volume_mm3": b.volume * 1000.0,
                "bbox_mm": {{
                    "width_x": round(dx, 3),
                    "depth_y": round(dy, 3),
                    "height_z": round(dz, 3),
                    "min": [round(min_pt.x * 10.0, 3), round(min_pt.y * 10.0, 3), round(min_pt.z * 10.0, 3)],
                    "max": [round(max_pt.x * 10.0, 3), round(max_pt.y * 10.0, 3), round(max_pt.z * 10.0, 3)]
                }},
                "face_count": b.faces.count
            }}
            info["bodies"].append(b_info)

        for s in comp.sketches:
            dims = [f"{{d.parameter.name}}={{d.parameter.expression}}" for d in s.sketchDimensions if d.parameter]
            info["sketches"].append({{
                "name": s.name,
                "is_visible": s.isLightBulbOn,
                "profile_count": s.profiles.count,
                "dimensions": dims
            }})

        for child in comp.occurrences:
            info["children"].append(inspect_comp(child.component, child.name))
        return info

    hierarchy = inspect_comp(root, "Root")

    # 4. Optional Spatial Face Query
    matched_faces = []
    face_filter = "{find_face}".strip()
    if face_filter:
        filter_dict = {{}}
        for token in face_filter.split(","):
            if "=" in token:
                k, v = token.split("=", 1)
                filter_dict[k.strip().lower()] = v.strip()
            else:
                filter_dict["normal"] = token.strip()

        target_bname = filter_dict.get("body", "").lower()
        target_norm = filter_dict.get("normal", "+Z").upper()

        def scan_faces(comp, occ_name):
            for b in comp.bRepBodies:
                if target_bname and target_bname not in b.name.lower():
                    continue
                for f_idx in range(b.faces.count):
                    f = b.faces.item(f_idx)
                    geom = f.geometry
                    if geom.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                        plane = adsk.core.Plane.cast(geom)
                        n = plane.normal
                        match = False
                        if target_norm == "+Z" and n.z > 0.99: match = True
                        elif target_norm == "-Z" and n.z < -0.99: match = True
                        elif target_norm == "+Y" and n.y > 0.99: match = True
                        elif target_norm == "-Y" and n.y < -0.99: match = True
                        elif target_norm == "+X" and n.x > 0.99: match = True
                        elif target_norm == "-X" and n.x < -0.99: match = True

                        if match:
                            f_box = f.boundingBox
                            matched_faces.append({{
                                "component": occ_name,
                                "body": b.name,
                                "face_index": f_idx,
                                "normal": target_norm,
                                "area_mm2": round(f.area * 100.0, 2),
                                "origin_z_mm": round(plane.origin.z * 10.0, 3),
                                "bbox_min": [round(f_box.minPoint.x * 10.0, 2), round(f_box.minPoint.y * 10.0, 2), round(f_box.minPoint.z * 10.0, 2)],
                                "bbox_max": [round(f_box.maxPoint.x * 10.0, 2), round(f_box.maxPoint.y * 10.0, 2), round(f_box.maxPoint.z * 10.0, 2)]
                            }})
            for occ in comp.occurrences:
                scan_faces(occ.component, occ.name)

        scan_faces(root, "Root")

    manifest = {{
        "document_name": doc_name,
        "timeline_summary": timeline_summary,
        "user_parameters": user_params,
        "model_parameters_count": len(model_params),
        "sample_model_parameters": model_params[:20],
        "hierarchy": hierarchy,
        "matched_faces": matched_faces
    }}

    print("INSPECT_MODEL_JSON_START")
    print(json.dumps(manifest, indent=2))
    print("INSPECT_MODEL_JSON_END")
'''

def parse_inspect_output(raw_output: str) -> dict:
    """Extracts JSON manifest from inspect script output."""
    if "INSPECT_MODEL_JSON_START" in raw_output:
        start = raw_output.find("INSPECT_MODEL_JSON_START") + len("INSPECT_MODEL_JSON_START")
        end = raw_output.find("INSPECT_MODEL_JSON_END", start)
        return json.loads(raw_output[start:end].strip())
    try:
        return json.loads(raw_output)
    except Exception:
        return {"error": "Failed to parse script output", "raw": raw_output}

def inspect_fusion_model(mcp_client=None, target_comp: str = "") -> dict:
    """Programmatic entrypoint to inspect active Fusion 360 session."""
    script = generate_inspect_script(target_comp)
    if mcp_client:
        res = mcp_client.execute_api_script(script)
        return parse_inspect_output(res)
    return {"script": script}

def format_inspect_table(manifest: dict) -> str:
    """Formats manifest into a comprehensive markdown summary."""
    doc = manifest.get("document_name", "Untitled")
    tl = manifest.get("timeline_summary", {})
    user_params = manifest.get("user_parameters", [])
    model_param_count = manifest.get("model_parameters_count", 0)

    lines = [
        f"### 🔍 Fusion 360 Model Introspection: `{doc}`",
        f"- **Timeline Count:** {tl.get('total', 0)} objects ({', '.join(f'{k}: {v}' for k, v in tl.get('feature_types', {}).items())})",
        f"- **Parameters:** {len(user_params)} User Parameters, {model_param_count} Model Dimensions",
        "",
        "#### Assembly Occurrence Tree & Bounding Boxes",
        "| Component / Occurrence | Body Name | Width (X) | Depth (Y) | Height (Z) | Faces |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |"
    ]

    def recurse_comp(comp_info, indent=""):
        c_name = comp_info.get("occurrence_name", "Root")
        for b in comp_info.get("bodies", []):
            bbox = b.get("bbox_mm", {})
            w = f"{bbox.get('width_x', 0):.2f} mm"
            d = f"{bbox.get('depth_y', 0):.2f} mm"
            h = f"{bbox.get('height_z', 0):.2f} mm"
            lines.append(f"| {indent}{c_name} | `{b.get('name')}` | {w} | {d} | {h} | {b.get('face_count', 0)} |")
        for child in comp_info.get("children", []):
            recurse_comp(child, indent + "&nbsp;&nbsp;↳ ")

    recurse_comp(manifest.get("hierarchy", {}))

    if user_params:
        lines.append("\n#### Driving User Parameters")
        lines.append("| Name | Expression | Value (mm) | Comment |")
        lines.append("| :--- | :--- | :---: | :--- |")
        for p in user_params:
            lines.append(f"| `{p['name']}` | `{p['expression']}` | {p['value_mm']:.2f} mm | {p.get('comment', '')} |")

    matched_faces = manifest.get("matched_faces", [])
    if matched_faces:
        lines.append("\n#### 🎯 Matched Planar Faces")
        lines.append("| Occurrence | Body | Face # | Normal | Area (mm²) | Origin Z (mm) |")
        lines.append("| :--- | :--- | :---: | :---: | :---: | :---: |")
        for f in matched_faces:
            lines.append(f"| {f['component']} | `{f['body']}` | {f['face_index']} | `{f['normal']}` | {f['area_mm2']} | {f['origin_z_mm']} |")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Fusion 360 Deep Model Introspection")
    parser.add_argument("--format", choices=["table", "json", "script"], default="table")
    parser.add_argument("--comp", default="", help="Filter by component name")
    parser.add_argument("--find-face", default="", help="Filter planar faces by direction (e.g. '+Z' or 'body=Body1,normal=+Z')")
    args = parser.parse_args()

    if args.format == "script":
        print(generate_inspect_script(args.comp, args.find_face))
        return

    # In standalone execution, print script
    print(generate_inspect_script(args.comp, args.find_face))

if __name__ == "__main__":
    main()
