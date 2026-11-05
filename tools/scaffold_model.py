#!/usr/bin/env python3
"""
Scaffold Model: Initializes a standardized Model Project Context (CAD-ICM) structure.
Enforces the 4-pillar context standard:
  1. CONTEXT.md (Design Intent, Kinematic Tree, Reference Index)
  2. SPEC.md (Envelope, Tolerances, BOM)
  3. DECISIONS.md (Architectural Decision Records / ADRs)
  4. TIMELINE.md (Chronological Prompt & Feature Change Audit Log)
  5. assets/ (Safe store for user-provided media, reference photos, renders)
"""
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

def find_monorepo_root(custom_root=None):
    if custom_root and os.path.exists(custom_root):
        return os.path.abspath(custom_root)

    # Environment variables
    env_root = os.environ.get("CAD_MONOREPO_ROOT") or os.environ.get("FUSION_PROJECT_ROOT")
    if env_root and os.path.exists(env_root):
        return os.path.abspath(env_root)

    # Check ancestors for 'models/' folder
    curr = os.path.abspath(os.getcwd())
    while curr and curr != "/":
        if os.path.isdir(os.path.join(curr, "models")):
            return curr
        curr = os.path.dirname(curr)

    # Known local paths
    user_home = Path.home()
    for fallback in [
        user_home / "Desktop" / "JEBZ DEVVV" / "-to-Fusion-Project",
        user_home / "Desktop" / "JEBZ DEVVV" / "Media-To-Fusion-Projects",
        Path.cwd(),
    ]:
        if fallback.exists():
            return str(fallback.resolve())

    return os.path.abspath(os.getcwd())

def get_next_model_index(models_dir):
    if not os.path.exists(models_dir):
        return 1
    existing = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
    indices = []
    import re
    for d in existing:
        m = re.match(r"^(\d+)", d)
        if m:
            indices.append(int(m.group(1)))
    return max(indices) + 1 if indices else 1

