#!/usr/bin/env python3
"""
Rollback Edit: Tier 2 Timeline Surgery tool for Autodesk Fusion 360.
Rolls the timeline marker back to an existing feature or sketch, applies targeted
modifications within that historical context, and rolls forward to the end,
ensuring all downstream features update naturally.
"""
import json
import sys
import argparse

def generate_rollback_script(
    target_name: str,
    action_type: str = "modify_extrude",
    action_params: dict = None,
    custom_snippet: str = ""
) -> str:
    """Generates Python script for timeline rollback surgery."""
    params_json = json.dumps(action_params or {})
    return f'''import adsk.core, adsk.fusion, json

def run(context):
    app = adsk.core.Application.get()
    if not app:
        print(json.dumps({{"error": "Fusion 360 not running"}}))
        return
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print(json.dumps({{"error": "No active design document"}}))
        return

    target_name = "{target_name}"
    action_type = "{action_type}"
    action_params = json.loads('{params_json}')
    timeline = design.timeline

    # Locate target timeline object
    target_obj = None
    target_index = -1
    for i in range(timeline.count):
        obj = timeline.item(i)
        if obj.name == target_name:
            target_obj = obj
            target_index = i
            break

    if not target_obj:
        print(json.dumps({{"error": f"Timeline object '{{target_name}}' not found"}}))
        return

    # Roll timeline marker to this object
    original_marker = timeline.markerPosition
    success = target_obj.rollTo(False) # roll marker after this object
    if not success:
        print(json.dumps({{"error": f"Failed to roll timeline to '{{target_name}}'"}}))
        return

    edit_error = None
    try:
        # Action Payload Execution
        entity = target_obj.entity
        if action_type == "modify_extrude" and entity:
            ext = adsk.fusion.ExtrudeFeature.cast(entity)
            if "distance_mm" in action_params:
                dist_val = action_params["distance_mm"] / 10.0
                ext.extentOne.distance.value = dist_val
            elif "distance_expr" in action_params:
                ext.extentOne.distance.expression = action_params["distance_expr"]
            if "taper_deg" in action_params:
                ext.taperAngle.value = action_params["taper_deg"] * (3.141592653589793 / 180.0)

        elif action_type == "modify_fillet" and entity:
            fillet = adsk.fusion.FilletFeature.cast(entity)
            if "radius_mm" in action_params and fillet.edgeSets.count > 0:
                fillet.edgeSets.item(0).radius.value = action_params["radius_mm"] / 10.0

        elif action_type == "custom" and """{custom_snippet}""".strip():
            # Run custom user snippet in rolled context
            {custom_snippet}

    except Exception as e:
        edit_error = str(e)

    # Always attempt to roll timeline back to end
    timeline.moveToEnd()

    # Verify downstream health
    warnings = []
    errors = []
    for i in range(timeline.count):
        obj = timeline.item(i)
        hs = obj.healthState
        if hs == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
            warnings.append({{"index": i, "name": obj.name, "message": obj.errorOrWarningMessage}})
        elif hs == adsk.fusion.FeatureHealthStates.ErrorFeatureHealthState:
            errors.append({{"index": i, "name": obj.name, "message": obj.errorOrWarningMessage}})

    result = {{
        "status": "ERROR" if edit_error or len(errors) > 0 else ("WARNING" if len(warnings) > 0 else "SUCCESS"),
        "target": target_name,
        "target_index": target_index,
        "action": action_type,
        "edit_error": edit_error,
        "warnings": warnings,
        "errors": errors
    }}

    print("ROLLBACK_EDIT_JSON_START")
    print(json.dumps(result, indent=2))
    print("ROLLBACK_EDIT_JSON_END")
'''

def parse_rollback_output(raw_output: str) -> dict:
    """Parses JSON from rollback script execution."""
    if "ROLLBACK_EDIT_JSON_START" in raw_output:
        start = raw_output.find("ROLLBACK_EDIT_JSON_START") + len("ROLLBACK_EDIT_JSON_START")
        end = raw_output.find("ROLLBACK_EDIT_JSON_END", start)
        return json.loads(raw_output[start:end].strip())
    try:
        return json.loads(raw_output)
    except Exception:
        return {"error": "Failed to parse script output", "raw": raw_output}

def rollback_and_edit(
    mcp_client=None,
    target_name: str = "",
    action_type: str = "modify_extrude",
    action_params: dict = None,
    custom_snippet: str = ""
) -> dict:
    """Entrypoint to execute rollback edit programmatically."""
    script = generate_rollback_script(target_name, action_type, action_params, custom_snippet)
    if mcp_client:
        res = mcp_client.execute_api_script(script)
        return parse_rollback_output(res)
    return {"script": script}

def main():
    parser = argparse.ArgumentParser(description="Fusion 360 Timeline Rollback Surgery (Tier 2)")
    parser.add_argument("--target", required=True, help="Timeline feature/sketch name to roll back to")
    parser.add_argument("--action", default="modify_extrude", choices=["modify_extrude", "modify_fillet", "custom"])
    parser.add_argument("--params", default="{}", help="JSON string of action parameters")
    args = parser.parse_args()

    params = json.loads(args.params)
    script = generate_rollback_script(args.target, args.action, params)
    print(script)

if __name__ == "__main__":
    main()
