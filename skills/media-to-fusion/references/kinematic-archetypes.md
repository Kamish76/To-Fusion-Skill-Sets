# Catalog of Mastered Kinematic Archetypes

A growing mathematical catalog of mechanical systems mastered by the `media-to-fusion` skill. Before calculating custom geometry, match user reference media against these verified archetypes.

---

## Archetype 1: Coplanar Echelon Multi-Pin Parallelogram Linkage
**Use When:** Multi-tier cantilever toolboxes, stepped display racks, vanity cases, and deployable drawer systems where all bars must swing without lateral layer collisions or overlapping pins.

```text
Tier 0 (Top Anchor)    [Station A]     [Station B]     [Station C]
                           │               │
                           │ (Bar 2, 3-pin)│ (Bar 1, 2-pin)
                           ▼               ▼
Tier 1 (Coupler 1)     [Station A]     [Station B]     [Station C]
                           │               │
                           │ (Bar 3, 3-pin)│ (Bar 2, 3-pin)
                           ▼               ▼
Tier 2 (Coupler 2)     [Station A]     [Station B]     [Station C]
                           │               │
                           │ (Bar 4, 2-pin)│ (Bar 3, 3-pin)
                           ▼               ▼
Tier 3 (Bottom Base)   [Station A]     [Station B]     [Station C]
```

### Mathematical Formulation
Given uniform horizontal station pitch $\Delta y_{\text{station}}$ and collapsed vertical rise per tier $\Delta Z_{\text{collapsed}}$:
1. **Link Hole Pitch per Tier ($L_{\text{step}}$):**
   $$L_{\text{step}} = \sqrt{\Delta y_{\text{station}}^2 + \Delta Z_{\text{collapsed}}^2}$$
2. **Collapsed State Angle ($\theta_{\text{col}}$):**
   $$\theta_{\text{col}} = -\arcsin\left(\frac{\Delta y_{\text{station}}}{L_{\text{step}}}\right)$$
   Trays align at $Y = 0\text{ mm}$ (perfect vertical stack) while bars sit at $-\theta_{\text{col}}$.
3. **Opened State Angle ($\theta_{\text{open}}$):**
   $$\theta_{\text{open}} = +\arcsin\left(\frac{\Delta y_{\text{station}}}{L_{\text{step}}}\right) = -\theta_{\text{col}}$$
   Trays step forward by $\Delta Y = -2 \Delta y_{\text{station}}$ per tier while bars swing to $+\theta_{\text{open}}$.
4. **Echelon Bar Structure (Single Lateral Layer):**
   - In an $N$-tier box, exactly $N$ bars exist on each side.
   - Outer bars (`Bar 1` and `Bar N`): 2-pin short bars with length $L_{\text{step}}$.
   - Inner bars (`Bar 2` to `Bar N-1`): 3-pin long bars with length $2 \times L_{\text{step}}$.
   - Every bar connects `(Tier t, Station s) -> (Tier t+1, Station s+1)` with zero shared pins!

---

## Archetype 2: Modular Skådis Pegboards & Sliding H-Clip Joiners
**Use When:** Wall organizers, backboards, or vertical tool panels exceeding 3D printer build volumes.

### Standards & Geometry
1. **Grid Layout:**
   - Horizontal same-row slot pitch: **`40.0 mm`** center-to-center
   - Vertical row-to-row pitch: **`20.0 mm`** (alternate rows staggered horizontally by **`20.0 mm`**)
   - Stadium slot dimensions: **`5.0 mm` wide $\times$ `15.0 mm` tall** (`10.0 mm` straight center-to-center with $R = 2.5\text{ mm}$ ends)
   - Board thickness: **`4.0–5.0 mm`**
2. **Horizontal Bed-Split H-Clips:**
   - Panel edge step: `1.5 mm` tongue, `0.20 mm` sliding gap
   - H-Clip channel: `4.4 mm` internal width for `4.0 mm` board

---

## Archetype 3: Stepped Orthogonal Linkage System (FTO Design Workaround)
**Use When:** Overcoming registered design patent strikes (e.g. EUIPO RCD `015153914-0002` claiming straight diagonal/pill bars) on multi-tier cantilever organizers, or achieving an industrial/cyberpunk aesthetic while maintaining 100% planar parallel kinematics.

```text
Opened State:
  Link 1 (Upper Rear 2-Pin):   L-bracket (⮑) connecting Tier 2 rear pin to Tier 1 rear pin.
  Link 2 (Upper Mid 3-Pin):    Z-crank (Z) connecting Tier 3 rear, Tier 2 mid, Tier 1 front.
  Link 3 (Lower Mid 3-Pin):    Z-crank (Z) connecting Tier 4 rear, Tier 3 mid, Tier 2 front.
  Link 4 (Lower Front 2-Pin):  Inverted L-elbow (⮎) connecting Tier 4 front to Tier 3 front.
```

### Mathematical Formulation & Protrusion Elimination
1. **Kinematic Equivalence:**
   - Planar parallel motion requires **only** that the Euclidean distance between pin centers remains invariant:
     $$L_{\text{step}} = \sqrt{\Delta y_{\text{station}}^2 + \Delta Z_{\text{collapsed}}^2} = 80.35\text{ mm}$$
   - Centerline clearance between adjacent links across the full $63.03^\circ$ sweep is $19.15\text{ mm}$ ($> 7\text{ mm}$ air gap with $12\text{ mm}$ bar width).
2. **Collapsed State Flush Envelope ($45^\circ$ Chiseled Corner Facets):**
   - Pure $90^\circ$ orthogonal corners swing beyond the rectangular tray footprint when closed ($+12.04\text{ mm}$ protrusion).
   - Applying a **$d = 9.0\text{ mm}$ $45^\circ$ chiseled facet** to every outer elbow corner truncates the protrusion completely, keeping the folded linkage bars ($Y \in [-8.04 .. 122.04]\text{ mm}$) 100% flush within the tray envelope ($Y \in [-11.00 .. 122.00]\text{ mm}$).
3. **Display Tray Low-Lip Ergonomics:**
   - Cantilever trays need high side walls ($68.0\text{ mm}$) to house pivot holes, but high front walls block product visibility.
   - Standardize a **$20.0\text{ mm}$ internal front display lip** ($22.8\text{ mm}$ from base floor) with vertical $90^\circ$ upright side ears. This maximizes visibility while maintaining structural pin support.

