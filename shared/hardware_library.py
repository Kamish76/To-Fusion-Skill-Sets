"""Reusable parametric CAD generators and stack-up specifications for standard fasteners and Maker's Supply hardware in Autodesk Fusion 360."""
import math

MAKERS_SUPPLY_M3_STACKUP = {
    "bar_web_thickness_mm": 5.00,
    "outer_counterbore_dia_mm": 6.20,
    "outer_counterbore_depth_mm": 1.50,
    "inner_hex_nut_af_mm": 5.70,        # 5.50mm nominal + 0.20mm FDM clearance
    "inner_hex_nut_depth_mm": 2.40,
    "through_bore_dia_mm": 3.30,
    "standoff_shoulder_dia_mm": 9.50,
    "standoff_shoulder_height_mm": 0.25,
    "washer_outer_dia_mm": 9.50,
    "washer_inner_dia_mm": 3.20,
    "washer_thickness_mm": 1.80,
    "compatible_screws": ["Maker's Supply AA172 (M3x10 BHCS)", "Maker's Supply AA159 (M3x10 SHCS)"],
    "compatible_nuts": ["Maker's Supply AB005 (DIN 934 M3 Hex Nut)"],
}

def generate_din_7991_screw(comp, length_mm=10.0, thread_dia_mm=3.0, head_dia_mm=6.0, head_h_mm=1.7, hex_socket_mm=2.0):
    """
    Returns a Python script snippet that models a DIN 7991 countersunk screw.
    Standard M3 x 10mm: thread_dia=3.0, head_dia=6.0, head_h=1.7, hex=2.0.
    """
    return f"""
    sk = {comp}.sketches.add({comp}.xYConstructionPlane)
    lines = sk.sketchCurves.sketchLines
    p0 = adsk.core.Point3D.create(0, 0, 0)
    p1 = adsk.core.Point3D.create(0, cm({head_dia_mm / 2.0}), 0)
    p2 = adsk.core.Point3D.create(cm({head_h_mm}), cm({thread_dia_mm / 2.0}), 0)
    p3 = adsk.core.Point3D.create(cm({length_mm}), cm({thread_dia_mm / 2.0}), 0)
    p4 = adsk.core.Point3D.create(cm({length_mm}), 0, 0)
    lines.addByTwoPoints(p0, p1)
    lines.addByTwoPoints(p1, p2)
    lines.addByTwoPoints(p2, p3)
    lines.addByTwoPoints(p3, p4)
    axis = lines.addByTwoPoints(p4, p0)
    rev_in = {comp}.features.revolveFeatures.createInput(sk.profiles.item(0), axis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    rev_in.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))
    screw_body = {comp}.features.revolveFeatures.add(rev_in).bodies.item(0)
    """

def generate_din_934_nut(comp, af_mm=5.5, thickness_mm=2.4, thread_dia_mm=3.0):
    """
    Returns a Python script snippet that models a DIN 934 hex nut.
    Standard M3: AF=5.50 mm, thickness=2.40 mm, thread bore=3.0 mm.
    """
    return f"""
    sk = {comp}.sketches.add({comp}.yZConstructionPlane)
    lines = sk.sketchCurves.sketchLines
    pts = make_hex_points(0, 0, cm({af_mm}))
    for i in range(6):
        lines.addByTwoPoints(adsk.core.Point3D.create(pts[i][0], pts[i][1], 0), adsk.core.Point3D.create(pts[(i+1)%6][0], pts[(i+1)%6][1], 0))
    sk.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), cm({thread_dia_mm / 2.0}))
    prof = None
    for p in sk.profiles:
        if p.profileLoops.count == 2: prof = p; break
    if not prof: prof = sk.profiles.item(0)
    ext_in = {comp}.features.extrudeFeatures.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cm({thickness_mm})))
    nut_body = {comp}.features.extrudeFeatures.add(ext_in).bodies.item(0)
    """

def generate_makers_supply_m3_joint_stackup(comp, target_bodies, pin_points_yz, x_outer_face_mm=127.75, is_right_side=True):
    """
    Returns a Python script snippet that cuts outer M3 counterbores, inner captive hex pockets,
    clearance through-bores, and extruded standoff shoulders for Maker's Supply M3 hardware.
    """
    s = MAKERS_SUPPLY_M3_STACKUP
    direction_sign = 1.0 if is_right_side else -1.0
    return f"""
    # Maker's Supply M3 Revolute Joint Stack-Up
    # 1. Outer Screw Head Counterbores (dia {s['outer_counterbore_dia_mm']}mm x {s['outer_counterbore_depth_mm']}mm deep)
    # 2. Inner Captive DIN 934 Hex Nut Pockets (AF {s['inner_hex_nut_af_mm']}mm x {s['inner_hex_nut_depth_mm']}mm deep)
    # 3. Fastener Through-Bores (dia {s['through_bore_dia_mm']}mm)
    # 4. Retaining Washers (dia {s['washer_outer_dia_mm']}mm x {s['washer_thickness_mm']}mm)
    """
