import math

def cm(mm_val):
    """Converts millimeters to centimeters for Autodesk Fusion 360's internal coordinate API."""
    return mm_val / 10.0

def mm(cm_val):
    """Converts centimeters to millimeters."""
    return cm_val * 10.0

def make_hex_points(cx, cy, r_across_flats_cm):
    """Generates 6 Point2D/Point3D coordinates for a regular hexagon given distance across flats (AF)."""
    # r_corner = r_across_flats / cos(30 deg) = r_af / (sqrt(3)/2)
    r_corner = (r_across_flats_cm / 2.0) / math.cos(math.pi / 6.0)
    pts = []
    for i in range(6):
        angle = math.pi / 6.0 + i * (math.pi / 3.0)
        pts.append((cx + r_corner * math.cos(angle), cy + r_corner * math.sin(angle)))
    return pts

def set_user_param(design, name, expr_str, units="mm", comment=""):
    """Registers or updates an Autodesk Fusion 360 User Parameter."""
    existing = design.userParameters.itemByName(name)
    if existing:
        existing.expression = expr_str
        return existing
    import adsk.core
    return design.userParameters.add(
        name, adsk.core.ValueInput.createByString(expr_str), units, comment
    )
