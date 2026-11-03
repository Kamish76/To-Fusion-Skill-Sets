# Fusion 360 Feature Reconstruction Recipes

Production-ready, copy-pasteable Python API recipes for executing clean parametric reverse-engineering in Fusion 360 via `execute_api_script`.

---

## 1. Unit Helper & Component Scaffolding

```python
import adsk.core, adsk.fusion, math

def mm(val):
    """Fusion 360 internal database strictly uses centimeters. Always divide mm by 10.0."""
    return adsk.core.ValueInput.createByReal(float(val) / 10.0)

def setup_part_component(root, part_name):
    """Creates a clean isolated occurrence and returns (occ, comp)."""
    transform = adsk.core.Matrix3D.create()
    occ = root.occurrences.addNewComponent(transform)
    comp = occ.component
    comp.name = part_name
    return occ, comp
```

---

## 2. Parametric User Parameters

```python
def add_user_parameter(design, name, val_mm, comment=""):
    """Adds or updates a driving user parameter in millimeters."""
    params = design.userParameters
    existing = params.itemByName(name)
    if existing:
        existing.expression = f"{val_mm} mm"
        return existing
    return params.add(name, mm(val_mm), "mm", comment)
```

---

## 3. Base Extruded Plate (Centered)

```python
def create_base_plate(comp, width_mm, length_mm, height_mm):
    """Draws a centered rectangular base plate and extrudes it."""
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    
    sketch = sketches.add(comp.xYConstructionPlane)
    lines = sketch.sketchCurves.sketchLines
    w_half = width_mm / 20.0  # cm
    l_half = length_mm / 20.0 # cm
    
    p1 = adsk.core.Point3D.create(-w_half, -l_half, 0)
    p2 = adsk.core.Point3D.create(w_half, -l_half, 0)
    p3 = adsk.core.Point3D.create(w_half, l_half, 0)
    p4 = adsk.core.Point3D.create(-w_half, l_half, 0)
    
    lines.addByTwoPoints(p1, p2)
    lines.addByTwoPoints(p2, p3)
    lines.addByTwoPoints(p3, p4)
    lines.addByTwoPoints(p4, p1)
    
    prof = sketch.profiles.item(0)
    ext_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ext_in.setDistanceExtent(False, mm(height_mm))
    ext_feature = extrudes.add(ext_in)
    return ext_feature.bodies.item(0)
```

---

## 4. Slot (Obround / Stadium) Cutout

```python
def create_slot_cut(comp, base_body, cx_mm, cy_mm, width_mm, length_mm, depth_mm):
    """Draws a vertical slot (two lines + two semicircular tangent arcs) and cuts through."""
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    
    sketch = sketches.add(comp.xYConstructionPlane)
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    
    slot_cx = cx_mm / 10.0
    slot_cy = cy_mm / 10.0
    r_cm = (width_mm / 2.0) / 10.0
    straight_half_cm = (length_mm - width_mm) / 20.0
    
    top_center = adsk.core.Point3D.create(slot_cx, slot_cy + straight_half_cm, 0)
    bot_center = adsk.core.Point3D.create(slot_cx, slot_cy - straight_half_cm, 0)
    
    p_tl = adsk.core.Point3D.create(slot_cx - r_cm, slot_cy + straight_half_cm, 0)
    p_tr = adsk.core.Point3D.create(slot_cx + r_cm, slot_cy + straight_half_cm, 0)
    p_bl = adsk.core.Point3D.create(slot_cx - r_cm, slot_cy - straight_half_cm, 0)
    p_br = adsk.core.Point3D.create(slot_cx + r_cm, slot_cy - straight_half_cm, 0)
    
    lines.addByTwoPoints(p_tl, p_bl)
    lines.addByTwoPoints(p_tr, p_br)
    arcs.addByCenterStartSweep(top_center, p_tr, math.pi)
    arcs.addByCenterStartSweep(bot_center, p_bl, math.pi)
    
    prof = sketch.profiles.item(0)
    cut_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_in.setDistanceExtent(False, mm(depth_mm + 1.0))
    cut_in.participantBodies = [base_body]
    return extrudes.add(cut_in)
```

---

## 5. Rectangular Pattern Feature

```python
def pattern_feature_rectangular(comp, feature_to_pattern, count_x, pitch_x_mm, count_y, pitch_y_mm):
    """Arrays a seed feature across X and Y axes using spacing distance."""
    patterns = comp.features.rectangularPatternFeatures
    entities = adsk.core.ObjectCollection.create()
    entities.add(feature_to_pattern)
    
    x_axis = comp.xConstructionAxis
    y_axis = comp.yConstructionAxis
    
    pat_in = patterns.createInput(
        entities, 
        x_axis, 
        adsk.core.ValueInput.createByString(str(count_x)), 
        mm(pitch_x_mm), 
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType
    )
    if count_y > 1:
        pat_in.setDirectionTwo(
            y_axis, 
            adsk.core.ValueInput.createByString(str(count_y)), 
            mm(pitch_y_mm)
        )
    return patterns.add(pat_in)
```

