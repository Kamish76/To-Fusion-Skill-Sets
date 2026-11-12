# Changelog

All notable changes to the `To-Fusion-Skill-Sets` repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.1.0] - 2026-11-08

### Fixed
- **[to-fusion-sync]**: support directory copy mode on Windows to ensure Antigravity skill discovery
- **[3mf-to-fusion]**: Fix extraction staging order, single MeshBody binding, component opacity, and multi-part handover cleanup
### Changed
- **[core]**: Harden CI workflow with unit test execution, 3MF pipeline tests, dev branch trigger, and update packaging to v1.1.0
- **[3mf-to-fusion]**: Restructure pipeline into per-part phased feature ledger, batched X/Y/Z section packs, in-CAD isolated staging, and quantitative slice diffs
- **[3mf-to-fusion]**: Establish In-CAD Mesh-First Staging & Multi-Perspective Metrology protocol with marketing photo ban and ghost overlay verification
### Added
- **[to-fusion-animate]**: Add to-fusion-animate skill for scene-graph animation, ephemeral Kinematic_Stage collision checks, and ping-pong GIF compilation
- **[to-fusion-dev-sync]**: Dedicated developer and beta-skills sync engine for dev branch laptop handoffs
- **[to-fusion-sync]**: Universal repository and agent runtime sync engine across workstations
- **[text-to-fusion]**: Added kinematic-linkages.md reference, Maker's Supply M3 BOM synthesis, ephemeral Kinematic_Stage 3D BRep collision sweep, and zero-dependency PowerShell .NET GIF89a compiler fallback
- **[media-to-fusion]**: Added Archetype 4 (Burmester 2-position 4-bar 90-deg vertical stow linkage with hyperplane separation), 2-column U-cradle routing, and Maker's Supply M3 hardware stack-up
- **[media-to-fusion]**: Harvest stepped orthogonal linkages (FTO archetype #3) and Fusion API gotchas #5-#8 (BRep dissociation, extrude cut negation, golden translation, screenshot halos)
- **[text-to-fusion]**: add tools/fusion_editor/ in-place editing suite and Model-Level CAD-ICM context scaffolding
- **[3mf-to-fusion]**: add conical PIP hinge calculator, kinematic subassembly grouping, idempotent occurrence scoping rule, and pure cylindrical modeling mandate
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
