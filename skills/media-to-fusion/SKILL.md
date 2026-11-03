---
name: media-to-fusion
description: Converts images, multi-angle photo sets, technical drawings, or videos of mechanical/physical objects into functional, parametric 3D CAD models and assemblies in Fusion 360 via computer vision metrology, kinematic synthesis, and the Fusion 360 MCP server.
---

# Media (Image / Video / Reference Pack) to Fusion 360 Reconstruction Skill

When the user provides a photo, a multi-angle reference folder, or a video (`.mp4`, `.mov`, `.png`, `.jpg`, `.webp`) and asks to recreate the object in Autodesk Fusion 360, follow this **6-phase deterministic engineering workflow**.

**STRICT CAD MANDATE**:
- Never jump straight to writing Fusion MCP extrusions without running `process_media.py`, establishing a real-world millimeter scale datum, and writing out a Kinematic Bill of Materials (BOM).
- Every component must be reconstructed using native **Sketches**, **Construction Planes**, **Sketch Lines/Arcs/Circles**, **User Parameters**, and **Extrude/Fillet/Joint Features** in the Fusion 360 timeline. Never generate raw mesh bodies (`root.meshBodies.add`).

---

## Phase 0: Pre-Flight Safety Gate & Monorepo Environment (Mandatory)
Before creating CAD geometry in Fusion 360, align your workspace and verify live MCP connectivity:

1. **CAD Monorepo Alignment**:
   - Primary workspace: Active CAD monorepo or project root (e.g., `CAD_MONOREPO_ROOT` or current workspace).
   - **Strict Isolation Guarantee:** Never create temporary files, scripts, or renders in the repository root or mutate `shared/`.
   - Store new models under `models/<NN>_<Model_Name>/` (e.g. `models/02_Modular_Desk_Organizer/`). If starting a new model, scaffold with `scaffold_text_model.py "<Model_Name>"`.
   - Import universal CAD helpers from `shared/` (`fusion_client`, `cad_primitives`, `hardware_library`, `scene_animator`).
   - Read domain reference memory before writing scripts:
     - `references/kinematic-archetypes.md` (verified mechanism equations)
     - `references/fdm-hardware-tolerances.md` (print clearances & fastener counterbores)
     - `references/fusion-api-gotchas.md` (high-speed animation & API fixes)

2. **Canary Probe**:
   Call `fusion-mcp` tool `execute_api_script` with:
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
3. **Fail-Fast Rule**:
   - You may run Phase 1–3 media metrology while Fusion 360 is closed, but if `FUSION_MCP_READY` fails before Phase 4, **STOP before sending CAD build scripts** and instruct the user to open Fusion 360 with an active design document.

---

## Phase 1: Media Ingestion & Keyframe / Contour Extraction

> [!IMPORTANT]
> **Workspace Isolation Rule**: Never output media processing files into the main repo root (e.g. `./media_workspace` is forbidden). Always ensure a dedicated model folder exists under `models/<NN>_<Model_Name>/`, and route all media processing into `models/<NN>_<Model_Name>/workspace/media`.

1. Execute the preprocessing and metrology engine on the input image, video, or directory into the model's isolated workspace:
   ```bash
   python3 <path_to_skills>/media-to-fusion/scripts/process_media.py "<input_media_or_folder_path>" --out-dir models/<NN>_<Model_Name>/workspace/media
   ```
2. Inspect `models/<NN>_<Model_Name>/workspace/media/media_manifest.json` and view the generated visual artifacts with `read_file`:
   - **For Reference Folders**: View `dataset_overview.png` first, then inspect individual sub-workspaces (`models/<NN>_<Model_Name>/workspace/media/<slug>/`).
   - **For Videos**: View `contact_sheet.png` and individual `keyframe_XX_grid.png` files (automatically filtered to reject black fade-ins, motion blur, and hand wipes while capturing collapsed, mid-swing, and deployed kinematic states).
   - **For Images**: View `annotated_grid.png` (dual-contrast 100px major / 50px minor pixel ruler grid) and `contours_preview.png` (detected Canny contours + slot/hole centroids and median same-row pixel pitch).
   - **Split-Screen Check**: Check `viewport_layout.is_split` in `media_manifest.json` (e.g., side-by-side Front and Right orthographic views in a single image) so pixel spans are measured inside each sub-viewport independently.

---

## Phase 2: Multi-Tier Scale Calibration (Finding the "Golden Datum")
Before modeling anything, establish the real-world millimeter scale (`mm_per_px`) using this strict priority hierarchy:

