# -*- coding: utf-8 -*-
"""
gen_pine02.py — 用 bpy 生成器复刻 IL3DN_Tree_Pine_02 参考松树 (v2)
================================================================
v2 重写：修复 v1 "生日蛋糕式年轮分层"。v1 用 11 个离散等距轮生层 +
针叶卡片沿枝成薄条带 → 渲染成一圈圈平环。v2 改为：

  * 附着点：不规则间距"附着带"(泊松式间距) + 带内大抖动，方位角完全随机，
    全树 40~70 根枝，附着高度覆盖冠部 0.15H~0.97H（连续随机、无均分）
  * 枝长随高度递减保持圆锥轮廓，但同高度 ±40% 噪声，少量 rogue 长枝破形；
    仰角混合（下部平/垂、上部上仰），枝梢随机上翘或下挂
  * 针叶卡片按高斯聚簇在枝 40%~100% 段（非均匀条带），垂直散布
    σ=0.10~0.18×枝长 → 厚重蓬松叶垫；垫缘/末端加下垂针叶穗卡片
    （倾角 58°~88° 近竖直下垂）→ 参差下垂剪影
  * 相邻高度枝条的厚垫边缘互相嵌入（参差重叠厚垫，保留 IL3DN 分层感，
    但不是平环、也不混成一团）；冠内沿主干补位卡片，避免"光杆穿环"

贴图 UV / 配色沿用 v1 标定（整幅采样为主；LEAF_DARK #173E30 /
LEAF_LIGHT #54996F / BARK #4A302B）；底部 15% 裸干 + 1 枯枝 + 顶梢。

用法：
  blender -b --factory-startup --python gen_pine02.py -- --mode candidates
  blender -b --factory-startup --python gen_pine02.py -- --mode final --seed N
"""
import argparse
import math
import os
import random
import sys
from dataclasses import dataclass

import bpy
from mathutils import Vector, Quaternion

HERE = os.path.dirname(os.path.abspath(__file__))
GEN_DIR = r"d:\shadertoy\speedtree\rebuild_mesh"
sys.path.insert(0, GEN_DIR)
import blender_tree_gen as tg      # noqa: E402
import batch_render as br          # noqa: E402  复用 make_rig / render_to

TEX_DIR = r"d:\shadertoy\speedtree\mesh\IL3DN_Tree_Pine_02"
BARK_TEX = os.path.join(TEX_DIR, "IL3DN_Bark_Pine.png")
PINE_TEX = os.path.join(TEX_DIR, "IL3DN_Pine_01.png")

RENDER_DIR = os.path.join(HERE, "renders")
OUT_DIR = os.path.join(HERE, "output")

# ---- 松树风格色（覆盖生成器模块全局，材质函数在调用时读取）----
tg.LEAF_DARK = tg._srgb("#1D5240")    # 深松绿（偏蓝）
tg.LEAF_LIGHT = tg._srgb("#6BB98A")   # 亮部明快青绿（v3 提亮）
tg.BARK_TINT = tg._srgb("#6B4538")    # 暖红棕树干（v3.2 调暖）

# 针叶贴图采样区域（alpha 实测；重复项=权重。
# v3：整幅权重降到 ×2（大卡片会露贴图对角条纹边界=梳齿穿帮），
# 提高致密子区域权重，配合小卡片消除条纹感）
PINE_UV_RECTS = [
    (0.02, 0.02, 0.98, 0.98),      # 整幅 ×2
    (0.02, 0.02, 0.98, 0.98),
    (0.526, 0.417, 0.993, 0.988),  # 右上大团 ×2
    (0.526, 0.417, 0.993, 0.988),
    (0.060, 0.029, 0.600, 0.474),  # 左下团 ×2
    (0.060, 0.029, 0.600, 0.474),
    (0.024, 0.028, 0.458, 0.351),  # 左团 ×2
    (0.024, 0.028, 0.458, 0.351),
    (0.075, 0.029, 0.667, 0.526),  # 下半宽团
    (0.021, 0.031, 0.274, 0.207),  # 左下小团
    (0.026, 0.029, 0.379, 0.294),  # 左下中团
    (0.532, 0.398, 0.993, 0.894),  # 右团
]


