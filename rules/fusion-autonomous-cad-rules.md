# Fusion 360 Autonomous CAD Rules & Standards

These engineering rules govern autonomous AI agents creating and modifying 3D CAD models in Autodesk Fusion 360 via the Fusion 360 MCP server (`fusion-mcp`).

---

## 1. Unit Conversion Mandate (`cm` vs `mm`)
- **Internal Database Standard:** Autodesk Fusion 360's internal C++ core and Python API (`adsk.core.ValueInput.createByReal()`) strictly represent lengths in **centimeters (`cm`)**.
- **Millimeter Division:** All user specifications and mechanical standards are in millimeters (`mm`). Every millimeter value MUST be divided by `10.0` before passing into `createByReal`.
- **Mandatory Helper Function:** Define this helper at the top of every generated API script:
  ```python
  import adsk.core, adsk.fusion

  def mm(val):
      """Converts millimeters to Fusion 360 internal centimeters."""
      return adsk.core.ValueInput.createByReal(float(val) / 10.0)
  ```

---

## 2. Pre-Flight Canary Probe (Fail-Fast Rule)
Before running extensive mesh slicing, computer vision metrology, or constructing CAD models, verify that Autodesk Fusion 360 is open with an active document:
```python
def probe_fusion():
    import adsk.core, adsk.fusion
    app = adsk.core.Application.get()
    if not app:
        raise RuntimeError("Autodesk Fusion 360 is not running.")
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("No active Fusion 360 design document is open.")
    return app, design
```
If the probe fails or times out, **STOP immediately**. Instruct the user to launch Fusion 360 and open a new or existing design document.

---

## 3. Parametric BRep Solid Mandate (No Mesh-to-BREP)
> [!IMPORTANT]
> **Strictly Forbidden:** Never use `bRepBodies.addByMesh` or Fusion's built-in "Convert Mesh to Solid". Converting mesh facets into BRep creates thousands of tiny planar triangular facets that freeze the viewport, cannot be filleted or chamfered, break CAM workflows, and destroy parametric history.
>
> **Mandatory:** Construct 100% native parametric solid bodies in the Fusion 360 timeline using sketches, construction planes, driving user parameters, extrusions, revolves, sweeps, and pattern features.

---

## 4. Component Occurrence Isolation
Every distinct physical part or model must be contained in its own dedicated component occurrence:
```python
# Create dedicated component
root = design.rootComponent
transform = adsk.core.Matrix3D.create()
occ = root.occurrences.addNewComponent(transform)
comp = occ.component
comp.name = "Part_Name"
```
- **Never** leave bodies unparented on the root component.
- **Never** modify bodies belonging to a sibling model or component without explicit intent.

---

## 5. Visual Self-Verification Loop
Autonomous CAD cannot rely solely on script exit codes. Geometry can succeed programmatically while being physically inverted, intersecting, or misaligned.
- **Mandatory Action:** After running `execute_api_script` to create or modify geometry, ALWAYS call `get_screenshot`:
  ```json
  {
    "view": "iso-top-right",
    "width": 1024,
    "height": 1024
  }
  ```
- Inspect the resulting image with `read_file` to visually verify:
  1. No feature warnings or yellow/red timeline errors.
  2. Extrusions cut or joined in the expected direction (no inverted cuts).
  3. Mating parts fit with proper FDM clearances ($0.20 - 0.40\text{ mm}$).
  4. Pivot pins and linkage bars align with station holes.

---

## 6. High-Speed Kinematics & Animations
- Do **NOT** use timeline `MoveFeatures` for kinematic sweeps, exploded views, or multi-frame animations. Adding timeline move features bloats the history tree and slows down playback.
- **MANDATORY:** Directly manipulate the component's `Occurrence.transform` matrix:
  ```python
  matrix = occ.transform
  matrix.translation = adsk.core.Vector3D.create(mm(delta_x), mm(delta_y), mm(delta_z))
  occ.transform = matrix
  ```
- For rotational joints, apply Euler or Rodrigues rotation matrices directly to `occ.transform`.

---

## 7. Fastener Standardization & Captive Pockets
For 3D-printed assemblies and mechanical prototypes, standardize on standard metric hardware:
- **Default Screws:** DIN 7991 M3 Countersunk Socket Screws ($\varnothing 3.20\text{ mm}$ clearance bore, 90° conical head $\varnothing 6.20\text{ mm} \times 1.80\text{ mm}$).
- **Default Nuts:** DIN 934 M3 Hex Nuts (modeled across flats at **`5.70 mm`** with `+0.20 mm` FDM clearance over `5.50 mm` nominal, pocket depth **`2.50 mm`**).
- **Template Parking:** Master hardware templates must be parked far below the workspace floor (e.g., $Z = -500\text{ cm}$) so child occurrences stay visible in the assembly while templates stay hidden.

---

## 8. Non-Destructive Variant Management
When exploring design options or alternative geometries:
- Model candidate variations in an isolated showroom component.
- Hide rejected or superseded bodies using `body.isLightBulbOn = False`.
- **Never call `body.deleteMe()`** on features that might break downstream sketches or projections in the Fusion 360 timeline.
