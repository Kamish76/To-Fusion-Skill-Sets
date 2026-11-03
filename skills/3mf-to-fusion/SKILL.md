---
name: 3mf-to-fusion
description: Advanced CAD reverse-engineering engine for 3MF and STL files. Stages raw meshes in-CAD for multi-perspective inspection, slices and dices geometry (cross sections, true circumscribed circle radii, obround slots, hex pockets, turned profiles, pattern arrays), and synthesizes 100% native, editable parametric BRep solid bodies in Autodesk Fusion 360 via the Fusion 360 MCP server with translucent ghost overlay verification.
---

# 3MF / STL to Fusion 360 Analytical Reverse-Engineering Skill

When asked to copy, reverse-engineer, or recreate a `.3mf` or `.stl` file in Autodesk Fusion 360, follow this deterministic analytical pipeline.

---

## THE CAD REVERSE-ENGINEERING MANDATES

### Mandate 1: Strictly Forbidden — Convert Mesh to Solid (`MeshToBREP` / `bRepBodies.addByMesh`)
> [!IMPORTANT]
> **STRICTLY FORBIDDEN**: Never use Fusion 360's built-in "Convert Mesh to Solid" (`MeshToBREP` or `bRepBodies.addByMesh`). 
> 
> Converting mesh facets directly into BRep creates tens of thousands of planar triangular faces that freeze the viewport, cannot be filleted or chamfered, break downstream CAM/drawings, and destroy all parametric design intent.
> 
> **MANDATORY**: Dissect the mesh mathematically ("slice and dice"), extract its 2D cross sections and geometric primitives (slots, circumscribed holes, counterbores, turned profiles, rectangular patterns), and construct **100% native parametric solid bodies** in the Fusion 360 timeline using sketches, driving user parameters, extrusions, revolves, and pattern features.

### Mandate 2: Strict Ban on Marketing / Thumbnail Photo Reliance
> [!CAUTION]
> **STRICT MANDATE**: *Never infer geometry, mechanisms, or clearances from photos or thumbnail images found inside the 3MF archive. Ground truth is exclusively defined by the STL mesh files.*
> 
> Embedded 3MF thumbnails and slicer preview images (`Metadata/`, `Auxiliaries/`, `.webp`, `.png`, `.jpg`) frequently depict finished, user-decorated prints with arbitrary cosmetic mods, custom paint, non-standard aftermarket hardware, or deceptive camera lens perspective distortion and internal occlusions. 
> 
> Inferring mechanical features, travel stops, detents, or datum orientations from marketing photos causes catastrophic hallucinations and broken CAD models. **Ground truth is exclusively defined by the raw extracted mesh geometry (`.stl`).**

---

## Phase 0: Pre-Flight Safety Gate (Mandatory)
Before processing files, verify that Autodesk Fusion 360 and its MCP server are live:

1. **Canary Probe**:
   Call `fusion-mcp` tool `execute_api_script`:
   ```python
   def run(context):
       import adsk.core, adsk.fusion
       app = adsk.core.Application.get()
       if not app:
           raise RuntimeError("Autodesk Fusion 360 application instance not found.")
       design = adsk.fusion.Design.cast(app.activeProduct)
       if not design:
           raise RuntimeError("No active Fusion 360 design document open.")
       print("FUSION_MCP_READY")
   ```

2. **Fail-Fast Abort Rule**:
   - If the call fails or times out, **STOP immediately**.
   - Do NOT run extraction scripts or CAD commands.
   - Instruct the user to open Fusion 360, ensure the add-in is started, and open an active document.

---

## Phase 1: In-CAD Mesh Staging & Multi-Perspective Capture (Mandatory)

Before writing any solid reconstruction code or guessing dimensions, import the extracted raw STL meshes directly into Autodesk Fusion 360 for in-situ visualization and metrology.

### 1. In-CAD Mesh Staging
Import the raw STL mesh into an isolated staging component (`Reference_Meshes_Staging`) via `execute_api_script`:

```python
import adsk.core, adsk.fusion

app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
root = design.rootComponent

# 1. Create dedicated isolated reference staging occurrence
ref_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
ref_comp = ref_occ.component
ref_comp.name = "Reference_Meshes_Staging"

# 2. Import raw STL mesh as base feature
base_feat = ref_comp.features.baseFeatures.add()
base_feat.startEdit()
mesh_bodies = ref_comp.meshBodies.add(
    stl_path, 
    adsk.fusion.MeshUnits.MillimeterMeshUnit, 
    base_feat
)
base_feat.finishEdit()

print(f"Staged {mesh_bodies.count} mesh bodies in Reference_Meshes_Staging")
```

