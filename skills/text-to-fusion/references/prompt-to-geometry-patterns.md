# Prompt-to-Geometry Mapping Patterns

Translating natural language mechanical descriptions into explicit mathematical constraints, sketch curves, and solid features in Autodesk Fusion 360.

---

## 1. Spatial & Enclosure Descriptors

| User Prompt Phrase | Engineering Interpretation | Exact Fusion 360 Implementation |
| :--- | :--- | :--- |
| *"No lids, just the thing itself"* | Open-top container / tray | Shell feature or extrude with top face omitted. Wall thickness typically `2.0 - 2.5 mm`. |
| *"Full height back & side walls"* | Asymmetric rim height | Extrude side and rear profiles up to master tray height $H$, while keeping front wall low ($0.4 - 0.5 \times H$) for easy part extraction. |
| *"In 2 pieces, connects somehow"* | Modular split tray with lap or tongue joint | Split total depth into `Front_Piece` and `Rear_Piece`. Provide `0.20 mm` per-side clearance on mating step tabs/tongues so they interlock cleanly without fasteners. |
| *"Cover front during transport"* | Invertible lid / transport seal | The rear piece has a perimeter rebate matching the front piece rim. When flipped 180° in the collapsed state, it nests over the front tray to prevent contents spilling. |
| *"1 row, 2 columns"* | Subdivided bin pocket | Longitudinal divider along center: width $W / 2$, divider wall thickness $1.6 - 2.0\text{ mm}$ with $R = 1.0\text{ mm}$ floor fillets. |
| *"Beside the whole assembly"* | Zero-clearance mating face | Check mating face centroids: $X_{\text{bar\_inner}} = X_{\text{tray\_wall\_outer}}$. Displacement must equal exact coordinate delta, not guessed offsets. |

---

## 2. Fastener & Joint Descriptors

| User Prompt Phrase | Hardware Specification | Modeled Geometry |
| :--- | :--- | :--- |
| *"Show the screws and nuts"* | Standard DIN Hardware | DIN 7991 M3 × 10 mm countersunk screws + DIN 934 M3 hex nuts. |
| *"Maker's Supply hardware"* | Maker's Supply M3 Fasteners | M3 × 10 BHCS (`AA172`) / SHCS (`AA159`) + DIN 934 M3 hex nut (`AB005`). |
| *"Captured nut / hex hole"* | Friction press-fit nut pocket | Regular hexagon across flats (AF): modeled at **`5.70 mm`** (`+0.20 mm` FDM clearance over `5.50 mm` nut), depth `2.40 - 2.50 mm`. |
| *"Flush button-head screw"* | Outer screw counterbore | $\varnothing 6.20\text{ mm}$ cylindrical recess $\times 1.50\text{ mm}$ deep centered over $\varnothing 3.30\text{ mm}$ through-bore. |
| *"Flush countersunk screw"* | Countersink bore | 90° conical countersunk pocket ($d_k = 6.20\text{ mm}$, depth $k = 1.80\text{ mm}$) centered over $\varnothing 3.20\text{ mm}$ through-bore. |
| *"Retaining washer"* | 3D-printed washer clamp | $\varnothing 9.50\text{ mm}$ OD × $\varnothing 3.20\text{ mm}$ ID × `1.80 mm` thick. Clamps joint pivot tip with $0.25\text{ mm}$ standoff shoulder. |
| *"Smooth rotating pivot"* | Dynamic pin joint | Cylindrical pivot boss on tray wall: $\varnothing 6.0\text{ mm}$, hole bore in linkage bar $\varnothing 6.50\text{ mm}$ (`0.25 mm` radial clearance). |
