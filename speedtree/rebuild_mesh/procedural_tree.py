"""
手写代码程序化建模：风格化阔叶树原型
====================================
纯 Python + numpy，不依赖任何 DCC 软件。按参数表 + 随机种子生成
"细长主干 + 下部少量光秃短枝 + 顶部叶卡片簇树冠"的低模卡通树，
输出 OBJ + MTL（引用 mesh/IL3DN_Tree_Beech_02 下的两张贴图）。

用法：
    python procedural_tree.py                 # 默认种子，写 sample_tree.obj
    python procedural_tree.py --seed 12 --height 7 --out tree_a.obj

结构：
    1. 骨架：递归分枝（主干 + 树冠内 scaffold 分枝 + 下部光秃短枝）
    2. 树干网格：沿骨架折线的低段数变径圆柱扫掠
    3. 叶卡片：末端枝条处聚簇放置 quad，顶点色双色调绿
    4. 输出：OBJ（v x y z r g b 顶点色）+ MTL（贴图相对路径）
"""
from dataclasses import dataclass
import argparse
import math
import os
import random

import numpy as np


# --------------------------------------------------------------------------
# 参数表（泛化入口：同一套参数 = 同一种风格；改种子 = 同风格不同形状）
# --------------------------------------------------------------------------
@dataclass
class TreeParams:
    seed: int = 7

    # 整体
    height: float = 6.0           # 树高 (m)
    crown_start: float = 0.45     # 树冠起始相对高度（以下为光秃树干）
    crown_radius: float = 2.1     # 树冠包络水平半径 (m)
    crown_height: float = 3.2     # 树冠包络高度 (m)

    # 主干
    trunk_radius: float = 0.09    # 根部半径 (m)
    trunk_taper: float = 0.60     # 半径随高度线性衰减比例
    trunk_lean: float = 0.25      # 主干水平弯曲幅度 (m)
    trunk_segments: int = 9       # 主干纵向段数
    trunk_sides: int = 7          # 主干圆周段数（低段数 = 风格化）

    # 分枝（递归）
    scaffold_count: int = 6       # 主干伸入树冠的一级分枝数
    branch_angle: float = 50.0    # 子枝与父枝的夹角 (度)
    branch_angle_jitter: float = 18.0
    branch_length_ratio: float = 0.60   # 子枝长度 / 父枝剩余长度
    branch_length_jitter: float = 0.25
    branch_child_prob: float = 0.85     # 每个节点生出子枝的概率
    branch_radius_ratio: float = 0.55   # 子枝根部半径 / 父枝半径
    branch_sides: int = 5               # 枝条圆周段数
    max_depth: int = 3                  # 递归深度（0=主干）
    dead_branches: int = 3              # 下部光秃短枝数量
    dead_branch_len: float = 0.55

    # 叶卡片簇
    cards_per_cluster: int = 7    # 每簇卡片数
    cluster_radius: float = 0.55  # 簇内卡片散布半径 (m)
    card_size: float = 1.05       # 卡片边长 (m)，UV 整幅映射叶贴图
    card_size_jitter: float = 0.35
    extra_clusters: int = 22      # 树冠包络内额外补的填充簇

    # 配色（双色调绿：顶点色；叶贴图 RGB 为纯白，靠顶点色上色）
    color_dark: tuple = (0.16, 0.33, 0.13)    # 树冠内部 / 下部
    color_light: tuple = (0.48, 0.68, 0.25)   # 树冠顶部 / 外侧高光
    accent_prob: float = 0.22     # 整簇提亮（高光团块）的概率
    bark_color: tuple = (0.23, 0.16, 0.13)    # 树皮 MTL Kd（贴图为灰白纹理）


MAT_BARK, MAT_LEAF = 0, 1


