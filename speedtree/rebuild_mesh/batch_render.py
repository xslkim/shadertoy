# -*- coding: utf-8 -*-
"""
batch_render.py — 批量生成 4 棵同风格不同形态的风格化树并渲染验收图
=====================================================================
复用 blender_tree_gen.py 的生成器（风格参数全部继承，仅形态参数变化），
每棵树：导出 FBX -> 单棵渲染（仿参考图米色背景正交正视图）-> 暂存；
最后把 4 棵排一行渲染群体对比图。

运行：
  "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" ^
      --background --factory-startup --python batch_render.py
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blender_tree_gen as tg  # noqa: E402

OUT_DIR = os.path.join(HERE, "output")
RENDER_DIR = os.path.join(HERE, "renders")

# 4 棵变体：只动形态参数（高矮胖瘦/团数/倾斜/枯枝数），
# 贴图/配色/叶卡尺寸等风格参数一律保持默认 -> 风格统一
VARIANTS = [
    dict(seed=7,  height=6.2, crown_radius=1.9, crown_blob_count=4,
         crown_start=0.48, trunk_lean=0.22, dead_branch_max=3),
    dict(seed=12, height=7.1, crown_radius=1.7, crown_blob_count=5,
         crown_start=0.52, trunk_lean=0.15, dead_branch_max=2),
    dict(seed=23, height=5.4, crown_radius=2.2, crown_blob_count=3,
         crown_start=0.45, trunk_lean=0.30, dead_branch_max=3),
    dict(seed=31, height=6.6, crown_radius=1.8, crown_blob_count=4,
         crown_start=0.50, trunk_lean=0.25, dead_branch_max=4),
]


def _srgb(hex_str):
    h = hex_str.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
                 for c in srgb)


def make_rig():
    """创建世界(米色背景) + 太阳灯 + 正交相机；返回相机对象。"""
    scene = bpy.context.scene
    try:
        scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except Exception:
        scene.render.engine = 'BLENDER_EEVEE'
    try:
        scene.eevee.taa_render_samples = 32
    except Exception:
        pass
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False

    world = bpy.data.worlds.get("W_Beige") or bpy.data.worlds.new("W_Beige")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*_srgb("#CDC09F"), 1.0)  # 取样自参考截图背景
    bg.inputs[1].default_value = 0.8
    scene.world = world

    sun_data = bpy.data.lights.new("SunKey", type='SUN')
    sun_data.energy = 3.0
    sun_data.angle = math.radians(30)          # 柔和阴影
    sun = bpy.data.objects.new("SunKey", sun_data)
    sun.rotation_euler = (math.radians(50), math.radians(-15),
                          math.radians(-35))
    bpy.context.collection.objects.link(sun)

    cam_data = bpy.data.cameras.new("CamOrtho")
    cam_data.type = 'ORTHO'
    cam_data.clip_end = 200.0
    cam = bpy.data.objects.new("CamOrtho", cam_data)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)  # 朝 +Y 正视
    bpy.context.collection.objects.link(cam)
    scene.camera = cam
    return cam


def frame_objects(cam, objects, res_x, res_y, margin=0.35):
    """按对象包围盒精确取景；ortho_scale 适配较长的一边。"""
    xs, zs = [], []
    for ob in objects:
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            xs.append(w.x)
            zs.append(w.z)
    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)
    span_x = (max_x - min_x) + margin * 2
    span_z = (max_z - min_z) + margin * 2
    if res_y >= res_x:      # 竖构图：ortho_scale = 纵向范围
        scale = max(span_z, span_x * res_y / res_x)
    else:                   # 横构图：ortho_scale = 横向范围
        scale = max(span_x, span_z * res_x / res_y)
    cam.data.ortho_scale = scale
    cam.location = ((min_x + max_x) * 0.5, -30.0, (min_z + max_z) * 0.5)


def render_to(cam, objects, path, res_x, res_y):
    scene = bpy.context.scene
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    frame_objects(cam, objects, res_x, res_y)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[batch] rendered:", path)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RENDER_DIR, exist_ok=True)

    stashed = []   # [(objects, x_offset, params)]
    x_cursor = 0.0
    margin_between = 0.6

    for spec in VARIANTS:
        P = tg.TreeParams(export_fbx=True, export_dir=OUT_DIR, **spec)
        trunk, leaves = tg.build_tree(P)      # 内部会 clear_scene + 导出 FBX

        cam = make_rig()
        render_to(cam, [trunk, leaves],
                  os.path.join(RENDER_DIR, "tree_seed%02d.png" % P.seed),
                  600, 800)

        # 暂存：从场景摘除（clear_scene 删不到未链接对象），留给群体图
        half_w = 0.0
        for ob in (trunk, leaves):
            for v in ob.data.vertices:
                half_w = max(half_w, abs(v.co.x))
            for col in list(ob.users_collection):
                col.objects.unlink(ob)
        x_cursor += half_w
        stashed.append(([trunk, leaves], x_cursor, P))
        x_cursor += half_w + margin_between

    # ---- 群体对比图 ----
    total = x_cursor - margin_between
    center = total * 0.5
    all_obs = []
    for objects, x, _P in stashed:
        for ob in objects:
            ob.location.x = x - center
            bpy.context.collection.objects.link(ob)
            all_obs.append(ob)
    bpy.context.view_layer.update()   # 刷新 matrix_world 后再取景
    cam = make_rig()
    render_to(cam, all_obs, os.path.join(RENDER_DIR, "group.png"), 1600, 900)
    print("[batch] all done.")


if __name__ == "__main__":
    main()
