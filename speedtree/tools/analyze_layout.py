"""提取参考树的布局规律：叶卡中心的柱坐标分布、轮生层结构、单张卡片的局部形状。"""
import os
import sys
import math
from collections import defaultdict, Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_fbx import parse
from analyze_tree_fbx import unpack_geometry

SRC = sys.argv[1] if len(sys.argv) > 1 else "mesh/IL3DN_Tree_Pine_01_OneMesh.FBX"
root, _ = parse(SRC)
geo = root.first("Objects").find("Geometry")[0]
P, polys, mats, uvs, uv_idx, cols, col_idx = unpack_geometry(geo)

V = np.array(P)
V[:, 0] -= (V[:, 0].min() + V[:, 0].max()) / 2
V[:, 1] -= (V[:, 1].min() + V[:, 1].max()) / 2
V[:, 2] -= V[:, 2].min()
V *= 2.54 / 100.0
H = V[:, 2].max()

leaf_polys = [p for p, m in zip(polys, mats) if m == 1]
bark_polys = [p for p, m in zip(polys, mats) if m == 0]

# --- 叶卡连通分量 ---
adj = defaultdict(set)
for p in leaf_polys:
    for i in range(len(p)):
        adj[p[i]].add(p[(i + 1) % len(p)])
        adj[p[(i + 1) % len(p)]].add(p[i])
seen, cards = set(), []
for v in sorted(adj):
    if v in seen:
        continue
    stack, comp = [v], []
    seen.add(v)
    while stack:
        x = stack.pop()
        comp.append(x)
        for y in adj[x]:
            if y not in seen:
                seen.add(y)
                stack.append(y)
    cards.append(sorted(comp))

print(f"树高 {H:.2f} m,  叶卡 {len(cards)} 张")

centers = np.array([V[c].mean(0) for c in cards])
r = np.hypot(centers[:, 0], centers[:, 1])
z = centers[:, 2]
theta = np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) % 360

print("\n### 叶卡中心分布")
print(f"  高度 z: {z.min():.2f} ~ {z.max():.2f} m  (占树高 {z.min()/H:.0%} ~ {z.max()/H:.0%})")
print(f"  半径 r: {r.min():.2f} ~ {r.max():.2f} m")

# 按高度分层（轮生层）
order = np.argsort(z)
zs = z[order]
layers, cur = [], [order[0]]
for k in range(1, len(zs)):
    if zs[k] - z[cur[-1]] < 0.10:
        cur.append(order[k])
    else:
        layers.append(cur)
        cur = [order[k]]
layers.append(cur)
print(f"\n### 轮生层（高度间隔 >0.10m 分层）: 共 {len(layers)} 层")
print("  层  高度(m)  卡数   平均半径  半径范围     方位角(排序)")
for i, L in enumerate(layers):
    zl = z[L]
    rl = r[L]
    tl = np.sort(theta[L]).astype(int)
    print(
        f"  {i:2d}  {zl.mean():5.2f}   {len(L):3d}   {rl.mean():6.2f}   "
        f"{rl.min():.2f}-{rl.max():.2f}   {list(tl)[:10]}"
    )

# 轮生层间距
zl_means = [z[L].mean() for L in layers]
gaps = np.diff(zl_means)
print(f"\n  层间距: 平均 {gaps.mean():.3f} m, 范围 {gaps.min():.3f}~{gaps.max():.3f} m")

# 树冠包络: 半径 vs 高度
print("\n### 树冠包络（每层最大半径 vs 归一化高度）")
for i, L in enumerate(layers):
    t = z[L].mean() / H
    print(f"  z/H={t:.2f}  Rmax={r[L].max():.2f}  Rmean={r[L].mean():.2f}")

# 线性拟合包络
tt = np.array([z[L].mean() / H for L in layers])
rr = np.array([r[L].max() for L in layers])
A = np.vstack([tt, np.ones_like(tt)]).T
k, b = np.linalg.lstsq(A, rr, rcond=None)[0]
print(f"  线性拟合: Rmax ≈ {k:.3f}*(z/H) + {b:.3f}")