@dataclass
class PineSpec:
    seed: int = 3
    height: float = 8.5
    crown_start: float = 0.17        # 冠部起始相对高度（其下为裸干）
    crown_top: float = 0.97
    # 枝条附着（带 = 叶垫簇中心，带内抖动使垫参差但不混成一团）
    n_bands: tuple = (11, 14)
    band_jitter: float = 0.22        # 带内附着高度抖动 σ（× 平均带距）
    branches_band: tuple = (2, 4)    # 每带基础枝数（低带额外加）
    # 枝形态（v3.1：叶垫需抵达枝端，目标高宽比 ~1.6:1）
    branch_len_max: float = 1.70     # 底部基准枝长（半径）
    branch_len_min: float = 0.32     # 顶部基准枝长
    len_jitter: float = 0.30         # 同高度枝长 ±30%
    rogue_prob: float = 0.06         # rogue 长枝概率（限冠中部，幅度收敛）
    # 针叶卡片（v3.3：中等卡片，垫面平铺与蓬松随机混合）
    card_density: float = 40.0       # 每米^1.05 枝长的卡片数
    card_size: float = 0.52
    pad_sigma_z: tuple = (0.10, 0.16)  # 垫厚垂直散布 σ（× 枝长）
    pad_sigma_h: float = 0.09        # 垫横向散布 σ（× 枝长）
    fringe_per_branch: tuple = (4, 6)  # 每枝下垂针叶穗卡片数
    trunk_cards: int = 150           # 冠内主干补位卡片
    trunk_radius: float = 0.11
    trunk_lean: float = 0.08
    gradient_dark: float = 0.38
    dead_branch_len: float = 0.55
    max_cards: int = 3200


def _spine(rng, S):
    n = 14
    lean_ang = rng.uniform(0, math.tau)
    lean = Vector((math.cos(lean_ang), math.sin(lean_ang), 0))
    phase = rng.uniform(0, math.tau)
    pts = []
    for i in range(n + 1):
        t = i / n
        sway = math.sin(t * math.pi * 1.2 + phase) * 0.05 * t
        off = lean * (S.trunk_lean * t * t + sway)
        pts.append(Vector((off.x, off.y, S.height * t)))
    return pts


def _spine_at(spine, t):
    n = len(spine) - 1
    t = max(0.0, min(1.0, t)) * n
    i0 = min(int(t), n - 1)
    return spine[i0].lerp(spine[i0 + 1], t - i0)


def _bezier(p0, p1, p2, s):
    a = p0.lerp(p1, s)
    b = p1.lerp(p2, s)
    return a.lerp(b, s)


