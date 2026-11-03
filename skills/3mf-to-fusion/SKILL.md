---
name: 3mf-to-fusion
description: Advanced CAD reverse-engineering engine for 3MF and STL files. Slices, dices, and mathematically inspects raw meshes (cross sections, true circumscribed circle radii, obround slots, hex pockets, turned profiles, and pattern arrays), and synthesizes 100% native, editable parametric BRep solid bodies in Autodesk Fusion 360 via the Fusion 360 MCP server.
---

# 3MF / STL to Fusion 360 Analytical Reverse-Engineering Skill

When asked to copy, reverse-engineer, or recreate a `.3mf` or `.stl` file in Autodesk Fusion 360, follow this deterministic analytical pipeline.

## THE CAD REVERSE-ENGINEERING MANDATE
> [!IMPORTANT]
> **STRICTLY FORBIDDEN**: Never use Fusion 360's built-in "Convert Mesh to Solid" (`MeshToBREP` or `bRepBodies.addByMesh`). 
> 
> Converting mesh facets directly into BRep creates tens of thousands of planar triangular faces that freeze the viewport, cannot be filleted or chamfered, break downstream CAM/drawings, and destroy all parametric design intent.
> 
> **MANDATORY**: Dissect the mesh mathematically ("slice and dice"), extract its 2D cross sections and geometric primitives (slots, circumscribed holes, counterbores, turned profiles, rectangular patterns), and construct **100% native parametric solid bodies** in the Fusion 360 timeline using sketches, driving user parameters, extrusions, revolves, and pattern features.

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

## Phase 1: Slice, Dice & Classify (Metrology Engine)

> [!IMPORTANT]
> **Workspace Isolation Rule**: Never output extraction files into the main repo root (e.g. `./extracted_cad` is forbidden). Always ensure a dedicated model folder exists under `models/<NN>_<Model_Name>/` (scaffold with `scaffold_text_model.py "<Model_Name>"` if new), and route all slice/dice outputs into `models/<NN>_<Model_Name>/workspace/extracted_cad`.

1. Execute the deep metrology engine into the model's isolated workspace:
   ```bash
   python3 <path_to_skills>/3mf-to-fusion/scripts/inspect_3mf.py <path_to_file.3mf_or_stl> --out-dir models/<NN>_<Model_Name>/workspace/extracted_cad
   ```
2. Read `models/<NN>_<Model_Name>/workspace/extracted_cad/manifest.json`.
3. Check the `archetype` and detected features for each part:
   - **Type A: Prismatic / Stepped CAD**: Planar base extrusion + pocket cuts + hole arrays.
   - **Type T: Turned / Axisymmetric**: Collinear circular slices along Z axis. Modeled using a single half-profile sketch + 360° `RevolveFeature`.
   - **Type B: Multi-tier Enclosure / Shell**: Stepped construction planes + thin-wall extrusions + shell.
   - **Type C: Organic Freeform Sculpture**: High non-planar curvature ($> 15$ tiers). Immediately alert the user:
     > *"This part is a continuous organic sculpture without discrete planar faces or prismatic sketches. Reconstructing it using planar sketches will generate a stepped staircase approximation rather than a smooth organic sculpt."*

4. Present a summary table to the user:
   | Part ID | Archetype | Bounding Box ($X \times Y \times Z\text{ mm}$) | Tiers | Key Primitives / Patterns Detected |
   | :--- | :--- | :--- | :--- | :--- |

---

## Phase 2: Metrology Mathematics & Rules

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

Execute CAD generation via `execute_api_script`. Reconstruct each part using clean timeline features:

### Step 1: Occurrence & User Parameters
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
- **If Type A/B (Prismatic)**: Sketch base outline on `comp.xYConstructionPlane` (centered at origin) and extrude base solid.

### Step 3: Secondary Cutouts & Patterns
- Draw master seed cutout (slot, counterbore, or pocket).
- Apply `comp.features.extrudeFeatures.add` with `adsk.fusion.FeatureOperations.CutFeatureOperation`.
- Apply `comp.features.rectangularPatternFeatures.add` across `comp.xConstructionAxis` and `comp.yConstructionAxis`.

### Step 4: Finishing Touches
- Apply corner fillets (`comp.features.filletFeatures`) and chamfers (`comp.features.chamferFeatures`).

---

## Phase 4: Reference Ghost Overlay & In-CAD Inspection

To verify mathematical and dimensional alignment without polluting the final model:

1. **Ghost Reference Mesh (Optional)**:
   If detailed visual alignment is needed, import the raw mesh into a separate temporary reference occurrence:
   ```python
   # Import mesh as reference backdrop
   ref_occ = root.occurrences.addNewComponent(transform)
   ref_occ.component.name = "Reference_Mesh_Ghost"
   # Set transparent visual style
   ```
2. **Visual & Interference Inspection**:
   - Check that the parametric solid completely encompasses and aligns with the mesh envelope.
   - Once verified, hide or remove `ref_occ`.

---

## Phase 5: Timeline Health & Visual Self-Verification Gate

1. **Timeline Feature Verification**:
   Ensure zero mesh bodies exist in the reconstructed part:
   ```python
   assert comp.bRepBodies.count > 0, "No solid bodies produced!"
   assert comp.meshBodies.count == 0, "Forbidden MeshBody detected in component!"
   assert comp.sketches.count > 0, "No sketches found in timeline!"
   ```
2. **Visual Inspection**:
   Call `get_screenshot(view="iso-top-right", width=1024, height=1024)` to visually verify the clean parametric solid model and the clean timeline tree.