1. **Priority 1 — Explicit Dimension Callouts or Build-Plate Constraints in Media**:
   - Check reference images for dimension callout arrows (e.g., overall width `35 cm / 350 mm`, height `63 cm / 630 mm`, depth `32 cm / 320 mm`, or inset inner tray callouts like `330 x 100 x 70 mm`).
   - Check for 3D printer build-plate callouts (e.g., `"FOR 220 x 220 mm PRINTERS"` $\rightarrow$ maximum single-piece width/length is typically `200–210 mm`).
2. **Priority 2 — Standard Ecosystem & Hardware Features Visible in Frame**:
   - **IKEA Skådis Pegboard Pattern**:
     - Horizontal same-row slot pitch (center-to-center): **`40.0 mm`**
     - Vertical row-to-row pitch: **`20.0 mm`** (alternate rows staggered horizontally by **`20.0 mm`**)
     - Slot dimensions: **`5.0 mm` wide $\times$ `15.0 mm` tall** (stadium/obround slot: `10.0 mm` straight vertical center-to-center with `R = 2.5 mm` full-round ends)
     - Standard board thickness: **`5.0 mm`** (`3.2 mm – 4.0 mm` on 3D-printed modular pegboard panels)
   - **Electronics & Mechanical Hardware**:
     - Mechanical keyboard MX switch cutout: `14.0 x 14.0 mm` (1u keycap pitch = `19.05 mm`)
     - Standard smartphone width (e.g., when shown resting on a stand): `~71.5 mm`
     - USB-C receptacle opening: `8.94 x 3.26 mm`
     - Fasteners: M3 socket head cap diameter = `5.5 mm` (clearance hole = `3.2–3.4 mm`), M4 head = `7.0 mm`
3. **Priority 3 — Ergonomic / Hand Reference**:
   - If human hands hold the part and no hardware datum exists, use average adult thumb width (`~20.0 mm`) or palm breadth (`~85.0 mm`), and expose the overall width as a master Fusion User Parameter (`Tray_Width`) so the user can rescale in one click.

---

## Phase 3: Kinematic & Structural Decomposition (BOM)
Decompose the assembly into a structured **Component Bill of Materials (BOM)** before writing any Fusion MCP script:

1. **Classify Fixed vs. Moving Components**:
   - **Fixed Base / Frame Components**: e.g., `Top_Anchor_Tray`, `Rear_Support_Legs` (extending down to ground plane $Z = 0$), and `Backboard_Pegboard_Panels`.
   - **Driven / Coupler Components**: e.g., `Stepped_Trays` (Tier 2..N), sliding drawers, or rotating doors.
   - **Linkage / Constraint Components**: e.g., `Parallel_Link_Bars`, `Side_Joiner_Clips` (H-clips joining split pegboard halves), `Pivot_Pins`.
   - **Modular Inserts / Accessories**: e.g., `Divider_Sub_Trays` ($1/3$, $1/2$, or $1/1$ width with 1–3 compartments), `Skadis_Hooks`.
2. **Enforce Kinematic Laws Over Perspective Pixel Noise**:
   - **Coplanar Echelon Multi-Pin Parallelogram Law (Non-Overlapping Single-Layer Bars)**:
     Before modeling any linkage, count the **exact number of bars and pins per bar** in the side orthographic/perspective views:
     - Never assume linkage bars share pins end-to-end in overlapping lateral layers if the reference shows **parallel, non-overlapping coplanar bars** (e.g., 4 parallel bars arranged in an echelon: `Bar 1` = 2-pin short bar, `Bar 2` = 3-pin long bar, `Bar 3` = 3-pin long bar, `Bar 4` = 2-pin short bar).
     - In an $N$-tier coplanar echelon linkage, each tray $t \in \{0, \dots, N-1\}$ has horizontal pin stations $s \in \{0, 1, 2\}$ spaced by `Pin_Station_Pitch` $\Delta y_{\text{station}}$ along the tray depth (`Station A` front, `Station B` middle, `Station C` rear), and every bar connects **(Tray $t$, Station $s$) $\longrightarrow$ (Tray $t+1$, Station $s+1$)** with single-tier hole pitch $L_{\text{step}} = \sqrt{\Delta y_{\text{station}}^2 + \Delta Z_{\text{collapsed}}^2}$:
       - `Bar 1 (2-pin, length L_step)`: `(Tray 0, Station B) -> (Tray 1, Station C)`
       - `Bar 2 (3-pin, length 2*L_step)`: `(Tray 0, Station A) -> (Tray 1, Station B) -> (Tray 2, Station C)`
       - `Bar 3 (3-pin, length 2*L_step)`: `(Tray 1, Station A) -> (Tray 2, Station B) -> (Tray 3, Station C)`
       - `Bar 4 (2-pin, length L_step)`: `(Tray 2, Station A) -> (Tray 3, Station B)`
     - At bar angle $\theta$ from vertical, the tray-to-tray translation is:
       $$\Delta Y_{\text{tray}}(\theta) = -L_{\text{step}}\sin(\theta) - \Delta y_{\text{station}}, \qquad \Delta Z_{\text{tray}}(\theta) = -L_{\text{step}}\cos(\theta)$$
       - In the **Collapsed State** ($\theta_{\text{col}} = -\arcsin(\Delta y_{\text{station}} / L_{\text{step}})$), $\Delta Y_{\text{tray}} = + \Delta y_{\text{station}} - \Delta y_{\text{station}} = 0\text{ mm}$ (trays stack **100% vertically** while the bars sit at $-\theta_{\text{col}}$, and tray rear walls rest flush against the front of the rear support legs).
       - In the **Open State** ($\theta_{\text{open}} = +\arcsin(\Delta y_{\text{station}} / L_{\text{step}})$), the exact same bars swing through vertical to $+\theta_{\text{open}}$, stepping each tray forward by $\Delta Y_{\text{tray}} = -2 \Delta y_{\text{station}}$ while keeping all 4 bars in a **single coplanar layer** with zero shared pins!