### 2. Multi-Perspective Visual Capture
Immediately capture orthographic and isometric screenshots of each raw mesh component directly in Fusion 360 using `get_screenshot`:
- `view="top"`
- `view="front"`
- `view="right"`
- `view="iso-top-right"`

Inspect these captures to visually determine:
- True tessellation boundaries, parting lines, and draft angles.
- Internal undercuts, pockets, and hollow chambers.
- Mechanical travel limits, guide rails, and pin stops.
- True primary coordinate datum (e.g. build plate flat face vs. axis of symmetry).

---

## Phase 2: In-CAD Metrology & Deep Slice Analysis

Never guess mechanical dimensions or rely on external visual estimates. Combine direct in-CAD API queries with the deep slicing engine.

### 1. In-CAD Direct Mesh Metrology
Directly query the staged mesh geometry via `execute_api_script`:
- **Bounding Box Extents**:
  ```python
  # Note: Fusion 360 API bounding boxes return values in centimeters (cm)
  bbox = mesh_body.boundingBox
  dx_mm = (bbox.maxPoint.x - bbox.minPoint.x) * 10.0
  dy_mm = (bbox.maxPoint.y - bbox.minPoint.y) * 10.0
  dz_mm = (bbox.maxPoint.z - bbox.minPoint.z) * 10.0
  print(f"Exact Mesh Extents: {dx_mm:.2f} x {dy_mm:.2f} x {dz_mm:.2f} mm")
  ```
- **Internal Cross-Section Slicing**:
  Create temporary construction planes (`comp.constructionPlanes`) through midpoints and critical heights, then project silhouette or cross-section cut edges to measure internal wall thicknesses, slot widths, and travel stop locations.

### 2. Deep Slicing Engine (`inspect_3mf.py`)
Run the metrology engine to extract mathematical primitives into the model's isolated workspace:

> [!IMPORTANT]
> **Workspace Isolation Rule**: Never output extraction files into the main repo root (e.g. `./extracted_cad` is forbidden). Always ensure a dedicated model folder exists under `models/<NN>_<Model_Name>/` (scaffold with `scaffold_text_model.py "<Model_Name>"` if new), and route all slice/dice outputs into `models/<NN>_<Model_Name>/workspace/extracted_cad`.

```bash
python3 <path_to_skills>/3mf-to-fusion/scripts/inspect_3mf.py <path_to_file.3mf_or_stl> --out-dir models/<NN>_<Model_Name>/workspace/extracted_cad
```

Read `models/<NN>_<Model_Name>/workspace/extracted_cad/manifest.json` and classify the archetype:
- **Type A: Prismatic / Stepped CAD**: Planar base extrusion + pocket cuts + hole arrays.
- **Type T: Turned / Axisymmetric**: Collinear circular slices along Z axis. Modeled using a single half-profile sketch + 360° `RevolveFeature`.
- **Type B: Multi-tier Enclosure / Shell**: Stepped construction planes + thin-wall extrusions + shell.
- **Type C: Organic Freeform Sculpture**: High non-planar curvature ($> 15$ tiers). Immediately alert the user:
  > *"This part is a continuous organic sculpture without discrete planar faces or prismatic sketches. Reconstructing it using planar sketches will generate a stepped staircase approximation rather than a smooth organic sculpt."*

Present a summary table to the user:
| Part ID | Archetype | Bounding Box ($X \times Y \times Z\text{ mm}$) | Tiers | Key Primitives / Patterns Detected |
| :--- | :--- | :--- | :--- | :--- |

### 3. Metrology Mathematics & Compensation Rules
1. **Unit Conversion (`cm = mm / 10.0`)**:
   - Fusion 360's internal database (`adsk.core.ValueInput.createByReal()`) strictly uses **centimeters (`cm`)**.
   - Define at the top of every script:
     ```python
     def mm(val): return adsk.core.ValueInput.createByReal(float(val) / 10.0)
     ```
2. **Circumscribed Circle Compensation (Chord Error)**:
   - STL tessellations approximate circular holes with inscribed polygons whose edges cut inward along chords.
   - Never use the inner minimum diameter. Always use `radius_mm` from `manifest.json["primitives"]["circles"]` (95th-percentile circumscribed radius) rounded to the nearest $0.05\text{ mm}$.
