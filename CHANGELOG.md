# Changelog

All notable changes to the `To-Fusion-Skill-Sets` repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]



### Fixed
- **[3mf-to-fusion]**: Fix extraction staging order, single MeshBody binding, component opacity, and multi-part handover cleanup
### Changed
- **[3mf-to-fusion]**: Restructure pipeline into per-part phased feature ledger, batched X/Y/Z section packs, in-CAD isolated staging, and quantitative slice diffs
- **[3mf-to-fusion]**: Establish In-CAD Mesh-First Staging & Multi-Perspective Metrology protocol with marketing photo ban and ghost overlay verification
### Added
- **[core]**: Initialized public git repository with multi-agent support (Antigravity, Claude, Cursor)
- Staging area for upcoming changes, improvements, and fixes.

---

## [1.0.0] - 2026-11-03

### Added
- **Initial Public Release of To-Fusion Skill Suite**:
  - `skills/3mf-to-fusion`: Advanced CAD reverse-engineering engine for `.3mf` and `.stl` files.
    - Slice-and-dice metrology engine (`inspect_3mf.py`) detecting planar tiers, turned profiles, obround slots, hex pockets, and pattern arrays.
    - 95th-percentile circumscribed circle radius calculation to compensate for tessellation chord errors.
    - Strict avoidance of `bRepBodies.addByMesh` / `MeshToBREP` in favor of 100% native parametric timeline sketches, driving user parameters, extrusions, and revolves.
    - Reference theory: `references/mesh-to-cad-theory.md` and `references/feature-reconstruction-recipes.md`.
  - `skills/media-to-fusion`: Computer vision metrology & kinematic synthesis from photos, technical drawings, and videos.
    - Multimodal frame extraction and contour analysis engine (`process_media.py`) with calibrated dual-contrast pixel grids and Canny edge detection.
    - Multi-tier scale calibration ("Golden Datum") supporting IKEA Skådis patterns (40mm pitch, 5x15mm slots), DIN fasteners, USB-C ports, and ergonomic references.
    - Coplanar echelon multi-pin parallelogram kinematic synthesis for multi-tier cantilever mechanisms.
    - Reference theory: `references/kinematic-archetypes.md`, `references/fdm-hardware-tolerances.md`, and `references/fusion-api-gotchas.md`.
  - `skills/text-to-fusion`: Natural language to parametric CAD assemblies.
    - Parametric specification engine with envelope constraints, wall thicknesses, and user parameter bindings.
    - Standardized DIN hardware BOM generation (DIN 7991 M3 countersunk screws, DIN 934 M3 captive hex pockets, retaining washers).
    - Non-destructive showroom variant staging and A/B exploration pattern.
    - High-speed `Occurrence.transform` Matrix3D kinematics and multi-frame animation pipeline.
    - Reference theory: `references/prompt-to-geometry-patterns.md`, `references/exploded-view-guidelines.md`, `references/assembly-animation-pipeline.md`, and `references/variant-management-and-undo.md`.
- **Engineering Rulesets**:
  - `rules/fusion-autonomous-cad-rules.md`: Mandatory rules for centimeters (`cm = mm / 10.0`), pre-flight canary probes, visual self-verification loops (`get_screenshot`), and timeline hygiene.
  - `rules/model-isolation-rules.md`: Strict project directory layout (`models/<NN>_<Model_Name>/`) and root directory cleanliness guarantees.
  - Drop-in agent configurations:
    - `rules/CLAUDE.md` for Anthropic Claude Code & Claude Desktop.
    - `rules/GEMINI.md` for Google Antigravity & Gemini CLI.
    - `rules/CURSOR_RULES.md` for Cursor & Windsurf.
- **Portability & Distribution**:
  - Universal Python requirements (`requirements.txt`, `pyproject.toml`) removing hardcoded system paths.
  - One-click setup script (`setup.sh`) supporting Antigravity, Claude Code, and standalone Python environments.
  - Local sync utility (`tools/sync_local.sh`) linking active Antigravity installations directly to this Git repository.
  - Change tracking CLI (`tools/log_change.py`) to systematically record skill improvements, audit agent modifications, and bump versions.
