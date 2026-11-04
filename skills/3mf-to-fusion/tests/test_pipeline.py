#!/usr/bin/env python3
"""
Self-check for the 3mf-to-fusion pipeline (no third-party files): run `python3 test_pipeline.py` with the repo venv.
Builds a Bambu-style 3MF (multi-component object + a rotated duplicate), then checks inventory, feature
candidates and the section-diff gate.
"""
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    import numpy as np
    import trimesh
    from shapely.geometry import LineString, Polygon
except ImportError as e:
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    venv_py = repo_root / ".venv" / "bin" / "python3"
    if venv_py.exists() and sys.executable != str(venv_py):
        os.execv(str(venv_py), [str(venv_py)] + sys.argv)
    sys.stderr.write(
        f"Missing required dependency: {e}\n"
        "Ensure Python dependencies are installed in .venv\n"
    )
    sys.exit(1)

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"


def make_plate(with_boss=True):
    """40 x 60 x 4 plate, through obround slot (2.1 wide, 20 straight), 45 deg chamfer on one top edge, optional boss."""
    outline = Polygon([(-20, -30), (20, -30), (20, 30), (-20, 30)])
    slot = LineString([(0, -10), (0, 10)]).buffer(1.05, quad_segs=16)
    plate = trimesh.creation.extrude_polygon(Polygon(outline.exterior, [slot.exterior]), 4.0)
    plate = plate.slice_plane([0, 29, 4], [0, -1, -1], cap=True)  # normal points to the side that is kept
    if with_boss:
        boss = trimesh.creation.cylinder(radius=1.0, height=0.8, sections=48)
        boss.apply_translation([10, 15, 4.4])
        plate = trimesh.util.concatenate([plate, boss])
    return plate


def xf(T):
    """4x4 column-form -> 3MF 12-number row-vector transform string."""
    return " ".join(f"{v:.9g}" for v in list(T[:3, :3].T.flatten()) + list(T[:3, 3]))


