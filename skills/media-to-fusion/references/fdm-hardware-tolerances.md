# FDM Mechanical Clearances & Fastener Tolerances

Ground-truth mechanical fits for FDM 3D printing (0.4mm nozzle, PLA/PETG) used across `media-to-fusion` builds.

---

## 1. Fastener Stack-Ups & Counterbores

### Standard Maker's Supply M3 Revolute Joint Stack-Up
Standardized non-printed hardware joint replacing fragile printed pins with off-the-shelf fasteners:
- **Compatible Fasteners:** Maker's Supply `AA172` (M3 × 10 mm BHCS), `AA159` (M3 × 10 mm SHCS), and `AB005` (DIN 934 M3 Hex Nut).
- **Bar Web Thickness:** $5.00\text{ mm}$ flat linkage web.
- **Outer Screw Counterbore:** $\varnothing 6.20\text{ mm} \times 1.50\text{ mm}$ deep cylindrical counterbore on outer face allowing screw heads to seat flush.
- **Inner Captive Hex Pocket:** Regular hexagon across flats modeled at **`5.70 mm`** (`+0.20 mm` clearance for layer bulging over `5.50 mm` nut) $\times 2.40\text{ mm}$ depth on the inner face.
- **Clearance Through-Bore:** $\varnothing 3.30\text{ mm}$ clearance hole for smooth M3 shank pass.
- **Standoff Shoulder:** $0.25\text{ mm}$ proud circular shoulder ($\varnothing 9.50\text{ mm}$) centered on each pivot hole on the bar inner face to prevent broad-area friction against tray walls.
- **Retaining Washer:** 3D-printed washer ($\varnothing 9.50\text{ mm}$ OD $\times \varnothing 3.20\text{ mm}$ ID $\times 1.80\text{ mm}$ thick) clamping the joint pivot tip.

### DIN 7991 M3 Countersunk Socket Head Screw
- **Nominal Dimensions:** Shank $\varnothing 3.0\text{ mm}$, Head $\varnothing 6.0\text{ mm}$, Head Height $k = 1.7\text{ mm}$, 90° countersink angle.
- **Clearance Hole (Bore):** $\varnothing 3.20 - 3.40\text{ mm}$ for smooth through-pass.
- **Pilot Hole (Self-Tapping into Plastic):** $\varnothing 2.70 - 2.80\text{ mm}$.

### DIN 934 M3 Hex Nut
- **Nominal Dimensions:** Across Flats (AF) $s = 5.50\text{ mm}$, Height $m = 2.40\text{ mm}$.
- **Captive Hex Pocket (Press-Fit / Friction Lock):**
  - Modeled AF: **`5.70 mm`** (`+0.20 mm` clearance for layer bulging).
  - Modeled Depth: **`2.40 - 2.60 mm`** (`+0.00 - 0.20 mm` clearance).
  - Corner Radii: $0.20\text{ mm}$ dog-bone relief or sharp hex.

---

## 2. Dynamic Mechanical Fits (FDM Clearances)

| Fit Class | Application | Clearance (Diametral / Total) | Notes |
| :--- | :--- | :---: | :--- |
| **Rotating Pivot** | Linkage bar over tray boss | **`0.50 mm` diametral** (`0.25 mm` per side) | Lubricate with synthetic grease / PTFE |
| **Sliding Fit** | Removable organizer trays | **`0.40 mm` total** (`0.20 mm` per side) | Prevents binding in deep tray pockets |
| **Snap-Fit / Interlock** | Latch tongues, H-clips | **`0.30 mm` total** (`0.15 mm` per side) | Snap cantilever beam thickness $1.2 - 1.6\text{ mm}$ |
| **Press-Fit** | Captive hex nuts, magnets | **`0.15 - 0.20 mm` total** | Snug friction lock without splitting layers |

---

## 3. Surface Detailing & Micro-Engraving Printability Thresholds

Fine engraved cosmetic and functional markings must be evaluated against additive manufacturing process limits (0.4mm nozzle FDM and standard SLA/DLP resin):

| Feature Type | Modeled Geometry | Printability Verdict | Engineering Recommendation |
| :--- | :--- | :---: | :--- |
| **Micro-Graduations / Ruler Ticks** | $0.10\text{–}0.15\text{ mm}$ width, $0.12\text{ mm}$ depth | **FAIL (FDM & Resin)** | **Omit from 3D-printable geometry.** Micro-ticks fall below $0.40\text{ mm}$ nozzle resolution, triggering slicing anomalies, layer gaps, and nozzle stringing on FDM, and capillary resin pooling in DLP. Use post-print laser marking or pad printing. |
| **Tactile Grip Flutes / Stadium Ribs** | $0.80\text{–}1.00\text{ mm}$ width, $0.25\text{–}0.35\text{ mm}$ depth | **PASS** | Excellent for ergonomics and grip. Prints cleanly as a single or double perimeter stroke without retractions. |
| **Debossed Numerals & Cartouche Badges** | $1.4\text{–}2.5\text{ mm}$ height, $\ge 0.25\text{ mm}$ stroke width, $0.18\text{ mm}$ depth | **PASS** | Legible on both FDM (0.12mm layer height) and SLA/Resin. Ensure stroke thickness $\ge 0.25\text{ mm}$. |
| **Ground Cutting Edge Relief Facets** | $0.10\text{–}0.15\text{ mm}$ bevel relief | **PASS** | Facet creates a distinct visual reflect line in CAD and slicers. Knife edges should terminate with at least $0.20\text{ mm}$ edge flat for FDM durability. |
