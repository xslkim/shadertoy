"""
程序化低模松树生成器
====================
纯 Python + numpy，不依赖任何 DCC。生成规格对齐参考资产
IL3DN_Tree_Pine_01_OneMesh.FBX 的实测结构：

  * 树干 + 轮生枝：锥形管状网格，全四边形
  * 叶片：V 形对折双 quad 卡片（6 顶点 / 2 面），UV 沿 U 跨 0→2
  * 顶点色编码风数据：A = 归一化高度，叶片 G = 每卡随机抖动相位
  * 三级 LOD：叶卡完全一致，只简化树干与枝条

输出 TreeMesh，含 positions / polys / uvs / normals / colors / mat_ids。
"""
from dataclasses import dataclass, field, replace
import math

import numpy as np


# --------------------------------------------------------------------------
# 参数
# --------------------------------------------------------------------------
@dataclass
class PineParams:
    seed: int = 0

    height: float = 4.94              # 树高 (m)
    trunk_radius: float = 0.105       # 根部半径 (m)
    trunk_taper: float = 1.35         # 半径衰减指数，越大越尖
    trunk_lean: float = 0.05          # 主干随机弯曲幅度 (m)

    whorl_count: int = 7              # 轮生层数
    whorl_start: float = 0.20         # 最低一层的相对高度
    whorl_end: float = 0.98
    branches_per_whorl: int = 5
    whorl_jitter: float = 0.05        # 层高随机扰动

    crown_radius: float = 1.50        # 最宽处枝条长度 (m)
    crown_taper: float = 0.70         # 树冠收敛指数
    branch_droop: float = 30.0        # 枝条下垂角 (度)
    branch_droop_tip: float = 10.0    # 末端上翘补偿 (度)
    branch_radius: float = 0.022      # 枝条根部半径 (m)

    cards_base: float = 5.6           # 底层每根枝上的叶卡数
    cards_top: float = 2.0            # 顶层每根枝上的叶卡数
    apex_cards: int = 4               # 树顶补的叶卡数，避免露出光秃的主干尖
    card_len: float = 0.70            # 叶卡脊线长度 (m)
    card_wing: float = 0.44           # 翼展 (m)
    card_fold: float = 34.0           # 对折半角 (度)，越小翼展越平
    card_size_jitter: float = 0.42
    card_roll_jitter: float = 45.0    # 绕枝条轴的滚转抖动 (度)，0 = 全部水平铺开
    card_pitch: float = 0.35          # 叶卡向下倾斜量
    card_span_start: float = 0.12     # 叶卡沿枝条的起始位置比例

    # 各 LOD 的细分参数：(树干边数, 树干纵段, 枝条边数, 枝条纵段, 保留枝条比例)
    lod_specs: tuple = (
        (6, 20, 6, 3, 1.0),
        (6, 16, 4, 1, 0.55),
        (6, 8, 0, 0, 0.0),
    )


MAT_BARK, MAT_LEAF = 0, 1


class TreeMesh:
    """四边形网格容器。UV / 法线 / 顶点色按 polygon-vertex 存储。"""

    def __init__(self):
        self.pos = []        # [(x,y,z)]
        self.polys = []      # [[vi,...]]
        self.mat_ids = []    # 每面一个
        self.uv = []         # 每 polygon-vertex 一个 (u,v)
        self.nrm = []        # 每 polygon-vertex 一个 (x,y,z)
        self.col = []        # 每 polygon-vertex 一个 (r,g,b,a)

    def add_vert(self, p):
        self.pos.append(tuple(p))
        return len(self.pos) - 1

    def add_poly(self, idxs, mat, uvs, nrms, cols):
        self.polys.append(list(idxs))
        self.mat_ids.append(mat)
        self.uv.extend(uvs)
        self.nrm.extend(nrms)
        self.col.extend(cols)

    @property
    def tri_count(self):
        return sum(len(p) - 2 for p in self.polys)

    def stats(self):
        bark = sum(1 for m in self.mat_ids if m == MAT_BARK)
        leaf = sum(1 for m in self.mat_ids if m == MAT_LEAF)
        return dict(verts=len(self.pos), polys=len(self.polys), tris=self.tri_count,
                    bark_polys=bark, leaf_polys=leaf)