def object_xml(objs):
    rows = []
    for oid, m in objs.items():
        v = "".join(f'<vertex x="{a:.6f}" y="{b:.6f}" z="{c:.6f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        rows.append(f'<object id="{oid}" type="model"><mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh></object>')
    return f'<model xmlns="{CORE}"><resources>{"".join(rows)}</resources></model>'


def write_3mf(path):
    # Stored on edge (thin axis = source X) like a slicer plate, to prove the design frame restores thin axis -> Z.
    R = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
    plate = make_plate()
    plate.apply_transform(R)
    block = trimesh.creation.box([10, 10, 10])
    flip = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])
    move = trimesh.transformations.translation_matrix([50, 0, 0])
    model = (f'<model xmlns="{CORE}" xmlns:p="{PROD}" unit="millimeter"><resources>'
             f'<object id="10" type="model"><components>'
             f'<component p:path="/3D/Objects/object_1.model" objectid="1" transform="{xf(np.eye(4))}"/>'
             f'<component p:path="/3D/Objects/object_1.model" objectid="2" transform="{xf(move)}"/></components></object>'
             f'<object id="20" type="model"><components>'
             f'<component p:path="/3D/Objects/object_2.model" objectid="3" transform="{xf(flip)}"/></components></object>'
             f'</resources><build><item objectid="10"/><item objectid="20"/></build></model>')
    settings = ('<config><object id="10"><metadata key="name" value="Assembly"/>'
                '<part id="1"><metadata key="name" value="plate"/></part><part id="2"><metadata key="name" value="block"/></part></object>'
                '<object id="20"><metadata key="name" value="plate_copy"/><part id="3"><metadata key="name" value="plate_copy"/></part></object>'
                '<plate><metadata key="plater_id" value="1"/><model_instance><metadata key="object_id" value="10"/></model_instance></plate>'
                '<plate><metadata key="plater_id" value="2"/><model_instance><metadata key="object_id" value="20"/></model_instance></plate></config>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("3D/3dmodel.model", model)
        z.writestr("3D/Objects/object_1.model", object_xml({1: plate, 2: block}))
        z.writestr("3D/Objects/object_2.model", object_xml({3: plate}))
        z.writestr("Metadata/model_settings.config", settings)


def run(*args, check=True):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    if check and r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return r


def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        write_3mf(td / "t.3mf")
        run(SCRIPTS / "inspect_3mf.py", td / "t.3mf", "--out-dir", td / "ex")
        man = json.loads((td / "ex/manifest.json").read_text())
        parts = {p["name"]: p for p in man["parts"]}

        # inventory: 3 bodies -> 2 phases; duplicate shares the phase; real names + plates kept
        assert len(man["parts"]) == 2, [p["name"] for p in man["parts"]]
        plate = parts["plate"]
        assert sorted(i["name"] for i in plate["instances"]) == ["plate", "plate_copy"]
        assert sorted(i["plate"] for i in plate["instances"]) == [1, 2]
        assert "block" in parts
        # design frame: X=40, Y=60, thin axis (4 + 0.8 boss) -> Z even though stored on edge
        assert np.allclose(plate["extents_xyz_mm"], [40, 60, 4.8], atol=0.2), plate["extents_xyz_mm"]

        # print-in-place kinematic subassembly detection
        assert "pip_subassemblies" in man, "pip_subassemblies missing from manifest"
        pip_subs = man["pip_subassemblies"]
        assert len(pip_subs) >= 1, pip_subs
        assert pip_subs[0]["name"] == "Assembly"
        assert sorted(pip_subs[0]["parts"]) == ["block", "plate"]
        assert sorted(pip_subs[0]["phases"]) == [1, 2]
        assert pip_subs[0]["plate"] == 1

        # features
        pk = td / "pk"
        run(SCRIPTS / "section_pack.py", "pack", td / "ex" / plate["stl_file"], "--out", pk)
        f = json.loads((pk / "features.json").read_text())
        assert any(abs(a["angle_from_dominant_axis_deg"] - 45) < 1.5 for a in f["angled_planes"]), f["angled_planes"]
        assert any(abs(c["radius_mm"] - 1.0) < 0.1 and abs(c["height_mm"] - 0.8) < 0.1 and "boss" in c["role"]
                   for c in f["cylinders"]), f["cylinders"]
        assert any(abs(s["width_mm"] - 2.1) < 0.1 and abs(s["straight_length_mm"] - 20) < 0.3 for s in f["obround_slots"]), f["obround_slots"]
        for img in ("sheet_sections_X_p1.png", "sheet_sections_Y_p1.png", "sheet_sections_Z_p1.png", "sheet_views_p1.png"):
            assert (pk / img).exists(), img

        # diff gate: identical passes, missing boss fails
        src = td / "ex" / plate["stl_file"]
        run(SCRIPTS / "section_pack.py", "diff", src, src, "--out", td / "d_same")
        nb = make_plate(with_boss=False)
        nb.apply_translation([0, 0, 0])
        nb.export(str(td / "noboss.stl"))
        s = trimesh.load(str(src))
        nb.apply_translation(s.bounds[0] - nb.bounds[0])
        nb.export(str(td / "noboss.stl"))
        r = run(SCRIPTS / "section_pack.py", "diff", src, td / "noboss.stl", "--out", td / "d_bad", "--vol-pct", "0.01", check=False)
        assert r.returncode == 1 and "FAIL" in r.stdout, r.stdout + r.stderr

        # conical print-in-place calculator CLI
        r_calc = run(
            SCRIPTS / "conical_pip_calc.py",
            "--knuckle-dia", "4.828",
            "--gap-radial", "0.35",
            "--gap-axial", "0.40",
            "--taper-deg", "30",
            "--format", "json",
        )
        calc_json = json.loads(r_calc.stdout)
        assert abs(calc_json["male_cone"]["base_radius_mm"] - 1.650) < 0.01
        assert abs(calc_json["male_cone"]["height_mm"] - 2.20) < 0.05
        assert abs(calc_json["male_cone"]["engagement_depth_mm"] - 1.80) < 0.05
        assert abs(calc_json["male_cone"]["tip_dia_mm"] - 0.76) < 0.02
        assert abs(calc_json["female_socket"]["entrance_radius_mm"] - 1.769) < 0.02
        assert abs(calc_json["female_socket"]["depth_mm"] - 2.00) < 0.05
        assert abs(calc_json["tolerances"]["normal_3d_air_gap_mm"] - 0.303) < 0.01
        assert calc_json["feasibility"]["is_feasible"] is True

        r_code = run(
            SCRIPTS / "conical_pip_calc.py",
            "--knuckle-dia", "4.828",
            "--format", "fusion-api",
        )
        assert "male_base_radius_cm" in r_code.stdout
        assert "female_entrance_radius_cm" in r_code.stdout

    print("OK: inventory, design frame, duplicate grouping, PIP subassemblies, feature candidates, diff gate, conical PIP calc")


if __name__ == "__main__":
    main()
