## Fusion 360 Autonomous CAD Workflow

- **Unit Conversion (`cm` vs `mm`):** Fusion 360's internal API (`adsk.core.ValueInput.createByReal()`) strictly uses **centimeters (`cm`)**. Whenever dimensions are specified in `mm`, always divide by `10.0` (e.g., `25mm` -> `2.5`) or define a helper `def mm(val): return adsk.core.ValueInput.createByReal(val / 10.0)` at the top of every `execute_api_script`.
- **Pre-Flight Canary Probe:** Before running geometry generation, verify Fusion 360 is open with an active document via `app = adsk.core.Application.get()` and `design = adsk.fusion.Design.cast(app.activeProduct)`. Fail fast if unreachable.
- **Parametric Solid Bodies Only:** Strictly forbidden to convert faceted meshes to solids (`addByMesh`). Always synthesize native parametric timeline features (sketches, parameters, extrusions, revolves).
- **Component Occurrence Isolation:** Build every model or part in its own component occurrence (`root.occurrences.addNewComponent(...)`). Never leave loose bodies on the root component.
- **Doc Lookup First:** Before using unfamiliar `adsk.fusion` features (e.g., lofts, threads, shells, sweeps, or STL export), call `get_api_documentation` first to verify exact method signatures.
- **Self-Contained Scripts:** In `execute_api_script`, write clean Python scripts that grab `app` and `design`, create a dedicated `Component`, and wrap operations in `try/except` returning readable tracebacks on failure.
- **Visual Self-Verification Loop:** After running `execute_api_script` to generate or modify geometry, ALWAYS call `get_screenshot` (`view="iso-top-right"`, `width=1024`, `height=1024`) to visually inspect the result and verify no features failed or went inverted.
- **High-Speed Animation:** Manipulate `occurrence.transform` matrix directly rather than adding timeline `MoveFeatures`.
