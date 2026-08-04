# -*- coding: utf-8 -*-
"""
blender_tree_gen.py — Blender 程序化生成风格化低多边形树木（原型）
=================================================================
目标风格：单根细长主干 + 下部少量光秃短枝 + 多团叶卡片（quad）簇树冠，
复用 mesh/IL3DN_Tree_Beech_02 下的同一张叶子/树皮贴图（alpha 裁切、
绿色双色调渐变、平面化着色），导出 FBX（内嵌贴图）供 Unity 导入。

运行方式：
  1) Blender GUI：文本编辑器打开本文件 -> Run Script（默认 seed=7 生成一棵并导出）
  2) 命令行后台（推荐批量）：
     "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" ^
         --background --factory-startup ^
         --python blender_tree_gen.py -- --seed 7 --count 3
  3) 经 blender-mcp 驱动：AI 客户端 execute_code 执行
     exec(compile(open(r"d:\\shadertoy\\speedtree\\rebuild_mesh\\blender_tree_gen.py",
                       encoding="utf-8").read(), __file__, 'exec'))

风格统一关键：所有随机都来自同一个带种子 random.Random；
贴图 / 配色 / 叶卡片尺寸分布 / 形态比例全部集中在 TreeParams，
改种子只改形状，不改风格。
"""
import argparse
import math
import os
import random
import sys
from dataclasses import dataclass, field

import bpy
from mathutils import Vector, Quaternion

# --------------------------------------------------------------------------
# 路径配置（按本机工程位置；如需迁移只改 TEXTURE_DIR）
# --------------------------------------------------------------------------
TEXTURE_DIR = r"d:\shadertoy\speedtree\mesh\IL3DN_Tree_Beech_02"
BARK_TEX = os.path.join(TEXTURE_DIR, "IL3DN_Bark_Pine.png")
LEAF_TEX = os.path.join(TEXTURE_DIR, "IL3DN_Leaf_01.png")


def _script_dir():
    """兼容 Blender 文本编辑器（无 __file__）与命令行两种方式。"""
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return bpy.path.abspath("//")


OUTPUT_DIR = os.path.join(_script_dir(), "output")

# --------------------------------------------------------------------------
# 叶贴图采样区域（UV 矩形，origin 左下）
# 由 _analyze_leaf_atlas.py 对 alpha 通道实测：图集 = 左上巨大连通叶团
# (0.032,0.309)-(0.778,0.976) + 7 个小团；原资产的卡片即整幅采样贴图。
# 列表中重复项 = 采样权重（整幅为主，子区域增加多样性）。
# --------------------------------------------------------------------------
LEAF_UV_RECTS = [
    (0.02, 0.02, 0.98, 0.98),     # 整幅（主）×5
    (0.02, 0.02, 0.98, 0.98),
    (0.02, 0.02, 0.98, 0.98),
    (0.02, 0.02, 0.98, 0.98),
    (0.02, 0.02, 0.98, 0.98),
    (0.032, 0.309, 0.778, 0.976),  # 大叶团整取 ×3
    (0.032, 0.309, 0.778, 0.976),
    (0.032, 0.309, 0.778, 0.976),
    (0.032, 0.309, 0.420, 0.976),  # 大叶团左半
    (0.400, 0.309, 0.778, 0.976),  # 大叶团右半
    (0.325, 0.074, 0.581, 0.241),  # 中下宽团
    (0.767, 0.268, 0.958, 0.454),  # 右侧团
    (0.538, 0.331, 0.692, 0.472),  # 中部团
    (0.620, 0.111, 0.731, 0.281),  # 右下团
]


def _srgb(hex_str):
    """'#RRGGBB' -> Blender 线性空间 RGB 元组。"""
    h = hex_str.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
                 for c in srgb)