---

## 6. Axisymmetric Revolve Feature (Turned Parts)

```python
def create_revolved_body(comp, half_profile_points_rz_mm):
    """
    Creates a turned / axisymmetric body from a half-profile [(radius, z), ...].
    Sketches on the XZ plane and revolves 360 degrees around the Z axis.
    """
    sketches = comp.sketches
    revolves = comp.features.revolveFeatures
    
    sketch = sketches.add(comp.xZConstructionPlane)
    lines = sketch.sketchCurves.sketchLines
    
    # Draw contour along outer radius and close along centerline X=0
    pts_3d = []
    for r, z in half_profile_points_rz_mm:
        pts_3d.append(adsk.core.Point3D.create(r / 10.0, z / 10.0, 0))
    
    # Close profile to Z axis
    z_min = half_profile_points_rz_mm[0][1] / 10.0
    z_max = half_profile_points_rz_mm[-1][1] / 10.0
    p_center_top = adsk.core.Point3D.create(0, z_max, 0)
    p_center_bot = adsk.core.Point3D.create(0, z_min, 0)
    
    for i in range(len(pts_3d) - 1):
        lines.addByTwoPoints(pts_3d[i], pts_3d[i + 1])
        
    lines.addByTwoPoints(pts_3d[-1], p_center_top)
    lines.addByTwoPoints(p_center_top, p_center_bot)
    lines.addByTwoPoints(p_center_bot, pts_3d[0])
    
    prof = sketch.profiles.item(0)
    z_axis = comp.zConstructionAxis
    rev_in = revolves.createInput(prof, z_axis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    rev_in.setAngleExtent(False, adsk.core.ValueInput.createByReal(2.0 * math.pi))
    return revolves.add(rev_in)
```

---

## 7. Concentric Counterbore Hole

```python
def create_counterbore_hole(comp, base_body, cx_mm, cy_mm, hole_dia_mm, cbore_dia_mm, cbore_depth_mm, total_depth_mm):
    """Creates a counterbored screw hole (large shallow bore + small through-bore)."""
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    
    # Sketch on top plane
    sketch = sketches.add(comp.xYConstructionPlane)
    circles = sketch.sketchCurves.sketchCircles
    center = adsk.core.Point3D.create(cx_mm / 10.0, cy_mm / 10.0, 0)
    
    c_cbore = circles.addByCenterRadius(center, mm(cbore_dia_mm / 2.0))
    c_hole = circles.addByCenterRadius(center, mm(hole_dia_mm / 2.0))
    
    # Cut through hole
    prof_hole = sketch.profiles.item(0)
    cut1_in = extrudes.createInput(prof_hole, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut1_in.setDistanceExtent(False, mm(total_depth_mm + 1.0))
    cut1_in.participantBodies = [base_body]
    extrudes.add(cut1_in)
    
    # Cut counterbore
    prof_cbore = sketch.profiles.item(1)
    cut2_in = extrudes.createInput(prof_cbore, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut2_in.setDistanceExtent(False, mm(cbore_depth_mm))
    cut2_in.participantBodies = [base_body]
    return extrudes.add(cut2_in)

---

## 8. In-CAD Reference Mesh Staging, Ghost Overlay & Handover Assertion

```python
def stage_reference_mesh(root, stl_path):
    """Imports raw STL into an isolated Reference_Meshes_Staging component."""
    ref_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    ref_comp = ref_occ.component
    ref_comp.name = "Reference_Meshes_Staging"
    
    base_feat = ref_comp.features.baseFeatures.add()
    base_feat.startEdit()
    mesh_body = ref_comp.meshBodies.add(
        stl_path, 
        adsk.fusion.MeshUnits.MillimeterMeshUnit, 
        base_feat
    )
    base_feat.finishEdit()
    print(f"Staged mesh body '{mesh_body.name}' in {ref_comp.name} (total: {ref_comp.meshBodies.count})")
    return ref_occ, ref_comp

def apply_ghost_overlay(ref_target, opacity=0.5):
    """Sets a translucent opacity override on the reference component (Component has opacity setter; Occurrence does not)."""
    comp = getattr(ref_target, "component", ref_target)
    comp.opacity = opacity

