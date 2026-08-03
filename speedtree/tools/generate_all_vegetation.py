"""
批量生成 mesh/ 中所有参考植被的近似模型。

每个参考文件单独输出到：
    rebuild_mesh/<参考文件名去掉扩展名>/
        model.fbx
        render.png
        metadata.json

这是第一版批处理器：它的目标是保持品类、尺寸、材质槽、LOD 和整体轮廓
相似，而不是逐顶点复制参考资产。后续可按 metadata 中记录的参数继续调参。
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from pine_gen import (MAT_BARK, MAT_LEAF, PineParams, TreeMesh, _leaf_card,
                      _normalize, _tube, generate_lods)
from fbx_writer import export_lod_fbx
import render_hq as R


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "mesh"
OUT = ROOT / "rebuild_mesh"
TEX = ROOT / "exports" / "textures"


def ensure_birch_texture():
    """Create a broad leafy clump atlas for birch previews."""
    path = TEX / "birch_leaf.png"
    if path.exists():
        return path
    TEX.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(441)
    S = 512
    hi = Image.new("RGBA", (S * 2, S * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(hi)
    colors = [(45, 96, 34, 235), (68, 126, 43, 245),
              (92, 148, 54, 230), (35, 78, 31, 220)]
    for _ in range(260):
        x, y = rng.uniform(30, S * 2 - 30, 2)
        rx, ry = rng.uniform(8, 34), rng.uniform(4, 18)
        c = colors[int(rng.integers(0, len(colors)))]
        d.ellipse((x - rx, y - ry, x + rx, y + ry), fill=c)
        d.line((x - rx * .7, y, x + rx * .7, y), fill=(28, 72, 24, 180), width=2)
    alpha = hi.getchannel("A").filter(ImageFilter.GaussianBlur(1.2))
    hi.putalpha(alpha)
    hi.resize((S, S), Image.Resampling.LANCZOS).save(path)
    return path


def variant_number(source):
    """Extract the numeric variant from names such as *_02_OneMesh.FBX."""
    nums = re.findall(r"_(\d+)(?:_|\.|$)", source, flags=re.IGNORECASE)
    return int(nums[-1]) if nums else 1


def add_quad(mesh, points, mat, uv=None, normal=None, height=1.0, phase=0.0):
    """Add one quad with the common per-polygon-vertex attributes."""
    points = [np.asarray(p, dtype=float) for p in points]
    idx = [mesh.add_vert(p) for p in points]
    if uv is None:
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    if normal is None:
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        normal = tuple(_normalize(normal))
    nrms = [normal] * 4
    cols = [(0.0, phase if mat == MAT_LEAF else 0.0, 0.0,
             min(max(float(p[2]) / height, 0.0), 1.0)) for p in points]
    mesh.add_poly(idx, mat, uv, nrms, cols)


def add_strip(mesh, points, widths, mat, height, phase, uv_span=1.0):
    """Add a curved ribbon as quads. points are its centerline."""
    points = [np.asarray(p, float) for p in points]
    for i in range(len(points) - 1):
        d = _normalize(points[i + 1] - points[i])
        side = np.cross(d, np.array([0.0, 0.0, 1.0]))
        if np.linalg.norm(side) < 1e-5:
            side = np.array([1.0, 0.0, 0.0])
        side = _normalize(side)
        a = points[i] - side * widths[i] * 0.5
        b = points[i] + side * widths[i] * 0.5
        c = points[i + 1] + side * widths[i + 1] * 0.5
        d2 = points[i + 1] - side * widths[i + 1] * 0.5
        add_quad(mesh, [a, b, c, d2], mat,
                 uv=[(0, i / max(len(points) - 1, 1) * uv_span),
                     (1, i / max(len(points) - 1, 1) * uv_span),
                     (1, (i + 1) / max(len(points) - 1, 1) * uv_span),
                     (0, (i + 1) / max(len(points) - 1, 1) * uv_span)],
                 height=height, phase=phase)


def leaf_card(mesh, origin, direction, side, length, width, height, phase,
              mat=MAT_LEAF, fold=34.0):
    """A material-selectable version of pine_gen's folded card."""
    d = _normalize(np.asarray(direction, float))
    s = _normalize(np.asarray(side, float) - d * (np.asarray(side) @ d))
    up = np.cross(d, s)
    fold = math.radians(fold)
    w1 = math.cos(fold) * s + math.sin(fold) * up
    w2 = -math.cos(fold) * s + math.sin(fold) * up
    p0 = np.asarray(origin, float)
    p1 = p0 + d * length
    a0, a1 = p0 + w1 * width, p1 + w1 * width
    b0, b1 = p0 + w2 * width, p1 + w2 * width
    for q, uv in (
        ([p0, p1, a1, a0], [(1, 0), (2, 0), (2, 1), (1, 1)]),
        ([p1, p0, b0, b1], [(1, 0), (0, 0), (0, 1), (1, 1)]),
    ):
        add_quad(mesh, q, mat, uv=uv, height=height, phase=phase)


