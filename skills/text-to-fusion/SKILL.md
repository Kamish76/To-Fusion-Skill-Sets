---
name: text-to-fusion
description: Translates natural language descriptions, mechanical adjustments, fastener BOM requests, exploded assembly diagrams, and kinematic animations into 100% native, parametric 3D CAD models and assemblies in Autodesk Fusion 360 via the Fusion 360 MCP server.
---

# Text to Fusion 360 Pure Parametric CAD Skill

When the user describes a mechanical object, part, modification, accessory tray, fastener specification, exploded assembly, or kinematic animation in natural language without providing reference 3D files (`.3mf`/`.stl` $\rightarrow$ use `3mf-to-fusion`) or visual media (`.png`/`.mp4` $\rightarrow$ use `media-to-fusion`), follow this **6-phase deterministic CAD workflow**.

**STRICT CAD MANDATE**:
- Reconstruct all geometry using native **Sketches**, **Construction Planes**, **User Parameters**, and **Extrude/Revolve/Joint Features** in the Fusion 360 timeline. Never generate raw mesh bodies (`root.meshBodies.add`) or faceted mesh conversions.
- All code must execute cleanly inside `execute_api_script` using centimeters (`cm = mm / 10.0`).
- Always visually verify every generated or modified body using `get_screenshot`.

---

## Phase 0: Pre-Flight Probe & Workspace Alignment

1. **Verify Live Fusion 360 MCP Session**:
   Execute canary probe via `fusion-mcp` tool `execute_api_script`:
   ```python
   def run(context):
       import adsk.core, adsk.fusion
       app = adsk.core.Application.get()
       if not app or not adsk.fusion.Design.cast(app.activeProduct):
           raise RuntimeError("No active Fusion 360 design document open.")
       print("FUSION_MCP_READY")
   ```
   *Fail-Fast Rule:* If the probe fails, stop and instruct the user to open Autodesk Fusion 360.

2. **Workspace & Monorepo Routing**:
   - Primary repository: Active CAD monorepo or project root (`CAD_MONOREPO_ROOT` or current workspace).
   - **Strict Isolation Guarantee:** Never create temporary files, scripts, or renders in the repository root or mutate `shared/`.
   - If starting a brand-new model, scaffold its dedicated folder:
     ```bash
     python3 <path_to_skills>/text-to-fusion/scripts/scaffold_text_model.py "<Model_Name>"
     ```
   - Store model scripts in `models/<NN>_<Model_Name>/scripts/`, visual renders in `models/<NN>_<Model_Name>/renders/`, and intermediate workspace files in `models/<NN>_<Model_Name>/workspace/`.
   - Import universal CAD helpers from `../../shared/` (`fusion_client`, `cad_primitives`, `hardware_library`, `scene_animator`).

3. **Domain References**:
   Consult the local reference library before writing custom geometry:
   - `references/prompt-to-geometry-patterns.md` — Translates natural language into parametric sketch constraints.
   - `references/kinematic-linkages.md` — Burmester 4-bar synthesis, hyperplane separation, coplanar U-cradles, and SE(3) transforms.
   - `references/exploded-view-guidelines.md` — Explosion vectors, golden guide rods, and orthographic framing.
   - `references/assembly-animation-pipeline.md` — Matrix3D occurrence transform animation and GIF compilation.
   - `references/variant-management-and-undo.md` — Safe A/B variant showrooming and non-destructive hiding.

---

## Phase 1: Disambiguation & Parametric Specification

When users describe geometry conversationally, identify and formalize the missing engineering constraints:
1. **Envelope & Critical Dimensions**:
   - Overall bounding box ($W \times D \times H$ in mm).
   - Minimum wall thickness (default `2.0 - 2.5 mm` for structural parts, `1.6 mm` for internal dividers).
   - 3D printer bed limit (e.g. `220 × 220 × 250 mm`).
2. **Register Master User Parameters (`design.userParameters`)**:
   Always expose critical dimensions as user parameters so the user can rescale in one click:
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

---

## Phase 2: Variant Staging & Reversible Exploration