def handover_and_assert_timeline(root, comp):
    """Deletes all staging reference mesh occurrences across document and asserts pure parametric BRep solid bodies."""
    for occ in list(root.occurrences):
        if "Reference_Meshes_Staging" in occ.component.name:
            occ.deleteMe()
        
    assert comp.bRepBodies.count > 0, "No solid bodies produced in reconstructed component!"
    assert comp.meshBodies.count == 0, "Forbidden MeshBody detected in reconstructed component!"
    assert comp.sketches.count > 0, "No sketches found in timeline!"

    total_doc_meshes = sum(occ.component.meshBodies.count for occ in root.allOccurrences) + root.meshBodies.count
    assert total_doc_meshes == 0, f"Document tree contains {total_doc_meshes} uncleaned mesh bodies!"
    print("✅ Parametric handover verified: pure BRep solid bodies with 0 mesh bodies remaining in document.")
```

---

## 9. In-CAD Camera Framing & Batch Screenshot Capture

```python
def frame_part_camera(app, comp):
    """Adjusts the active camera viewport to fit snugly around the target component."""
    viewport = app.activeViewport
    camera = viewport.camera
    camera.isFitToView = True
    camera.isSmoothTransition = False
    viewport.camera = camera

# Batch capture call list for MCP get_screenshot (execute in sequence):
# get_screenshot(view="top", width=1024, height=1024)
# get_screenshot(view="bottom", width=1024, height=1024)
# get_screenshot(view="front", width=1024, height=1024)
# get_screenshot(view="back", width=1024, height=1024)
# get_screenshot(view="left", width=1024, height=1024)
# get_screenshot(view="right", width=1024, height=1024)
# get_screenshot(view="iso-top-right", width=1024, height=1024)
# get_screenshot(view="iso-top-left", width=1024, height=1024)
```

---

## 10. High-Refinement STL Export for Quantitative Section-Diff

```python
def export_component_stl(design, comp, output_path):
    """Exports a reconstructed component as high-refinement STL for section_pack.py diff verification."""
    export_mgr = design.exportManager
    body = comp.bRepBodies.item(0)
    stl_opts = export_mgr.createSTLExportOptions(body, output_path)
    stl_opts.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    export_mgr.execute(stl_opts)
    print(f"Exported BRep solid to {output_path} for quantitative metrology diff.")
```

---

## 11. Specialized Precision Feature Recipes

### 11.1 Continuous 45° Knife-Edge / Dovetail Sliding Rail

```python
def create_45deg_sliding_rail(comp, base_body, rail_w_mm, rail_h_mm, length_mm, is_positive=True):
    """
    Creates a continuous 45-degree beveled sliding rail along the margin edge.
    Sketches a right-triangle profile on the side/end plane and extrudes along the length.
    """
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    
    # Sketch on end face / xZ plane
    sketch = sketches.add(comp.xZConstructionPlane)
    lines = sketch.sketchCurves.sketchLines
    
    w_cm = rail_w_mm / 10.0
    h_cm = rail_h_mm / 10.0
    
    p0 = adsk.core.Point3D.create(0, 0, 0)
    p1 = adsk.core.Point3D.create(w_cm, 0, 0)
    p2 = adsk.core.Point3D.create(0, 0, h_cm)
    
    lines.addByTwoPoints(p0, p1)
    lines.addByTwoPoints(p1, p2)
    lines.addByTwoPoints(p2, p0)
    
    prof = sketch.profiles.item(0)
    op = adsk.fusion.FeatureOperations.JoinFeatureOperation if is_positive else adsk.fusion.FeatureOperations.CutFeatureOperation
    ext_in = extrudes.createInput(prof, op)
    ext_in.setDistanceExtent(False, mm(length_mm))
    ext_in.participantBodies = [base_body]
    return extrudes.add(ext_in)
