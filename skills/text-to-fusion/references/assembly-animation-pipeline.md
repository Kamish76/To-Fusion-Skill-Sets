# Assembly Animation & Dynamic Kinematics Pipeline

A high-performance pipeline for compiling smooth, 60fps-equivalent animated GIFs of parts driving into place and continuous 3D collision sweeps without Fusion 360 timeline rebuild delays.

---

## 1. The Core Architecture: Direct Occurrence Transforms

### Why Timeline `moveFeatures` Fails
In Fusion 360, `component.features.moveFeatures.add()` adds a parametric feature to the document history. In a 30-frame animation loop, each frame triggers a full timeline recalculation ($2.2\text{ s/frame} \implies 70\text{ seconds}$).

### The Direct Scene-Graph Method
Isolate each moving mechanical group into its own `Occurrence` (`anim_bars`, `anim_stand`, `anim_washers`, `anim_fasteners`). In each animation step, directly reassign its 4x4 affine matrix via `occ.transform`:
```python
trans = adsk.core.Matrix3D.create()
trans.translation = adsk.core.Vector3D.create(cm(dx * s), cm(dy * s), cm(dz * s))
anim_occ.transform = trans
```
- **Execution Speed:** Takes **`0.005 seconds per update`** directly on the GPU scene graph!

---

## 2. Staged Motion Choreography & Smoothstep Easing

Physical assemblies do not slam into place simultaneously. Choreograph the sequence in logical subassembly stages using normalized time $t \in [0.0, 1.0]$:

```python
def clamp(v, min_v, max_v):
    return max(min_v, min(max_v, v))

def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t) # Zero acceleration at start and stop
```

### Typical 4-Stage Assembly Sequence
1. **Stage 1: Stationary Sub-Assemblies Dock ($t \in [0.00, 0.40]$)**
   - Rear legs, backboards, or structural frames slide into the primary chassis.
2. **Stage 2: Linkage Mechanism Mounts ($t \in [0.15, 0.60]$)**
   - Linkage bars slide inward onto cylindrical tray pivot bosses.
3. **Stage 3: Retaining Elements Seat ($t \in [0.30, 0.70]$)**
   - Retaining washers slide into position against tray inner faces.
4. **Stage 4: Fasteners Torque Down ($t \in [0.40, 0.92]$)**
   - Screws drive inward through through-bores; nuts drive inward onto screw threads and recess into hex pockets.
5. **Stage 5: Alignment Fade & Final Lock ($t \ge 0.88$)**
   - Toggle `guides_occ.isLightBulbOn = (t < 0.88)` to vanish golden alignment rods as joints tighten.

---

## 3. High-Speed Frame Rendering (`saveAsImageFile`)

Instead of making 30 individual MCP API calls over the network, render all frames directly inside the Fusion 360 script in a single batch pass:
```python
for frame in range(num_frames):
    t = frame / float(num_frames - 1)
    # ... update occurrence transforms ...
    vp.refresh()
    vp.saveAsImageFile(f'/tmp/frames/frame_{frame:03d}.png', 800, 800)
```
- **Performance:** Takes **`0.08 s/frame`** (entire 28-frame sequence renders in ~3.5 seconds).

---

## 4. GIF Compilation & Loop Timing

Use `PIL.Image` to build a seamless ping-pong loop with generous holds:
- **Forward Assembly:** 28 frames @ `45 ms` ($1.26\text{ s}$)
- **Hold Assembled State:** 28 frames @ `50 ms` ($1.40\text{ s}$) — Gives the viewer ample time to inspect the fully tightened model.
- **Reverse Disassembly:** 26 frames @ `45 ms` ($1.17\text{ s}$) — Parts smoothly explode back out.
- **Hold Exploded State:** 20 frames @ `50 ms` ($1.00\text{ s}$) — Viewer inspects individual components.
- **Total Loop Duration:** $\approx 4.8\text{ seconds}$.
- **Palette Optimization:** Quantize using `f.quantize(colors=128, method=Image.Resampling.LANCZOS, dither=Image.Dither.FLOYDSTEINBERG)`. Compresses down to ~`2.3 MB` with sharp edges and zero color banding.
- **Cache-Busting Rule:** In chat environments, always generate with unique/versioned filenames (e.g., `_final.gif`, `_v2.gif`) to bypass browser image caching.

---

## 5. Ephemeral `Kinematic_Stage` & Multi-Frame 3D BRep Interference Verification

To verify that mechanisms do not collide mid-stroke:
1. Create a temporary occurrence `stage_occ = container.occurrences.addNewComponent(Matrix3D.create())`.
2. Populate rigid subassemblies into child occurrences (`Ground_Group`, `Tier2_Group`, `Bar1_Group`, etc.) using `copyPasteBodies`.
3. Step through intermediate states $s \in \{0.00, 0.25, 0.50, 0.75, 1.00\}$ and evaluate:
   ```python
   inp = design.createInterferenceInput(stage_bodies)
   inp.areCoincidentFacesIncluded = False
   results = design.analyzeInterference(inp)
   for r in results:
       if r.interferenceBody.volume * 1000.0 > 3.0: # Filter coincident face noise
           print(f"COLLISION: {r.entityOne.name} <-> {r.entityTwo.name}")
   ```
4. Call `stage_occ.deleteMe()` immediately after verification to leave the parametric timeline pristine.

---

## 6. Zero-Dependency Windows PowerShell `.NET` GIF Compiler Fallback

When `PIL` / `Pillow` or `ffmpeg` are not installed in the Python environment, invoke the native Windows Presentation Framework (`System.Windows.Media.Imaging.GifBitmapEncoder`) with binary `NETSCAPE2.0` looping block and Graphic Control Extension (GCE) delay splicing (`shared/scene_animator.py` `compile_ping_pong_gif_powershell`). This provides a 100% zero-dependency fallback producing valid looping GIF89a animations on any Windows workstation.
