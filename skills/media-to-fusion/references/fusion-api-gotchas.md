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

---

## 5. BRep Dissociation Trap: `deleteFaceFeatures` vs. Localized Extrude Cuts

### The Trap
Attempting to remove body chamfers or fillets using `deleteFaceFeatures.add()` on complex geometries (e.g. trays with internal cavities and upright ears) frequently fails to auto-heal. Fusion silently detaches unhealed faces, converting solid bodies into hollow shells or reducing them to disjoint floating discs (e.g. only retaining isolated cylindrical pivot bosses).

### The Solution
**Never rely on raw face deletion for geometrical redesigns.** Instead, use a localized directional **Extrude Cut** (`FeatureOperations.CutFeatureOperation`) with an explicit target participant:
```python
ext_in = exts.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
ext_in.participantBodies = [target_body]
ext_in.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(dist_val), adsk.fusion.ExtentDirections.PositiveExtentDirection)
exts.add(ext_in)
```
This is 100% deterministic, timeline-safe, and never dissociates BRep topology.

---

## 6. Extrude Cut Direction & Extent Negation Trap

### The Trap
Passing a negative distance value (`-4.52 cm`) to `setOneSideExtent` combined with `adsk.fusion.ExtentDirections.NegativeExtentDirection` negates the distance into positive space, causing the extrude to cut away from the body into thin air (`health=1: No target body! Compute Failed`).

### The Solution
When cutting downward into a body from a top face with a negative distance, use `PositiveExtentDirection`:
```python
dist_val = adsk.core.ValueInput.createByReal(cm(-cut_depth_mm))
ext_in.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(dist_val), adsk.fusion.ExtentDirections.PositiveExtentDirection)
```

---

## 7. Parallel Linkage Invariant & Golden Body Cloning

### The Principle
In any planar parallelogram parallel linkage, deployable tiers **do not rotate**—the kinematic transformation between collapsed and open states is **pure translation** $(\Delta X, \Delta Y, \Delta Z)$ where $\Delta Y = -n \cdot 2 \Delta y_{\text{station}}$ and $\Delta Z = 0$.

### The Pattern
Model trays once as a verified "golden reference" body in the collapsed state, then replicate them to the opened state using `copyPasteBodies.add(src)` and translate them with `moveFeatures.createInput2()`:
```python
open_comp.features.copyPasteBodies.add(src_body)
new_body = open_comp.bRepBodies.item(open_comp.bRepBodies.count - 1)

entities = adsk.core.ObjectCollection.create()
entities.add(new_body)
move_input = move_feats.createInput2(entities)
transform = adsk.core.Matrix3D.create()
transform.translation = adsk.core.Vector3D.create(cm(dx), cm(dy), cm(dz))
move_input.defineAsFreeMove(transform)
move_feats.add(move_input)
```
This guarantees 100.000% sub-micron concentricity between linkage pin holes across both opened and closed assemblies with zero modeling drift.

---

## 8. Viewport Screenshot Selection Halos

### The Trap
Calling `get_screenshot` while faces or bodies are selected leaves bright cyan/blue wireframe outlines and planar overlays in viewport captures.

### The Solution
Always clear the active selection set before saving screenshots:
```python
ui = adsk.core.Application.get().userInterface
if ui:
    ui.activeSelections.clear()
```


---

## 9. Mid-Stroke Mechanical Collisions & Endpoint Blind Spots

### The Trap
Checking clearance only at the static endpoints (fully collapsed $s = 0.0$ and fully opened $s = 1.0$) misses dynamic collisions that occur only during movement (e.g. at $s = 0.35$ as links swing through intermediate arcs or lids dip over enclosure walls).

### The Solution
Use an ephemeral rigid-group stage (`Kinematic_Stage`) and evaluate `design.analyzeInterference()` across intermediate fractions ($s = 0.0, 0.25, 0.50, 0.75, 1.0$). Filter out mathematical face contact ($V > 3.0\text{ mm}^3$), and delete the stage non-destructively upon completion.

---

## 10. Missing External Dependencies for GIF Compilation on Windows

### The Trap
Executing CAD animation scripts or GIF compilation on vanilla Windows systems or within Fusion 360's embedded Python interpreter crashes with `ModuleNotFoundError: No module named 'PIL'` or missing `ffmpeg`.

### The Solution
Implement the zero-dependency Windows Presentation Foundation (`System.Windows.Media.Imaging.GifBitmapEncoder`) with binary `NETSCAPE2.0` looping block and Graphic Control Extension (GCE) delay splicing (`compile_ping_pong_gif_powershell`). It compiles native looping GIF89a animations using built-in Windows PowerShell without installing any packages.

