# Contributing to To-Fusion-Skill-Sets

Welcome! This repository maintains autonomous CAD engineering skills and rulesets for Autodesk Fusion 360, built for AI coding assistants such as **Google Antigravity**, **Anthropic Claude Code**, and **Cursor / Windsurf**.

---

## 1. Core Engineering Principles

Every skill and script in this repository adheres to these strict non-negotiables:

1. **Pure Parametric CAD (No Faceted Mesh Conversions):**
   - We **never** convert meshes directly to BRep bodies (`bRepBodies.addByMesh` / `MeshToBREP`).
   - All geometry must be reconstructed using native sketches, construction planes, user parameters, extrusions, revolves, sweeps, and pattern features.
2. **Centimeter API standard (`cm = mm / 10.0`):**
   - Fusion 360's internal database operates strictly in centimeters. Always divide millimeter inputs by `10.0`.
3. **Visual Self-Verification:**
   - Geometry must always be verified visually using `get_screenshot` (`iso-top-right`) to verify no feature inversion, unexpected interference, or missing clearances.
4. **Platform Agnostic & Portable:**
   - Never commit absolute machine paths (e.g. `/Users/...` or `C:\...`). Use relative resolution or standard environment variables (`CAD_MONOREPO_ROOT`, `FUSION_PROJECT_ROOT`).

---

## 2. Documenting & Logging Changes (Mandatory)

Whenever you improve a skill, fix a bug, or add a reference pattern:

### Option A: Use the Change Logger CLI (Recommended)
```bash
# For a newly added capability:
python3 tools/log_change.py --skill 3mf-to-fusion --type added --message "Added chord error compensation for hex pockets"

# For a bug fix:
python3 tools/log_change.py --skill media-to-fusion --type fixed --message "Fixed skew in split-viewport Canny detection"
```

### Option B: Manual `CHANGELOG.md` Entry
Add your bullet under `## [Unreleased]` in [CHANGELOG.md](CHANGELOG.md):
```markdown
### Added
- **[3mf-to-fusion]**: Added chord error compensation for hex pockets.
```

---

## 3. Adding a New Skill

When creating a new `-to-fusion` skill (e.g., `sheetmetal-to-fusion`, `pcb-to-fusion`):

1. **Create Directory:**
   ```text
   skills/<new-skill-name>/
   ├── SKILL.md            # YAML frontmatter (name, description) + step-by-step phases
   ├── references/         # Theory, formulas, engineering clearances, and gotchas
   └── scripts/            # Python CLI tools with portable shebang (#!/usr/bin/env python3)
   ```
2. **Register in `skills_manifest.json`:**
   Add the new skill entry with description, entrypoint, scripts, and package dependencies.
3. **Log Initial Capability:**
   Run `python3 tools/log_change.py --skill <new-skill-name> --type added --message "Initial release of <new-skill-name>"`.

---

## 4. Releasing a New Version

To package unreleased changes into a formal semver release:
```bash
python3 tools/log_change.py --release 1.1.0
git commit -am "chore(release): bump version to 1.1.0"
git tag v1.1.0
```