3. **Print-Bed Modularity Rule**:
   - If a flat panel (such as a tall Skådis backboard) exceeds the target printer bed height (e.g. `> 210 mm`), split it horizontally into `Upper_Panel` and `Lower_Panel` and generate matching side H-profile joiner clips (`0.20 mm` sliding clearance).
4. **Optional Perspective Homography Dewarping (`--rectify`)**:
   - For angled photos of flat patterned plates or complex 2D silhouettes, run:
     ```bash
     ~/.gemini/antigravity/skills/media-to-fusion/scripts/process_media.py "<image_path>" \
       --out-dir ./media_workspace \
       --rectify "x1,y1,x2,y2,x3,y3,x4,y4" \
       --real-w <width_mm> --real-h <height_mm>
     ```
   - `process_media.py` automatically sorts the 4 corners clockwise (`TL, TR, BR, BL`), dewarps the plane to `rectified_ortho.png` at `0.1 mm/px`, exports `rectified_contour.dxf`, and saves simplified closed polygon loops (`points_xy_mm`) inside `media_manifest.json`.

---

## Phase 4: Parametric Modeling via Fusion 360 MCP
Build the CAD assembly cleanly in Fusion 360 via `execute_api_script`:

1. **Mandatory Centimeter Conversion (`cm = mm / 10.0`)**:
   - Fusion 360's internal API (`adsk.core.ValueInput.createByReal()`, `adsk.core.Point3D.create()`) strictly uses **centimeters (`cm`)**.
   - Always define `def cm(mm_val): return mm_val / 10.0` at the top of every `execute_api_script`.
2. **Register Master User Parameters (`design.userParameters`)**:
   Create editable millimeter/degree parameters first so the user can reconfigure scale, tier count, or fold state anytime:
   ```python
   def set_user_param(design, name, expr_str, units="mm", comment=""):
       existing = design.userParameters.itemByName(name)
       if existing:
           existing.expression = expr_str
           return existing
       return design.userParameters.add(
           name, adsk.core.ValueInput.createByString(expr_str), units, comment
       )
   ```
   Recommended parameters for foldable/modular assemblies:
   - `Tray_Width`, `Tray_Depth`, `Tray_Height`, `Wall_Thickness` (default `2.4 mm`)
   - `Link_Step_Pitch`, `Link_Width`, `Link_Thickness` (default `3.5 mm`)
   - `Deploy_Angle_Deg` (e.g., `40 deg` for Open/Deployed state, `0 deg` for Collapsed vertical stack)
   - `Clearance` (default `0.25 mm`)
3. **3D-Printing Mechanical Clearances**:
   - **Rotating pivot pins / linkage holes**: `0.25 mm` radial (`0.50 mm` diametral) clearance, with a `0.8 mm` lip or M3 fastener bore so links stay retained.
   - **Sliding joiner clips / removable divider inserts**: `0.20 mm` per-side clearance (`0.40 mm` total width/depth deduction on insert trays).
   - **Bottom Tray Ergonomics & Rear Support Legs**:
     - Include rounded oblong side handle cutouts on the lowest tray if visible in reference media.
     - Ensure `Rear_Support_Legs` reach from the top anchor tray all the way down to the ground plane ($Z = Z_{\text{bottom\_tray\_floor}}$) so the assembly stands level when deployed.

---

## Phase 5: Closed-Loop Visual & Interference Verification
Never conclude after a blind script execution. Perform both **visual** and **mathematical** verification:

