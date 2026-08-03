"""
参考 FBX vs 程序化模型的同条件对比渲染。

每个 rebuild_mesh/<asset>/ 增加：
    comparison.png

并生成总览：
    rebuild_mesh/all_comparisons.png

两侧使用同一个：
  - 目标点和相机距离
  - 实际尺度（参考 FBX 原始单位按 2.54 cm 转成米）
  - 光照、背景、地面、材质预览
  - 阴影范围
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import render_hq as R
from analyze_tree_fbx import get_name, unpack_geometry
from generate_all_vegetation import (OUT, ROOT, SRC, TEX, ensure_birch_texture,
                                     make_asset)
from inspect_fbx import parse


def common_materials(kind):
    bark = R.load_texture(str(TEX / "bark_pine.png"))
    leaf = R.load_texture(str(TEX / "needle_card.png"))
    birch_leaf = R.load_texture(str(ensure_birch_texture()))
    ground = R.load_texture(str(TEX / "ground.png"))
    if kind == "flower":
        # Reference flower slot 0 is green stem/leaf, slot 1 is white petal.
        mats = [
            R.Material(None, color=(.20, .59, .18), two_sided=True),
            R.Material(None, color=(.92, .40, .56), two_sided=True),
        ]
    elif kind == "grass":
        mats = [R.Material(leaf, color=(.78, .92, .46), two_sided=True)]
    elif kind == "dead_leaf_decal":
        mats = [R.Material(bark, color=(.72, .48, .20), two_sided=True)]
    elif kind == "dead_leaf":
        mats = [R.Material(bark, color=(.76, .43, .16), two_sided=True)]
    else:
        if kind == "birch":
            leaf = birch_leaf
        mats = [
            R.Material(leaf, color=(1.0, 1.0, 1.0), two_sided=True,
                       alpha_cutout=True, cutoff=.45, translucency=.45),
            R.Material(bark, color=(1.0, .95, .88)),
        ]
    mats.append(R.Material(ground, spec=0.0))
    return mats


def geometry_to_draw(geo, kind, mat_remap=None):
    """Convert one FBX geometry to the renderer's meter/Z-up mesh."""
    P, polys, mats, uvs, uv_idx, cols, col_idx = unpack_geometry(geo)
    p = np.asarray(P, dtype=float)
    # The library is not axis-consistent: tree and grass geometry are authored
    # with Z as the visible height, flowers with Y as height, while dead-leaf
    # assets are already lying in XY. The FBX global UpAxis alone is therefore
    # not enough; use the measured category convention.
    if kind == "flower":
        p = np.stack([p[:, 0], p[:, 2], p[:, 1]], axis=1)
    else:
        p = p.copy()
    p *= .0254
    lo, hi = p.min(axis=0), p.max(axis=0)
    # Place the object on z=0; do not independently normalize scale.
    p[:, 2] -= lo[2]

    uv_out, nrm_out = [], []
    pv = 0
    for poly in polys:
        a, b, c = p[poly[0]], p[poly[1]], p[poly[2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n) or 1.0
        for _ in poly:
            ui = uv_idx[pv] if uv_idx else pv
            uv_out.append((uvs[ui * 2], uvs[ui * 2 + 1])
                          if uvs is not None else (0.0, 0.0))
            nrm_out.append(tuple(n))
            pv += 1
    if mat_remap:
        mats = [mat_remap.get(int(m), int(m)) for m in mats]
    return R.from_polys(p, polys, mats, uv_out, nrm_out)


def select_reference_meshes(path, kind):
    """Select the visible LOD0 parts from split reference FBXs."""
    root, _ = parse(str(path))
    objects = root.first("Objects")
    geos = objects.find("Geometry")
    material_names = []
    for material in objects.find("Material"):
        material_names.append(get_name(material).lower())
    mat_remap = {}
    for i, material_name in enumerate(material_names):
        if any(x in material_name for x in ("leaf", "grass", "flower", "petal")):
            mat_remap[i] = 1 if kind not in ("grass", "dead_leaf", "dead_leaf_decal") else 0
        else:
            mat_remap[i] = 0
    models = [m for m in objects.find("Model")
              if len(m.props) > 2 and m.props[2] == "Mesh"]
    names = [get_name(m) for m in models]
    by_name = {n: geos[i] for i, n in enumerate(names) if i < len(geos)}

    name = path.name.lower()
    if "grass" in name:
        chosen = [by_name.get(next((n for n in names if "lod0" in n.lower()), names[0]))]
    elif "birch" in name and "onemesh" not in name:
        chosen = [by_name[n] for n in names
                  if "leaves_lod0" in n.lower() or "branch_lod0" in n.lower()]
    elif "pine" in name and "onemesh" not in name:
        chosen = [by_name[n] for n in names
                  if "leaves" in n.lower() or "branch_lod0" in n.lower()]
    elif "onemesh" in name:
        chosen = [by_name[next(n for n in names if "lod0" in n.lower())]]
    else:
        chosen = [geos[0]]
    return [geometry_to_draw(g, kind, mat_remap) for g in chosen if g is not None]


def bounds(meshes):
    v = np.vstack([m.pos for m in meshes])
    return v.min(axis=0), v.max(axis=0)


def render_side(meshes, mats, target, radius, shadow_bounds, kind, width=500, height=650):
    ground = R.ground_mesh(size=max(20, radius * 8), repeat=22, mat=len(mats) - 1, div=12)
    return R.render(
        list(meshes) + [ground], mats, width=width, height=height, ss=1,
        azimuth=35, elevation=8, fov=35, target=target, radius=radius,
        shadow_res=500, shadow_bounds=shadow_bounds,
        exposure=1.35, fog=.002, shadow_strength=.30,
    )


def pair_image(left, right, label_left, label_right):
    gap, band = 14, 36
    w = left.shape[1] + right.shape[1] + gap * 3
    h = max(left.shape[0], right.shape[0]) + band + gap * 2
    canvas = Image.new("RGB", (w, h), (13, 17, 23))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 18)
    except OSError:
        font = ImageFont.load_default()
    d.text((gap, 9), label_left, fill=(235, 240, 245), font=font)
    d.text((gap * 2 + left.shape[1], 9), label_right,
           fill=(235, 240, 245), font=font)
    canvas.paste(Image.fromarray(left), (gap, band))
    canvas.paste(Image.fromarray(right), (gap * 2 + left.shape[1], band))
    return np.asarray(canvas)


