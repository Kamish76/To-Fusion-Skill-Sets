# Parametric Variant Management & Non-Destructive Revisions

How to handle user pivots ("let's try another set", "no lids", "let's go back to option A") without breaking Fusion 360 timeline references or corrupting models.

---

## 1. The Multi-Variant Showroom Pattern

When a user asks to explore options ("give me option 2", "try a different lid design"):
1. **Never Overwrite Active Bodies In-Place:**
   - Do not modify existing master bodies directly unless the user explicitly asks to replace them permanently.
2. **Create a Dedicated Showroom / Option Occurrence:**
   - Create a sub-component: `Sample_Options_Showroom:1` or `Accessorie_Set_2:1`.
   - Place experimental variants side-by-side on the virtual workspace floor (e.g. shifted by $Y = -350\text{ mm}$ or $X = -200\text{ mm}$).
   - Color variants with distinctive appearances (`Rack_Desert_Tan`, `Rack_Matte_White`) so the user can easily distinguish them.
3. **Selective In-Situ Substitution:**
   - When the user selects a winner ("let's go with option 2"), clone the winning bodies into the master assembly (`InSitu_Tier3_Option2`) and toggle `isLightBulbOn = False` on the rejected showroom bodies.

---

## 2. Non-Destructive Hiding vs. `deleteMe()`

### The Hazard of `deleteMe()`
Calling `body.deleteMe()` or `occurrence.deleteMe()` on objects referenced by downstream fillets, chamfers, or joints creates broken timeline warnings (yellow/red warnings) that can corrupt parametric regeneration.

### Safe Practices
1. **Body Hiding:** Set `bRepBody.isLightBulbOn = False`. The body is hidden from viewport screenshots and interference checks, but timeline history remains intact.
2. **Template Parking (Underground Translation):**
   When child occurrences reference a master template component, setting `template.isLightBulbOn = False` hides the instances!
   Instead, park the template occurrence far underground (`Z = -500.0 cm`). The template is completely off-screen, while all instanced parts in the active design render normally.

---

## 3. Mathematical Verification of Mating Faces

When a user notes that a part looks "left behind" or has an unwanted gap:
1. **Never Guess Adjustment Numbers:**
   - Do not arbitrarily change an offset from `35 mm` to `40 mm`.
2. **Inspect Bounding Boxes & World Coordinates Directly:**
   ```python
   # 1. Measure target mating face in world space
   target_face_x = target_body.boundingBox.maxPoint.x
   # 2. Measure moving body current position in world space
   moving_face_x = moving_body.boundingBox.minPoint.x + occ.transform.translation.x
   # 3. Exact delta required
   delta_x = target_face_x - moving_face_x
   ```
   This guarantees mathematical alignment with zero floating gap on the very next render!
