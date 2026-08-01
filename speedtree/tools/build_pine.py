"""
端到端流水线：程序化生成松树 -> 导出多 LOD FBX -> 回读校验 -> 渲染出图。

用法:
    python tools/build_pine.py [seed ...]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pine_gen import PineParams, generate_lods, MAT_BARK, MAT_LEAF
from fbx_writer import export_lod_fbx
from inspect_fbx import parse
from analyze_tree_fbx import unpack_geometry, get_name
from softrender import Mesh, render, save_png, hstack_labeled

OUT = "exports"
MATERIALS = [("Default_Bark", (0.349, 0.180, 0.067)),
             ("Default_Leaves", (0.204, 0.588, 0.176))]


def to_fbx_payload(mesh, scale_cm=100.0):
    """米 / Z-up  ->  厘米 / Y-up，并整理成写出器需要的结构。"""
    pos = [(p[0] * scale_cm, p[2] * scale_cm, -p[1] * scale_cm) for p in mesh.pos]
    nrm = [(n[0], n[2], -n[1]) for n in mesh.nrm]
    return dict(pos=pos, polys=mesh.polys, uv=mesh.uv, nrm=nrm,
                col=mesh.col, mat_ids=mesh.mat_ids)


def verify(path, expect, height_cm):
    """把刚写出的 FBX 用独立解析器读回来，逐项断言。"""
    root, ver = parse(path)
    objects = root.first("Objects")
    geos = objects.find("Geometry")
    models = [get_name(m) for m in objects.find("Model")]
    report = {"fbx_version": ver, "models": models, "lods": []}

    assert len(geos) == len(expect), f"Geometry 数量 {len(geos)} != {len(expect)}"
    for i, geo in enumerate(geos):
        Pp, polys, mats, uvs, uv_idx, cols, col_idx = unpack_geometry(geo)
        tris = sum(len(p) - 2 for p in polys)
        quads = sum(1 for p in polys if len(p) == 4)
        bark = sum(1 for m in mats if m == MAT_BARK)
        leaf = sum(1 for m in mats if m == MAT_LEAF)

        # 顶点色 Alpha 应等于按树高归一化并截断到 [0,1] 的高度（Y-up 下取 y 轴）
        pv, alpha_err = 0, 0.0
        for p, m in zip(polys, mats):
            for vi in p:
                ci = col_idx[pv] if col_idx else pv
                a = cols[ci * 4 + 3]
                want = min(max(Pp[vi][1] / height_cm, 0.0), 1.0)
                alpha_err = max(alpha_err, abs(a - want))
                pv += 1

        e = expect[i]
        assert tris == e["tris"], f"LOD{i} 三角面 {tris} != {e['tris']}"
        assert quads == len(polys), f"LOD{i} 存在非四边形"
        assert bark == e["bark_polys"] and leaf == e["leaf_polys"], f"LOD{i} 材质槽面数不符"
        assert alpha_err < 1e-3, f"LOD{i} 顶点色 Alpha 与归一化高度偏差 {alpha_err}"

        report["lods"].append(dict(tris=tris, quads=quads, bark=bark, leaf=leaf,
                                   verts=len(Pp), uv_count=len(uvs) // 2,
                                   alpha_max_err=round(alpha_err, 9)))
    return report


def reference_mesh(lod=0):
    root, _ = parse("mesh/IL3DN_Tree_Pine_01_OneMesh.FBX")
    geo = root.first("Objects").find("Geometry")[lod]
    Pp, polys, mats, *_ = unpack_geometry(geo)
    v = np.array(Pp)
    v[:, 0] -= (v[:, 0].min() + v[:, 0].max()) / 2
    v[:, 1] -= (v[:, 1].min() + v[:, 1].max()) / 2
    v[:, 2] -= v[:, 2].min()
    v *= 2.54 / 100.0
    return Mesh(v, polys, mats)


def build_one(seed):
    p = PineParams(seed=seed)
    lods = generate_lods(p)
    expect = [m.stats() for m in lods]

    os.makedirs(OUT, exist_ok=True)
    name = f"ProcPine_{seed:02d}"
    path = os.path.join(OUT, name + ".fbx")
    size = export_lod_fbx(path, name, [to_fbx_payload(m) for m in lods], MATERIALS)

    rep = verify(path, expect, p.height * 100.0)
    print(f"\n=== {name} ===")
    print(f"  写出 {path}  ({size/1024:.1f} KB)")
    print(f"  回读校验通过。FBX 版本 {rep['fbx_version']}，节点: {rep['models']}")
    for i, l in enumerate(rep["lods"]):
        print(f"    LOD{i}: {l['tris']:5d} tris  {l['quads']:4d} quads "
              f"(bark {l['bark']} / leaf {l['leaf']})  顶点 {l['verts']}  "
              f"Alpha 最大误差 {l['alpha_max_err']}")
    return p, lods, name


def main():
    seeds = [int(x) for x in sys.argv[1:]] or [3]
    all_imgs, all_labels = [], []

    ref = reference_mesh(0)
    all_imgs.append(render([ref], width=440, height=640, azimuth=35, elevation=6))
    all_labels.append("REFERENCE  2076 tris")

    for s in seeds:
        p, lods, name = build_one(s)
        m = lods[0]
        mesh = Mesh(np.array(m.pos), m.polys, m.mat_ids)
        all_imgs.append(render([mesh], width=440, height=640, azimuth=35, elevation=6))
        all_labels.append(f"{name}  {m.tri_count} tris")

    sheet = hstack_labeled(all_imgs, all_labels)
    out = os.path.join(OUT, "variants.png")
    save_png(sheet, out)
    print("\n已输出对比图", out)


if __name__ == "__main__":
    main()