1. **Multi-Angle Visual Comparison (`get_screenshot`)**:
   - Call `fusion-mcp` tool `get_screenshot` with:
     - `view="iso-top-right", width=1024, height=1024`
     - `view="right", width=1024, height=1024` (crucial for inspecting linkage bar alignment, stair-step angle, and rear leg ground contact!)
     - `view="front", width=1024, height=1024` (crucial for inspecting Skådis slot grid symmetry and divider proportions!)
   - Compare the rendered screenshots side-by-side against the reference keyframes/photos (`keyframe_XX_grid.png` / `annotated_grid.png`).
2. **Automated Timeline & Interference Verification**:
   Run a verification pass via `execute_api_script` to assert native solid geometry and check for physical collisions between components:
   ```python
   def run(context):
       import adsk.core, adsk.fusion
       app = adsk.core.Application.get()
       design = adsk.fusion.Design.cast(app.activeProduct)
       root = design.rootComponent

       assert root.sketches.count > 0, "No native sketches found!"
       assert root.features.extrudeFeatures.count > 0, "No extrude features found!"
       assert root.meshBodies.count == 0, "Forbidden MeshBody objects detected!"

       # Collect all visible solid bodies across occurrences and root
       bodies = adsk.core.ObjectCollection.create()
       for b in root.bRepBodies:
           if b.isVisible:
               bodies.add(b)
       for occ in root.allOccurrences:
           for b in occ.bRepBodies:
               if b.isVisible:
                   bodies.add(b)

       if bodies.count >= 2:
           input_obj = design.createInterferenceInput(bodies)
           input_obj.areCoincidentFacesIncluded = False
           results = design.analyzeInterference(input_obj)
           print(f"Total bodies checked: {bodies.count} | Interferences: {results.count}")
           for i in range(results.count):
               res = results.item(i)
               v_mm3 = res.interferenceBody.volume * 1000.0
               if v_mm3 > 1.0:
                   print(f"WARNING Collision: {res.entityOne.name} <-> {res.entityTwo.name} ({v_mm3:.1f} mm^3)")
   ```
3. **Self-Correction Loop & Fusion 360 API Guardrails**:
   - **Plane-Independent 3D Sketch Mapping**: Always map 3D coordinates `(x, y, z)` onto any sketch plane via `sk.modelToSketchSpace(adsk.core.Point3D.create(cm(x), cm(y), cm(z)))` so UV axis flips on `YZ` or `XZ` planes never invert geometry.
   - **Stadium / Slot Arc Endpoint Ordering**: In Fusion 360 API, `sketchArcs.addByThreePoints(p1, mid, p2)` reorders `arc.startSketchPoint` and `arc.endSketchPoint` counter-clockwise. Never chain `lines.addByTwoPoints(arc.endSketchPoint, ...)`; instead, create explicit `SketchPoint` instances (`sp = sk.sketchPoints.add(...)`) and pass them to both `addByTwoPoints` and `addByThreePoints`.
   - **Single-Component (`Part Design`) Fallback**: Newer Fusion 360 documents initialized in `Part Design` mode disallow `root.occurrences.addNewComponent()`. Wrap component creation in a helper that falls back to `root` and assign `.name`, `.appearance`, and `.participantBodies` directly on `feat.bodies`.
   - If any linkage bar collides with a tray wall, a rear leg floats above/below the floor plane, or proportions deviate from the reference keyframe, fix the parametric sketch/offset immediately and re-verify with `get_screenshot`.

---

## Phase 6: Durable Knowledge Harvest & Skill Self-Upgrade (The Flywheel)
Never exit a completed build without feeding learned lessons back into the CAD harness:

1. **Model Specification & Assembly Manual**:
   - Write `SPEC.md` inside `models/<NN>_<Name>/` with exact envelope, volume, and kinematic datum.
   - Update `Media-To-Fusion-Projects/README.md` catalog table with the new model.
2. **Promote Reusable Mechanism / API Gotchas**:
   - If a new kinematic mechanism or linkage law was derived:
     - Append it to `references/kinematic-archetypes.md`.
     - Create a reusable pattern in Obsidian DevBrain: `03_Resources/Code-Patterns/Fusion-<Mechanism>.md`.
   - If a non-obvious Fusion 360 API trap was resolved:
     - Append it to `references/fusion-api-gotchas.md`.
     - Update DevBrain: `02_Areas/Engineering-Standards/Fusion-360-CAD-Standards.md`.
3. **Execute `/wrapup`**:
   - Commit the scoped changes in `Media-To-Fusion-Projects`.
   - Update `01_Projects/Media-To-Fusion-Projects/Models/<NN>_<Name>.md` in DevBrain.
   - Run `brainsync` to sync DevBrain to GitHub.
