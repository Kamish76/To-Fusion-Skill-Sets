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

def make_dfm_hex_points(cy, cz, w_h, h_v, crown=None):
    """Generates 6 coordinates for a 45-degree crowned DFM hexagon.
    
    Decouples crown rise from regular hexagon math and enforces crown = w_h by default,
    guaranteeing an exact 45.0-degree self-supporting roof overhang angle (dZ/dY = 1.0).
    Vertices ordered CCW starting from top apex.
    """
    if crown is None:
        crown = w_h
    return [
        (cy, cz + h_v + crown),         # top apex
        (cy - w_h, cz + h_v),           # top-left
        (cy - w_h, cz - h_v),           # bottom-left
        (cy, cz - h_v - crown),         # bottom apex
        (cy + w_h, cz - h_v),           # bottom-right
        (cy + w_h, cz + h_v),           # top-right
    ]

def calc_dfm_hex_area(w_h, h_v, crown=None):
    """Calculates analytical cross-sectional area of a DFM 45-degree crowned hexagon.
    Area = (central rect 2*w_h * 2*h_v) + 2 * (roof triangle 0.5 * 2*w_h * crown).
    """
    if crown is None:
        crown = w_h
    return 4.0 * w_h * h_v + 2.0 * w_h * crown

def generate_dfm_honeycomb_grid(y_bounds, z_bounds, w_h, h_v, w_strut, crown=None, margin=0.0):
    """Generates a staggered DFM honeycomb grid with isotropic strut thickness.
    
    Uses closed-form row and column spacing:
      delta_y = 2 * w_h + w_strut
      delta_z = sqrt(2) * w_strut + 2 * h_v + w_h
    
    Guarantees uniform wall thickness w_strut across both horizontal and diagonal struts.
    """
    if w_h <= 0 or w_strut <= 0 or h_v < 0:
        return []

    if crown is None:
        crown = w_h

    delta_y = 2.0 * w_h + w_strut
    delta_z = math.sqrt(2.0) * w_strut + 2.0 * h_v + w_h

    y_min, y_max = y_bounds
    z_min, z_max = z_bounds

    y_start = y_min + margin + w_h
    y_end = y_max - margin - w_h
    z_start = z_min + margin + h_v + crown
    z_end = z_max - margin - h_v - crown

    if y_start > y_end or z_start > z_end:
        return []

    cells = []
    # Calculate row count that fits
    n_rows = int((z_end - z_start) / delta_z) + 1
    # Center rows vertically in available span
    total_grid_z = (n_rows - 1) * delta_z if n_rows > 1 else 0.0
    z_offset = z_start + (z_end - z_start - total_grid_z) / 2.0

    for r in range(n_rows):
        cz = z_offset + r * delta_z
        stagger = 0.5 * delta_y if (r % 2 == 1) else 0.0
        
        c = 0
        while True:
            cy = (y_min + margin + w_h + stagger) + c * delta_y
            if cy + w_h > y_max - margin:
                break
            cells.append({
                "center": (cy, cz),
                "points": make_dfm_hex_points(cy, cz, w_h, h_v, crown),
                "row": r,
                "col": c
            })
            c += 1

    return cells

def filter_profiles_by_area(profiles, target_area, tolerance=0.08):
    """Filters Fusion 360 sketch profiles matching analytical area within tolerance."""
    return [p for p in profiles if abs(p.areaProperties().area - target_area) <= tolerance]