# 配色取样自参考截图 screenshot-1/2.png（sRGB 十六进制）
LEAF_DARK = _srgb("#2E6234")    # 叶簇暗部绿
LEAF_LIGHT = _srgb("#8AC162")   # 叶簇亮部绿
BARK_TINT = _srgb("#6E5148")    # 树皮贴图为浅灰白，乘此色得到棕紫树干


# --------------------------------------------------------------------------
# 参数表（泛化入口：同一套参数 = 同一种风格；改种子 = 同风格不同形状）
# --------------------------------------------------------------------------
@dataclass
class TreeParams:
    seed: int = 7

    # 整体比例
    height: float = 6.2           # 树高 (m)
    crown_start: float = 0.48     # 树冠起始相对高度（以下为光秃树干）
    crown_radius: float = 1.9     # 树冠包络水平半径 (m)
    crown_height: float = 3.0     # 树冠包络高度 (m)
    crown_blob_count: int = 4     # 叶簇团数（3~5 效果都好）
    crown_flatten: float = 0.85   # 叶簇团纵向压扁系数

    # 主干
    trunk_radius: float = 0.10    # 根部半径 (m)
    trunk_taper: float = 0.65     # 半径随高度线性衰减比例
    root_flare: float = 0.6       # 根部外扩程度
    trunk_lean: float = 0.22      # 主干整体倾斜幅度 (m)
    trunk_sway: float = 0.10      # 主干 S 弯幅度 (m)
    trunk_sway_freq: float = 1.3  # S 弯频率
    trunk_segments: int = 9       # 主干纵向段数
    trunk_sides: int = 7          # 主干圆周段数（低段数 = 风格化）

    # 下部光秃短枝
    dead_branch_min: int = 1
    dead_branch_max: int = 3
    dead_branch_len: float = 0.55  # 基准长度 (m)

    # 分枝公共
    branch_radius_ratio: float = 0.5   # 枝根半径 / 附着点主干半径
    branch_sides: int = 5

    # 叶卡片
    leaf_cards: int = 1000        # 全树叶卡片总数
    leaf_card_size: float = 0.56  # 基准边长 (m)，实际按 ±30% 抖动
    leaf_shell_bias: float = 0.35 # 采样偏向团表面概率（强化剪影）
    leaf_normal_jitter_deg: float = 65.0  # 卡片法线相对径向的抖动
    leaf_gradient_dark: float = 0.38      # 双色调暗端顶点色（灰度）
    leaf_double_sided: bool = False       # True=复制翻面三角形（Unity 单面 shader 时用）

    # 材质 / 贴图
    alpha_cutoff: float = 0.5
    bark_uv_scale: float = 0.35   # 树皮贴图 V 向密度（每米）

    # 导出
    export_fbx: bool = True
    export_dir: str = OUTPUT_DIR
    export_name: str = ""         # 留空自动 stylized_tree_seed{N}.fbx


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def clear_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def load_image(path):
    return bpy.data.images.load(os.path.abspath(path), check_existing=True)


def build_mesh_object(name, verts, faces, face_uvs=None, face_vcols=None):
    """由顶点/面列表建网格；face_uvs / face_vcols 与 faces 平行（每面每角一个）。"""
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if face_uvs is not None:
        uv_layer = me.uv_layers.new(name="UVMap")
        for poly, uvs in zip(me.polygons, face_uvs):
            for li, uv in zip(poly.loop_indices, uvs):
                uv_layer.data[li].uv = uv
    if face_vcols is not None:
        # FLOAT_COLOR：存 0..1 灰度作为双色调插值因子，材质里再映射到两种绿
        ca = me.color_attributes.new(name="Color", type='FLOAT_COLOR',
                                     domain='CORNER')
        for poly, cols in zip(me.polygons, face_vcols):
            for li, c in zip(poly.loop_indices, cols):
                ca.data[li].color = (c, c, c, 1.0)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def _perp(tangent):
    ref = Vector((0, 0, 1)) if abs(tangent.z) < 0.9 else Vector((1, 0, 0))
    return tangent.cross(ref).normalized()