def gen_pine(rng, S):
    """返回 (branches, hosts, spine)。branches: (pts, radii, sides)；
    hosts: (p0, p1, p2, L, tn, kind, pad_bright)。"""
    spine = _spine(rng, S)
    R = S.trunk_radius
    trunk_radii = [max(R * (1 - 0.72 * i / 14) + R * 0.5 * (1 - i / 14) ** 4,
                       0.02) for i in range(15)]
    branches = [(spine, trunk_radii, 7)]
    hosts = []

    # ---- 底部枯枝 ----
    t0 = rng.uniform(0.08, 0.13)
    p0 = _spine_at(spine, t0)
    az = rng.uniform(0, math.tau)
    d = Vector((math.cos(az), math.sin(az), 0.15)).normalized()
    L = S.dead_branch_len * rng.uniform(0.8, 1.2)
    branches.append(([p0, p0 + d * L * 0.6 + Vector((0, 0, -0.05 * L)),
                      p0 + d * L + Vector((0, 0, 0.04 * L))],
                     [0.03, 0.018, 0.008], 5))

    # ---- 附着带：不规则间距（泊松式），低带宽、高处略密 ----
    z0, z1 = S.crown_start, S.crown_top
    n_bands = rng.randint(*S.n_bands)
    mean_gap = (z1 - z0) / n_bands
    bands = []
    t = z0 + rng.uniform(0, 0.3 * mean_gap)
    while t < z1 - 0.4 * mean_gap:
        bands.append(t)
        tn = (t - z0) / (z1 - z0)
        t += mean_gap * rng.uniform(0.55, 1.45) * (1.0 - 0.10 * tn)
    bands.append(z1 - rng.uniform(0.0, 0.02))

    for tb in bands:
        tn_b = (tb - z0) / (z1 - z0)
        k = rng.randint(*S.branches_band) + round(1.5 * (1.0 - tn_b))
        for _ in range(k):
            # 带内高斯抖动 → 附着高度连续随机（带间尾部互相搭接）
            t = min(max(rng.gauss(tb, S.band_jitter * mean_gap), z0), z1)
            tn = (t - z0) / (z1 - z0)
            az = rng.uniform(0, math.tau)          # 方位角完全随机
            L = S.branch_len_min + (S.branch_len_max - S.branch_len_min) \
                * (1 - tn) ** 1.12
            L *= rng.uniform(1.0 - S.len_jitter, 1.0 + S.len_jitter)
            if rng.random() < S.rogue_prob and 0.15 < tn < 0.80:
                L *= rng.uniform(1.20, 1.35)       # rogue 长枝限冠中部
            L = max(L, 0.30)
            # 仰角：下部平/微垂 → 上部上仰；部分枝额外下垂
            elev = math.radians(-10 + 38 * tn + rng.gauss(0, 9))
            if rng.random() < 0.16:
                elev -= math.radians(rng.uniform(8, 24))
            ch = math.cos(elev)
            d = Vector((math.cos(az) * ch, math.sin(az) * ch,
                        math.sin(elev)))
            p0 = _spine_at(spine, t) + d * 0.03
            # 梢部形态随高度：下垫平/微垂，上垫明显上翘
            lift = rng.uniform(-0.15 + 0.30 * tn, 0.10 + 0.22 * tn) * L
            p1 = p0 + d * (L * 0.55) + Vector((0, 0, 0.3 * lift))
            p2 = p0 + d * L + Vector((0, 0, lift))
            r0 = 0.045 * min(L / S.branch_len_max, 1.0) + 0.012
            branches.append(([p0, p1, p2], [r0, r0 * 0.5, 0.008], 5))
            hosts.append((p0, p1, p2, L, tn, 'pad',
                          rng.uniform(0.82, 1.12)))

    # ---- 顶梢 ----
    p_top = spine[-1]
    hosts.append((p_top - Vector((0, 0, 0.18)), p_top + Vector((0, 0, 0.12)),
                  p_top + Vector((0, 0, 0.42)), 0.60, 1.0, 'leader', 1.06))
    return branches, hosts, spine


