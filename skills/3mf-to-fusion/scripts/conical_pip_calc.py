#!/usr/bin/env python3
"""
conical_pip_calc.py - Automated Conical Print-in-Place (PIP) Hinge Calculator & Parameter Synthesizer

Calculates mathematically verified dimensions for captive 3D conical print-in-place pivots
(typically 30° taper angle) ensuring a uniform mathematical 3D air gap, maximum engagement depth,
and printable blunt frustum tips without metal pins or droopy horizontal cylindrical bridges.

Usage:
    python3 conical_pip_calc.py --knuckle-dia 4.828 --gap-radial 0.35 --gap-axial 0.40 --taper-deg 30
    python3 conical_pip_calc.py --knuckle-dia 5.0 --format fusion-api
    python3 conical_pip_calc.py --knuckle-dia 4.828 --format json
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path


def calculate_conical_pip(
    knuckle_dia: float,
    knuckle_span: float = None,
    gap_radial: float = 0.35,
    gap_axial: float = 0.40,
    taper_deg: float = 30.0,
    min_tip_dia: float = 0.76,
    base_radius: float = None,
    shoulder_margin: float = None,
    engagement: float = None,
    tip_clearance: float = 0.20,
) -> dict:
    """
    Computes deterministic conical PIP pivot and socket parameters.

    All inputs and output dimensions are in millimeters (mm).
    Angles are in degrees.
    """
    if knuckle_dia <= 0:
        raise ValueError(f"knuckle_dia must be positive, got {knuckle_dia}")
    if taper_deg <= 0 or taper_deg >= 85:
        raise ValueError(f"taper_deg must be between 0 and 85 degrees, got {taper_deg}")
    if gap_radial < 0 or gap_axial < 0:
        raise ValueError("Clearance gaps must be non-negative.")

    r_knuckle = knuckle_dia / 2.0
    alpha_rad = math.radians(taper_deg)
    tan_a = math.tan(alpha_rad)
    cos_a = math.cos(alpha_rad)

    # 1. Male Cone Base Radius
    if base_radius is not None:
        r_male_base = float(base_radius)
        eff_shoulder = r_knuckle - r_male_base
    elif shoulder_margin is not None:
        eff_shoulder = float(shoulder_margin)
        r_male_base = r_knuckle - eff_shoulder
    else:
        # Standard optimal ratio (leaves >= 0.70 mm shoulder on knuckle)
        r_male_base = round(r_knuckle * 0.6835, 3)
        eff_shoulder = round(r_knuckle - r_male_base, 3)

    if r_male_base <= 0 or r_male_base >= r_knuckle:
        raise ValueError(
            f"Invalid male cone base radius {r_male_base:.3f} mm for knuckle radius {r_knuckle:.3f} mm"
        )

    # 2. Male Cone Height and Engagement
    r_tip = min_tip_dia / 2.0
    if r_tip >= r_male_base:
        raise ValueError(
            f"min_tip_dia ({min_tip_dia:.3f} mm) must be smaller than base diameter ({2*r_male_base:.3f} mm)"
        )

    if engagement is not None:
        d_engage = float(engagement)
        h_male = round(d_engage + gap_axial, 3)
        r_tip = round(r_male_base - h_male * tan_a, 3)
        if r_tip < 0.20:
            raise ValueError(
                f"Engagement {d_engage:.3f} mm produces a sharp or inverted tip (r_tip = {r_tip:.3f} mm). "
                f"Reduce engagement or taper angle."
            )
    else:
        # Maximum height constrained by min_tip_dia
        h_male = round((r_male_base - r_tip) / tan_a, 3)
        d_engage = round(h_male - gap_axial, 3)

    actual_tip_dia = round(r_tip * 2.0, 3)

    # 3. Female Socket Sizing (Constant 3D Radial Air Gap)
    # The male cone enters the socket at axial offset = gap_axial
    r_cone_at_entrance = r_male_base - gap_axial * tan_a
    r_socket_entrance = round(r_cone_at_entrance + gap_radial, 3)
    socket_shoulder = round(r_knuckle - r_socket_entrance, 3)

    d_socket = round(d_engage + tip_clearance, 3)
    r_socket_bottom = round(r_socket_entrance - d_socket * tan_a, 3)

    # 4. Air Gaps and Verification
    normal_gap = round(gap_radial * cos_a, 3)

    # Check wall thickness feasibility
    is_feasible = (
        eff_shoulder >= 0.50
        and socket_shoulder >= 0.50
        and actual_tip_dia >= 0.50
        and d_engage >= 0.80
        and r_socket_bottom >= 0.10
    )

    # Fusion API Parameter Block (in centimeters)
    fusion_params = {
        "knuckle_dia_cm": round(knuckle_dia / 10.0, 5),
        "male_base_radius_cm": round(r_male_base / 10.0, 5),
        "male_height_cm": round(h_male / 10.0, 5),
        "male_engagement_cm": round(d_engage / 10.0, 5),
        "male_tip_radius_cm": round(r_tip / 10.0, 5),
        "female_entrance_radius_cm": round(r_socket_entrance / 10.0, 5),
        "female_socket_depth_cm": round(d_socket / 10.0, 5),
        "female_bottom_radius_cm": round(max(0.0, r_socket_bottom) / 10.0, 5),
        "taper_angle_rad": round(alpha_rad, 6),
        "taper_angle_deg": round(taper_deg, 2),
        "gap_axial_cm": round(gap_axial / 10.0, 5),
        "gap_radial_cm": round(gap_radial / 10.0, 5),
        "normal_air_gap_cm": round(normal_gap / 10.0, 5),
    }

    return {
        "inputs": {
            "knuckle_dia_mm": knuckle_dia,
            "knuckle_radius_mm": r_knuckle,
            "knuckle_span_mm": knuckle_span,
            "gap_radial_mm": gap_radial,
            "gap_axial_mm": gap_axial,
            "taper_deg": taper_deg,
            "min_tip_dia_mm": min_tip_dia,
            "tip_clearance_mm": tip_clearance,
        },
        "male_cone": {
            "base_radius_mm": r_male_base,
            "base_dia_mm": round(r_male_base * 2.0, 3),
            "height_mm": h_male,
            "engagement_depth_mm": d_engage,
            "tip_radius_mm": r_tip,
            "tip_dia_mm": actual_tip_dia,
            "knuckle_shoulder_margin_mm": eff_shoulder,
        },
        "female_socket": {
            "entrance_radius_mm": r_socket_entrance,
            "entrance_dia_mm": round(r_socket_entrance * 2.0, 3),
            "depth_mm": d_socket,
            "bottom_radius_mm": round(max(0.0, r_socket_bottom), 3),
            "bottom_dia_mm": round(max(0.0, r_socket_bottom * 2.0), 3),
            "knuckle_shoulder_margin_mm": socket_shoulder,
            "tip_clearance_mm": tip_clearance,
        },
        "tolerances": {
            "radial_gap_mm": gap_radial,
            "normal_3d_air_gap_mm": normal_gap,
            "axial_face_gap_mm": gap_axial,
            "axial_tip_gap_mm": tip_clearance,
        },
        "feasibility": {
            "is_feasible": is_feasible,
            "adequate_male_shoulder": eff_shoulder >= 0.50,
            "adequate_socket_shoulder": socket_shoulder >= 0.50,
            "adequate_blunt_tip": actual_tip_dia >= 0.50,
            "adequate_engagement": d_engage >= 0.80,
            "socket_not_pointed": r_socket_bottom >= 0.10,
        },
        "fusion_api": fusion_params,
    }


def format_table(res: dict) -> str:
    inp = res["inputs"]
    m = res["male_cone"]
    f = res["female_socket"]
    t = res["tolerances"]
    v = res["feasibility"]

    span_str = f"{inp['knuckle_span_mm']:.2f} mm" if inp["knuckle_span_mm"] else "N/A"
    lines = [
        "================================================================================",
        "          CONICAL PRINT-IN-PLACE (PIP) HINGE METROLOGY & PARAMETERS",
        "================================================================================",
        f"Knuckle Barrel:       OD {inp['knuckle_dia_mm']:.3f} mm (R = {inp['knuckle_radius_mm']:.3f} mm) | Span: {span_str}",
        f"Taper Half-Angle (a): {inp['taper_deg']:.1f}° (tan a = {math.tan(math.radians(inp['taper_deg'])):.4f})",
        f"Air Gap Clearances:   Radial: {t['radial_gap_mm']:.3f} mm | 3D Normal: {t['normal_3d_air_gap_mm']:.3f} mm | Axial: {t['axial_face_gap_mm']:.3f} mm",
        "--------------------------------------------------------------------------------",
        "MALE CONICAL PIVOT (Cover Knuckle):",
        f"  * Base Radius (R_base):     {m['base_radius_mm']:.3f} mm (Dia: {m['base_dia_mm']:.3f} mm)",
        f"  * Cone Full Height (H):     {m['height_mm']:.3f} mm",
        f"  * Penetration Depth (D_eng):{m['engagement_depth_mm']:.3f} mm into opposing socket",
        f"  * Truncated Tip Radius:     {m['tip_radius_mm']:.3f} mm (Blunt Tip Dia: {m['tip_dia_mm']:.3f} mm)",
        f"  * Knuckle Shoulder Margin:  {m['knuckle_shoulder_margin_mm']:.3f} mm (Wall thickness around cone)",
        "--------------------------------------------------------------------------------",
        "FEMALE CONICAL SOCKET (Spine Knuckle):",
        f"  * Entrance Radius (R_sock): {f['entrance_radius_mm']:.3f} mm (Dia: {f['entrance_dia_mm']:.3f} mm)",
        f"  * Socket Depth (D_sock):    {f['depth_mm']:.3f} mm",
        f"  * Socket Bottom Radius:     {f['bottom_radius_mm']:.3f} mm (Dia: {f['bottom_dia_mm']:.3f} mm)",
        f"  * Knuckle Shoulder Margin:  {f['knuckle_shoulder_margin_mm']:.3f} mm (Outer rim thickness)",
        f"  * Axial Tip Clearance:      {f['tip_clearance_mm']:.3f} mm (Beyond cone tip)",
        "--------------------------------------------------------------------------------",
        f"FEASIBILITY CHECK:            {'[PASS] Feasible & Printable' if v['is_feasible'] else '[WARNING] Clearance/Wall Limits Exceeded'}",
        "================================================================================",
    ]
    return "\n".join(lines)


def format_fusion_code(res: dict) -> str:
    fp = res["fusion_api"]
    code = f'''# Fusion 360 API Parameter Block - Conical PIP Hinge (Internal Centimeters)
# Knuckle Dia: {res["inputs"]["knuckle_dia_mm"]:.3f} mm | Taper: {res["inputs"]["taper_deg"]:.1f}°
import adsk.core, adsk.fusion, math

def cm(val_mm): return val_mm / 10.0
def val_in(val_mm): return adsk.core.ValueInput.createByReal(cm(val_mm))

# Conical PIP Dimension Block (cm)
PIP_PARAMS = {{
    "male_base_radius_cm": {fp["male_base_radius_cm"]},
    "male_height_cm": {fp["male_height_cm"]},
    "male_engagement_cm": {fp["male_engagement_cm"]},
    "female_entrance_radius_cm": {fp["female_entrance_radius_cm"]},
    "female_socket_depth_cm": {fp["female_socket_depth_cm"]},
    "taper_angle_rad": {fp["taper_angle_rad"]}, # {fp["taper_angle_deg"]} deg
    "gap_axial_cm": {fp["gap_axial_cm"]},
    "gap_radial_cm": {fp["gap_radial_cm"]},
}}

# --- MALE PIVOT CONSTRUCTION EXAMPLE (Extrude with Taper) ---
# sketch_circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(center_pt, PIP_PARAMS["male_base_radius_cm"])
# ext_input = comp.features.extrudeFeatures.createInput(sketch.profiles.item(0), adsk.fusion.FeatureOperations.JoinFeatureOperation)
# ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(PIP_PARAMS["male_height_cm"]))
# ext_input.taperAngle = adsk.core.ValueInput.createByReal(-PIP_PARAMS["taper_angle_rad"])
# comp.features.extrudeFeatures.add(ext_input)

# --- FEMALE SOCKET CONSTRUCTION EXAMPLE (Cut Extrude with Taper) ---
# sock_circle = spine_sketch.sketchCurves.sketchCircles.addByCenterRadius(sock_center_pt, PIP_PARAMS["female_entrance_radius_cm"])
# sock_input = spine_comp.features.extrudeFeatures.createInput(spine_sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
# sock_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(PIP_PARAMS["female_socket_depth_cm"]))
# sock_input.taperAngle = adsk.core.ValueInput.createByReal(-PIP_PARAMS["taper_angle_rad"])
# spine_comp.features.extrudeFeatures.add(sock_input)
'''
    return code


def main():
    parser = argparse.ArgumentParser(
        description="Calculate 30° Conical Print-in-Place (PIP) hinge parameters for Fusion 360."
    )
    parser.add_argument(
        "--knuckle-dia",
        type=float,
        required=True,
        help="Knuckle barrel outer diameter in mm (e.g. 4.828).",
    )
    parser.add_argument(
        "--knuckle-span",
        "--span",
        type=float,
        default=None,
        help="Knuckle segment span along hinge axis in mm.",
    )
    parser.add_argument(
        "--gap-radial",
        type=float,
        default=0.35,
        help="Radial air gap between male cone and socket in mm (default: 0.35).",
    )
    parser.add_argument(
        "--gap-axial",
        type=float,
        default=0.40,
        help="Axial clearance between planar knuckle faces in mm (default: 0.40).",
    )
    parser.add_argument(
        "--taper-deg",
        type=float,
        default=30.0,
        help="Cone half-angle taper in degrees (default: 30.0).",
    )
    parser.add_argument(
        "--min-tip-dia",
        type=float,
        default=0.76,
        help="Minimum printable blunt tip diameter in mm (default: 0.76).",
    )
    parser.add_argument(
        "--base-radius",
        type=float,
        default=None,
        help="Explicit male cone base radius in mm (overrides ratio).",
    )
    parser.add_argument(
        "--shoulder-margin",
        type=float,
        default=None,
        help="Explicit knuckle shoulder wall margin in mm.",
    )
    parser.add_argument(
        "--engagement",
        type=float,
        default=None,
        help="Target engagement penetration depth in mm (overrides derived).",
    )
    parser.add_argument(
        "--tip-clearance",
        type=float,
        default=0.20,
        help="Axial gap beyond cone tip inside socket in mm (default: 0.20).",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "fusion-api"],
        default="table",
        help="Output format: table (human readable), json, or fusion-api Python code.",
    )

    args = parser.parse_args()

    try:
        res = calculate_conical_pip(
            knuckle_dia=args.knuckle_dia,
            knuckle_span=args.knuckle_span,
            gap_radial=args.gap_radial,
            gap_axial=args.gap_axial,
            taper_deg=args.taper_deg,
            min_tip_dia=args.min_tip_dia,
            base_radius=args.base_radius,
            shoulder_margin=args.shoulder_margin,
            engagement=args.engagement,
            tip_clearance=args.tip_clearance,
        )
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(res, indent=2))
    elif args.format == "fusion-api":
        print(format_fusion_code(res))
    else:
        print(format_table(res))


if __name__ == "__main__":
    main()
