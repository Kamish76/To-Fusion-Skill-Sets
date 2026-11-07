# Kinematic Linkages, Burmester Synthesis & Planar Mechanisms

Mathematical foundations, closed-form synthesis methods, and Fusion 360 API implementations for multi-bar mechanisms, 90° stowing covers, and coplanar echelon linkages.

---

## 1. Planar Parallelogram Cantilever Kinematics

### Geometry & Constraints
For multi-tier stepped boxes or deployable trays:
- Horizontal station pitch: $\Delta y_{\text{station}}$
- Vertical rise per tier (collapsed): $\Delta Z_{\text{collapsed}}$
- Center-to-center link length:
  $$L_{\text{step}} = \sqrt{\Delta y_{\text{station}}^2 + \Delta Z_{\text{collapsed}}^2}$$
- Swing angle:
  $$\theta_{\text{col}} = -\arcsin\left(\frac{\Delta y_{\text{station}}}{L_{\text{step}}}\right), \qquad \theta_{\text{open}} = -\theta_{\text{col}}$$

### Coplanar Echelon Architecture
- All links reside within a single lateral $X$-plane.
- Outer links are 2-pin ($L = L_{\text{step}}$), inner links are 3-pin ($L = 2 \times L_{\text{step}}$).
- Trays step forward by $\Delta Y = -2 \Delta y_{\text{station}}$ per tier while maintaining purely parallel (zero rotation) translation.

---

## 2. Burmester 2-Position Synthesis with Continuous Hyperplane Separation

### Problem: Zero Mid-Stroke Dipping
When designing a lid, hood, or cover that swings $90^\circ$ vertically to stow behind an enclosure:
1. Purely circular motion or unconstrained 4-bar links dip downwards during intermediate rotation ($t \in [0.2, 0.6]$), colliding with the top-rear corner of the enclosure $(Y_{\text{rear}}, Z_{\text{deck}})$.
2. Purely horizontal sliders block top slots or pegboards.

### Hyperplane Separation Law
Define a horizontal hyperplane at $Z = Z_{\text{deck}}$. The cover must satisfy:
$$\forall t \in [0, 1], \quad Z_{\text{cover\_local}}(t) \ge Z_{\text{deck}} \quad \text{for all } Y \le Y_{\text{rear}}$$

### Closed-Form Synthesis Procedure
1. Choose kinematic pole $O_{\text{pole}} = (y_{\text{pole}}, z_{\text{pole}})$ behind and below the enclosure deck.
2. Place both cover attachment pins (`Pin 10` on crank, `Pin 11` on guide) on an elevated rear ear:
   $$Y_{\text{pin}} > Y_{\text{rear}}, \qquad Z_{\text{pin}} > Z_{\text{deck}}$$
3. Rotating through $-90^\circ$ around $O_{\text{pole}}$ maps:
   $$y_{\text{open}} = y_p + (z_{\text{col}} - z_p), \qquad z_{\text{open}} = z_p - (y_{\text{col}} - y_p)$$
4. Driving crank `Bar 1` rotates $\Delta \theta$ around base pivot $P_9 = (y_9, z_9)$.
5. Guide link `Bar 0` of length $L_0$ anchors at $P_{9b}$ on the perpendicular bisector of `Pin 11`'s displacement.

---

## 3. Coplanar 2-Column U-Cradle Link Routing

When two links must operate simultaneously in the same mechanism without adding lateral thickness:
- **U-Cradle Morphology:** The primary crank (`Bar 1`) has a horizontal lower base runner ($Z = Z_{\text{base}}$) and two vertical upright columns, forming a U-shaped cradle.
- **Internal Sweep:** Follower link `Bar 0` shares the **exact same $X$-plane** ($X = X_{\text{links}}$) and sweeps inside the open throat of `Bar 1`.
- **Centerline Clearance:** Ensure the minimum clearance between `Bar 0` and `Bar 1` satisfies $\Delta d \ge \frac{w_0 + w_1}{2} + 2.0\text{ mm}$ across the entire stroke.

---

## 4. Exact $SE(3)$ Affine Matrix Formulation (`make_yz_transform`)

Planar rotations around arbitrary pivot centers $(y_0, z_0)$ combined with linear translations $(\Delta y, \Delta z)$ are mapped into a single $4 \times 4$ transformation matrix for direct scene-graph assignment:

```python
def make_yz_transform(y0_mm, z0_mm, dy_mm, dz_mm, ang_rad):
    ca = math.cos(ang_rad)
    sa = math.sin(ang_rad)
    ty_mm = (y0_mm + dy_mm) - (y0_mm * ca - z0_mm * sa)
    tz_mm = (z0_mm + dz_mm) - (y0_mm * sa + z0_mm * ca)
    mat = adsk.core.Matrix3D.create()
    mat.setCell(1, 1, ca)
    mat.setCell(1, 2, -sa)
    mat.setCell(1, 3, ty_mm / 10.0) # mm -> cm for Fusion 360
    mat.setCell(2, 1, sa)
    mat.setCell(2, 2, ca)
    mat.setCell(2, 3, tz_mm / 10.0)
    return mat
```

---

## 5. Ephemeral `Kinematic_Stage` Collision Sweep

Never rely solely on static endpoints ($s = 0.0$ and $s = 1.0$) for kinematic verification:
1. Isolate moving subassemblies into an ephemeral `Kinematic_Stage` component via `copyPasteBodies`.
2. Step through normalized stroke $s \in \{0.00, 0.25, 0.50, 0.75, 1.00\}$.
3. Run native `design.analyzeInterference(stage_bodies)` with threshold $V > 3.0\text{ mm}^3$.
4. Delete `stage_occ` upon completion to leave the parametric timeline 100% clean.
