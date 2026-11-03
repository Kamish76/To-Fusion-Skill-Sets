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