# --------------------------------------------------------------------------
# 网格容器（面不共享顶点：每面独立角点，天然平面化着色）
# --------------------------------------------------------------------------
class Mesh:
    def __init__(self):
        self.v = []      # (x,y,z)
        self.vc = []     # (r,g,b) 顶点色
        self.vt = []     # (u,v)
        self.f = []      # ([vi...], mat_id)

    def add_face(self, pts, uvs, cols, mat):
        idx = []
        for p, uv, c in zip(pts, uvs, cols):
            self.v.append(tuple(p))
            self.vc.append(tuple(c))
            self.vt.append(tuple(uv))
            idx.append(len(self.v) - 1)
        self.f.append((idx, mat))

    def stats(self):
        tris = sum(len(i) - 2 for i, _ in self.f)
        bark = sum(1 for _, m in self.f if m == MAT_BARK)
        leaf = sum(1 for _, m in self.f if m == MAT_LEAF)
        return dict(verts=len(self.v), faces=len(self.f), tris=tris,
                    bark_faces=bark, leaf_faces=leaf)


# --------------------------------------------------------------------------
# 向量工具
# --------------------------------------------------------------------------
def _norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.array([0.0, 1.0, 0.0])


def _rand3(rng):
    """3 维 [-1,1] 均匀随机向量。"""
    return np.array([rng.uniform(-1.0, 1.0) for _ in range(3)])


def _frame(d):
    """由方向构造正交基 (side, up, dir)。"""
    d = _norm(np.asarray(d, float))
    ref = np.array([0.0, 1.0, 0.0])
    if abs(d @ ref) > 0.95:
        ref = np.array([1.0, 0.0, 0.0])
    s = _norm(np.cross(d, ref))
    u = np.cross(d, s)
    return s, u, d


def _rot(v, axis, ang):
    """Rodrigues 旋转：v 绕 axis 转 ang 弧度。"""
    a = _norm(axis)
    v = np.asarray(v, float)
    return v * math.cos(ang) + np.cross(a, v) * math.sin(ang) \
        + a * (a @ v) * (1.0 - math.cos(ang))