def add_tube(verts, faces, face_uvs, pts, radii, sides, uv_v_start, uv_v_scale):
    """沿折线 pts 扫掠低段数变径圆管（接缝处重复顶点以展开圆柱 UV）。
    返回累计 V 坐标。平面着色(flat)自然呈现风格化棱面。"""
    n_rings = len(pts)
    ring_base = []
    v_acc = uv_v_start
    prev_n = None
    v_of_ring = []
    for i in range(n_rings):
        if i == 0:
            tan = (pts[1] - pts[0]).normalized()
        elif i == n_rings - 1:
            tan = (pts[-1] - pts[-2]).normalized()
        else:
            tan = (pts[i + 1] - pts[i - 1]).normalized()
        n = _perp(tan) if prev_n is None else \
            (prev_n - tan * prev_n.dot(tan)).normalized()   # 平行传输，避免扭结
        b = tan.cross(n).normalized()
        prev_n = n
        if i > 0:
            v_acc += (pts[i] - pts[i - 1]).length * uv_v_scale
        v_of_ring.append(v_acc)
        ring_base.append(len(verts))
        for s in range(sides + 1):          # +1 重复接缝顶点
            ang = math.tau * s / sides
            off = n * (math.cos(ang) * radii[i]) + b * (math.sin(ang) * radii[i])
            verts.append(pts[i] + off)
    for i in range(n_rings - 1):
        r0, r1 = ring_base[i], ring_base[i + 1]
        v0, v1 = v_of_ring[i], v_of_ring[i + 1]
        for s in range(sides):
            u0, u1 = s / sides, (s + 1) / sides
            faces.append((r0 + s, r0 + s + 1, r1 + s + 1, r1 + s))
            face_uvs.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))
    # 末端封口（尖端 n-gon，UV 收到一点）
    tip = ring_base[-1]
    faces.append(tuple(tip + s for s in reversed(range(sides))))
    face_uvs.append(tuple((0.5, v_of_ring[-1]) for _ in range(sides)))
    return v_acc


# --------------------------------------------------------------------------
# 骨架生成：主干脊线 + 下部光秃短枝 + 伸入各叶簇团的 scaffold 分枝
# --------------------------------------------------------------------------
def gen_clusters(rng, P, spine_top_xy):
    """返回 [(center, radius)]；布局模仿参考图：顶部大团 + 2~4 个侧团。"""
    layout = [  # (相对偏移, 半径系数)
        (Vector((0.00, 0.00, 1.00)), 1.00),   # 顶部主团
        (Vector((-0.80, 0.06, 0.30)), 0.72),  # 左团
        (Vector((0.78, -0.06, 0.18)), 0.68),  # 右团
        (Vector((0.06, 0.55, -0.28)), 0.60),  # 前下团
        (Vector((-0.10, -0.55, 0.02)), 0.56), # 后团
    ]
    count = max(3, min(P.crown_blob_count, len(layout)))
    picked = layout[:1] + rng.sample(layout[1:], count - 1)
    R, Hc = P.crown_radius, P.crown_height
    base_z = P.crown_start * P.height + 0.45 * Hc
    center0 = Vector((spine_top_xy[0], spine_top_xy[1], base_z))
    clusters = []
    for off, f in picked:
        c = center0 + Vector((off.x * R, off.y * R, off.z * 0.5 * Hc))
        c += Vector((rng.uniform(-0.12, 0.12) * R,
                     rng.uniform(-0.12, 0.12) * R,
                     rng.uniform(-0.10, 0.10) * Hc * 0.5))
        clusters.append((c, f * R * rng.uniform(0.9, 1.1)))
    return clusters


