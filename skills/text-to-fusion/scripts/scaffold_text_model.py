#!/usr/bin/env python3
"""
Scaffolds a new parametric CAD model subfolder inside a CAD monorepo or project.
Usage:
    python3 scaffold_text_model.py "<Model_Name>" [--envelope "WxDxH"] [--root "/path/to/repo"]
"""
import os
import sys
import argparse
from pathlib import Path

def find_monorepo_root(custom_root=None):
    if custom_root and os.path.exists(custom_root):
        return os.path.abspath(custom_root)

    # Check environment variables
    env_root = os.environ.get("CAD_MONOREPO_ROOT") or os.environ.get("FUSION_PROJECT_ROOT")
    if env_root and os.path.exists(env_root):
        return os.path.abspath(env_root)

    # Check current working directory or ancestors for models and shared folders
    curr = os.path.abspath(os.getcwd())
    while curr and curr != "/":
        if os.path.isdir(os.path.join(curr, "models")):
            return curr
        curr = os.path.dirname(curr)

    # Known local fallbacks
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
    for d in existing:
        prefix = d.split('_')[0]
        if prefix.isdigit():
            indices.append(int(prefix))
    return max(indices) + 1 if indices else 1

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new CAD model folder")
    parser.add_argument("name", help="Name of the model (e.g. 'Modular_Desk_Organizer')")
    parser.add_argument("--envelope", default="200 x 150 x 100 mm", help="Approximate bounding envelope")
    parser.add_argument("--category", default="Mechanical / 3D Print", help="Category of the model")
    parser.add_argument("--root", default=None, help="Root folder of the CAD repository containing models/")
    args = parser.parse_args()

    repo_root = find_monorepo_root(args.root)
    models_dir = os.path.join(repo_root, "models")
    os.makedirs(models_dir, exist_ok=True)

    clean_name = args.name.replace(" ", "_")
    idx = get_next_model_index(models_dir)
    folder_name = f"{idx:02d}_{clean_name}"
    model_path = os.path.join(models_dir, folder_name)

    os.makedirs(os.path.join(model_path, "scripts"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "docs"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "renders"), exist_ok=True)
    os.makedirs(os.path.join(model_path, "workspace"), exist_ok=True)

    # SPEC.md
    with open(os.path.join(model_path, "SPEC.md"), "w") as f:
        f.write(f"""# Model {idx:02d}: {clean_name}

## 1. Specifications & Datum
- **Envelope:** {args.envelope}
- **Category:** {args.category}
- **Status:** In Design

## 2. Bill of Materials (BOM)
| Item | Spec | Qty | Function |
| :--- | :--- | :---: | :--- |
| **Screws** | DIN 7991 M3 × 10 mm | TBD | Fasteners |
| **Nuts** | DIN 934 M3 | TBD | Captive hex pockets |
""")

    # README.md
    with open(os.path.join(model_path, "README.md"), "w") as f:
        f.write(f"""# {clean_name}

Parametric solid CAD model generated via To-Fusion skill set.

## Quickstart
Ensure Autodesk Fusion 360 is active, then run:
```bash
python3 scripts/build_model.py
```
""")

    # GEMINI.md
    with open(os.path.join(model_path, "GEMINI.md"), "w") as f:
        f.write(f"""## {clean_name} CAD Model Routing
1. Universal CAD helpers: import from `../../shared/` if available.
2. Model scripts live in `scripts/`. Renders live in `renders/`.
3. Standard DIN fasteners: default to DIN 7991 M3 screws and DIN 934 M3 nuts.
""")

    print(f"✅ Successfully scaffolded Model {idx:02d} at {model_path}")

if __name__ == "__main__":
    main()