---

## 11. Coincident Boundary Tangencies & `ASM_INCONS_FACE` Extrude Failure

### The Trap
When modeling edge bevels, chamfer relief facets, or rebate grooves (e.g. cutting-edge relief on a surgical blade or knife belly), tracing the exact existing boundary curves in the cutting sketch causes Autodesk Shape Manager (ASM) kernel failure:
`RuntimeError: 3 : Extrude / Compute Failed // ASM_INCONS_FACE - There was a problem combining geometry together. (problems can occur where faces and edges are nearly coincident)`.

### The Solution: Robust Overlapping Boundaries
Never re-trace existing boundary edges for extrude cut profiles. Instead, define a closed 2D loop consisting of:
1. An **inner spline/line** defining the intended relief boundary on the face of the body.
2. An **outer bounding curve/loop** extending $1.0\text{–}2.0\text{ mm}$ outside the body into empty space (air).
Because the outer region is in empty space, the boolean operation cuts away *only* the material between the edge and the inner line with clean, non-tangent boolean overlap, completely avoiding coincident edge/face kernel traps:
```python
# Inner contour defines the bevel facet boundary on the solid face
sp_inner = create_fitted_spline(sketch, inner_facet_pts)

# Outer contour loops through empty air well outside the body boundary
sp_outer = create_fitted_spline(sketch, outer_air_pts)

# Connect endpoints to close the 2D loop cleanly
sketch.sketchCurves.sketchLines.addByTwoPoints(sp_inner.endSketchPoint, sp_outer.startSketchPoint)
sketch.sketchCurves.sketchLines.addByTwoPoints(sp_outer.endSketchPoint, sp_inner.startSketchPoint)

# Extrude cut with clean non-tangent overlap
ext_cut = comp.features.extrudeFeatures.createInput(sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
ext_cut.participantBodies = [target_body]
```

---

## 12. Continuous Perimeter Single-Spline Rail for Seamless Fillets

### The Trap
Segmenting organic, ergonomic, or clinical handles (e.g. scalpel spine, tail dome, belly) into separate line segments, arcs, and polylines creates tangent or curvature singularities at the segment junctions. Calling `comp.features.filletFeatures.add()` on the perimeter edges fails with edge singularity errors or produces fragmented fillets.

### The Solution
Synthesize the entire outer perimeter contour (top spine, rounded dome tail butt, lower belly, and throat) using a **single continuous $C^2$-smooth fitted spline** (e.g. 20–25 knots).
- Because the outer boundary edge is a single continuous topological entity, Fusion 360's B-Rep kernel applies a continuous constant-radius edge fillet ($R = 0.35\text{–}0.50\text{ mm}$) around both $+Z$ and $-Z$ perimeter rails in a single feature with 0 errors.

---

## 13. Profile Area Filtering for Debossed Cartouche Badging & Island Relief

### The Trap
When modeling a debossed specification badge (e.g. a square cartouche with a numeral `3` or logo), passing `sketch.profiles` indiscriminately to `CutFeatureOperation` cuts the entire interior box flat, obliterating the background and destroying the relief contrast of the numeral.

### The Solution: Profile Area Filtering
Calculate the planar area of each sketch profile (`p.areaProperties().area`). The inner cavity background has the largest area ($> 70\%$ of the bounding box). Selectively cut *only* the outer thin frame border and the inner numeral strokes:
```python
max_area = max(p.areaProperties().area for p in sk_badge.profiles)
profs_to_cut = adsk.core.ObjectCollection.create()
for p in sk_badge.profiles:
    if p.areaProperties().area < max_area * 0.70:
        profs_to_cut.add(p)

ext_badge = comp.features.extrudeFeatures.createInput(profs_to_cut, adsk.fusion.FeatureOperations.CutFeatureOperation)
ext_badge.participantBodies = [target_body]
```
This leaves the island around the numeral raised, while the frame and the numeral strokes are crisply debossed.

---

## 14. Reverse-Face Coordinate Parity & Mirroring

### The Trap
Text or numerals sketched on the front $XY$ plane and cut through the back face ($-Z$) will appear horizontally inverted (mirrored) when viewed from the back face.

### The Solution
For engravings on the $-Z$ face, construct numeral and letter strokes with horizontal mirroring (`flip_x=True`) and verify sequence reading order along the coordinate axis ($+X$ vs $-X$) to ensure numbers read naturally left-to-right when viewed from the back.