When the user asks for design options ("give me option 2", "try a version with no lids"):
1. **The Showroom Pattern**:
   - Model experimental options in a dedicated component (e.g. `Sample_Options_Showroom:1`).
   - Space variants side-by-side on the virtual workspace floor (e.g. $Y = -350\text{ mm}$ or $X = -200\text{ mm}$) with distinctive appearances (`Rack_Desert_Tan`, `Rack_Matte_White`).
   - Capture a side-by-side overview screenshot with labels.
2. **Non-Destructive Adoption**:
   - When the user selects a winner, clone the chosen bodies into the active assembly (`InSitu_Tier3_Option2`).
   - Hide rejected showroom bodies via `bRepBody.isLightBulbOn = False`.
   - **Never call `body.deleteMe()`** on objects that might break downstream timeline references.

---

## Phase 2.5: In-Place Surgical Editing (Ban on Rebuilding)

When the user dictates modifications to an existing model ("make the slot 2mm wider", "deepen the finger tab", "add captive magnet pockets"):
> [!IMPORTANT]
> **NEVER WIPE AND REBUILD:** Do NOT call `child.deleteMe()` or re-execute the full generation script. Apply changes surgically via the 4-tier in-place editing tools in `tools/fusion_editor/`:

1. **Introspect First:**
   Execute `tools/fusion_editor/inspect_model.py` to identify component names, bodies, bounding boxes in mm, driving parameters, and timeline indices.
2. **Apply the 4-Tier Hierarchy:**
   - **Tier 1 (Parametric Tweak — < 50ms):** Modify driving parameters via `tools/fusion_editor/edit_parameter.py` (e.g. `Extrude10.distance = "4.0 mm"`).
   - **Tier 2 (Timeline Rollback Surgery — < 200ms):** Roll marker to earlier feature via `tools/fusion_editor/rollback_edit.py`, adjust sketch/extrude inputs, and advance marker to end.
   - **Tier 3 (Localized Downstream Append — < 300ms):** Query target body face and append cut/pocket/magnet hole via `tools/fusion_editor/append_feature.py`.
   - **Tier 4 (Scoped Subassembly Swap):** Only replace the single child component occurrence if a radical topological overhaul is required.

3. **Pre-Cut Boundary & Internal Partition Auditing:**
   Before cutting vents, windows, or lattices into an exterior wall face, introspect `target_body.faces` to detect transverse partition walls, recessed pockets, and hardware bosses:
   ```python
   # Check for transverse internal walls along Y inside the target body
   internal_partitions = [
       f.boundingBox.minPoint.y * 10.0
       for f in body.faces
       if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
       and abs(adsk.core.Plane.cast(f.geometry).normal.y) > 0.9
       and (f.boundingBox.maxPoint.x - f.boundingBox.minPoint.x) * 10.0 > 10.0
   ]
   ```
   Never let cut profiles clip through internal partition walls or pocket clearances.

4. **Robust Profile Filtering & 1-Cut + 1-Mirror Rule:**
   - **Analytical Area Filtering:** Calculate exact profile area beforehand ($A_{\text{cell}} = \frac{4 W_h h_v + 2 W_h \text{crown}}{100.0}\text{ cm}^2$) and collect only matching profiles via `filter_profiles_by_area()`:
     ```python
     profs = [p for p in sk.profiles if abs(p.areaProperties().area - A_cell) < 0.08]
     ```
   - **1-Cut + 1-Mirror Rule:** Bundle all lattice cells into a single `CutFeatureOperation`, followed immediately by a `MirrorFeature` across the center plane. This keeps timeline feature count minimal (2 features instead of 30+ separate extrusions), avoiding timeline lag and API timeouts.

5. **Verify Health & Log Audit:**
   - Run `tools/fusion_editor/timeline_doctor.py` to ensure zero yellow/red timeline errors.
   - Run `python3 tools/log_model_edit.py --model <name> --prompt "<prompt>" --tier <1-4>` to record the prompt, delta, and ADR into the model's `TIMELINE.md` and `DECISIONS.md`.

---

## Phase 3: Standard Fasteners & Hardware BOM Synthesis

When the user asks for screws, nuts, or assembly hardware:
1. **Hardware Standardization**:
   - Default to **DIN 7991 M3 Countersunk Screws** and **DIN 934 M3 Hex Nuts** for all pivots and structural joints.