def scaffold_model_directory(
    name: str,
    envelope: str = "200 x 150 x 100 mm",
    category: str = "Mechanical / 3D Print",
    repo_root: str = None,
    description: str = "",
    reference_files: list = None
) -> str:
    root = find_monorepo_root(repo_root)
    models_dir = os.path.join(root, "models")
    os.makedirs(models_dir, exist_ok=True)

    clean_name = name.replace(" ", "_").replace("-", "_")
    idx = get_next_model_index(models_dir)
    folder_name = f"{idx:02d}_{clean_name}"
    model_path = os.path.join(models_dir, folder_name)

    # Directories
    os.makedirs(os.path.join(model_path, "assets", "references"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "assets", "renders"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "docs"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "scripts", "edits"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "workspace"), exist_ok=True)

    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. CONTEXT.md (Model Context & Reference Architecture)
    with open(os.path.join(model_path, "CONTEXT.md"), "w") as f:
        f.write(f"""# Model {idx:02d}: {clean_name} — Master Design Context

Date Initialized: {now_iso}  
Status: Active Design  
Envelope: `{envelope}`  

---

## 1. System Intent & Design Objectives
{description or "Mechanical assembly and parametric solid model engineered for FDM 3D printing and precise functional operation."}

---

## 2. Kinematic & Subassembly Architecture
| Component / Occurrence | Role | Kinematic Joint / Motion | Mating Counterpart |
| :--- | :--- | :--- | :--- |
| `01_Base_Frame` | Primary structural chassis | Fixed datum | Workspace floor |
| `02_Moving_Carrier` | Sliding carriage / slider | Prismatic rail ($X$-axis) | `01_Base_Frame` guide slots |

---

## 3. Reference Artifacts & Media Index
All user-provided media, reference photos, drawings, and baseline files are archived in `assets/references/`:
| Filename | Type | Description & Dimensions Derived |
| :--- | :--- | :--- |
| *(None yet)* | Image / 3MF | *Drop reference photos or diagrams into assets/references/* |

---

## 4. Active Engineering Standards & Clearances
- **FDM Sliding Fit:** $0.30 - 0.40\\text{{ mm}}$ diametral / radial air gap.
- **FDM Press Fit:** $0.15 - 0.20\\text{{ mm}}$ interference clearance.
- **Captive DIN 934 Hex Pocket:** AF $+0.20\\text{{ mm}}$, depth nominal $+0.20\\text{{ mm}}$.
- **Fasteners Standard:** DIN 7991 M3 Countersunk screws ($\\varnothing 3.20\\text{{ mm}}$ clearance bore).
""")

    # 2. SPEC.md (Datum & Specifications)
    with open(os.path.join(model_path, "SPEC.md"), "w") as f:
        f.write(f"""# Specification: {clean_name}

## 1. Physical Envelope & Datum
- **Nominal Envelope:** {envelope}
- **Category:** {category}
- **Target Print Bed:** Bambu Lab X1C / P1S ($256 \\times 256 \\times 256\\text{{ mm}}$)
- **Primary Material:** PLA / PETG ($0.40\\text{{ mm}}$ nozzle, $0.20\\text{{ mm}}$ layer height)

## 2. Bill of Materials (BOM)
| Item | Specification | Qty | Role | Source |
| :--- | :--- | :---: | :--- | :--- |
| **Fasteners** | DIN 7991 M3 × 10 mm | TBD | Structural assembly | Off-the-shelf |
| **Hex Nuts** | DIN 934 M3 | TBD | Captive hex pockets | Off-the-shelf |
| **Magnets** | $\\varnothing 8.0 \\times 3.0\\text{{ mm}}$ Neodymium | TBD | Magnetic closure | Off-the-shelf |
""")

    # 3. DECISIONS.md (Mechanical Architectural Decision Records - ADRs)
    with open(os.path.join(model_path, "DECISIONS.md"), "w") as f:
        f.write(f"""# Design Decision Records (ADR): {clean_name}

Record mechanical trade-offs, clearance choices, and hardware dimensions to prevent regressions.

---

### ADR-001: Initial Tolerance & Hardware Baseline
- **Date:** {now_iso}
- **Status:** Accepted
- **Context:** Initializing model tolerances for FDM 3D printing.
- **Decision:** Standardize on $0.35\\text{{ mm}}$ radial clearance for sliding interfaces and $0.20\\text{{ mm}}$ clearance for captive hex nut and magnet pockets.
- **Consequences:** Eliminates binding on layer-line ridges without causing excessive mechanical wobble.
""")

    # 4. TIMELINE.md (Chronological Prompt & Feature Change Audit Log)
    with open(os.path.join(model_path, "TIMELINE.md"), "w") as f:
        f.write(f"""# Change & Prompt Timeline: {clean_name}

Chronological audit log of user directives, edit tiers, targeted features, and health verifications.

---

### [{now_iso}] Model Scaffolding & Context Initialization
- **Directive:** Project initialized via `tools/scaffold_model.py`.
- **Target Envelope:** `{envelope}`
- **Status:** Baseline context, reference directories, and ADR-001 established.
""")

    # 5. README.md
    with open(os.path.join(model_path, "README.md"), "w") as f:
        f.write(f"""# {clean_name}

Parametric CAD model engineered via To-Fusion skill sets and Model-Level ICM.

## Directory Structure
- `CONTEXT.md`: System intent, kinematic tree, and reference index.
- `SPEC.md`: Physical envelope, tolerances, and BOM table.
- `DECISIONS.md`: Architectural Decision Records (ADRs) and trade-offs.
- `TIMELINE.md`: Chronological log of prompts and feature edits.
- `assets/references/`: User-provided sketches, reference photos, 3MFs.
- `assets/renders/`: Viewport verification screenshots.
- `scripts/`: Parametric generators and surgical edit logs.

## Quickstart
Ensure Autodesk Fusion 360 is running, then inspect or edit:
```bash
python3 tools/fusion_editor/inspect_model.py
```
""")

    # .gitignore for scratch workspace
    with open(os.path.join(model_path, "workspace", ".gitignore"), "w") as f:
        f.write("*\n!.gitignore\n")

    return model_path

def main():
    parser = argparse.ArgumentParser(description="Scaffold Model Project Context (CAD-ICM)")
    parser.add_argument("name", help="Name of the model (e.g. 'Photo_Strip_Holder')")
    parser.add_argument("--envelope", default="200 x 150 x 100 mm", help="Approximate bounding envelope")
    parser.add_argument("--category", default="Mechanical / 3D Print", help="Category of the model")
    parser.add_argument("--root", default=None, help="Root folder of the CAD repository")
    parser.add_argument("--desc", default="", help="Description of model design intent")
    args = parser.parse_args()

    path = scaffold_model_directory(
        name=args.name,
        envelope=args.envelope,
        category=args.category,
        repo_root=args.root,
        description=args.desc
    )
    print(f"✅ Successfully scaffolded Model Context in: {path}")

if __name__ == "__main__":
    main()
