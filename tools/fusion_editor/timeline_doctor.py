#!/usr/bin/env python3
"""
Timeline Doctor: Diagnostic health verification for Autodesk Fusion 360 timelines.
Scans all timeline objects for warnings (yellow) and errors (red), reporting exact
feature indices, names, and error messages.
"""
import json
import sys
import argparse

def generate_health_script() -> str:
    """Returns self-contained Python script to execute inside Fusion 360."""
    return '''import adsk.core, adsk.fusion, json

def run(context):
    app = adsk.core.Application.get()
    if not app:
        print(json.dumps({"error": "Fusion 360 not running"}))
        return
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        print(json.dumps({"error": "No active design document"}))
        return

    timeline = design.timeline
    total = timeline.count
    healthy = 0
    suppressed = 0
    rolled_back = 0
    warnings = []
    errors = []

    for i in range(total):
        obj = timeline.item(i)
        hs = obj.healthState
        if hs == adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            healthy += 1
        elif hs == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
            warnings.append({
                "index": i,
                "name": obj.name,
                "type": obj.entity.objectType if obj.entity else "Unknown",
                "message": obj.errorOrWarningMessage
            })
        elif hs == adsk.fusion.FeatureHealthStates.ErrorFeatureHealthState:
            errors.append({
                "index": i,
                "name": obj.name,
                "type": obj.entity.objectType if obj.entity else "Unknown",
                "message": obj.errorOrWarningMessage
            })
        elif hs == adsk.fusion.FeatureHealthStates.SuppressedFeatureHealthState:
            suppressed += 1
        elif hs == adsk.fusion.FeatureHealthStates.RolledBackFeatureHealthState:
            rolled_back += 1

    report = {
        "status": "HEALTHY" if len(errors) == 0 and len(warnings) == 0 else ("WARNING" if len(errors) == 0 else "ERROR"),
        "total": total,
        "healthy": healthy,
        "suppressed": suppressed,
        "rolled_back": rolled_back,
        "warning_count": len(warnings),
        "error_count": len(errors),
        "warnings": warnings,
        "errors": errors
    }
    print("TIMELINE_DOCTOR_JSON_START")
    print(json.dumps(report, indent=2))
    print("TIMELINE_DOCTOR_JSON_END")
'''

def parse_doctor_output(raw_output: str) -> dict:
    """Extracts JSON report from script execution text."""
    if "TIMELINE_DOCTOR_JSON_START" in raw_output:
        start = raw_output.find("TIMELINE_DOCTOR_JSON_START") + len("TIMELINE_DOCTOR_JSON_START")
        end = raw_output.find("TIMELINE_DOCTOR_JSON_END", start)
        json_str = raw_output[start:end].strip()
        return json.loads(json_str)
    try:
        return json.loads(raw_output)
    except Exception:
        return {"error": "Failed to parse script output", "raw": raw_output}

def check_timeline_health(mcp_client=None) -> dict:
    """Entrypoint to run health check programmatically."""
    script = generate_health_script()
    if mcp_client:
        res = mcp_client.execute_api_script(script)
        return parse_doctor_output(res)
    return {"script": script}

def format_health_table(report: dict) -> str:
    """Formats report into human-readable markdown table."""
    status = report.get("status", "UNKNOWN")
    total = report.get("total", 0)
    healthy = report.get("healthy", 0)
    warnings = report.get("warnings", [])
    errors = report.get("errors", [])

    badge = "🟢 HEALTHY" if status == "HEALTHY" else ("🟡 WARNINGS DETECTED" if status == "WARNING" else "🔴 ERRORS DETECTED")
    lines = [
        f"### Fusion 360 Timeline Diagnostic: {badge}",
        f"| Total Objects | Healthy | Warnings | Errors | Suppressed |",
        f"| :---: | :---: | :---: | :---: | :---: |",
        f"| {total} | {healthy} | {len(warnings)} | {len(errors)} | {report.get('suppressed', 0)} |",
    ]

    if errors:
        lines.append("\n#### 🔴 Red Timeline Errors:")
        for e in errors:
            lines.append(f"- `[{e['index']}] {e['name']}` ({e['type']}): {e['message']}")

    if warnings:
        lines.append("\n#### 🟡 Yellow Timeline Warnings:")
        for w in warnings:
            lines.append(f"- `[{w['index']}] {w['name']}` ({w['type']}): {w['message']}")

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Fusion 360 Timeline Diagnostic Doctor")
    parser.add_argument("--format", choices=["table", "json", "script"], default="table")
    args = parser.parse_args()

    if args.format == "script":
        print(generate_health_script())
        return

    # In standalone execution, print ready-to-run script
    print(generate_health_script())

if __name__ == "__main__":
    main()