3. **Slot / Obround Recognition**:
   - When loops have two parallel straight lines and two semicircular ends, model them as a seed slot (`sketchLines` + `sketchArcs`) rather than a multi-segment polygon.
4. **Pattern Recognition (Grid / Polar)**:
   - When `manifest.json["patterns"]` detects a regular pitch ($\Delta X, \Delta Y$), model **one master seed cutout** and duplicate it using `comp.features.rectangularPatternFeatures`. Do not draw repetitive identical geometry by hand.

---

## Phase 3: Pure Parametric Fusion 360 Reconstruction

Execute CAD generation via `execute_api_script`. Reconstruct each part directly over or aligned with the staged reference mesh bodies using clean timeline features:

### Step 1: Occurrence & Driving Parameters
```python
transform = adsk.core.Matrix3D.create()
occ = root.occurrences.addNewComponent(transform)
comp = occ.component
comp.name = part_name

# Add Driving Parameters
params = design.userParameters
params.add(f"{part_name}_width", mm(width_mm), "mm", "Base width")
params.add(f"{part_name}_length", mm(length_mm), "mm", "Base length")
params.add(f"{part_name}_height", mm(height_mm), "mm", "Base height")
```

### Step 2: Primary Solid Geometry
- **If Type T (Turned)**: Sketch half-profile on `comp.xZConstructionPlane` and call `comp.features.revolveFeatures.add(prof, comp.zConstructionAxis, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)`.
- **If Type A/B (Prismatic)**: Sketch base outline on `comp.xYConstructionPlane` (aligned with reference staging coordinates) and extrude base solid.

### Step 3: Secondary Cutouts & Patterns
- Draw master seed cutout (slot, counterbore, or pocket).
- Apply `comp.features.extrudeFeatures.add` with `adsk.fusion.FeatureOperations.CutFeatureOperation`.
- Apply `comp.features.rectangularPatternFeatures.add` across `comp.xConstructionAxis` and `comp.yConstructionAxis`.

### Step 4: Finishing Touches
- Apply corner fillets (`comp.features.filletFeatures`) and chamfers (`comp.features.chamferFeatures`).

---

## Phase 4: 1:1 Translucent Ghost Overlay Verification

To guarantee 1:1 fidelity with the physical mesh without guessing:

1. **Apply Translucent Ghost Override**:
   Set a 50% opacity override on the staged reference occurrence to create a translucent ghost mesh overlay over the newly reconstructed solid body:
   ```python
   # Apply 50% opacity translucent override to staging occurrence
   ref_occ.opacity = 0.5
   ```

2. **Multi-Perspective Visual Overlay Inspection**:
   Capture overlay screenshots (`get_screenshot`) across key inspection angles:
   - `view="iso-top-right"`
   - `view="front"`
   - `view="top"`
   - `view="right"`

3. **Verify Critical Alignment Criteria**:
   - **Feature Envelope**: Solid body completely encompasses or perfectly aligns with the mesh silhouette.
   - **Clearances & Travel Limits**: Mounting tabs, hinge clearances, and sliding stops align within nominal 3D printing tolerances ($0.20\text{--}0.40\text{ mm}$).
   - **Zero Inversion**: Fillets and chamfers curve inward/outward in exact accordance with the ghost mesh contour.

---

## Phase 5: Clean Timeline Handover & Health Gate

Once verification passes, clean up the staging component and assert complete timeline integrity:

### 1. Clean Staging Removal
Delete or suppress `Reference_Meshes_Staging` so only pure parametric solid geometry remains in the active design tree:
```python
# Clean Timeline Handover: Delete staging occurrence
ref_occ.deleteMe()
```

### 2. Strict Timeline Assertions
Assert that the reconstructed component contains native parametric solid bodies and zero mesh bodies:
```python
# Assert clean parametric handover
assert comp.bRepBodies.count > 0, "No solid bodies produced!"
assert comp.meshBodies.count == 0, "Forbidden MeshBody detected in component!"
assert comp.sketches.count > 0, "No sketches found in timeline!"
print("✅ Parametric handover verified: pure BRep solid bodies with clean timeline history.")
```

### 3. Final Model Screenshot
Call `get_screenshot(view="iso-top-right", width=1024, height=1024)` to verify the final solid model and timeline appearance.