```

### 11.2 Raised Margin Strip with Cylindrical Guide Pins

```python
def create_margin_strip_with_pins(comp, base_body, strip_y_mm, strip_w_mm, strip_h_mm, 
                                  pin_dia_mm, pin_h_mm, pin_x_coords_mm):
    """
    Creates a raised lateral guide strip along the margin and adds an array of cylindrical guide pins.
    """
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    
    # 1. Sketch and extrude raised strip
    strip_sketch = sketches.add(comp.xYConstructionPlane)
    lines = strip_sketch.sketchCurves.sketchLines
    y0_cm = (strip_y_mm - strip_w_mm / 2.0) / 10.0
    y1_cm = (strip_y_mm + strip_w_mm / 2.0) / 10.0
    x_half_cm = (base_body.boundingBox.maxPoint.x - base_body.boundingBox.minPoint.x) / 2.0
    
    lines.addTwoPointRectangle(
        adsk.core.Point3D.create(-x_half_cm, y0_cm, 0),
        adsk.core.Point3D.create(x_half_cm, y1_cm, 0)
    )
    prof_strip = strip_sketch.profiles.item(0)
    ext_strip = extrudes.createInput(prof_strip, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_strip.setDistanceExtent(False, mm(strip_h_mm))
    ext_strip.participantBodies = [base_body]
    extrudes.add(ext_strip)
    
    # 2. Sketch guide pins on top surface
    pin_sketch = sketches.add(comp.xYConstructionPlane)
    circles = pin_sketch.sketchCurves.sketchCircles
    r_cm = (pin_dia_mm / 2.0) / 10.0
    
    for px in pin_x_coords_mm:
        center = adsk.core.Point3D.create(px / 10.0, strip_y_mm / 10.0, 0)
        circles.addByCenterRadius(center, r_cm)
        
    pin_collection = adsk.core.ObjectCollection.create()
    for prof in pin_sketch.profiles:
        pin_collection.add(prof)
        
    ext_pins = extrudes.createInput(pin_collection, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    ext_pins.setDistanceExtent(False, mm(strip_h_mm + pin_h_mm))
    ext_pins.participantBodies = [base_body]
    return extrudes.add(ext_pins)
```

### 11.3 Parallel Obround Travel Slots Array

```python
def create_parallel_obround_slots(comp, base_body, slot_w_mm, stroke_mm, slot_y_centers_mm, slot_cx_mm=0.0):
    """
    Creates multiple parallel transverse guide slots with semicircular rounded ends.
    """
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    
    sketch = sketches.add(comp.xYConstructionPlane)
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    
    r_cm = (slot_w_mm / 2.0) / 10.0
    half_stroke_cm = (stroke_mm / 2.0) / 10.0
    
    for cy_mm in slot_y_centers_mm:
        cx_cm = slot_cx_mm / 10.0
        cy_cm = cy_mm / 10.0
        
        # Semicircle centers
        p_left_center = adsk.core.Point3D.create(cx_cm - half_stroke_cm, cy_cm, 0)
        p_right_center = adsk.core.Point3D.create(cx_cm + half_stroke_cm, cy_cm, 0)
        
        # Tangent line endpoints
        p_tl = adsk.core.Point3D.create(cx_cm - half_stroke_cm, cy_cm + r_cm, 0)
        p_tr = adsk.core.Point3D.create(cx_cm + half_stroke_cm, cy_cm + r_cm, 0)
        p_bl = adsk.core.Point3D.create(cx_cm - half_stroke_cm, cy_cm - r_cm, 0)
        p_br = adsk.core.Point3D.create(cx_cm + half_stroke_cm, cy_cm - r_cm, 0)
        
        lines.addByTwoPoints(p_tl, p_tr)
        lines.addByTwoPoints(p_bl, p_br)
        arcs.addByCenterStartSweep(p_left_center, p_bl, math.pi)
        arcs.addByCenterStartSweep(p_right_center, p_tr, math.pi)
        
    slot_collection = adsk.core.ObjectCollection.create()
    for prof in sketch.profiles:
        slot_collection.add(prof)
        
    cut_in = extrudes.createInput(slot_collection, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_in.setDistanceExtent(False, mm(20.0)) # through-all cut
    cut_in.participantBodies = [base_body]
    return extrudes.add(cut_in)
```

### 11.4 Recessed Card Pocket with Perimeter Bezel & Finger Access Hole

```python
def create_card_pocket_and_finger_hole(comp, base_body, pocket_w_mm, pocket_l_mm, pocket_depth_mm, 
                                       hole_dia_mm, z_top_mm):
    """
    Creates a recessed Instax photo card pocket bounded by raised perimeter bezels,
    plus a central through-hole for finger ejection.
    """
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures
    planes = comp.constructionPlanes
    
    # Construction plane at pocket base
    p_input = planes.createInput()
    p_input.setByOffset(comp.xYConstructionPlane, mm(z_top_mm - pocket_depth_mm))
    pocket_plane = planes.add(p_input)
    
    # 1. Pocket cutout
    sketch_pocket = sketches.add(comp.xYConstructionPlane)
    w_half = (pocket_w_mm / 2.0) / 10.0
    l_half = (pocket_l_mm / 2.0) / 10.0
    sketch_pocket.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(-w_half, -l_half, 0),
        adsk.core.Point3D.create(w_half, l_half, 0)
    )
    prof_pocket = sketch_pocket.profiles.item(0)
    cut_pocket = extrudes.createInput(prof_pocket, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_pocket.setDistanceExtent(False, mm(pocket_depth_mm))
    cut_pocket.participantBodies = [base_body]
    extrudes.add(cut_pocket)
    
    # 2. Central finger ejection hole
    sketch_hole = sketches.add(comp.xYConstructionPlane)
    sketch_hole.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(0, 0, 0), 
        mm(hole_dia_mm / 2.0)
    )
    prof_hole = sketch_hole.profiles.item(0)
    cut_hole = extrudes.createInput(prof_hole, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut_hole.setDistanceExtent(False, mm(z_top_mm + 5.0)) # cut completely through bottom
    cut_hole.participantBodies = [base_body]
    return extrudes.add(cut_hole)
```
