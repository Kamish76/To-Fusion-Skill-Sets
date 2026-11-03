# Exploded Assembly & Technical Illustration Guidelines

Best practices for generating professional 3D exploded views, technical fastener diagrams, and visual assembly instructions directly inside Autodesk Fusion 360.

---

## 1. Linear Explosion Vectors

Always space components out along their natural **insertion / removal axes**:
- **Lateral Linkages & Washers (X-Axis):**
  - Trays stay stationary at origin ($X = [-127.5, +127.5]\text{ mm}$).
  - Linkage bars shifted outward by `+35 to +50 mm` along +X.
  - Retaining washers shifted inward to inner tray faces or along X.
  - Screws floating outward along -X (or inside the tray cavity).
  - Hex nuts floating outward along +X beyond the linkage bars.
- **Rear Support / Frame Mounts (Y-Axis):**
  - Stand / backboard shifted backward by `+45 to +60 mm` along +Y.
  - Mounting screws floating along +Y from the front.
  - Captured nuts floating along -Y behind the stand.
- **Removable Trays / Modular Inserts (Z-Axis):**
  - Lift vertically upward by `+40 to +60 mm` along +Z.

---

## 2. Golden Alignment Guide Rods

To make the assembly sequence instantly readable, generate thin cylindrical guide rods passing through joint centerlines:
- **Geometry:** Thin cylinders ($\varnothing 1.2 - 1.4\text{ mm}$) extruded along the principal explosion vector.
- **Appearance:** High-contrast warm metallic or yellow (`Rack_Mustard_Yellow` or `Gold - Polished`).
- **Span:** Extends from the innermost fastener position all the way through the bosses, washers, and bars to the outermost nut position.
- **Dedicated Component:** Always put guide rods into an `Opened_Explosion_Guides` component occurrence so they can be toggled on/off in one click (`guides_occ.isLightBulbOn = False`).

---

## 3. High-Contrast Appearance Palettes

In an exploded diagram, adjacent components must have high visual contrast:
- **Main Box Trays:** Dual-tone alternating palette (e.g. `Rack_Bright_Green` for Tiers 1 & 3, `Rack_Olive_Green` for Tiers 2 & 4).
- **Linkage Bars:** High-contrast neutral (e.g. `Rack_Desert_Tan` or `Wood - Maple`).
- **Fasteners (Screws & Nuts):** High-contrast metallic/white (e.g. `Rack_Matte_White` or `Stainless Steel - Polished`).
- **Retaining Washers:** Distinct accent color (e.g. `Rack_Crimson_Red`).

---

## 4. Orthographic Overview Framing

Always set camera to `OrthographicCameraType` to eliminate perspective distortion and maintain parallel alignment lines:
```python
vp = app.activeViewport
cam = vp.camera
cam.isSmoothTransition = False
cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
cam.target = adsk.core.Point3D.create(cm(70.0), cm(-170.0), cm(145.0))
cam.eye = adsk.core.Point3D.create(cm(1388.2), cm(-1505.8), cm(1339.3))
cam.upVector = adsk.core.Vector3D.create(-0.41, 0.41, 0.82)
cam.viewExtents = cm(760.0)
cam.isFitView = False
vp.camera = cam
vp.refresh()
```