def gen_skeleton(rng, P):
    """返回 (branches, clusters)。branches: (pts, radii, sides)。"""
    H, n = P.height, P.trunk_segments
    lean_ang = rng.uniform(0, math.tau)
    lean_dir = Vector((math.cos(lean_ang), math.sin(lean_ang), 0))
    phase = rng.uniform(0, math.tau)

    spine = []
    for i in range(n + 1):
        t = i / n
        sway = math.sin(t * math.pi * P.trunk_sway_freq + phase) * P.trunk_sway * t
        off = lean_dir * (P.trunk_lean * t * t + sway)
        spine.append(Vector((off.x, off.y, H * t)))

    def trunk_r(t):
        r = P.trunk_radius * (1.0 - P.trunk_taper * t)
        r += P.trunk_radius * P.root_flare * (1.0 - t) ** 4
        return max(r, 0.015)

    def spine_at(t):
        t = max(0.0, min(1.0, t)) * n
        i0 = min(int(t), n - 1)
        return spine[i0].lerp(spine[i0 + 1], t - i0)

    branches = [(spine, [trunk_r(i / n) for i in range(n + 1)], P.trunk_sides)]

    # 下部光秃短枝：中段略下垂、末端略回翘的三点折线
    for _ in range(rng.randint(P.dead_branch_min, P.dead_branch_max)):
        t0 = rng.uniform(0.40, 0.62)
        p0 = spine_at(t0)
        az = rng.uniform(0, math.tau)
        elev = math.radians(rng.uniform(50, 72))   # 与竖直方向夹角
        d = Vector((math.sin(elev) * math.cos(az),
                    math.sin(elev) * math.sin(az), math.cos(elev)))
        L = P.dead_branch_len * rng.uniform(0.7, 1.25)
        p1 = p0 + d * (L * 0.55) + Vector((0, 0, -0.06 * L))
        p2 = p0 + d * L + Vector((0, 0, 0.10 * L))
        r0 = trunk_r(t0) * P.branch_radius_ratio
        branches.append(([p0, p1, p2], [r0, r0 * 0.55, 0.012], P.branch_sides))

    # 树冠 scaffold 分枝：主干 -> 各叶簇中心（大部分被叶卡片遮住，
    # 但参考图中树冠内部能看到分枝，需要保留）
    clusters = gen_clusters(rng, P, (spine[-1].x, spine[-1].y))
    for c, r in clusters:
        t0 = max(P.crown_start + 0.04,
                 min(0.96, (c.z - 0.35 * r) / H))
        p0 = spine_at(t0)
        mid = p0.lerp(c, 0.55) + Vector((rng.uniform(-0.1, 0.1),
                                         rng.uniform(-0.1, 0.1),
                                         rng.uniform(0.0, 0.15)))
        r0 = max(trunk_r(t0) * P.branch_radius_ratio, 0.02)
        branches.append(([p0, mid, c], [r0, r0 * 0.5, 0.015], P.branch_sides))
    return branches, clusters


def build_trunk_object(branches, P):
    verts, faces, face_uvs = [], [], []
    for pts, radii, sides in branches:
        add_tube(verts, faces, face_uvs, pts, radii, sides, 0.0, P.bark_uv_scale)
    ob = build_mesh_object("StylizedTree_Trunk", verts, faces, face_uvs)
    ob["gen_seed"] = P.seed
    ob["style"] = "IL3DN_stylized_beech"
    return ob


