"""快速预览生成的松树，并与参考模型并排对比。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pine_gen import PineParams, generate_lods
from softrender import Mesh, render, save_png, hstack_labeled
from inspect_fbx import parse
from analyze_tree_fbx import unpack_geometry

OUT = "exports"
os.makedirs(OUT, exist_ok=True)


def reference_mesh(lod=0):
    root, _ = parse("mesh/IL3DN_Tree_Pine_01_OneMesh.FBX")
    geo = root.first("Objects").find("Geometry")[lod]
    P, polys, mats, *_ = unpack_geometry(geo)
    v = np.array(P)
    v[:, 0] -= (v[:, 0].min() + v[:, 0].max()) / 2
    v[:, 1] -= (v[:, 1].min() + v[:, 1].max()) / 2
    v[:, 2] -= v[:, 2].min()
    v *= 2.54 / 100.0
    return Mesh(v, polys, mats)


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    p = PineParams(seed=seed)
    lods = generate_lods(p)

    imgs, labels = [], []
    ref = reference_mesh(0)
    imgs.append(render([ref], width=520, height=720, azimuth=35, elevation=6))
    labels.append("REFERENCE  IL3DN LOD0  %d tris" % sum(len(f) - 2 for f in ref.faces))

    for i, m in enumerate(lods):
        st = m.stats()
        print(f"LOD{i}: {st}")
        mesh = Mesh(np.array(m.pos), m.polys, m.mat_ids)
        imgs.append(render([mesh], width=520, height=720, azimuth=35, elevation=6))
        labels.append(f"GENERATED LOD{i}  {st['tris']} tris  (bark {st['bark_polys']} / leaf {st['leaf_polys']} quads)")

    sheet = hstack_labeled(imgs, labels)
    path = os.path.join(OUT, f"compare_seed{seed}.png")
    save_png(sheet, path)
    print("已输出", path)


if __name__ == "__main__":
    main()