2. **Standard Pocket Dimensions**:
   - **Hex Nut Pocket:** Modeled across flats (AF) at **`5.70 mm`** (`+0.20 mm` FDM clearance over `5.50 mm` nut), depth **`2.50 mm`**.
   - **Screw Bore:** $\varnothing 3.20\text{ mm}$ through-pass with a 90° conical countersunk pocket ($\varnothing 6.20\text{ mm} \times 1.80\text{ mm}$).
   - **Retaining Washers:** 3D-printed washer ($\varnothing 9.50\text{ mm}$ OD × $\varnothing 3.20\text{ mm}$ ID × `1.80 mm` thick, 90° countersink) clamping the tip of the pivot boss while leaving the linkage bar free to rotate.
3. **Template Parking Rule**:
   - Master hardware templates (`Template_DIN_7991_M3x10`, `Template_DIN_934_M3`) must have `isLightBulbOn = True`.
   - Park templates far underground (`Z = -500.0 cm`) so child instances in the assembly stay visible while the templates remain completely off-screen.

---

## Phase 4: Exploded Diagrams & Technical Illustration

When the user asks to illustrate how parts assemble:
1. **Linear Explosion Offsets**:
   - Offset linkage bars outward along primary axis ($+X$ by `35 - 50 mm`).
   - Offset structural stands or frames backward along $Y$ (`+45 - 60 mm`).
   - Offset modular drop-in inserts upward along $Z$ (`+40 - 50 mm`).
2. **Golden Alignment Guide Rods**:
   - Extrude thin cylindrical rods ($\varnothing 1.2 - 1.4\text{ mm}$, appearance `Rack_Mustard_Yellow` or `Gold - Polished`) running through every screw/pivot joint axis from innermost screw head to outermost nut.
   - Group all rods in a dedicated component: `Opened_Explosion_Guides`.
3. **Orthographic Camera Setup**:
   Set `cam.cameraType = OrthographicCameraType` with targeted bounding extents to ensure parallel axes without perspective distortion.

---

## Phase 5: High-Speed Assembly Animation Pipeline

When the user requests an animated GIF showing parts animating into place:
1. **Occurrence-Based Scene-Graph Rigging**:
   - Group each moving assembly into its own dedicated `Occurrence` (`Anim_Bars`, `Anim_Stand`, `Anim_Fasteners`).
   - **DO NOT** use `features.moveFeatures.add()` inside the frame loop (causes ~2.2 s timeline rebuild per frame).
   - Directly reassign `occ.transform = Matrix3D` (`0.005 s/frame`).
2. **Multi-Stage Staggered Smoothstep**:
   Apply smoothstep easing $s(\tau) = 3\tau^2 - 2\tau^3$ over staged subassembly intervals ($t \in [0.0, 1.0]$):
   - Stand docking: $t \in [0.00, 0.40]$
   - Linkage bars seating: $t \in [0.15, 0.60]$
   - Retaining washers seating: $t \in [0.30, 0.70]$
   - Fasteners clamping: $t \in [0.40, 0.92]$
   - Fade guides: `guides_occ.isLightBulbOn = (t < 0.88)`
3. **In-Script Batch Rendering & Ping-Pong Compilation**:
   - Render frames directly to disk: `vp.saveAsImageFile('/tmp/frames/frame_%03d.png', 800, 800)`.
   - Compile using `PIL.Image`: 28 forward frames (45ms) $\to$ 28 hold frames assembled (50ms) $\to$ 26 reverse frames (45ms) $\to$ 20 hold frames exploded (50ms).
   - Quantize with 128 adaptive colors and Floyd-Steinberg dithering (~`2.3 MB`).
   - Use a unique/versioned filename (e.g. `_final.gif`) to bust browser chat image cache.

---

## Phase 6: Mathematical Self-Verification & DevBrain Sync

1. **Verify Mating Boundaries Mathematically**:
   - If a part appears with an unexpected gap ("looks left behind"), inspect world coordinates:
     `delta = target_face.x - moving_face.x`.
   - Apply the exact mathematical delta; never guess adjustments.
2. **Execute Wrap-up & Memory Sync**:
   - Commit scoped changes to the active CAD repository.
   - If a new mechanism, tolerance rule, or API quirk was cracked, record it in `references/` and log the change in `CHANGELOG.md`.