def process(path):
    asset_name = path.stem
    folder = OUT / asset_name
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    kind = meta["kind"]
    generated = R.from_tree_mesh(make_asset(path.name).lods[0])
    if kind in ("pine", "birch"):
        # The reference tree FBXs use slot 0 for foliage and slot 1 for bark
        # despite their material object order; the generated contract uses the
        # opposite order. Swap only the preview indices, not the exported FBX.
        generated.mat = np.where(generated.mat == 0, 1, 0)
    reference = select_reference_meshes(path, kind)

    all_meshes = reference + [generated]
    lo, hi = bounds(all_meshes)
    target = (lo + hi) * .5
    target[2] = (lo[2] + hi[2]) * .47
    radius = max(float(np.linalg.norm(hi - lo) * .58), .8)
    shadow_bounds = (lo - .35, hi + .35)
    mats = common_materials(kind)

    # Both sides receive exactly the same camera and render settings.
    left = render_side(reference, mats, target, radius, shadow_bounds, kind)
    right = render_side([generated], mats, target, radius, shadow_bounds, kind)
    image = pair_image(left, right, "参考 FBX  LOD0", "程序化生成  LOD0")
    R.save_png(image, str(folder / "comparison.png"))
    return image, {
        "source": str(path.relative_to(ROOT)).replace("\\", "/"),
        "output": str((folder / "comparison.png").relative_to(ROOT)).replace("\\", "/"),
        "kind": kind,
        "reference_parts": len(reference),
        "shared_camera": {
            "target_m": [round(float(x), 5) for x in target],
            "radius_m": round(radius, 5),
            "azimuth": 35,
            "elevation": 8,
            "fov": 35,
        },
    }


def main():
    files = sorted(p for p in SRC.iterdir()
                   if p.is_file() and p.suffix.lower() == ".fbx")
    reports, images, labels = [], [], []
    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {path.name}", flush=True)
        try:
            image, report = process(path)
            reports.append(report)
            images.append(image)
            labels.append(path.stem)
            print("  OK ->", report["output"], flush=True)
        except Exception as exc:
            reports.append({"source": str(path), "error": repr(exc)})
            print("  FAIL", repr(exc), flush=True)

    # Contact sheet: each cell is already a reference/generated pair.
    if images:
        cell_w = max(x.shape[1] for x in images)
        cell_h = max(x.shape[0] for x in images)
        cols, pad = 2, 14
        rows = (len(images) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w + (cols + 1) * pad,
                                   rows * cell_h + (rows + 1) * pad),
                          (8, 11, 16))
        for i, image in enumerate(images):
            x = pad + (i % cols) * (cell_w + pad)
            y = pad + (i // cols) * (cell_h + pad)
            sheet.paste(Image.fromarray(image), (x, y))
        sheet.save(OUT / "all_comparisons.png")

    (OUT / "comparison_report.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成：{len(images)}/{len(files)}，总览：{OUT / 'all_comparisons.png'}")


if __name__ == "__main__":
    main()
