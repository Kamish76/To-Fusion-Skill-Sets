#!/usr/bin/env python3
"""
section_pack.py - batched evidence for ONE part (design-frame STL from inspect_3mf.py).

  pack <part.design.stl> --out DIR      all views + X/Y/Z sections + feature candidates + pack_index.md
  zoom <part.design.stl> --box x0,y0,z0,x1,y1,z1 --out DIR   same, clipped to a region at high resolution
  diff <source.design.stl> <built.stl> --out DIR            section-by-section built-vs-source gate (exit 1 on fail)

Review every image of a pack together before modelling anything. Ids in pack_index.md (S-X-03, V-top, F-12)
are what the Feature Ledger cites as evidence.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

# Auto-switch to repo virtual environment if dependencies are missing from current python
try:
    import cv2
    import numpy as np
    import trimesh
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import unary_union
except ImportError as e:
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    venv_py = repo_root / ".venv" / "bin" / "python3"
    if venv_py.exists() and sys.executable != str(venv_py):
        os.execv(str(venv_py), [str(venv_py)] + sys.argv)
    sys.stderr.write(
        f"Missing required dependency: {e}\n"
        "Ensure Python dependencies are installed:\n"
        "  pip install -r requirements.txt (or run within the project virtual environment)\n"
    )
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent))
from inspect_3mf import analyze_primitive, fit_circle_circumscribed  # noqa: E402

AXN = {"X": 0, "Y": 1, "Z": 2}
UV = {0: (1, 2), 1: (0, 2), 2: (0, 1)}  # in-plane (u, v) axes of a section normal to X / Y / Z
UNIT = np.eye(3)
HDR = 28  # header strip height in px
FILL_BGR = (205, 170, 120)
TOL_DEG = 2.0


def mesh_load(path):
    m = trimesh.load(str(path), force="mesh")
    if not m.is_watertight:
        sys.stderr.write(f"WARNING: {path} is not watertight; sections/volume may be unreliable\n")
    return m


# ------------------------------------------------------------------ sections
def seg_signature(mesh, a, pos):
    """Cheap per-position signature (perimeter, boundary centroid u, v) from raw plane/mesh segments."""
    n = UNIT[a]
    o = np.zeros(3)
    o[a] = pos
    seg = trimesh.intersections.mesh_plane(mesh, n, o)
    if len(seg) == 0:
        return np.zeros(3)
    ln = np.linalg.norm(seg[:, 1] - seg[:, 0], axis=1)
    mid = seg.mean(axis=1)
    u, v = UV[a]
    tot = max(ln.sum(), 1e-9)
    return np.array([tot, (mid[:, u] * ln).sum() / tot, (mid[:, v] * ln).sum() / tot])


def differs(s0, s1):
    return abs(s1[0] - s0[0]) > max(0.5, 0.008 * max(s0[0], s1[0])) or np.hypot(s1[1] - s0[1], s1[2] - s0[2]) > 0.25


def scan_plateaus(mesh, a, lo, hi, step=0.4):
    """Splits the axis range into plateaus of constant cross-section signature; boundaries refined by bisection."""
    n = int(np.clip(math.ceil((hi - lo) / step), 40, 300))
    ps = np.linspace(lo + 0.05, hi - 0.05, n)
    sigs = [seg_signature(mesh, a, p) for p in ps]
    cuts, ref = [], 0
    for i in range(1, n):
        if differs(sigs[ref], sigs[i]):
            l, h = ps[i - 1], ps[i]
            for _ in range(7):
                m = 0.5 * (l + h)
                if differs(sigs[ref], seg_signature(mesh, a, m)):
                    h = m
                else:
                    l = m
            cuts.append(0.5 * (l + h))
            ref = i
    edges = [lo] + cuts + [hi]
    return [{"start": round(float(edges[i]), 3), "end": round(float(edges[i + 1]), 3),
             "mid": round(0.5 * (edges[i] + edges[i + 1]), 3), "width": round(edges[i + 1] - edges[i], 3)}
            for i in range(len(edges) - 1)]


def section_polys(mesh, a, pos):
    o = np.zeros(3)
    o[a] = pos
    sec = mesh.section(plane_origin=o, plane_normal=UNIT[a])
    if sec is None:
        return []
    u, v = UV[a]
    M = np.eye(4)
    M[0, :3], M[1, :3], M[2, :3] = UNIT[u], UNIT[v], UNIT[a]
    p2, _ = sec.to_2D(to_2D=M)
    return [p for p in p2.polygons_full if p.area > 0.01]


def pick_positions(plateaus, lo, hi, max_plateau=12, n_even=5):
    big = sorted(plateaus, key=lambda p: -p["width"])[:max_plateau]
    pos = [p["mid"] for p in big] + list(np.linspace(lo, hi, n_even + 2)[1:-1])
    out = []
    for p in sorted(pos):
        if not out or p - out[-1] > 0.3:
            out.append(round(float(p), 3))
    return out


# ------------------------------------------------------------------ drawing
def nice_step(span):
    for s in (0.5, 1, 2, 5, 10, 20, 50):
        if span / s <= 14:
            return s
    return 100


def geom_mask(geom, window, ppm, shape):
    """Rasterise a shapely (Multi)Polygon (holes respected) into a uint8 mask for window (u0,u1,v0,v1)."""
    u0, _, _, v1 = window
    mask = np.zeros(shape, np.uint8)

    def pts(coords):
        return (np.array([[(x - u0) * ppm, (v1 - y) * ppm] for x, y in coords]) * 16).astype(np.int32)

    polys = [] if geom is None or geom.is_empty else (list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom])
    for p in sorted([g for g in polys if isinstance(g, Polygon)], key=lambda g: -g.area):
        cv2.fillPoly(mask, [pts(p.exterior.coords)], 255, shift=4)
        for r in p.interiors:
            cv2.fillPoly(mask, [pts(r.coords)], 0, shift=4)
    return mask


def blank_cell(window, ppm, title):
    u0, u1, v0, v1 = window
    W, H = int(round((u1 - u0) * ppm)) + 1, int(round((v1 - v0) * ppm)) + 1
    img = np.full((H + HDR, W, 3), 255, np.uint8)
    body = img[HDR:]
    step = nice_step(max(u1 - u0, v1 - v0))
    for g in np.arange(math.ceil(u0 / step) * step, u1, step):
        x = int((g - u0) * ppm)
        cv2.line(body, (x, 0), (x, H), (225, 225, 225), 1)
        cv2.putText(body, f"{g:g}", (x + 2, H - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (130, 130, 130), 1)
    for g in np.arange(math.ceil(v0 / step) * step, v1, step):
        y = int((v1 - g) * ppm)
        cv2.line(body, (0, y), (W, y), (225, 225, 225), 1)
        cv2.putText(body, f"{g:g}", (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (130, 130, 130), 1)
    cv2.putText(img, title, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def draw_outline(body, geom, window, ppm, color=(40, 40, 40)):
    u0, _, _, v1 = window
    polys = [] if geom is None or geom.is_empty else (list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom])
    for p in polys:
        if not isinstance(p, Polygon):
            continue
        for ring in [p.exterior] + list(p.interiors):
            pts = (np.array([[(x - u0) * ppm, (v1 - y) * ppm] for x, y in ring.coords]) * 16).astype(np.int32)
            cv2.polylines(body, [pts], True, color, 1, cv2.LINE_AA, shift=4)


def paint(body, mask, color):
    body[mask > 0] = color


def section_cell(polys, window, ppm, title):
    img = blank_cell(window, ppm, title)
    body = img[HDR:]
    geom = unary_union(polys) if polys else None
    paint(body, geom_mask(geom, window, ppm, body.shape[:2]), FILL_BGR)
    draw_outline(body, geom, window, ppm)
    return img


def sheet(cells, path, max_dim=3600, pad=8):
    """Tile equally-sized cells into one or more pages; returns saved paths."""
    if not cells:
        return []
    ch, cw = max(c.shape[0] for c in cells), max(c.shape[1] for c in cells)
    cols = int(np.clip((max_dim) // (cw + pad), 1, 3))
    rows = int(np.clip(max_dim // (ch + pad), 1, 8))
    per = cols * rows
    paths = []
    for pi in range(0, len(cells), per):
        page = cells[pi:pi + per]
        r = math.ceil(len(page) / cols)
        img = np.full((r * (ch + pad) + pad, cols * (cw + pad) + pad, 3), 255, np.uint8)
        for k, c in enumerate(page):
            y, x = pad + (k // cols) * (ch + pad), pad + (k % cols) * (cw + pad)
            img[y:y + c.shape[0], x:x + c.shape[1]] = c
        p = Path(f"{path}_p{pi // per + 1}.png")
        cv2.imwrite(str(p), img)
        paths.append(p.name)
    return paths


# ------------------------------------------------------------------ views
ORTHO = {  # name: (u, v, w) with w toward the viewer, right-handed
    "top": (UNIT[0], UNIT[1], UNIT[2]), "bottom": (UNIT[0], -UNIT[1], -UNIT[2]),
    "front": (UNIT[0], UNIT[2], -UNIT[1]), "back": (-UNIT[0], UNIT[2], UNIT[1]),
    "right": (UNIT[1], UNIT[2], UNIT[0]), "left": (-UNIT[1], UNIT[2], -UNIT[0]),
}


def iso_basis(sx, sy):
    w = np.array([sx, sy, 1.0])
    w /= np.linalg.norm(w)
    u = np.cross(UNIT[2], w)
    u /= np.linalg.norm(u)
    return u, np.cross(w, u), w


def render_view(mesh, basis, mode, window, ppm, title):
    """
    Orthographic painter's-algorithm render with sharp-edge overlay. mode: shade | depth.
    shortcut: painter's order by mean face depth (not a z-buffer), fine for CAD-like parts, re-check any odd
    occlusion with a section; upgrade to a per-pixel z-buffer if intersecting large faces show artefacts.
    """
    u, v, w = basis
    P = np.stack([mesh.vertices @ u, mesh.vertices @ v, mesh.vertices @ w], 1)
    u0, u1, v0, v1 = window
    img = blank_cell(window, ppm, title)
    body = img[HDR:]
    body[:] = 255
    tri = P[mesh.faces]
    n = mesh.face_normals
    front = n @ w > 1e-6
    wd = tri[:, :, 2].mean(1)
    if mode == "shade":
        nv = np.stack([n @ u, n @ v, n @ w], 1)
        L = np.array([0.35, 0.5, 0.8])
        L /= np.linalg.norm(L)
        lam = np.clip(nv @ L, 0, 1)
        cols = (np.array([205, 185, 160]) * (0.3 + 0.7 * lam)[:, None]).clip(0, 255).astype(np.uint8)
    else:
        t = (wd - P[:, 2].min()) / max(np.ptp(P[:, 2]), 1e-9)
        cols = cv2.applyColorMap((t * 255).astype(np.uint8)[:, None], cv2.COLORMAP_TURBO)[:, 0, :]
        title += f"  depth {P[:, 2].min():.2f}..{P[:, 2].max():.2f} (blue far, red near)"
        cv2.putText(img, title[len(title) - 60:], (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    def px(pts):
        return (np.stack([(pts[..., 0] - u0) * ppm, (v1 - pts[..., 1]) * ppm], -1) * 16).astype(np.int32)

    fi = np.nonzero(front)[0]
    adj, ang, edges = mesh.face_adjacency, mesh.face_adjacency_angles, mesh.face_adjacency_edges
    sharp = (ang > math.radians(25)) & (front[adj[:, 0]] | front[adj[:, 1]])
    e_pts = px(P[edges[sharp]][:, :, :2])
    e_key = P[edges[sharp]][:, :, 2].mean(1) + 1e-3
    f_pts = px(tri[fi][:, :, :2])
    keys = np.concatenate([wd[fi], e_key])
    for k in np.argsort(keys):
        if k < len(fi):
            cv2.fillConvexPoly(body, f_pts[k], tuple(int(c) for c in cols[fi[k]]), shift=4)
        else:
            cv2.polylines(body, [e_pts[k - len(fi)]], False, (30, 30, 30), 1, cv2.LINE_AA, shift=4)
    # 10 mm scale bar (ortho views only; labelled so iso views are not mistaken for measurable)
    if mode in ("shade", "depth") and abs(abs(w[2]) - 1 / math.sqrt(3)) > 1e-3:
        x0, y0 = 8, body.shape[0] - 14
        cv2.line(body, (x0, y0), (x0 + int(10 * ppm), y0), (0, 0, 200), 3)
        cv2.putText(body, "10 mm", (x0, y0 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 200), 1, cv2.LINE_AA)
    return img


def view_window(mesh, basis, pad=1.0, box=None):
    u, v, _ = basis
    pts = mesh.vertices if box is None else np.array([[x, y, z] for x in (box[0], box[3]) for y in (box[1], box[4])
                                                      for z in (box[2], box[5])])
    pu, pv = pts @ u, pts @ v
    return (pu.min() - pad, pu.max() + pad, pv.min() - pad, pv.max() + pad)


def fit_ppm(window, cap_w=1500, cap_h=1500, max_ppm=40):
    u0, u1, v0, v1 = window
    return float(min(max_ppm, cap_w / (u1 - u0), cap_h / (v1 - v0)))


def render_all_views(mesh, out, box=None, max_ppm=14):
    names, cells = [], []
    bases = dict(ORTHO)
    for sx, sy, nm in ((1, -1, "iso-top-right"), (-1, -1, "iso-top-left"), (1, 1, "iso-back-right"), (-1, 1, "iso-back-left")):
        bases[nm] = iso_basis(sx, sy)
    for nm, b in bases.items():
        win = view_window(mesh, b, pad=1.0 if box is None else 0.3, box=box)
        ppm = fit_ppm(win, 1100, 1100, max_ppm if box is None else 40)
        for mode in (("shade", "depth") if not nm.startswith("iso") else ("shade",)):
            img = render_view(mesh, b, mode, win, ppm, f"V-{nm} [{mode}]")
            fn = f"V-{nm}-{mode}.png"
            cv2.imwrite(str(out / fn), img)
            names.append(fn)
            cells.append(img)
    return names, sheet(cells, str(out / "sheet_views"))


# ------------------------------------------------------------------ features
def _bounds(tri):
    return [[round(float(x), 3) for x in tri.reshape(-1, 3).min(0)], [round(float(x), 3) for x in tri.reshape(-1, 3).max(0)]]


def planar_levels(mesh):
    """Axis-aligned planar faces grouped by offset: gives every step height / pocket depth directly."""
    out, n, a, tris = [], mesh.face_normals, mesh.area_faces, mesh.triangles
    cth = math.cos(math.radians(TOL_DEG))
    for ax in range(3):
        for sg, lab in ((1, "+"), (-1, "-")):
            sel = np.nonzero(n[:, ax] * sg > cth)[0]
            if not len(sel):
                continue
            off = tris[sel][:, :, ax].mean(1)
            idx = np.argsort(off)
            groups, cur = [], [idx[0]]
            for i in idx[1:]:
                if off[i] - off[cur[-1]] > 0.05:
                    groups.append(cur)
                    cur = []
                cur.append(i)
            groups.append(cur)
            for g in groups:
                fs = sel[g]
                area = float(a[fs].sum())
                if area >= 1.0:
                    out.append({"kind": "planar_face", "normal": lab + "XYZ"[ax],
                                "offset_mm": round(float(np.average(off[g], weights=a[fs])), 3),
                                "area_mm2": round(area, 2), "bounds_mm": _bounds(tris[fs])})
    return out


def smooth_components(mesh):
    n = mesh.face_normals
    nonax = ~((np.abs(n) > math.cos(math.radians(TOL_DEG))).any(1))
    adj = mesh.face_adjacency
    ok = (mesh.face_adjacency_angles < math.radians(35)) & nonax[adj[:, 0]] & nonax[adj[:, 1]]
    nodes = np.nonzero(nonax)[0]
    if not len(nodes):
        return []
    return trimesh.graph.connected_components(adj[ok], nodes=nodes, min_len=1)


def angled_and_curved(mesh):
    """Non-axis-aligned smooth patches -> angled planes (chamfer / dovetail rail) or cylinders (boss / hole / arc)."""
    angled, cyl = [], []
    n, a, tris = mesh.face_normals, mesh.area_faces, mesh.triangles
    for comp in smooth_components(mesh):
        comp = np.asarray(comp)
        area = float(a[comp].sum())
        if area < 0.3:
            continue
        mn = (n[comp] * a[comp][:, None]).sum(0)
        mn /= np.linalg.norm(mn)
        spread = float(np.degrees(np.arccos(np.clip(n[comp] @ mn, -1, 1)).max()))
        b = _bounds(tris[comp])
        if spread < 3.0:
            if area < 1.5:
                continue
            d = float(np.average(tris[comp].mean(1) @ mn, weights=a[comp]))
            ax = int(np.argmax(np.abs(mn)))
            others = [i for i in range(3) if i != ax]
            ang = round(float(np.degrees(np.arctan2(abs(mn[others[np.argmax(np.abs(mn[others]))]]), abs(mn[ax])))), 1)
            angled.append({"kind": "angled_plane", "normal": [round(float(x), 3) for x in mn],
                           "plane_offset_mm": round(d, 3), "angle_from_dominant_axis_deg": ang,
                           "area_mm2": round(area, 2), "bounds_mm": b})
            continue
        for ax in range(3):
            if np.abs(n[comp][:, ax]).max() > 0.08:
                continue
            o = UV[ax]
            vi = np.unique(mesh.faces[comp])
            pts = mesh.vertices[vi]
            c, r, err = fit_circle_circumscribed(pts[:, list(o)])
            if c is None or err > 0.03 or r < 0.2:
                continue
            ang = np.degrees(np.arctan2(pts[:, o[1]] - c[1], pts[:, o[0]] - c[0]))
            gaps = np.diff(np.sort(np.concatenate([ang, [ang.min() + 360]])))
            cover = float(360 - gaps.max())
            rad = tris[comp].mean(1)[:, list(o)] - c
            outward = bool(((n[comp][:, list(o)] * rad).sum(1) * a[comp]).sum() > 0)
            unit_r = (pts[:, list(o)] - c) / np.maximum(np.linalg.norm(pts[:, list(o)] - c, axis=1), 1e-9)[:, None]
            bulge = unit_r.mean(0)
            bulge = bulge / max(np.linalg.norm(bulge), 1e-9)
            cyl.append({"kind": "cylinder_surface", "axis": "XYZ"[ax], "center_mm": [round(float(c[0]), 3), round(float(c[1]), 3)],
                        "center_axes": ["XYZ"[o[0]], "XYZ"[o[1]]], "radius_mm": round(float(r), 3),
                        "diameter_mm": round(float(2 * r), 3), "coverage_deg": round(cover, 0),
                        "role": "boss/convex" if outward else "hole/concave",
                        "range_mm": [round(float(pts[:, ax].min()), 3), round(float(pts[:, ax].max()), 3)],
                        "height_mm": round(float(np.ptp(pts[:, ax])), 3), "area_mm2": round(area, 2), "bounds_mm": b,
                        "bulge_dir": [round(float(bulge[0]), 3), round(float(bulge[1]), 3)]})
            break
        else:
            if area >= 1.5:
                angled.append({"kind": "curved_surface", "area_mm2": round(area, 2), "bounds_mm": b,
                               "normal_spread_deg": round(spread, 1)})
    return angled, cyl


def merge_cylinders(cyl):
    """Arc fragments split at axis-aligned tangent points (quadrant seams) -> one cylinder per axis/centre/radius/range."""
    out = []
    for c in cyl:
        for m in out:
            if (m["axis"] == c["axis"] and m["role"] == c["role"] and abs(m["radius_mm"] - c["radius_mm"]) < 0.06
                    and np.abs(np.subtract(m["center_mm"], c["center_mm"])).max() < 0.08
                    and np.abs(np.subtract(m["range_mm"], c["range_mm"])).max() < 0.06):
                bd = np.add(np.multiply(m["bulge_dir"], m["coverage_deg"]), np.multiply(c["bulge_dir"], c["coverage_deg"]))
                m["bulge_dir"] = (bd / max(np.linalg.norm(bd), 1e-9)).round(3).tolist()
                m["coverage_deg"] = min(360.0, m["coverage_deg"] + c["coverage_deg"])
                m["area_mm2"] = round(m["area_mm2"] + c["area_mm2"], 2)
                lo = np.minimum(m["bounds_mm"][0], c["bounds_mm"][0])
                hi = np.maximum(m["bounds_mm"][1], c["bounds_mm"][1])
                m["bounds_mm"] = [lo.round(3).tolist(), hi.round(3).tolist()]
                break
        else:
            out.append(dict(c))
    return out


def pair_slots(cyl):
    """Two ~180 deg arcs of equal radius/range that bulge away from each other = obround slot (or rounded boss)."""
    arcs = [c for c in cyl if 140 <= c["coverage_deg"] <= 220]
    used, slots = set(), []
    for i, p in enumerate(arcs):
        if i in used:
            continue
        best = None
        for j in range(len(arcs)):
            q = arcs[j]
            if j == i or j in used or p["axis"] != q["axis"] or p["role"] != q["role"]:
                continue
            if abs(p["radius_mm"] - q["radius_mm"]) > 0.06 or np.abs(np.subtract(p["range_mm"], q["range_mm"])).max() > 0.06:
                continue
            d = np.subtract(q["center_mm"], p["center_mm"])
            L = float(np.linalg.norm(d))
            if L < 0.2:
                continue
            dh = d / L
            if np.dot(p["bulge_dir"], dh) < -0.9 and np.dot(q["bulge_dir"], -dh) < -0.9 and (best is None or L < best[1]):
                best = (j, L, d)
        if best:
            j, L, d = best
            q = arcs[j]
            used |= {i, j}
            slots.append({"kind": "obround_slot" if "hole" in p["role"] else "obround_boss", "axis": p["axis"],
                          "center_mm": [round((p["center_mm"][0] + q["center_mm"][0]) / 2, 3),
                                        round((p["center_mm"][1] + q["center_mm"][1]) / 2, 3)],
                          "center_axes": p["center_axes"], "width_mm": round(2 * p["radius_mm"], 3),
                          "overall_length_mm": round(L + 2 * p["radius_mm"], 3), "straight_length_mm": round(L, 3),
                          "orientation_along": p["center_axes"][0] if abs(d[0]) >= abs(d[1]) else p["center_axes"][1],
                          "range_mm": p["range_mm"], "depth_mm": p["height_mm"]})
    keep = [c for k, c in enumerate(arcs) if k not in used] + [c for c in cyl if c not in arcs]
    return slots, keep


def find_patterns(items, key_fn, label):
    groups = {}
    for it in items:
        groups.setdefault(key_fn(it), []).append(it)
    out = []
    for k, g in groups.items():
        if len(g) < 2:
            continue
        pts = np.array([x["center_mm"] for x in g])
        axis_i = int(np.argmax(np.ptp(pts, axis=0)))
        order = np.argsort(pts[:, axis_i])
        pitches = np.diff(pts[order][:, axis_i])
        linear = bool(np.ptp(pts[:, 1 - axis_i]) < 0.1)
        out.append({"kind": f"{label}_pattern", "count": len(g), "key": str(k), "centers_mm": pts[order].round(3).tolist(),
                    "center_axes": g[0]["center_axes"], "linear": linear,
                    "pitch_mm": pitches.round(3).tolist(), "uniform": bool(len(pitches) and np.ptp(pitches) < 0.1)})
    return out


def section_primitives(mesh, axis_name, a, plateau_reps):
    out = []
    for sid, pos, rng in plateau_reps:
        for poly in section_polys(mesh, a, pos):
            tot = float(poly.area)
            for geom, is_hole in [(Polygon(poly.exterior), False)] + [(Polygon(r), True) for r in poly.interiors]:
                prim = analyze_primitive(geom, tot if not is_hole else tot * 4)
                if not prim:
                    continue
                prim.pop("points_xy_mm", None)
                prim.update({"section": sid, "axis": axis_name, "position_mm": pos, "plateau_range_mm": rng,
                             "is_hole": is_hole, "in_plane_axes": ["XYZ"[UV[a][0]], "XYZ"[UV[a][1]]]})
                out.append(prim)
    return out


def extract_features(mesh, plat_reps):
    feats = {"planar_faces": planar_levels(mesh)}
    angled, cyl = angled_and_curved(mesh)
    slots, cyl = pair_slots(merge_cylinders(cyl))
    feats["angled_planes"] = [x for x in angled if x["kind"] == "angled_plane"]
    feats["curved_surfaces"] = [x for x in angled if x["kind"] == "curved_surface"]
    feats["cylinders"] = cyl
    feats["obround_slots"] = slots
    feats["patterns"] = (find_patterns(cyl, lambda c: (c["axis"], c["role"], c["radius_mm"], tuple(c["range_mm"])), "cylinder")
                         + find_patterns(slots, lambda s: (s["axis"], s["kind"], s["width_mm"], s["overall_length_mm"],
                                                           s["orientation_along"], tuple(s["range_mm"])), "slot"))
    feats["section_primitives"] = []
    for ax, reps in plat_reps.items():
        feats["section_primitives"] += section_primitives(mesh, ax, AXN[ax], reps)
    i = 0
    for k, v in feats.items():
        for it in v:
            i += 1
            it["id"] = f"F-{i:02d}"
    return feats


def bounds_hit(it, box):
    b = it.get("bounds_mm")
    if b is None or box is None:
        return True
    return all(b[0][i] <= box[i + 3] and b[1][i] >= box[i] for i in range(3))


# ------------------------------------------------------------------ pack / zoom
def build_sections(mesh, out, lo_hi, windows, ppm_cap=30, n_even=5, max_plateau=12):
    """Plateau scan + section sheets per axis. Returns ({axis: plateaus}, {axis: reps}, images)."""
    plateaus, reps_out, images, loops = {}, {}, {}, {}
    for ax, a in AXN.items():
        lo, hi = lo_hi[a]
        plateaus[ax] = scan_plateaus(mesh, a, lo, hi)
        positions = pick_positions(plateaus[ax], lo, hi, max_plateau, n_even)
        win = windows[a]
        ppm = float(min(ppm_cap, 1800 / (win[1] - win[0]), 1200 / (win[3] - win[2])))
        cells, reps = [], []
        for k, pos in enumerate(positions, 1):
            sid = f"S-{ax}-{k:02d}"
            polys = section_polys(mesh, a, pos)
            plat = next((p for p in plateaus[ax] if p["start"] <= pos <= p["end"]), None)
            rng = [float(plat["start"]), float(plat["end"])] if plat else None
            cells.append(section_cell(polys, win, ppm, f"{sid}  {ax}={pos:.3f} mm  (plateau {rng})  u={'XYZ'[UV[a][0]]} v={'XYZ'[UV[a][1]]}"))
            reps.append((sid, pos, rng))
            loops[sid] = {"axis": ax, "position_mm": pos, "plateau_range_mm": rng, "in_plane_axes": ["XYZ"[UV[a][0]], "XYZ"[UV[a][1]]],
                          "polygons": [{"outer": [[round(x, 3), round(y, 3)] for x, y in p.simplify(0.02).exterior.coords],
                                        "holes": [[[round(x, 3), round(y, 3)] for x, y in r.coords] for r in p.simplify(0.02).interiors]}
                                       for p in polys]}
        images[ax] = sheet(cells, str(out / f"sheet_sections_{ax}"))
        reps_out[ax] = reps
    return plateaus, reps_out, images, loops


def write_index(path, title, mesh, view_names, view_sheets, plateaus, images, feats, box=None):
    L = [f"# {title}", "",
         f"Extents (design frame) {' x '.join(f'{x:.3f}' for x in mesh.extents)} mm, volume {mesh.volume:.1f} mm3, faces {len(mesh.faces)}",
         f"Region: {box if box else 'whole part'}", "",
         "## Images (review ALL together before modelling)",
         f"- view sheets: {', '.join(view_sheets)}", f"- single views: {', '.join(view_names)}"]
    for ax, ims in images.items():
        L.append(f"- {ax}-sections: {', '.join(ims)}")
    L += ["", "## Plateaus (constant cross-section ranges; every change is a feature boundary)"]
    for ax, pl in plateaus.items():
        L += [f"### {ax}", "| range mm | width |", "|---|---|"] + [f"| {p['start']} .. {p['end']} | {p['width']} |" for p in pl]
    L += ["", "## Axis-aligned planar faces (offset = step level)", "| id | normal | offset mm | area | bounds |", "|---|---|---|---|---|"]
    L += [f"| {f['id']} | {f['normal']} | {f['offset_mm']} | {f['area_mm2']} | {f['bounds_mm']} |" for f in feats["planar_faces"]]
    for key, hdr in (("angled_planes", "Angled planes (chamfer / dovetail rail candidates)"), ("cylinders", "Cylinders (boss / hole / arc)"),
                     ("obround_slots", "Obround slots / bosses"), ("patterns", "Patterns"), ("curved_surfaces", "Other curved surfaces (fillets / organic)")):
        L += ["", f"## {hdr}"] + [f"- `{f['id']}` {json.dumps({k: v for k, v in f.items() if k != 'id'})}" for f in feats[key]]
    L += ["", f"## Section primitives ({len(feats['section_primitives'])}, see features.json)",
          "", "## Reviewer reminders",
          "- A feature seen in any image but absent from features.json is still a feature: put it in the Ledger.",
          "- Hidden regions? Run `zoom --box ...` and review the new batch."]
    Path(path).write_text("\n".join(L))


def cmd_pack(a):
    mesh = mesh_load(a.part)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    vn, vs = render_all_views(mesh, out)
    lo_hi = {i: tuple(mesh.bounds[:, i]) for i in range(3)}
    windows = {i: (mesh.bounds[0, UV[i][0]] - 1, mesh.bounds[1, UV[i][0]] + 1, mesh.bounds[0, UV[i][1]] - 1, mesh.bounds[1, UV[i][1]] + 1)
               for i in range(3)}
    plateaus, reps, images, loops = build_sections(mesh, out, lo_hi, windows, n_even=a.even)
    feats = extract_features(mesh, reps)
    (out / "features.json").write_text(json.dumps(feats, indent=1))
    (out / "section_loops.json").write_text(json.dumps(loops))
    write_index(out / "pack_index.md", f"Analysis pack: {Path(a.part).name}", mesh, vn, vs, plateaus, images, feats)
    print(f"pack -> {out}/pack_index.md  ({sum(len(v) for v in reps.values())} sections, "
          f"{len(feats['angled_planes'])} angled planes, {len(feats['cylinders'])} cylinders, {len(feats['obround_slots'])} slots)")


def cmd_zoom(a):
    mesh = mesh_load(a.part)
    box = [float(x) for x in a.box.split(",")]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    clipped = mesh
    try:
        for ax in range(3):
            for sg, val in ((1, box[ax]), (-1, box[ax + 3])):
                o = np.zeros(3)
                o[ax] = val
                clipped = clipped.slice_plane(o, UNIT[ax] * sg, cap=True)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"WARNING: capped clip failed ({e}); rendering unclipped mesh\n")
        clipped = mesh
    vn, vs = render_all_views(clipped, out, box=box)
    lo_hi = {i: (box[i], box[i + 3]) for i in range(3)}
    windows = {i: (box[UV[i][0]] - 0.3, box[UV[i][0] + 3] + 0.3, box[UV[i][1]] - 0.3, box[UV[i][1] + 3] + 0.3) for i in range(3)}
    plateaus, reps, images, loops = build_sections(mesh, out, lo_hi, windows, ppm_cap=60, n_even=3, max_plateau=8)
    feats = extract_features(mesh, reps)
    for k in feats:
        feats[k] = [f for f in feats[k] if bounds_hit(f, box)]
    (out / "features.json").write_text(json.dumps(feats, indent=1))
    (out / "section_loops.json").write_text(json.dumps(loops))
    write_index(out / "pack_index.md", f"Zoom pack: {Path(a.part).name}", clipped, vn, vs, plateaus, images, feats, box)
    print(f"zoom -> {out}/pack_index.md")


# ------------------------------------------------------------------ diff
def cmd_diff(a):
    src, built = mesh_load(a.source), mesh_load(a.built)
    ratio = built.extents.max() / max(src.extents.max(), 1e-9)
    if 0.09 < ratio < 0.11:
        built.apply_scale(10.0)
        print("built STL looked like cm -> scaled x10")
    ext_delta = float(np.abs(built.extents - src.extents).max())
    built.apply_translation(src.bounds[0] - built.bounds[0])
    vol_pct = 100.0 * (built.volume - src.volume) / max(src.volume, 1e-9)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, fails = [], []
    if ext_delta > a.ext_max:
        fails.append(f"bbox extents differ by {ext_delta:.2f} mm")
    if abs(vol_pct) > a.vol_pct:
        fails.append(f"volume differs {vol_pct:+.2f}%")
    for ax, ai in AXN.items():
        lo, hi = src.bounds[:, ai]
        pl = scan_plateaus(src, ai, lo, hi)
        for pos in pick_positions(pl, lo, hi, 12, 9):
            s = unary_union(section_polys(src, ai, pos)) if section_polys(src, ai, pos) else Polygon()
            bp = section_polys(built, ai, pos)
            b = unary_union(bp) if bp else Polygon()
            union = s.union(b).area
            xor = s.symmetric_difference(b).area
            iou = 1.0 if union < 1e-9 else s.intersection(b).area / union
            rows.append({"axis": ax, "pos": pos, "iou": round(iou, 4), "xor_mm2": round(xor, 3), "src_area": round(s.area, 2), "_s": s, "_b": b})
            if iou < a.iou_min or xor > a.xor_max:
                fails.append(f"{ax}={pos:.2f}: IoU {iou:.3f}, XOR {xor:.2f} mm2")
    for ax, ai in AXN.items():
        ax_rows = sorted([r for r in rows if r["axis"] == ax], key=lambda r: -r["xor_mm2"])[:6]
        u, v = UV[ai]
        win = (src.bounds[0, u] - 1, src.bounds[1, u] + 1, src.bounds[0, v] - 1, src.bounds[1, v] + 1)
        ppm = float(min(30, 1800 / (win[1] - win[0]), 1200 / (win[3] - win[2])))
        cells = []
        for r in ax_rows:
            img = blank_cell(win, ppm, f"{ax}={r['pos']:.2f} IoU {r['iou']:.3f} XOR {r['xor_mm2']:.2f}mm2  red=missing in built, blue=extra in built")
            body = img[HDR:]
            sh = body.shape[:2]
            paint(body, geom_mask(r["_s"].intersection(r["_b"]), win, ppm, sh), (210, 210, 210))
            paint(body, geom_mask(r["_s"].difference(r["_b"]), win, ppm, sh), (60, 60, 230))
            paint(body, geom_mask(r["_b"].difference(r["_s"]), win, ppm, sh), (230, 120, 40))
            cells.append(img)
        sheet(cells, str(out / f"diff_{ax}"))
    for r in rows:
        r.pop("_s"), r.pop("_b")
    report = {"volume_src": round(src.volume, 2), "volume_built": round(built.volume, 2), "volume_pct": round(vol_pct, 3),
              "extents_delta_mm": round(ext_delta, 3), "slices": len(rows),
              "worst": sorted(rows, key=lambda r: -r["xor_mm2"])[:10], "fails": fails, "passed": not fails}
    (out / "diff_report.json").write_text(json.dumps(report, indent=1))
    print(f"volume {vol_pct:+.2f}%  extents delta {ext_delta:.2f} mm  slices {len(rows)}  worst XOR {report['worst'][0]['xor_mm2'] if rows else 0} mm2")
    print("PASS" if not fails else "FAIL:\n  " + "\n  ".join(fails[:15]))
    sys.exit(0 if not fails else 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pack")
    s.add_argument("part")
    s.add_argument("--out", required=True)
    s.add_argument("--even", type=int, default=5, help="evenly spaced sections per axis on top of plateau sections")
    s.set_defaults(fn=cmd_pack)
    s = sub.add_parser("zoom")
    s.add_argument("part")
    s.add_argument("--box", required=True, help="x0,y0,z0,x1,y1,z1 in mm (design frame)")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_zoom)
    s = sub.add_parser("diff")
    s.add_argument("source")
    s.add_argument("built")
    s.add_argument("--out", required=True)
    s.add_argument("--iou-min", dest="iou_min", type=float, default=0.97)
    s.add_argument("--xor-max", dest="xor_max", type=float, default=6.0, help="max per-slice XOR area mm2")
    s.add_argument("--vol-pct", dest="vol_pct", type=float, default=2.0)
    s.add_argument("--ext-max", dest="ext_max", type=float, default=0.3, help="max bbox extent delta mm")
    s.set_defaults(fn=cmd_diff)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
