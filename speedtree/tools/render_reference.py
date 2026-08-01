"""把参考 FBX 的三个 LOD 渲染出来，作为视觉基准。"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_fbx import parse
from analyze_tree_fbx import unpack_geometry, get_name
from softrender import Mesh, render, save_png, hstack_labeled

SRC = sys.argv[1] if len(sys.argv) > 1 else "mesh/IL3DN_Tree_Pine_01_OneMesh.FBX"
OUT = "exports"
os.makedirs(OUT, exist_ok=True)

root, _ = parse(SRC)
objects = root.first("Objects")
geos = objects.find("Geometry")
names = [get_name(m) for m in objects.find("Model") if len(m.props) > 2 and m.props[2] == "Mesh"]

imgs, labels = [], []
for i, geo in enumerate(geos):
    P, polys, mats, *_ = unpack_geometry(geo)
    verts = np.array(P)
    # 参考模型是 3ds Max 的 Z-up，原点不在树根，这里对齐到 Z=0 且居中
    verts[:, 0] -= (verts[:, 0].min() + verts[:, 0].max()) / 2
    verts[:, 1] -= (verts[:, 1].min() + verts[:, 1].max()) / 2
    verts[:, 2] -= verts[:, 2].min()
    verts *= 2.54 / 100.0  # UnitScaleFactor -> 米

    mesh = Mesh(verts, polys, mats)
    tris = sum(len(p) - 2 for p in polys)
    label = f"{names[i] if i < len(names) else i}  {tris} tris"
    print("渲染", label, " 高度 %.2f m" % verts[:, 2].max())
    imgs.append(render([mesh], width=560, height=760, azimuth=35, elevation=6))
    labels.append(label)

sheet = hstack_labeled(imgs, labels)
save_png(sheet, os.path.join(OUT, "reference_lods.png"))
print("已输出", os.path.join(OUT, "reference_lods.png"))