# --- 单张卡片的局部形状 ---
print("\n### 单张叶卡的局部几何（取 5 个样本）")
pv_uv = {}
pv = 0
for p, m in zip(polys, mats):
    for vi in p:
        ui = uv_idx[pv] if uv_idx else pv
        pv_uv.setdefault(vi, (uvs[ui * 2], uvs[ui * 2 + 1]))
        pv += 1

sizes = []
for ci, c in enumerate(cards):
    pts = V[c]
    ctr = pts.mean(0)
    d = pts - ctr
    # PCA 求局部坐标系
    u, s, vt = np.linalg.svd(d, full_matrices=False)
    sizes.append(s)
    if ci < 5:
        uvlist = [pv_uv.get(v, (0, 0)) for v in c]
        print(
            f"  卡{ci}: 中心 r={math.hypot(*ctr[:2]):.2f} z={ctr[2]:.2f}  "
            f"主轴长度 {s[0]*2:.2f}/{s[1]*2:.2f}/{s[2]*2:.3f} m"
        )
        print(f"        UV: {[(round(a,2), round(b,2)) for a, b in uvlist]}")

S = np.array(sizes)
print(f"\n  所有卡片主轴尺寸: 长 {np.median(S[:,0])*2:.2f}m  宽 {np.median(S[:,1])*2:.2f}m  厚(弯曲量) {np.median(S[:,2])*2:.3f}m")
print(f"  长度范围 {S[:,0].min()*2:.2f}~{S[:,0].max()*2:.2f} m")

# 卡片长轴与水平面的夹角（下垂角）
droop = []
for c in cards:
    pts = V[c]
    d = pts - pts.mean(0)
    _, _, vt = np.linalg.svd(d, full_matrices=False)
    ax = vt[0]
    droop.append(math.degrees(math.asin(abs(ax[2]))) * (1 if ax[2] < 0 else -1))
droop = np.array(droop)
print(f"  卡片长轴倾角: 中位 {np.median(np.abs(droop)):.0f}°  范围 {np.abs(droop).min():.0f}~{np.abs(droop).max():.0f}°")

# --- 树干 ---
bark_verts = sorted({v for p in bark_polys for v in p})
BV = V[bark_verts]
print("\n### 树干/枝条")
print(f"  树皮顶点 {len(bark_verts)}  面 {len(bark_polys)}")
# 主干：半径很小的那部分
rb = np.hypot(BV[:, 0], BV[:, 1])
trunk_mask = rb < 0.12
print(f"  近轴(r<0.12m)顶点 {trunk_mask.sum()}  -> 主干")
tz = BV[trunk_mask][:, 2]
print(f"  主干 z 范围 {tz.min():.2f}~{tz.max():.2f} m")
# 主干半径随高度
print("  主干半径随高度:")
for lo in np.arange(0, H, 0.6):
    sel = (BV[:, 2] >= lo) & (BV[:, 2] < lo + 0.6) & (rb < 0.2)
    if sel.sum() > 2:
        print(f"    z={lo:.1f}-{lo+0.6:.1f}m  r_mean={rb[sel].mean():.3f}  n={sel.sum()}")

# 枝条数量估计：树皮的连通分量
adjb = defaultdict(set)
for p in bark_polys:
    for i in range(len(p)):
        adjb[p[i]].add(p[(i + 1) % len(p)])
        adjb[p[(i + 1) % len(p)]].add(p[i])
seenb, comps_b = set(), []
for v in sorted(adjb):
    if v in seenb:
        continue
    stack, comp = [v], []
    seenb.add(v)
    while stack:
        x = stack.pop()
        comp.append(x)
        for y in adjb[x]:
            if y not in seenb:
                seenb.add(y)
                stack.append(y)
    comps_b.append(comp)
print(f"  树皮连通分量 {len(comps_b)} 个, 顶点数分布 {dict(Counter(len(c) for c in comps_b))}")