# --------------------------------------------------------------------------
# 几何工具
# --------------------------------------------------------------------------
def _normalize(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else np.array([0.0, 0.0, 1.0])


def _frame(direction):
    """给定方向，构造正交基 (side, up, dir)。"""
    d = _normalize(np.asarray(direction, float))
    ref = np.array([0.0, 0.0, 1.0])
    if abs(d @ ref) > 0.95:
        ref = np.array([1.0, 0.0, 0.0])
    s = _normalize(np.cross(ref, d))
    u = np.cross(d, s)
    return s, u, d


def _tube(mesh, spine, radii, sides, height_ref, u0=0.02, u1=0.98, v_repeat=1.0):
    """沿 spine 折线生成锥形管，全四边形，返回新增面数。

    spine  : (N,3) 折线点
    radii  : (N,)  每个环的半径
    """
    spine = np.asarray(spine, float)
    n = len(spine)
    if n < 2 or sides < 3:
        return 0

    # 每段方向 -> 每个环的平均方向，保证管体不扭结
    seg = np.diff(spine, axis=0)
    ring_dir = np.zeros_like(spine)
    ring_dir[0] = seg[0]
    ring_dir[-1] = seg[-1]
    for i in range(1, n - 1):
        ring_dir[i] = seg[i - 1] + seg[i]

    # 平行传输参考向量，避免逐环重新起算导致的扭转
    s0, _, d0 = _frame(ring_dir[0])
    rings = []
    ref = s0
    for i in range(n):
        d = _normalize(ring_dir[i])
        ref = _normalize(ref - d * (ref @ d))
        side = ref
        up = np.cross(d, side)
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            p = spine[i] + radii[i] * (math.cos(a) * side + math.sin(a) * up)
            ring.append(mesh.add_vert(p))
        rings.append((ring, side, up, d))

    faces = 0
    total_len = np.linalg.norm(seg, axis=1).sum() or 1.0
    acc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(seg, axis=1))]) / total_len
    for i in range(n - 1):
        r0, s_a, u_a, d_a = rings[i]
        r1, s_b, u_b, d_b = rings[i + 1]
        for k in range(sides):
            k2 = (k + 1) % sides
            quad = [r0[k], r0[k2], r1[k2], r1[k]]
            # 径向法线
            def radial(ring_i, kk):
                a = 2 * math.pi * kk / sides
                sd, up = (s_a, u_a) if ring_i == 0 else (s_b, u_b)
                return tuple(_normalize(math.cos(a) * sd + math.sin(a) * up))

            nrms = [radial(0, k), radial(0, k2), radial(1, k2), radial(1, k)]
            uu = lambda kk: u0 + (u1 - u0) * (kk / sides)
            vv = lambda ii: acc[ii] * v_repeat
            uvs = [(uu(k), vv(i)), (uu(k + 1), vv(i)), (uu(k + 1), vv(i + 1)), (uu(k), vv(i + 1))]
            cols = [_wind_color(mesh.pos[v], height_ref, MAT_BARK, 0.0) for v in quad]
            mesh.add_poly(quad, MAT_BARK, uvs, nrms, cols)
            faces += 1
    return faces


def _wind_color(p, height, mat, phase):
    """顶点色 = 风动画数据。A = 归一化高度；叶片 G = 每卡抖动相位。"""
    a = min(max(p[2] / height, 0.0), 1.0)
    g = phase if mat == MAT_LEAF else 0.0
    return (0.0, g, 0.0, a)