def branch_points(base, azimuth, length, droop, n=4):
    h = np.array([math.cos(azimuth), math.sin(azimuth), 0.0])
    pts = []
    for i, t in enumerate(np.linspace(0, 1, n)):
        z = -math.sin(math.radians(droop)) * length * t
        z += math.tan(math.radians(8)) * length * t * t
        pts.append(np.asarray(base) + h * length * t + np.array([0, 0, z]))
    return np.array(pts)


@dataclass
class Asset:
    source: str
    kind: str
    lods: list[TreeMesh]
    materials: list[tuple[str, tuple[float, float, float]]]
    params: dict


def make_birch(source):
    """Generate a broad, irregular birch rather than a pine-like whorl tree."""
    number = variant_number(source)
    height = {1: 10.36, 2: 7.90, 3: 19.63}[number]
    crown = {1: 3.05, 2: 2.72, 3: 3.60}[number]
    trunk_radius = {1: .22, 2: .24, 3: .28}[number]
    leaf_quads = (826, 372, 216, 72)
    rng = np.random.default_rng(300 + number * 10)

    t = np.linspace(0, 1, 23)
    trunk = np.stack([
        .16 * np.sin(t * 2.3 + number) + .07 * np.sin(t * 5.1),
        .10 * np.cos(t * 1.9 + number), t * height
    ], axis=1)

    primary, secondary = [], []
    tier_f = sorted(rng.uniform(.20, .86, 8))
    for j, f in enumerate(tier_f):
        z = height * f
        ti = min(int(z / height * (len(trunk) - 1)), len(trunk) - 1)
        base = trunk[ti]
        count = 3 + j % 3
        for k in range(count):
            az = math.tau * k / count + j * 1.71 + rng.uniform(-.30, .30)
            length = crown * (1.0 - .48 * f) * rng.uniform(.76, 1.20)
            br = branch_points(base, az, length, rng.uniform(4, 20), n=5)
            primary.append((br, length))
            for s in (.34, .62, .84):
                si = min(int(s * (len(br) - 1)), len(br) - 1)
                sb = br[si]
                saz = az + rng.uniform(-1.1, 1.1)
                sl = length * rng.uniform(.22, .48) * (1.0 - .2 * s)
                secondary.append((branch_points(sb, saz, sl,
                                                rng.uniform(-5, 12), n=4), sl))

    all_branches = primary + secondary
    leaf_positions = []
    for br, length in all_branches:
        n = max(2, int(round(length * 4.4)))
        for q in range(n):
            s = (q + .5) / n
            i = min(int(s * (len(br) - 1)), len(br) - 1)
            pos = br[i].copy()
            tangent = _normalize(br[min(i + 1, len(br) - 1)] - br[max(i - 1, 0)])
            az = math.atan2(tangent[1], tangent[0]) + rng.uniform(-.8, .8)
            leaf_positions.append((pos + rng.normal(0, .10, 3), tangent, az,
                                   rng.uniform(.72, 1.25)))
    # Birch foliage is a continuous crown, not a set of horizontal shelves.
    # Add a deterministic ellipsoidal cloud around the branch skeleton so the
    # silhouette stays broad and rounded while branches remain its support.
    for _ in range(700):
        az = rng.uniform(0, math.tau)
        rr = math.sqrt(rng.uniform(0, 1.0))
        zf = rng.uniform(.29, .89)
        crown_r = crown * (1.0 - .50 * abs(zf - .60) / .31)
        pos = np.array([
            math.cos(az) * crown_r * rr + rng.normal(0, .10),
            math.sin(az) * crown_r * rr + rng.normal(0, .10),
            height * zf,
        ])
        tangent = np.array([0.0, 0.0, 1.0])
        leaf_positions.append((pos, tangent, az, rng.uniform(.82, 1.32)))

    lods = []
    for lod in range(4):
        rng_lod = np.random.default_rng(5000 + number * 10 + lod)
        mesh = TreeMesh()
        ts, tsegs = ((10, 20), (8, 16), (6, 10), (5, 7))[lod]
        step = max(1, (len(trunk) - 1) // tsegs)
        tspine = trunk[::step][:tsegs + 1]
        tt = np.linspace(0, 1, len(tspine))
        _tube(mesh, tspine, trunk_radius * (1 - tt) ** 1.15 + .018,
              ts, height, v_repeat=5)

        pkeep = (1.0, .82, .55, .20)[lod]
        skeep = (1.0, .55, .25, .0)[lod]
        for br, length in primary:
            if rng_lod.random() > pkeep:
                continue
            sides, segs = ((8, 4), (6, 3), (5, 2), (4, 1))[lod]
            step = max(1, (len(br) - 1) // segs)
            _tube(mesh, br[::step][:segs + 1],
                  .055 * np.linspace(1, .20, segs + 1), sides, height,
                  u1=.45, v_repeat=2)
        for br, length in secondary:
            if rng_lod.random() > skeep:
                continue
            sides, segs = ((6, 3), (5, 2), (4, 1), (4, 1))[lod]
            step = max(1, (len(br) - 1) // segs)
            _tube(mesh, br[::step][:segs + 1],
                  .035 * np.linspace(1, .18, segs + 1), sides, height,
                  u1=.45, v_repeat=2)

        # Each folded card contributes two quads. Leaves remain at LOD3.
        cards_needed = leaf_quads[lod] // 2
        order = np.argsort([-x[3] - .12 * rng_lod.random()
                            for x in leaf_positions])
        for oi in order[:cards_needed]:
            pos, tangent, az, scale = leaf_positions[int(oi)]
            radial = np.array([math.cos(az), math.sin(az), 0.0])
            direction = _normalize(radial * .65 + np.array([0, 0, .25])
                                   + rng_lod.normal(0, .18, 3))
            side = np.cross(direction, np.array([0, 0, 1.0]))
            if np.linalg.norm(side) < .1:
                side = np.array([1., 0., 0.])
            size = scale
            leaf_card(mesh, pos - direction * .28, direction, side,
                      .90 * size, .50 * size, height,
                      float(rng_lod.random()), fold=25)
        lods.append(mesh)
    return Asset(source, "birch", lods, [
        ("Default_Bark", (.35, .18, .07)), ("Default_Leaves", (.20, .59, .18))
    ], {"height_m": height, "variant": number})


def make_pine(source):
    number = variant_number(source)
    p = PineParams(seed=100 + number, height=4.7 + number * .30,
                   crown_radius=1.35 + number * .08)
    lods = generate_lods(p)
    return Asset(source, "pine", lods, [
        ("Default_Bark", (.35, .18, .07)), ("Default_Leaves", (.20, .59, .18))
    ], {"height_m": p.height, "variant": number})


def make_grass(source):
    number = variant_number(source)
    height = {1: 1.2, 2: 1.5, 3: 1.9}[number]
    widths = {1: .22, 2: .26, 3: .18}[number]
    count = {1: 50, 2: 50, 3: 30}[number]
    lods = []
    for lod, keep in enumerate((1.0, .60, .30)):
        rng = np.random.default_rng(600 + number)
        mesh = TreeMesh()
        n = max(1, int(count * keep))
        for i in range(n):
            a = rng.uniform(0, math.tau)
            h = height * rng.uniform(.72, 1.16)
            r = rng.uniform(0, .12)
            base = np.array([math.cos(a) * r, math.sin(a) * r, 0])
            lean = rng.uniform(.06, .32)
            tip = base + np.array([math.cos(a) * lean, math.sin(a) * lean, h])
            mid = (base + tip) * .48 + np.array([0, 0, h * .08])
            if lod == 2:
                mid = (base + tip) * .5
            add_strip(mesh, [base, mid, tip],
                      [widths, widths * .62, .008], 0, height,
                      float(rng.random()), uv_span=1)
        lods.append(mesh)
    return Asset(source, "grass", lods, [
        ("Default_Grass", (.20, .59, .18))
    ], {"height_m": height, "variant": number, "blades_lod0": count})


def make_flower(source):
    number = variant_number(source)
    height = {1: .95, 2: 1.1, 3: 1.65}[number]
    petals = {1: 6, 2: 4, 3: 8}[number]
    petal_len = {1: .42, 2: .55, 3: .36}[number]
    lods = []
    for lod in range(3):
        mesh = TreeMesh()
        rng = np.random.default_rng(800 + number)
        _tube(mesh, np.array([[0, 0, 0], [0.01, 0.0, height * .78]]),
              [.025, .010], 5 if lod == 0 else 4, height)
        n = petals if lod < 2 else max(3, petals // 2)
        center = np.array([0, 0, height * .78])
        for i in range(n):
            a = math.tau * i / n + rng.uniform(-.08, .08)
            d = np.array([math.cos(a), math.sin(a), .18])
            side = np.array([-math.sin(a), math.cos(a), 0])
            leaf_card(mesh, center - d * petal_len * .3, d, side,
                      petal_len * rng.uniform(.85, 1.12), .16, height,
                      float(rng.random()), mat=MAT_LEAF, fold=12)
        # flower center is a small crossed pair of quads using the leaf slot
        add_quad(mesh, center + [-.10, 0, -.03], center + [0.10, 0, -.03],
                 ) if False else None
        lods.append(mesh)
    return Asset(source, "flower", lods, [
        ("Default_Grass", (.20, .59, .18)), ("Default_White", (.78, .70, .55))
    ], {"height_m": height, "petals": petals, "variant": number})


def make_dead_leaf(source):
    number = variant_number(source)
    mesh = TreeMesh()
    rng = np.random.default_rng(900 + number)
    if "Decal" in source:
        # A slightly folded ground decal, matching the 4-quad reference.
        scale = 2.5 if number == 1 else 2.2
        for i in range(2):
            for j in range(2):
                x0, y0 = (i - 1) * scale, (j - 1) * scale
                z = .025 + .06 * math.sin((i + j) * 1.7)
                add_quad(mesh, [(x0, y0, z), (x0 + scale, y0, z + .01),
                                (x0 + scale, y0 + scale, z + .04),
                                (x0, y0 + scale, z + .02)],
                         0, height=.2, phase=0)
    else:
        # A dry curled leaf: several widening ribbons around a central vein.
        length = 2.0 if number == 1 else 3.7
        width = .42 if number == 1 else .72
        center = np.array([0, 0, .08])
        for side_sign in (-1, 1):
            pts = []
            for t in np.linspace(0, 1, 8):
                x = side_sign * width * math.sin(math.pi * t) * (.65 + .35 * t)
                y = length * t - length * .5
                z = .08 + .18 * math.sin(math.pi * t) + .04 * t
                pts.append(center + [x, y, z])
            add_strip(mesh, pts, [width*.18*(1-t)+.015 for t in np.linspace(0,1,8)],
                      MAT_BARK, .5, 0, uv_span=2)
        # central raised vein
        pts = [center + [0, length * (t - .5), .12 + .1 * math.sin(math.pi*t)]
               for t in np.linspace(0, 1, 5)]
        add_strip(mesh, pts, [.045] * 5, MAT_BARK, .5, 0)
    return Asset(source, "dead_leaf_decal" if "Decal" in source else "dead_leaf",
                 [mesh], [("Default_Bark", (.35, .18, .07))],
                 {"variant": number})


def make_asset(source):
    low = source.lower()
    if "birch" in low:
        return make_birch(source)
    if "pine" in low:
        return make_pine(source)
    if "grass" in low:
        return make_grass(source)
    if "flower" in low:
        return make_flower(source)
    if "dead_leaf" in low:
        return make_dead_leaf(source)
    raise ValueError(source)


def to_payload(mesh):
    # Generator is meters/Z-up; FBX is centimeters/Y-up.
    return {
        "pos": [(p[0] * 100, p[2] * 100, -p[1] * 100) for p in mesh.pos],
        "polys": mesh.polys,
        "uv": mesh.uv,
        "nrm": [(n[0], n[2], -n[1]) for n in mesh.nrm],
        "col": mesh.col,
        "mat_ids": mesh.mat_ids,
    }


def render_asset(asset, folder):
    textures = {
        "bark": R.load_texture(str(TEX / "bark_pine.png")),
        "leaf": R.load_texture(str(TEX / "needle_card.png")),
        "ground": R.load_texture(str(TEX / "ground.png")),
    }
    mats = []
    for i, (name, color) in enumerate(asset.materials):
        # The reference FBXs contain material slots but no image files. For the
        # preview, flowers deliberately use a solid petal color instead of
        # putting the pine-needle atlas on their petals.
        if asset.kind == "flower" and i == 1:
            tex = None
        elif asset.kind == "birch" and i == 1:
            tex = R.load_texture(str(ensure_birch_texture()))
        else:
            tex = textures["bark"] if i == 0 and asset.kind not in ("grass",) else textures["leaf"]
        if asset.kind == "flower" and i == 1:
            color = (.92, .28 + .12 * (asset.params.get("variant", 1) % 3), .42)
        mats.append(R.Material(tex, color=color, two_sided=asset.kind in
                               ("grass", "flower", "dead_leaf", "dead_leaf_decal"),
                               alpha_cutout=False, spec=.02))
    ground_id = len(mats)
    mats.append(R.Material(textures["ground"], spec=0))
    dm = R.from_tree_mesh(asset.lods[0])
    ground = R.ground_mesh(size=20, repeat=24, mat=ground_id, div=12)
    allv = dm.pos
    lo, hi = allv.min(0), allv.max(0)
    center = (lo + hi) / 2
    radius = max(float(np.linalg.norm(hi - lo) * .58), .8)
    img = R.render([dm, ground], mats, width=560, height=700, ss=1,
                   azimuth=35, elevation=8, target=center, radius=radius,
                   fov=35, shadow_res=500, shadow_bounds=(lo - .3, hi + .3),
                   exposure=1.35, fog=.002, shadow_strength=.30)
    R.save_png(img, str(folder / "render.png"))


def process(source_path):
    source = source_path.name
    asset = make_asset(source)
    folder = OUT / Path(source).stem
    folder.mkdir(parents=True, exist_ok=True)
    fbx = folder / "model.fbx"
    export_lod_fbx(str(fbx), Path(source).stem,
                   [to_payload(m) for m in asset.lods],
                   asset.materials,
                   unit_scale_cm=1.0,
                   creator="procedural-vegetation-batch (pure python)")
    render_asset(asset, folder)
    meta = {
        "source": str(source_path.relative_to(ROOT)).replace("\\", "/"),
        "kind": asset.kind,
        "lod_count": len(asset.lods),
        "lod_stats": [m.stats() for m in asset.lods],
        "parameters": asset.params,
        "outputs": ["model.fbx", "render.png", "metadata.json"],
        "note": "Procedural approximation based on reference FBX analysis; not a vertex-exact conversion.",
    }
    (folder / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    return meta


def main():
    files = sorted([p for p in SRC.iterdir()
                    if p.is_file() and p.suffix.lower() == ".fbx"])
    print(f"发现 {len(files)} 个参考 FBX")
    reports = []
    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name}", flush=True)
        try:
            rep = process(path)
            reports.append(rep)
            print("  OK", rep["kind"], rep["lod_stats"], flush=True)
        except Exception as exc:
            reports.append({"source": str(path), "error": repr(exc)})
            print("  FAIL", repr(exc), flush=True)
    (OUT / "batch_report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    ok = sum("error" not in x for x in reports)
    print(f"完成：{ok}/{len(reports)} 个模型成功，报告：{OUT / 'batch_report.json'}")


if __name__ == "__main__":
    main()
