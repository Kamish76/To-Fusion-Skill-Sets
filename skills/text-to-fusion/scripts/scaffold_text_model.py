#!/usr/bin/env python3
"""
Scaffolds a new parametric CAD model subfolder inside a CAD monorepo or project.
Uses the unified Model Context (CAD-ICM) standard (CONTEXT.md, SPEC.md, DECISIONS.md, TIMELINE.md, assets/).
Usage:
    python3 scaffold_text_model.py "<Model_Name>" [--envelope "WxDxH"] [--root "/path/to/repo"]
"""
import os
import sys
import argparse
from pathlib import Path

# Add repo root to sys.path to access tools.scaffold_model
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    from tools.scaffold_model import scaffold_model_directory
except ImportError:
    # If called outside repo root, fallback dynamically
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../tools")))
    from scaffold_model import scaffold_model_directory

def main():
    parser = argparse.ArgumentParser(description="Scaffold a new CAD model folder with Model-Level ICM Context")
    parser.add_argument("name", help="Name of the model (e.g. 'Modular_Desk_Organizer')")
    parser.add_argument("--envelope", default="200 x 150 x 100 mm", help="Approximate bounding envelope")
    parser.add_argument("--category", default="Mechanical / 3D Print", help="Category of the model")
    parser.add_argument("--root", default=None, help="Root folder of the CAD repository containing models/")
    parser.add_argument("--desc", default="", help="Description of model design intent")
    args = parser.parse_args()

    model_path = scaffold_model_directory(
        name=args.name,
        envelope=args.envelope,
        category=args.category,
        repo_root=args.root,
        description=args.desc
    )
    print(f"✅ Successfully scaffolded Model Context in: {model_path}")

if __name__ == "__main__":
    main()
