# Model Isolation & Workspace Cleanliness Rules

These rules enforce directory discipline and hygiene across CAD workspaces and monorepos using `-to-fusion` skills.

---

## 1. Clean Root Guarantee
The root directory of any CAD monorepo or project MUST remain spotless:
- **Forbidden at Workspace Root:**
  - Mesh slicing output folders (e.g. `./extracted_cad/`)
  - Computer vision media work directories (e.g. `./media_workspace/`)
  - Loose Python scripts (e.g. `test.py`, `run.py`, `build.py`)
  - Loose image renders, keyframes, or contour previews (`*.png`, `*.jpg`, `*.gif`)
  - Temporary JSON manifests or CSV dumps

---

## 2. Standard Model Directory Structure (Model-Level ICM)
Every discrete mechanical model or project must be housed in a numbered folder under `models/` adhering to the 4-pillar CAD-ICM context standard:
```text
models/<NN>_<Model_Name>/
├── CONTEXT.md                  # Master context: design intent, kinematic tree, reference index
├── SPEC.md                     # Engineering constraints, envelope, BOM, target kinematics
├── DECISIONS.md                # Architectural Decision Records (ADRs) & mechanical trade-offs
├── TIMELINE.md                 # Chronological log of user prompts, dictated edits, and health
├── README.md                   # Model summary and quickstart build instructions
├── GEMINI.md / CLAUDE.md       # Model-specific agent routing and helper imports
├── assets/                     # Safe persistent storage for media & reference files
│   ├── references/             # User sketches, photos, reference 3MF/STL, datasheets
│   └── renders/                # Viewport captures, diffs, inspection screenshots
├── docs/                       # Calculation sheets, dimension drawings, exploded views
├── scripts/                    # Python build, surgical edit, and animation scripts
│   ├── build_model.py          # Primary Fusion 360 parametric baseline generator
│   ├── edits/                  # Log of surgical edit scripts applied
│   └── generate_animation.py   # Occurrence matrix kinematic animator
└── workspace/                  # Scratch files, CV contours, sliced 3MF manifests (gitignored)
    ├── media/                  # process_media.py outputs
    └── extracted_cad/          # inspect_3mf.py outputs
```

---

## 3. Scaffolding Rule
Whenever starting a new model from text, 3MF, or media:
- Run the model scaffolder first before generating any intermediate files:
  ```bash
  python3 <path_to_skills>/text-to-fusion/scripts/scaffold_text_model.py "<Model_Name>" --envelope "WxDxH mm"
  ```
- Pass `--out-dir models/<NN>_<Model_Name>/workspace/...` to all extraction tools (`inspect_3mf.py` and `process_media.py`).

---

## 4. Shared Utilities Library (`shared/`)
- Universal CAD helpers (`fusion_client`, `cad_primitives`, `hardware_library`, `scene_animator`) live in the top-level `shared/` directory.
- `shared/` is strictly **read-only** during model generation. Never write model-specific logic, hardcoded dimensions, or output files into `shared/`.
