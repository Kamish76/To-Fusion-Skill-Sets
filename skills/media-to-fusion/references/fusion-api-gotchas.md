# Autodesk Fusion 360 API Gotchas & High-Performance Patterns

Verified solutions to non-obvious Fusion 360 Python API traps discovered during autonomous CAD scripting.

---

## 1. Animation Performance: Timeline Bloat vs. Occurrence Transforms

### The Trap
Calling `component.features.moveFeatures.add()` inside a frame loop recalculates the entire parametric timeline. 30 frames takes ~70 seconds and pollutes the timeline history with 30 useless features.

### The Solution
Isolate moving bodies into dedicated `Occurrence` instances (`anim_occ = parent.occurrences.addNewComponent(Matrix3D.create())`) and assign their affine matrix directly:
```python
trans = adsk.core.Matrix3D.create()
trans.translation = adsk.core.Vector3D.create(dx * s, dy * s, dz * s)
anim_occ.transform = trans
vp.refresh()
vp.saveAsImageFile(frame_path, 800, 800)
```
- **Performance:** Runs in **`0.005 s/update`** directly in the scene graph. 30 frames renders in under 4 seconds!

---

## 2. Occurrence Visibility Inheritance vs. Underground Templates

### The Trap
When instancing hardware components (e.g. screws and nuts) from a template occurrence, setting `template_occ.isLightBulbOn = False` causes all child instances in the assembly to become invisible (`visible = False`).

### The Solution
Keep `template_occ.isLightBulbOn = True`, but translate the master template occurrence far underground out of camera frame (`Z = -500.0 cm`):
```python
t_hide = adsk.core.Matrix3D.create()
t_hide.translation = adsk.core.Vector3D.create(0, 0, -500.0) # cm
template_occ.transform = t_hide
```

---

## 3. Extrude Cut Target Body Participants

### The Trap
Calling `ExtrudeFeatures.add` with `FeatureOperations.CutFeatureOperation` fails with:
`RuntimeError: No target body found to cut or intersect!`.

### The Solution
Explicitly pass the intended body to `participantBodies`:
```python
cut_input = comp.features.extrudeFeatures.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
cut_input.participantBodies = [target_body]
cut_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(depth_cm))
comp.features.extrudeFeatures.add(cut_input)
```

---

## 4. Plane-Independent 3D Sketch Mapping

### The Trap
Placing sketch circles or lines on `YZ` or `XZ` construction planes using raw 3D coordinates causes inverted or mirrored geometry due to differing sketch UV axis directions.

### The Solution
Always map 3D world points into sketch space via:
```python
sketch_point = sk.modelToSketchSpace(adsk.core.Point3D.create(cm(x), cm(y), cm(z)))
sk.sketchCurves.sketchCircles.addByCenterRadius(sketch_point, cm(radius_mm))
```
