# FDM Mechanical Clearances & Fastener Tolerances

Ground-truth mechanical fits for FDM 3D printing (0.4mm nozzle, PLA/PETG) used across `media-to-fusion` builds.

---

## 1. Fastener Stack-Ups & Counterbores

### DIN 7991 M3 Countersunk Socket Head Screw
- **Nominal Dimensions:** Shank $\varnothing 3.0\text{ mm}$, Head $\varnothing 6.0\text{ mm}$, Head Height $k = 1.7\text{ mm}$, 90° countersink angle.
- **Clearance Hole (Bore):** $\varnothing 3.20 - 3.40\text{ mm}$ for smooth through-pass.
- **Pilot Hole (Self-Tapping into Plastic):** $\varnothing 2.70 - 2.80\text{ mm}$.

### DIN 934 M3 Hex Nut
- **Nominal Dimensions:** Across Flats (AF) $s = 5.50\text{ mm}$, Height $m = 2.40\text{ mm}$.
- **Captive Hex Pocket (Press-Fit / Friction Lock):**
  - Modeled AF: **`5.70 mm`** (`+0.20 mm` clearance for layer bulging).
  - Modeled Depth: **`2.50 - 2.60 mm`** (`+0.10 - 0.20 mm` clearance).
  - Corner Radii: $0.20\text{ mm}$ dog-bone relief or sharp hex.

### 3D-Printed Retaining Washers
- **Outer Diameter:** $\varnothing 9.50\text{ mm}$.
- **Inner Bore:** $\varnothing 3.20\text{ mm}$ with matching 90° conical countersink pocket.
- **Thickness:** $1.80\text{ mm}$.
- **Function:** Clamps the tip of the tray pivot boss, keeping the linkage bar retained without binding against the rotating face.

---

## 2. Dynamic Mechanical Fits (FDM Clearances)

| Fit Class | Application | Clearance (Diametral / Total) | Notes |
| :--- | :--- | :---: | :--- |
| **Rotating Pivot** | Linkage bar over tray boss | **`0.50 mm` diametral** (`0.25 mm` per side) | Lubricate with synthetic grease / PTFE |
| **Sliding Fit** | Removable organizer trays | **`0.40 mm` total** (`0.20 mm` per side) | Prevents binding in deep tray pockets |
| **Snap-Fit / Interlock** | Latch tongues, H-clips | **`0.30 mm` total** (`0.15 mm` per side) | Snap cantilever beam thickness $1.2 - 1.6\text{ mm}$ |
| **Press-Fit** | Captive hex nuts, magnets | **`0.15 - 0.20 mm` total** | Snug friction lock without splitting layers |