def _leaf_card(mesh, origin, direction, side_hint, length, wing, fold_deg, height_ref, phase):
    """V 形对折叶卡：2 个脊点 + 两侧各 2 个翼点 = 6 顶点 / 2 四边形。"""
    d = _normalize(np.asarray(direction, float))
    s = np.asarray(side_hint, float)
    s = _normalize(s - d * (s @ d))
    up = np.cross(d, s)

    s0 = np.asarray(origin, float)
    s1 = s0 + d * length

    fold = math.radians(fold_deg)
    w1 = math.cos(fold) * s + math.sin(fold) * up
    w2 = -math.cos(fold) * s + math.sin(fold) * up

    a0 = s0 + w1 * wing
    a1 = s1 + w1 * wing
    b0 = s0 + w2 * wing
    b1 = s1 + w2 * wing

    vs = [mesh.add_vert(p) for p in (s0, s1, a0, a1, b0, b1)]
    Vs0, Vs1, Va0, Va1, Vb0, Vb1 = vs

    n1 = tuple(_normalize(np.cross(d, w1)))
    n2 = tuple(_normalize(np.cross(w2, d)))

    # 翼 1 -> UV u∈[1,2]；翼 2 -> UV u∈[0,1]（贴图沿 U 平铺两次）
    q1 = [Vs0, Vs1, Va1, Va0]
    uv1 = [(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)]
    q2 = [Vs1, Vs0, Vb0, Vb1]
    uv2 = [(1.0, 0.0), (0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]

    for q, uvs, nn in ((q1, uv1, n1), (q2, uv2, n2)):
        cols = [_wind_color(mesh.pos[v], height_ref, MAT_LEAF, phase) for v in q]
        mesh.add_poly(q, MAT_LEAF, uvs, [nn] * 4, cols)


# --------------------------------------------------------------------------
# 骨架
# --------------------------------------------------------------------------
def _trunk_spine(p: PineParams, rng, samples=64):
    """主干折线：轻微随机弯曲，顶端收细。"""
    t = np.linspace(0, 1, samples)
    z = t * p.height
    phi = rng.uniform(0, 2 * math.pi)
    bend = p.trunk_lean * p.height
    x = bend * (t ** 2) * math.cos(phi) + 0.35 * bend * np.sin(t * 3.1 + phi)
    y = bend * (t ** 2) * math.sin(phi) + 0.35 * bend * np.cos(t * 2.7 + phi)
    x -= x[0]
    y -= y[0]
    return np.stack([x, y, z], axis=1)


def _sample_spine(spine, t):
    """按归一化高度在主干上取点（含线性插值）。"""
    zs = spine[:, 2] / spine[-1, 2]
    i = np.searchsorted(zs, t)
    i = min(max(i, 1), len(spine) - 1)
    f = (t - zs[i - 1]) / max(zs[i] - zs[i - 1], 1e-9)
    return spine[i - 1] + (spine[i] - spine[i - 1]) * f


def _branch_layout(p: PineParams, rng, spine):
    """生成所有枝条：起点、方向、长度、所属层。"""
    branches = []
    golden = math.radians(137.5)
    for j in range(p.whorl_count):
        f = j / max(p.whorl_count - 1, 1)
        t = p.whorl_start + (p.whorl_end - p.whorl_start) * f
        t = min(max(t + rng.uniform(-1, 1) * p.whorl_jitter, 0.05), 0.995)
        base = _sample_spine(spine, t)

        # 树冠包络：越高越短
        shrink = max((1.0 - t) / (1.0 - p.whorl_start), 0.0) ** p.crown_taper
        length = p.crown_radius * shrink
        if length < 0.06:
            continue

        n_br = p.branches_per_whorl
        a0 = golden * j + rng.uniform(0, 0.5)
        for k in range(n_br):
            a = a0 + 2 * math.pi * k / n_br + rng.uniform(-0.18, 0.18)
            L = length * rng.uniform(0.78, 1.15)
            droop = math.radians(p.branch_droop * rng.uniform(0.7, 1.3))
            horiz = np.array([math.cos(a), math.sin(a), 0.0])
            direction = _normalize(horiz * math.cos(droop) - np.array([0, 0, 1.0]) * math.sin(droop))
            branches.append(dict(t=t, base=base, dir=direction, len=L, azim=a, layer=j))
    return branches


def _branch_spine(p: PineParams, br, segments):
    """枝条折线：根部按下垂角出发，末端上翘。"""
    n = max(segments, 1) + 1
    ts = np.linspace(0, 1, n)
    d = br["dir"]
    horiz = _normalize(np.array([d[0], d[1], 0.0]))
    up = np.array([0.0, 0.0, 1.0])
    lift = math.tan(math.radians(p.branch_droop_tip))
    pts = []
    for t in ts:
        along = br["len"] * t
        # 末端上翘：二次项
        dz = d[2] * along + lift * br["len"] * (t ** 2) * 0.9
        pts.append(br["base"] + horiz * (along * math.hypot(d[0], d[1])) + up * dz)
    return np.array(pts)


# --------------------------------------------------------------------------
# 主入口
# --------------------------------------------------------------------------
def generate(p: PineParams, lod: int = 0):
    """生成指定 LOD 的松树网格。叶卡在所有 LOD 完全一致（由 seed 决定）。"""
    rng = np.random.default_rng(p.seed)
    spine = _trunk_spine(p, rng)
    branches = _branch_layout(p, rng, spine)

    t_sides, t_segs, b_sides, b_segs, b_keep = p.lod_specs[lod]
    mesh = TreeMesh()

    # --- 主干 ---
    idx = np.linspace(0, len(spine) - 1, t_segs + 1).astype(int)
    tspine = spine[idx]
    tt = tspine[:, 2] / p.height
    tradii = p.trunk_radius * np.clip(1.0 - tt, 0.0, 1.0) ** p.trunk_taper + 0.006
    _tube(mesh, tspine, tradii, t_sides, p.height, u0=0.02, u1=0.98, v_repeat=4.0)

    # --- 枝条（LOD 降级时按比例保留，并降低细分）---
    if b_sides >= 3 and b_segs >= 1 and b_keep > 0:
        keep_n = max(int(round(len(branches) * b_keep)), 0)
        # 优先保留低层的粗枝（视觉贡献最大）
        order = sorted(range(len(branches)), key=lambda i: -branches[i]["len"])
        keep = set(order[:keep_n])
        for i, br in enumerate(branches):
            if i not in keep:
                continue
            bs = _branch_spine(p, br, b_segs)
            r0 = p.branch_radius * (0.55 + 0.45 * br["len"] / max(p.crown_radius, 1e-6))
            radii = r0 * np.linspace(1.0, 0.25, len(bs))
            _tube(mesh, bs, radii, b_sides, p.height, u0=0.02, u1=0.5, v_repeat=2.0)

    # --- 叶卡（与 LOD 无关，用独立 rng 保证三个 LOD 完全一致）---
    lrng = np.random.default_rng(p.seed + 991)
    for br in branches:
        f = (br["t"] - p.whorl_start) / max(p.whorl_end - p.whorl_start, 1e-6)
        n_cards = int(round(p.cards_base + (p.cards_top - p.cards_base) * f))
        n_cards = max(n_cards, 1)
        bs = _branch_spine(p, br, 8)
        seg_len = np.linalg.norm(np.diff(bs, axis=0), axis=1)
        acc = np.concatenate([[0.0], np.cumsum(seg_len)])
        total = acc[-1] or 1.0

        for c in range(n_cards):
            s0_ = p.card_span_start
            s = s0_ + (1.0 - s0_) * ((c + 0.5) / n_cards)
            s = min(max(s + lrng.uniform(-0.05, 0.05), 0.05), 1.0)
            target = s * total
            i = int(np.searchsorted(acc, target))
            i = min(max(i, 1), len(bs) - 1)
            w = (target - acc[i - 1]) / max(acc[i] - acc[i - 1], 1e-9)
            pos = bs[i - 1] + (bs[i] - bs[i - 1]) * w
            tang = _normalize(bs[i] - bs[i - 1])

            # 叶卡默认沿水平方向铺开（形成层叠"托盘"轮廓），再按抖动量绕枝条轴滚转
            base_side = np.cross(tang, np.array([0.0, 0.0, 1.0]))
            if np.linalg.norm(base_side) < 1e-6:
                base_side = np.array([1.0, 0.0, 0.0])
            base_side = _normalize(base_side)
            roll = math.radians(p.card_roll_jitter) * lrng.uniform(-1, 1)
            k = tang
            side_hint = (base_side * math.cos(roll)
                         + np.cross(k, base_side) * math.sin(roll)
                         + k * float(k @ base_side) * (1 - math.cos(roll)))

            scale = (1.0 - 0.55 * br["t"]) * lrng.uniform(1 - p.card_size_jitter, 1 + p.card_size_jitter)
            length = p.card_len * scale
            wing = p.card_wing * scale
            # 叶卡略微向外下方倾斜
            cdir = _normalize(tang + np.array([0, 0, -p.card_pitch]) + lrng.normal(0, 0.12, 3))
            phase = float(lrng.random())
            _leaf_card(mesh, pos - cdir * length * 0.35, cdir, side_hint,
                       length, wing, p.card_fold, p.height, phase)

    # --- 顶端叶卡：包住主干尖，避免树顶露出一截光杆 ---
    apex = spine[-1]
    for c in range(p.apex_cards):
        a = 2 * math.pi * c / max(p.apex_cards, 1) + lrng.uniform(-0.3, 0.3)
        cdir = _normalize(np.array([math.cos(a) * 0.55, math.sin(a) * 0.55, 0.78]))
        side_hint = np.array([-math.sin(a), math.cos(a), 0.0])
        scale = 0.5 * lrng.uniform(1 - p.card_size_jitter, 1 + p.card_size_jitter)
        _leaf_card(mesh, apex - cdir * p.card_len * scale * 0.75, cdir, side_hint,
                   p.card_len * scale, p.card_wing * scale, p.card_fold,
                   p.height, float(lrng.random()))

    return mesh


def generate_lods(p: PineParams):
    return [generate(p, i) for i in range(len(p.lod_specs))]