# --------------------------------------------------------------------------
# 叶卡片：簇内椭球采样 + 径向偏置随机朝向 + 图集 UV + 灰度顶点色双色调
# --------------------------------------------------------------------------
def build_leaf_object(rng, P, clusters):
    verts, faces, face_uvs, face_vcols = [], [], [], []
    weights = [r * r for _, r in clusters]
    total_w = sum(weights)
    z_min = min(c.z - r for c, r in clusters)
    z_max = max(c.z + r for c, r in clusters)
    z_span = max(z_max - z_min, 1e-3)

    for (center, radius), w in zip(clusters, weights):
        count = max(8, round(P.leaf_cards * w / total_w))
        for _ in range(count):
            # 椭球内均匀采样 + 可选表面偏置
            while True:
                p = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1),
                            rng.uniform(-1, 1)))
                if p.length_squared <= 1.0:
                    break
            if rng.random() < P.leaf_shell_bias and p.length > 1e-3:
                p = p.normalized() * rng.uniform(0.75, 1.0)
            pos = center + Vector((p.x * radius, p.y * radius,
                                   p.z * radius * P.crown_flatten))

            # 尺寸：基准 × ±30%，宽度按图集子区域宽高比（钳制）调整
            rect = rng.choice(LEAF_UV_RECTS)
            u0, v0, u1, v1 = rect
            aspect = (u1 - u0) / max(v1 - v0, 1e-3)
            aspect = max(0.7, min(aspect, 1.9))
            h = P.leaf_card_size * rng.uniform(0.7, 1.3)
            w_card = h * math.sqrt(aspect)

            # 朝向：法线朝簇径向 + 圆锥抖动 + 绕法线随机翻滚 + 随机翻面
            radial = pos - center
            n = radial.normalized() if radial.length_squared > 1e-6 \
                else Vector((0, 0, 1))
            q = n.to_track_quat('Z', 'Y')
            jr = Vector((rng.gauss(0, 1), rng.gauss(0, 1),
                         rng.gauss(0, 1))).normalized()
            q = Quaternion(n, rng.uniform(0, math.tau)) \
                @ Quaternion(jr, math.radians(
                    rng.uniform(0, P.leaf_normal_jitter_deg))) @ q
            if rng.random() < 0.5:
                q = q @ Quaternion(Vector((0, 1, 0)), math.pi)
            right = (q @ Vector((1, 0, 0))) * (w_card * 0.5)
            up = (q @ Vector((0, 1, 0))) * (h * 0.5)

            b = len(verts)
            verts += [pos - right - up, pos + right - up,
                      pos + right + up, pos - right + up]
            faces.append((b, b + 1, b + 2, b + 3))
            face_uvs.append(((u0, v0), (u1, v0), (u1, v1), (u0, v1)))

            # 顶点色：下暗上亮双色调因子；叠加深度的假 AO + 轻微抖动
            depth = 0.75 + 0.25 * (pos.z - z_min) / z_span
            jit = rng.uniform(0.92, 1.05)
            lo = min(P.leaf_gradient_dark * depth * jit, 1.0)
            hi = min(1.0 * depth * jit, 1.0)
            face_vcols.append((lo, lo, hi, hi))
            if P.leaf_double_sided:  # Unity 单面 shader 时复制翻面
                faces.append((b + 3, b + 2, b + 1, b))
                face_uvs.append(((u0, v1), (u1, v1), (u1, v0), (u0, v0)))
                face_vcols.append((hi, hi, lo, lo))

    return build_mesh_object("StylizedTree_Leaves", verts, faces,
                             face_uvs, face_vcols)


# --------------------------------------------------------------------------
# 材质：alpha 裁切（Math > cutoff），叶 = 贴图 × (顶点色->双色渐变)，
# 树皮 = 贴图 × 棕色。FBX 只携带贴图与 UV；Unity 端按同名语义重建材质。
# --------------------------------------------------------------------------
def make_leaf_material(img, P):
    m = bpy.data.materials.new("M_Leaf_Cutout")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:     # Blender 4.x
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    vcol = nt.nodes.new("ShaderNodeVertexColor")
    vcol.layer_name = "Color"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*LEAF_DARK, 1.0)
    ramp.color_ramp.elements[1].color = (*LEAF_LIGHT, 1.0)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = 1.0
    cut = nt.nodes.new("ShaderNodeMath")
    cut.operation = 'GREATER_THAN'
    cut.inputs[1].default_value = P.alpha_cutoff
    nt.links.new(vcol.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(tex.outputs["Color"], mix.inputs[1])
    nt.links.new(ramp.outputs["Color"], mix.inputs[2])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], cut.inputs[0])
    nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    # Blender 4.2 (EEVEE Next)：blend_method 已移除，改用 surface_render_method
    try:
        m.surface_render_method = 'DITHERED'
    except Exception:
        try:
            m.blend_method = 'CLIP'
            m.alpha_threshold = P.alpha_cutoff
        except Exception:
            pass
    return m


