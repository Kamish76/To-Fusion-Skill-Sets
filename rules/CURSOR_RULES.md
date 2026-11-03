# Cursor & Windsurf Rules: Fusion 360 Autonomous CAD

When assisting with Autodesk Fusion 360 CAD generation via `fusion-mcp`:
1. **Centimeter API standard:** Fusion 360 uses centimeters internally (`cm = mm / 10.0`). Divide all mm by 10.0.
2. **Parametric features only:** Generate sketches, user parameters, extrusions, revolves, and pattern features. Never use `bRepBodies.addByMesh`.
3. **Dedicated occurrences:** Wrap parts in `root.occurrences.addNewComponent(transform)`.
4. **Visual verification:** Always capture `get_screenshot` (`iso-top-right`) after modifying bodies.
5. **Fast kinematics:** Update `occurrence.transform` matrix directly; do not create timeline `MoveFeatures`.
6. **Model directory isolation:** Put files in `models/<NN>_<Model_Name>/` (`scripts/`, `renders/`, `workspace/`).