def _lerp3(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# --------------------------------------------------------------------------
# 骨架：递归分枝
# --------------------------------------------------------------------------
class Branch:
    __slots__ = ("spine", "radii", "depth", "leafy")

    def __init__(self, spine, radii, depth, leafy):
        self.spine = spine      # [np vec3]
        self.radii = radii      # [float]
        self.depth = depth
        self.leafy = leafy      # 末端是否长叶簇


def _grow_spine(rng, origin, direction, length, r0, r1, n_seg, wiggle, up_bias):
    """从 origin 沿 direction 长一条带随机摆动的折线，返回 (spine, radii)。"""
    d = _norm(direction)
    spine = [np.asarray(origin, float)]
    radii = [r0]
    step = length / n_seg
    for i in range(1, n_seg + 1):
        d = _norm(d + _rand3(rng) * wiggle
                  + np.array([0.0, up_bias, 0.0]))
        spine.append(spine[-1] + d * step)
        radii.append(r0 + (r1 - r0) * i / n_seg)
    return spine, radii


def _child_dir(rng, parent_dir, angle_deg, jitter_deg):
    """父枝方向偏转 angle，方位角随机。"""
    s, u, d = _frame(parent_dir)
    az = rng.uniform(0.0, 2.0 * math.pi)
    axis = s * math.cos(az) + u * math.sin(az)
    ang = math.radians(angle_deg + rng.uniform(-jitter_deg, jitter_deg))
    return _rot(d, axis, ang)


def _grow(rng, p, origin, direction, length, radius, depth, branches):
    """递归生长一根枝条，并把自己加入 branches。"""
    n_seg = max(2, int(round(length / 0.7)))
    tip_r = max(0.008, radius * 0.35)
    spine, radii = _grow_spine(rng, origin, direction, length,
                               radius, tip_r, n_seg, wiggle=0.10, up_bias=0.06)
    branch = Branch(spine, radii, depth, leafy=False)
    branches.append(branch)

    if depth >= p.max_depth:
        branch.leafy = True
        return
    # 在节点上生子枝（跳过根部节点，末端节点必生 1~2 根保证延续）
    before = len(branches)
    for i in range(1, n_seg + 1):
        last = (i == n_seg)
        if not last and rng.random() > p.branch_child_prob:
            continue
        n_child = 1 if (last and rng.random() < 0.6) else (2 if rng.random() < 0.35 else 1)
        for _ in range(n_child):
            remain = length * (1.0 - i / (n_seg + 1.0))
            cl = remain * p.branch_length_ratio \
                * (1.0 + rng.uniform(-1.0, 1.0) * p.branch_length_jitter)
            if cl < 0.15:
                continue
            cd = _child_dir(rng, spine[i] - spine[i - 1],
                            p.branch_angle, p.branch_angle_jitter)
            _grow(rng, p, spine[i], cd, cl,
                  radii[i] * p.branch_radius_ratio, depth + 1, branches)
    # 没有生出任何子枝的末端细枝同样长叶
    branch.leafy = len(branches) == before


def build_skeleton(p, rng):
    """主干 + 树冠 scaffold 分枝 + 下部光秃短枝，返回 [Branch]。"""
    branches = []

    # 主干：垂直 + 平滑随机弯曲
    spine = [np.zeros(3)]
    radii = [p.trunk_radius]
    step = p.height / p.trunk_segments
    off = np.zeros(3)
    for i in range(1, p.trunk_segments + 1):
        off += _rand3(rng) * (p.trunk_lean / p.trunk_segments)
        off[1] = 0.0
        spine.append(np.array([off[0], i * step, off[2]]))
        radii.append(max(0.02, p.trunk_radius * (1.0 - p.trunk_taper * i / p.trunk_segments)))
    branches.append(Branch(spine, radii, depth=0, leafy=False))

    # 树冠内 scaffold 一级分枝（从主干节点伸出，递归成细枝网络）
    crown_nodes = [i for i in range(1, p.trunk_segments + 1)
                   if spine[i][1] >= p.crown_start * p.height]
    picks = rng.sample(crown_nodes, min(p.scaffold_count, len(crown_nodes)))
    for i in picks:
        d = spine[i] - spine[i - 1]
        bl = (p.height - spine[i][1]) * 0.9 \
            * (1.0 + rng.uniform(-1.0, 1.0) * p.branch_length_jitter)
        cd = _child_dir(rng, d, p.branch_angle, p.branch_angle_jitter)
        _grow(rng, p, spine[i], cd, max(0.5, bl),
              radii[i] * p.branch_radius_ratio, depth=1, branches=branches)

    # 下部光秃短枝（不长叶，参考截图中部的枯枝）
    low_nodes = [i for i in range(2, p.trunk_segments)
                 if spine[i][1] < p.crown_start * p.height]
    for i in rng.sample(low_nodes, min(p.dead_branches, len(low_nodes))):
        d = _child_dir(rng, spine[i] - spine[i - 1], 65.0, 15.0)
        dl = p.dead_branch_len * rng.uniform(0.6, 1.4)
        ds, dr = _grow_spine(rng, spine[i], d, dl, 0.02, 0.006, 2,
                             wiggle=0.15, up_bias=0.0)
        branches.append(Branch(ds, dr, depth=1, leafy=False))

    return branches


# --------------------------------------------------------------------------
# 树干网格：沿骨架折线的低段数变径圆柱扫掠
# --------------------------------------------------------------------------
def _sweep(mesh, spine, radii, sides, rng):
    """单根枝条扫掠成管。UV：u 绕圆周，v 沿长度（按周长换算重复次数）。"""
    n = len(spine)
    rings = []
    for i in range(n):
        d = spine[min(i + 1, n - 1)] - spine[max(i - 1, 0)]
        s, u, _ = _frame(d)
        ring = []
        for k in range(sides):
            a = 2.0 * math.pi * k / sides
            ring.append(spine[i] + (s * math.cos(a) + u * math.sin(a)) * radii[i])
        rings.append(ring)
    # v 坐标按实际长度 / 周长比例平铺，保证树皮纹理密度一致
    v_len = [0.0]
    for i in range(1, n):
        v_len.append(v_len[-1] + np.linalg.norm(spine[i] - spine[i - 1]))
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            pts = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
            circumference = max(0.05, 2.0 * math.pi * radii[i])
            uvs = [(k / sides, v_len[i] / circumference),
                   ((k + 1) / sides, v_len[i] / circumference),
                   ((k + 1) / sides, v_len[i + 1] / circumference),
                   (k / sides, v_len[i + 1] / circumference)]
            cols = [(1.0, 1.0, 1.0)] * 4
            mesh.add_face(pts, uvs, cols, MAT_BARK)


# --------------------------------------------------------------------------
# 叶卡片簇
# --------------------------------------------------------------------------
def _in_crown(p, pt):
    """点是否落在树冠椭球包络内。"""
    cy = p.crown_start * p.height + p.crown_height * 0.5
    dx = pt[0] / p.crown_radius
    dy = (pt[1] - cy) / (p.crown_height * 0.5)
    dz = pt[2] / p.crown_radius
    return dx * dx + dy * dy + dz * dz <= 1.25


def _leaf_color(p, rng, center, accent):
    """双色调绿：按高度 + 随机抖动在深 / 浅绿之间插值，部分簇整体提亮。"""
    h0 = p.crown_start * p.height
    h_rel = (center[1] - h0) / max(0.01, p.crown_height)
    if accent:
        t = rng.uniform(0.80, 1.0)
    else:
        t = 0.25 + 0.55 * h_rel + rng.uniform(-0.18, 0.18)
    return _lerp3(p.color_dark, p.color_light, t)


def _add_card(mesh, rng, p, center, color):
    """单张叶卡片 quad：随机朝向 + 随机滚转，UV 整幅映射叶贴图，
    底部两个顶点压暗，制造卡片内的明暗层次。"""
    size = p.card_size * (1.0 + rng.uniform(-1.0, 1.0) * p.card_size_jitter)
    d = _norm(_rand3(rng) + np.array([0.0, 0.35, 0.0]))  # 略偏上
    s, u, _ = _frame(d)
    roll = rng.uniform(0.0, 2.0 * math.pi)
    s2 = _rot(s, d, roll)
    u2 = _rot(u, d, roll)
    hx, hy = s2 * (size * 0.5), u2 * (size * 0.5)
    pts = [center - hx - hy, center + hx - hy, center + hx + hy, center - hx + hy]
    uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    dark = tuple(c * 0.72 for c in color)
    cols = [dark, dark, color, color]
    mesh.add_face(pts, uvs, cols, MAT_LEAF)


def _add_cluster(mesh, rng, p, center):
    """一簇叶卡片：簇内随机散布，整簇统一色调（高光簇整体偏浅绿）。"""
    accent = rng.random() < p.accent_prob
    for _ in range(p.cards_per_cluster):
        off = _rand3(rng)
        off[1] *= 0.75  # 压扁成扁团块，更接近参考图的云状树冠
        c = center + off * p.cluster_radius
        _add_card(mesh, rng, p, c, _leaf_color(p, rng, c, accent))


def add_leaves(mesh, p, rng, branches):
    """末端枝条的叶簇 + 树冠包络内的填充簇。"""
    cy = p.crown_start * p.height + p.crown_height * 0.5
    for b in branches:
        if not b.leafy or not _in_crown(p, b.spine[-1]):
            continue
        _add_cluster(mesh, rng, p, b.spine[-1])          # 末端簇
        if len(b.spine) > 2 and rng.random() < 0.5:      # 沿末段再补一簇
            _add_cluster(mesh, rng, p, b.spine[-2])
    # 填充簇：包络壳层随机撒点，补上细枝没长到的空洞
    for _ in range(p.extra_clusters):
        d = _norm(_rand3(rng))
        r = rng.uniform(0.55, 0.95)
        pt = np.array([d[0] * p.crown_radius * r,
                       cy + d[1] * p.crown_height * 0.5 * r,
                       d[2] * p.crown_radius * r])
        if pt[1] > p.crown_start * p.height + 0.3:
            _add_cluster(mesh, rng, p, pt)


# --------------------------------------------------------------------------
# 生成入口
# --------------------------------------------------------------------------
def generate(p):
    rng = random.Random(p.seed)
    np.random.seed(p.seed)
    mesh = Mesh()
    branches = build_skeleton(p, rng)
    for b in branches:
        sides = p.trunk_sides if b.depth == 0 else p.branch_sides
        _sweep(mesh, b.spine, b.radii, sides, rng)
    add_leaves(mesh, p, rng, branches)
    return mesh


# --------------------------------------------------------------------------
# OBJ + MTL 输出
# --------------------------------------------------------------------------
TEX_DIR = os.path.join("..", "mesh", "IL3DN_Tree_Beech_02").replace("\\", "/")


def write_mtl(path):
    leaf = f"{TEX_DIR}/IL3DN_Leaf_01.png"
    bark = f"{TEX_DIR}/IL3DN_Bark_Pine.png"
    with open(path, "w", encoding="utf-8") as f:
        f.write("# procedural stylized tree\n")
        f.write("newmtl bark\n")
        f.write("Kd 0.23 0.16 0.13\n")          # 深棕，贴图为灰白纹理
        f.write("Ks 0.0 0.0 0.0\n")
        f.write(f"map_Kd {bark}\n\n")
        f.write("newmtl leaf\n")
        f.write("Kd 1.0 1.0 1.0\n")               # 颜色来自顶点色
        f.write("Ks 0.0 0.0 0.0\n")
        f.write("d 1.0\n")
        f.write(f"map_Kd {leaf}\n")
        f.write(f"map_d {leaf}\n")                # alpha cutout


def write_obj(mesh, path, mtl_name):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# procedural stylized tree (vertex colors: v x y z r g b)\n")
        f.write(f"mtllib {mtl_name}\n")
        for (x, y, z), (r, g, b) in zip(mesh.v, mesh.vc):
            f.write(f"v {x:.5f} {y:.5f} {z:.5f} {r:.4f} {g:.4f} {b:.4f}\n")
        for u, vv in mesh.vt:
            f.write(f"vt {u:.5f} {vv:.5f}\n")
        # 平面化着色：每面一条法线
        nrm = []
        for idx, _ in mesh.f:
            a, b, c = (np.array(mesh.v[idx[k]]) for k in (0, 1, 2))
            nrm.append(_norm(np.cross(b - a, c - a)))
            f.write(f"vn {nrm[-1][0]:.4f} {nrm[-1][1]:.4f} {nrm[-1][2]:.4f}\n")
        cur = None
        for fi, (idx, mat) in enumerate(mesh.f):
            if mat != cur:
                f.write(f"usemtl {'leaf' if mat == MAT_LEAF else 'bark'}\n")
                cur = mat
            f.write("f " + " ".join(f"{i + 1}/{i + 1}/{fi + 1}" for i in idx) + "\n")


def main():
    ap = argparse.ArgumentParser(description="程序化风格化阔叶树生成器")
    ap.add_argument("--seed", type=int, default=TreeParams.seed)
    ap.add_argument("--height", type=float, default=TreeParams.height)
    ap.add_argument("--cards", type=int, default=TreeParams.cards_per_cluster,
                    help="每簇叶卡片数（叶密度）")
    ap.add_argument("--out", default=None, help="输出 OBJ 路径")
    args = ap.parse_args()

    p = TreeParams(seed=args.seed, height=args.height,
                   cards_per_cluster=args.cards)
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "sample_tree.obj")
    mesh = generate(p)
    write_mtl(os.path.splitext(out)[0] + ".mtl")
    write_obj(mesh, out, os.path.basename(os.path.splitext(out)[0]) + ".mtl")
    print("written:", out)
    print("stats:", mesh.stats())


if __name__ == "__main__":
    main()