def make_bark_material(img):
    m = bpy.data.materials.new("M_Bark")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 1.0
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mix = m.node_tree.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = 1.0
    mix.inputs[2].default_value = (*BARK_TINT, 1.0)
    m.node_tree.links.new(tex.outputs["Color"], mix.inputs[1])
    m.node_tree.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    return m


# --------------------------------------------------------------------------
# 导出 FBX（Unity 约定：米制、-Z forward / Y up、内嵌贴图）
# 注意：FBX 导出器只识别【直连】到 Principled BSDF Base Color / Alpha 的
# 贴图节点，经过 MixRGB 调色就识别不到（贴图丢失）。因此导出时临时把
# 网格材质槽换成"导出版直连材质"，导出后恢复原材质。
# --------------------------------------------------------------------------
def _make_direct_material(name, img, with_alpha):
    """贴图直连 Principled 的简版材质，仅供 FBX 导出器拾取贴图。"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 1.0
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if with_alpha:
        nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def export_fbx(objects, filepath, bark_img, leaf_img):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    trunk, leaves = objects
    saved = {ob: ob.material_slots[0].material for ob in objects
             if ob.material_slots}
    trunk.material_slots[0].material = _make_direct_material(
        "FBXEXP_Bark", bark_img, with_alpha=False)
    leaves.material_slots[0].material = _make_direct_material(
        "FBXEXP_Leaf", leaf_img, with_alpha=True)
    try:
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_selection=True,
            object_types={'MESH'},
            apply_scale_options='FBX_SCALE_ALL',   # 场景单位(米)直接写入，Unity 1:1
            axis_forward='-Z', axis_up='Y',
            mesh_smooth_type='FACE',               # 平面着色
            path_mode='COPY',
            embed_textures=True,                   # 贴图内嵌进 FBX
            use_custom_props=True,
        )
    finally:
        for ob, mat in saved.items():            # 恢复带调色的渲染材质
            ob.material_slots[0].material = mat
    print("[tree_gen] exported:", filepath)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def build_tree(P):
    rng = random.Random(P.seed)
    clear_scene()
    bpy.context.scene.unit_settings.system = 'METRIC'

    branches, clusters = gen_skeleton(rng, P)
    trunk = build_trunk_object(branches, P)
    leaves = build_leaf_object(rng, P, clusters)

    bark_img = load_image(BARK_TEX)
    leaf_img = load_image(LEAF_TEX)
    trunk.data.materials.append(make_bark_material(bark_img))
    leaves.data.materials.append(make_leaf_material(leaf_img, P))

    if P.export_fbx:
        name = P.export_name or "stylized_tree_seed%d.fbx" % P.seed
        export_fbx([trunk, leaves], os.path.join(P.export_dir, name),
                   bark_img, leaf_img)
    return trunk, leaves


def _parse_cli(argv):
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--count", type=int, default=1, help="批量生成棵数(seed 递增)")
    ap.add_argument("--outdir", type=str, default=OUTPUT_DIR)
    ap.add_argument("--no-export", action="store_true")
    return ap.parse_args(args)


def main(argv=None):
    cli = _parse_cli(argv if argv is not None else sys.argv)
    for i in range(cli.count):
        P = TreeParams(seed=cli.seed + i, export_fbx=not cli.no_export,
                       export_dir=cli.outdir)
        build_tree(P)
        print("[tree_gen] done seed=%d (%d/%d)" % (P.seed, i + 1, cli.count))


if __name__ == "__main__":
    main()
