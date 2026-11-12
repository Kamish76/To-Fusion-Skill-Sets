# Animation Rigging & Scene-Graph Patterns

Quick-reference patterns for rigging assemblies, exploded views, and multi-tier mechanisms using direct `Occurrence.transform` Matrix3D updates.

---

## 1. Planar Hinge & Linkage Motion ($SE(3)$ Mapping)

Given an occurrence pivoting around $(y_0, z_0)$ by angle $\theta(s)$ with linear offset $(\Delta y, \Delta z)$:

```python
import math
import adsk.core

def make_yz_transform(y0_mm, z0_mm, dy_mm, dz_mm, ang_rad):
    ca = math.cos(ang_rad)
    sa = math.sin(ang_rad)
    ty_mm = (y0_mm + dy_mm) - (y0_mm * ca - z0_mm * sa)
    tz_mm = (z0_mm + dz_mm) - (y0_mm * sa + z0_mm * ca)
    mat = adsk.core.Matrix3D.create()
    mat.setCell(1, 1, ca)
    mat.setCell(1, 2, -sa)
    mat.setCell(1, 3, ty_mm / 10.0) # cm conversion
    mat.setCell(2, 1, sa)
    mat.setCell(2, 2, ca)
    mat.setCell(2, 3, tz_mm / 10.0) # cm conversion
    return mat
```

---

## 2. Linear Exploded Views

For exploded illustrations, compute displacement vectors per group along dominant axes ($X$, $Y$, or $Z$) and scale by smoothstep easing:

```python
# Staggered explosion timing
s_fasteners = smoothstep(0.00, 0.40, s) # Fasteners unseat first
s_washers   = smoothstep(0.20, 0.60, s) # Washers follow
s_covers    = smoothstep(0.40, 0.85, s) # Covers lift
s_subplates = smoothstep(0.60, 1.00, s) # Internal trays slide out

trans = adsk.core.Matrix3D.create()
trans.translation = adsk.core.Vector3D.create(
    (dx_mm * s_group) / 10.0,
    (dy_mm * s_group) / 10.0,
    (dz_mm * s_group) / 10.0
)
occ.transform = trans
```

---

## 3. Ephemeral Collision Sweep Pattern

Never gamble on mid-stroke clearances:

```python
# 1. Create temporary stage
stage_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
stage_occ.component.name = "Kinematic_Stage"

# 2. Duplicate moving bodies into temporary components
# ...

# 3. Step s in [0.0, 0.25, 0.50, 0.75, 1.0]
for s in [0.0, 0.25, 0.5, 0.75, 1.0]:
    # Update transforms
    collisions = check_stage_interference(design, groups_dict, s_val=s, min_vol_mm3=3.0)
    if collisions:
        print(f"Warning: Mid-stroke collision detected at s={s:.2f}")

# 4. Mandatory cleanup
stage_occ.deleteMe()
```
