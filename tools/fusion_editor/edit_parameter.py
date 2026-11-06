#!/usr/bin/env python3
"""
Edit Parameter: Tier 1 Instant Parametric Surgery tool for Autodesk Fusion 360.
Modifies driving user parameters or feature dimensions in-place within milliseconds.
Includes automatic pre-capture, post-edit timeline health verification, and
instant auto-revert if downstream geometry errors are triggered.
"""
import json
import sys
import argparse

def generate_param_edit_script(
    param_name: str = "",
    comp_name: str = "",
    feature_name: str = "",
    feature_prop: str = "distance",
    new_expression: str = "",
    revert_on_warning: bool = True
) -> str:
    """Generates Python script to execute parameter edit inside Fusion 360."""
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

    param_name = "{param_name}"
    comp_name = "{comp_name}"
    feature_name = "{feature_name}"
    feature_prop = "{feature_prop}"
    new_expr = "{new_expression}"
    revert_on_warn = {revert_on_warning}

    old_expr = None
    target_entity = None
    target_type = None

    # Case A: Named User / Model Parameter
    if param_name:
        p = design.userParameters.itemByName(param_name) or design.allParameters.itemByName(param_name)
        if p:
            old_expr = p.expression
            target_entity = p
            target_type = "Parameter"
        else:
            print(json.dumps({{"error": f"Parameter '{{param_name}}' not found"}}))
            return

    # Case B: Specific Component Feature Property
    elif comp_name and feature_name:
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

        # Check extrudeFeatures
        ext = target_comp.features.extrudeFeatures.itemByName(feature_name)
        if ext:
            if hasattr(ext.extentOne, 'distance') and ext.extentOne.distance:
                old_expr = ext.extentOne.distance.expression
                target_entity = ext.extentOne.distance
                target_type = "ExtrudeFeature.distance"

        # Check holeFeatures
        if not target_entity:
            hole = target_comp.features.holeFeatures.itemByName(feature_name)
            if hole and hasattr(hole, 'holeDiameter'):
                old_expr = hole.holeDiameter.expression
                target_entity = hole.holeDiameter
                target_type = "HoleFeature.diameter"

        # Check filletFeatures
        if not target_entity:
            fillet = target_comp.features.filletFeatures.itemByName(feature_name)
            if fillet and fillet.edgeSets.count > 0:
                old_expr = fillet.edgeSets.item(0).radius.expression
                target_entity = fillet.edgeSets.item(0).radius
                target_type = "FilletFeature.radius"

        if not target_entity:
            print(json.dumps({{"error": f"Feature '{{feature_name}}' with property '{{feature_prop}}' not found in component '{{comp_name}}'"}}))
            return
    else:
        print(json.dumps({{"error": "Must provide either --param or (--comp and --feature)"}}))
        return

    # Apply in-place edit
    try:
        target_entity.expression = new_expr
    except Exception as e:
        print(json.dumps({{"error": f"Failed to assign expression '{{new_expr}}': {{str(e)}}"}}))
        return

    # Immediate Timeline Health Verification
    timeline = design.timeline
    warnings = []
    errors = []
    for i in range(timeline.count):
        obj = timeline.item(i)
        hs = obj.healthState
        if hs == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
            warnings.append({{"index": i, "name": obj.name, "message": obj.errorOrWarningMessage}})
        elif hs == adsk.fusion.FeatureHealthStates.ErrorFeatureHealthState:
            errors.append({{"index": i, "name": obj.name, "message": obj.errorOrWarningMessage}})

    has_degradation = len(errors) > 0 or (revert_on_warn and len(warnings) > 0)
    reverted = False

    if has_degradation:
        # Auto-revert
        try:
            target_entity.expression = old_expr
            reverted = True
        except Exception:
            pass

    result = {{
        "status": "REVERTED_ON_ERROR" if reverted else ("SUCCESS" if not has_degradation else "SUCCESS_WITH_WARNINGS"),
        "target_type": target_type,
        "target_name": param_name or f"{{comp_name}}.{{feature_name}}",
        "previous_expression": old_expr,
        "applied_expression": new_expr if not reverted else old_expr,
        "attempted_expression": new_expr,
        "reverted": reverted,
        "warnings": warnings,
        "errors": errors
    }}

    print("PARAM_EDIT_JSON_START")
    print(json.dumps(result, indent=2))
    print("PARAM_EDIT_JSON_END")
'''

def parse_edit_output(raw_output: str) -> dict:
    """Parses JSON from edit script execution."""
    if "PARAM_EDIT_JSON_START" in raw_output:
        start = raw_output.find("PARAM_EDIT_JSON_START") + len("PARAM_EDIT_JSON_START")
        end = raw_output.find("PARAM_EDIT_JSON_END", start)
        return json.loads(raw_output[start:end].strip())
    try:
        return json.loads(raw_output)
    except Exception:
        return {"error": "Failed to parse script output", "raw": raw_output}

def edit_parameter_in_place(
    mcp_client=None,
    param_name: str = "",
    comp_name: str = "",
    feature_name: str = "",
    feature_prop: str = "distance",
    new_expression: str = ""
) -> dict:
    """Entrypoint to execute parameter edit programmatically."""
    script = generate_param_edit_script(
        param_name=param_name,
        comp_name=comp_name,
        feature_name=feature_name,
        feature_prop=feature_prop,
        new_expression=new_expression
    )
    if mcp_client:
        res = mcp_client.execute_api_script(script)
        return parse_edit_output(res)
    return {"script": script}

def main():
    parser = argparse.ArgumentParser(description="Fusion 360 In-Place Parameter Editor (Tier 1)")
    parser.add_argument("--param", default="", help="User parameter or model parameter name")
    parser.add_argument("--comp", default="", help="Component name")
    parser.add_argument("--feature", default="", help="Feature name (e.g. Extrude10)")
    parser.add_argument("--prop", default="distance", help="Property name")
    parser.add_argument("--expr", required=True, help="New expression string (e.g. '3.5 mm')")
    parser.add_argument("--no-revert", action="store_true", help="Do not revert on timeline warnings")
    args = parser.parse_args()

    script = generate_param_edit_script(
        param_name=args.param,
        comp_name=args.comp,
        feature_name=args.feature,
        feature_prop=args.prop,
        new_expression=args.expr,
        revert_on_warning=not args.no_revert
    )
    print(script)

if __name__ == "__main__":
    main()
