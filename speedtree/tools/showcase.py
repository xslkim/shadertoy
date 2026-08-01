"""
出三张展示图 + 一次批量吞吐测试：
  1. showcase_lods.png   —— 生成树的 LOD0/1/2 与参考并排
  2. showcase_wind.png   —— 顶点色风数据可视化（Alpha 弯曲权重 / G 抖动相位）
  3. showcase_forest.png —— 一次生成多棵不同种子的树
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pine_gen import PineParams, generate, generate_lods
from fbx_writer import export_lod_fbx
from softrender import Mesh, render, save_png, hstack_labeled
from build_pine import reference_mesh, to_fbx_payload, MATERIALS

OUT = "exports"
os.makedirs(OUT, exist_ok=True)


def sheet_lods(seed=3):
    lods = generate_lods(PineParams(seed=seed))
    imgs, labels = [], []
    ref = reference_mesh(0)
    imgs.append(render([ref], width=430, height=630, azimuth=35, elevation=6))
    labels.append("参考 IL3DN LOD0  2076 tris")
    for i, m in enumerate(lods):
        st = m.stats()
        imgs.append(render([Mesh(np.array(m.pos), m.polys, m.mat_ids)],
                           width=430, height=630, azimuth=35, elevation=6))
        labels.append(f"生成 LOD{i}  {st['tris']} tris  (bark {st['bark_polys']} quads)")
    save_png(hstack_labeled(imgs, labels), os.path.join(OUT, "showcase_lods.png"))
    print("-> showcase_lods.png")


def sheet_wind(seed=3):
    """把顶点色画出来：Alpha 通道 = 风弯曲权重，G 通道 = 每卡抖动相位。"""
    m = generate(PineParams(seed=seed), 0)
    verts = np.array(m.pos)
    imgs, labels = [], []

    imgs.append(render([Mesh(verts, m.polys, m.mat_ids)],
                       width=430, height=630, azimuth=35, elevation=6))
    labels.append("常规着色")

    # 顶点色是 per-polygon-vertex，这里取每个面的首个 corner 值给整面上色
    corner = 0
    face_a, face_g = [], []
    for poly in m.polys:
        face_a.append(m.col[corner][3])
        face_g.append(m.col[corner][1])
        corner += len(poly)

    for vals, name, ramp in (
        (face_a, "顶点色 Alpha = 风弯曲权重（根部 0 → 梢部 1）",
         lambda v: (0.10 + 0.90 * v, 0.25 * v, 0.85 * (1 - v))),
        (face_g, "顶点色 G = 每张叶卡的抖动相位（树干恒 0）",
         lambda v: (0.15, 0.25 + 0.75 * v, 0.25 + 0.35 * (1 - v))),
    ):
        pal = np.array([ramp(v) for v in vals])
        mesh = Mesh(verts, m.polys, list(range(len(m.polys))))
        imgs.append(render([mesh], width=430, height=630, azimuth=35, elevation=6,
                           palette=pal))
        labels.append(name)

    save_png(hstack_labeled(imgs, labels), os.path.join(OUT, "showcase_wind.png"))
    print("-> showcase_wind.png")


def sheet_forest(seeds=(2, 5, 8, 13, 21, 34)):
    imgs, labels = [], []
    for s in seeds:
        m = generate(PineParams(seed=s), 0)
        imgs.append(render([Mesh(np.array(m.pos), m.polys, m.mat_ids)],
                           width=300, height=470, azimuth=35, elevation=6))
        labels.append(f"seed={s}  {m.tri_count} tris")
    save_png(hstack_labeled(imgs, labels), os.path.join(OUT, "showcase_forest.png"))
    print("-> showcase_forest.png")


def throughput(n=100):
    """批量生成 + 导出 FBX 的吞吐。"""
    tmp = os.path.join(OUT, "_bench")
    os.makedirs(tmp, exist_ok=True)
    t0 = time.perf_counter()
    tris = 0
    for i in range(n):
        p = PineParams(seed=1000 + i)
        lods = generate_lods(p)
        tris += lods[0].tri_count
        export_lod_fbx(os.path.join(tmp, f"t{i:04d}.fbx"), f"Pine_{i:04d}",
                       [to_fbx_payload(m) for m in lods], MATERIALS)
    dt = time.perf_counter() - t0
    size = sum(os.path.getsize(os.path.join(tmp, f)) for f in os.listdir(tmp))
    print(f"\n批量测试: {n} 棵树（每棵 3 个 LOD）")
    print(f"  总耗时 {dt:.2f}s  ->  {dt/n*1000:.0f} ms/棵  ({n/dt:.1f} 棵/秒，单线程)")
    print(f"  LOD0 平均 {tris/n:.0f} tris   FBX 总体积 {size/1024/1024:.1f} MB")
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


if __name__ == "__main__":
    sheet_lods()
    sheet_wind()
    sheet_forest()
    throughput(100)