def build_needles(rng, S, hosts, spine):
    verts, faces, face_uvs, face_vcols = [], [], [], []
    cards = []   # (pos, nrm, spin, size, bright, elong)

    z_bot = min(h[0].z for h in hosts)
    z_top = max(h[2].z for h in hosts)
    z_span = max(z_top - z_bot, 1e-3)
    z_floor = S.height * S.crown_start - 0.05   # 保住底部裸干

    def shade(pos_z, pad_b, factor=1.0):
        # 全局高度渐变放缓，双色对比主要由垫级 f 承担
        return (0.80 + 0.30 * (pos_z - z_bot) / z_span) * pad_b * factor

    def rand_nrm(rng_, tilt_lo, tilt_hi):
        """老朝向模式：绕随机方位角后倾斜（顶梢/补位卡用）"""
        yaw = rng_.uniform(0, math.tau)
        tilt = math.radians(rng_.uniform(tilt_lo, tilt_hi))
        return Quaternion(Vector((0, 0, 1)), yaw) \
            @ Quaternion(Vector((1, 0, 0)), tilt) @ Vector((0, 0, 1))

    for p0, p1, p2, L, tn, kind, pad_b in hosts:
        if kind == 'leader':
            n = max(16, int(22 * rng.uniform(0.85, 1.15)))
        else:
            n = max(5, int(S.card_density * (L ** 1.05)
                           * rng.uniform(0.8, 1.2)))
        sigma_z = L * rng.uniform(*S.pad_sigma_z)
        sigma_h = L * S.pad_sigma_h
        dh = Vector((p2.x - p0.x, p2.y - p0.y, 0))
        hperp = Vector((-dh.y, dh.x, 0)).normalized() \
            if dh.length_squared > 1e-6 else Vector((1, 0, 0))
        along = (p2 - p0).normalized() \
            if (p2 - p0).length_squared > 1e-6 else Vector((1, 0, 0))
        # v3.2：垫平面法线 = 竖直略外倾，垫内卡片与该面共面平铺
        n_pad = (Vector((0, 0, 1))
                 + Vector((along.x, along.y, 0)) * 0.25).normalized()

        for _ in range(n):
            if kind == 'leader':
                s = rng.uniform(0.0, 1.0)
                pos = _bezier(p0, p1, p2, s) + Vector(
                    (rng.gauss(0, 0.045), rng.gauss(0, 0.045),
                     rng.gauss(0, 0.04)))
                nrm = rand_nrm(rng, -10, 55)
                size = S.card_size * rng.uniform(0.50, 0.80)
                bright = shade(pos.z, pad_b, 1.05)
                elong = 1.0
            else:
                # 高斯聚簇偏枝外段（中心 0.72，垫外缘抵达枝端之外）
                s = min(max(rng.gauss(0.72, 0.18), 0.12), 1.12)
                base = _bezier(p0, p1, p2, s)
                pos = Vector((base.x, base.y, base.z))
                pos += hperp * rng.gauss(0, sigma_h)
                pos += along * rng.gauss(0, 0.04 * L)
                pos.z += rng.gauss(0, sigma_z) - 0.02 * L
                pos.z = max(pos.z, z_floor)
                # v3.4：75% 垫面平铺 + 25% 蓬松随机
                if rng.random() < 0.75:
                    nrm = (n_pad + Vector((rng.gauss(0, 0.40),
                                           rng.gauss(0, 0.40),
                                           rng.gauss(0, 0.25)))).normalized()
                else:
                    nrm = rand_nrm(rng, 5, 55)
                size = S.card_size * rng.uniform(0.75, 1.30) \
                    * (1.15 - 0.30 * tn)
                # 垫级双色（v3.4 加强暗部）：垫顶亮 / 垫底深墨绿
                if pos.z > base.z + 0.15 * sigma_z:
                    f = 1.08                        # 垫顶亮
                elif pos.z < base.z - 0.15 * sigma_z:
                    f = 0.55                        # 垫底深墨绿
                else:
                    f = 0.85
                if s < 0.4:
                    f *= 0.95                       # 近干内侧略暗
                bright = shade(pos.z, pad_b, f)
                elong = 1.0
            cards.append((pos, nrm, rng.uniform(0, math.tau), size,
                          bright, elong))

        # ---- 垫缘/末端下垂针叶穗（近竖直下垂，参差剪影，压暗）----
        if kind != 'leader':
            k = max(2, int(rng.randint(*S.fringe_per_branch)
                           * min(L / 1.2, 1.5)))
            for _ in range(k):
                s = rng.uniform(0.50, 1.00)
                base = _bezier(p0, p1, p2, s)
                pos = Vector((base.x, base.y, base.z))
                pos += hperp * rng.gauss(0, sigma_h * 0.6)
                # 低层垫下垂幅度收敛，避免侵入裸干区
                pos.z -= rng.uniform(0.08, 0.18) * L * (0.55 + 0.45 * tn)
                pos.z = max(pos.z, z_floor)
                nrm = rand_nrm(rng, 60, 88)
                size = S.card_size * rng.uniform(0.8, 1.20) \
                    * (1.10 - 0.25 * tn)
                bright = shade(pos.z, pad_b, 0.55)
                cards.append((pos, nrm, rng.uniform(0, math.tau), size,
                              bright, 1.15))

    # ---- 冠内主干补位卡片（少量，离干一小段距离避免淹没主干）----
    for _ in range(S.trunk_cards):
        t = rng.triangular(S.crown_start, S.crown_top, 0.55)
        c = _spine_at(spine, t)
        az = rng.uniform(0, math.tau)
        rr = rng.uniform(0.12, 0.48) * (1.15 - 0.55 * t)
        pos = c + Vector((math.cos(az) * rr, math.sin(az) * rr,
                          rng.gauss(0, 0.08)))
        nrm = rand_nrm(rng, 5, 65)
        size = S.card_size * rng.uniform(0.60, 1.10) * (1.1 - 0.3 * t)
        bright = shade(pos.z, 1.0, 0.62)
        cards.append((pos, nrm, rng.uniform(0, math.tau), size, bright,
                      1.0))

    # ---- 总量控制 ----
    if len(cards) > S.max_cards:
        cards = rng.sample(cards, S.max_cards)

    for pos, nrm, spin, size, bright, elong in cards:
        h = size * elong
        w = size * rng.uniform(0.85, 1.05)
        # 由法线 + 自旋角构建面内基
        ref = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
        r0 = nrm.cross(ref).normalized()
        right = Quaternion(nrm, spin) @ r0
        up2 = nrm.cross(right).normalized()
        right = right * (w * 0.5)
        up2 = up2 * (h * 0.5)
        # UV 内缩 2% 防贴图边缘漏色（须边伪影）
        u0, v0, u1, v1 = rng.choice(PINE_UV_RECTS)
        du, dv = (u1 - u0) * 0.02, (v1 - v0) * 0.02
        u0, v0, u1, v1 = u0 + du, v0 + dv, u1 - du, v1 - dv
        b = len(verts)
        quad = [pos - right - up2, pos + right - up2,
                pos + right + up2, pos - right + up2]
        uvs = ((u0, v0), (u1, v0), (u1, v1), (u0, v1))
        jit = rng.uniform(0.92, 1.06)
        lo = min(S.gradient_dark * bright * jit, 1.0)
        hi = min(bright * jit, 1.0)
        cols = (lo, lo, hi, hi)
        if rng.random() < 0.5:                   # 随机翻面
            quad.reverse()
            uvs = tuple(reversed(uvs))
            cols = (hi, hi, lo, lo)
        verts += quad
        faces.append((b, b + 1, b + 2, b + 3))
        face_uvs.append(uvs)
        face_vcols.append(cols)

    print("[pine02] needle cards: %d (~%d tris)" % (len(cards),
                                                    len(cards) * 2))
    return tg.build_mesh_object("StylizedPine_Needles", verts, faces,
                                face_uvs, face_vcols)


