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
