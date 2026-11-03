# Claude Code & Claude Desktop Rules: Autodesk Fusion 360 Autonomous CAD

When working on CAD projects or executing `-to-fusion` skills (`3mf-to-fusion`, `media-to-fusion`, `text-to-fusion`), follow these mandatory rules:

## 1. Unit Conversion Mandate (`cm` vs `mm`)
- Fusion 360's internal API (`adsk.core.ValueInput.createByReal()`) strictly uses **centimeters (`cm`)**.
- Always divide millimeters by 10: `def mm(val): return adsk.core.ValueInput.createByReal(float(val) / 10.0)`.

## 2. Pre-Flight Canary Probe
- Before running CAD scripts, verify Autodesk Fusion 360 is open with an active document by querying `Application.get()` and `Design.cast(app.activeProduct)`.
- If the probe fails, stop and notify the user to launch Fusion 360.

## 3. 100% Native Parametric Solids Only
- **Strictly Forbidden:** Never use `bRepBodies.addByMesh` or Fusion's mesh conversion tools.
- **Mandatory:** Construct parametric solid bodies in the timeline using sketches, construction planes, driving user parameters, extrusions, revolves, and pattern features.

## 4. Component Occurrence Isolation
- Every part or assembly must be built inside its own component occurrence (`root.occurrences.addNewComponent(transform)`).
- Never place unparented bodies on the root component.

## 5. Visual Self-Verification Loop
- ALWAYS call `get_screenshot` (`view="iso-top-right"`, `width=1024`, `height=1024`) after modifying CAD geometry to visually verify that features succeeded without inversion, unexpected intersections, or missing clearance.

## 6. Workspace Cleanliness & Model Layout
- Never create scratch files, mesh slices, or computer vision previews in the project root.
- All model files must live in `models/<NN>_<Model_Name>/`:
  - `scripts/`: Generation and animation Python scripts.
  - `renders/`: Viewport screenshots and GIFs.
  - `workspace/`: Intermediate CV contours and sliced 3MF manifests (gitignored).

## 7. Fast Kinematics
- Use direct `Occurrence.transform` matrix manipulation instead of timeline `MoveFeatures` for fast animations and exploded views.