def build_pine(S, export_fbx, export_name=""):
    rng = random.Random(S.seed)
    tg.clear_scene()
    bpy.context.scene.unit_settings.system = 'METRIC'

    branches, hosts, spine = gen_pine(rng, S)
    verts, faces, face_uvs = [], [], []
    for pts, radii, sides in branches:
        tg.add_tube(verts, faces, face_uvs, pts, radii, sides, 0.0, 0.35)
    trunk = tg.build_mesh_object("StylizedPine_Trunk", verts, faces, face_uvs)
    trunk["gen_seed"] = S.seed
    trunk["style"] = "IL3DN_stylized_pine"
    print("[pine02] branches: %d, trunk tris: %d"
          % (len(branches), len(faces)))

    leaves = build_needles(rng, S, hosts, spine)

    bark_img = tg.load_image(BARK_TEX)
    pine_img = tg.load_image(PINE_TEX)
    trunk.data.materials.append(tg.make_bark_material(bark_img))
    leaves.data.materials.append(
        tg.make_leaf_material(pine_img, tg.TreeParams(alpha_cutoff=0.60)))

    if export_fbx:
        tg.export_fbx([trunk, leaves],
                      os.path.join(OUT_DIR, export_name),
                      bark_img, pine_img)
    return trunk, leaves


CANDIDATE_SEEDS = [3, 9, 17]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["candidates", "final"],
                    default="candidates")
    ap.add_argument("--seed", type=int, default=3)
    cli = ap.parse_args(argv)

    os.makedirs(RENDER_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    if cli.mode == "candidates":
        for seed in CANDIDATE_SEEDS:
            trunk, leaves = build_pine(PineSpec(seed=seed), export_fbx=False)
            cam = br.make_rig()
            br.render_to(cam, [trunk, leaves],
                         os.path.join(RENDER_DIR,
                                      "cand_v3_seed%02d.png" % seed),
                         600, 760)
        print("[pine02] v3 candidates done:", CANDIDATE_SEEDS)
        return

    name = "IL3DN_style_Pine02_v3_seed%d.fbx" % cli.seed
    trunk, leaves = build_pine(PineSpec(seed=cli.seed), export_fbx=True,
                               export_name=name)
    cam = br.make_rig()
    br.render_to(cam, [trunk, leaves],
                 os.path.join(RENDER_DIR, "pine02_v3_front.png"), 600, 760)
    for ob in (trunk, leaves):
        ob.rotation_euler.z = math.radians(35)
    bpy.context.view_layer.update()
    br.render_to(cam, [trunk, leaves],
                 os.path.join(RENDER_DIR, "pine02_v3_three_quarter.png"),
                 600, 760)
    print("[pine02] v3 final done, seed=%d -> %s" % (cli.seed, name))


if __name__ == "__main__":
    main()
