"""多视角渲染松树预览。"""
import bpy
import math
import os

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

# 确保有阳光
sun = None
for o in bpy.data.objects:
    if o.type == 'LIGHT' and o.data.type == 'SUN':
        sun = o
        break
if sun is None:
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    sun = bpy.context.object
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(45), math.radians(20), math.radians(30))

# 世界背景
world = scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.55, 0.65, 0.75, 1.0)
    bg.inputs[1].default_value = 0.8

# 找到相机（或创建）
cam = bpy.context.scene.camera
if cam is None:
    bpy.ops.object.camera_add(location=(10, -10, 5))
    cam = bpy.context.object
    scene.camera = cam
cam.data.lens = 38

# 多视角渲染
views = [
    ("front", (10, -10, 5.5), (math.radians(82), 0, math.radians(45))),
    ("side", (10, 0, 5.5), (math.radians(90), 0, math.radians(90))),
    ("angle", (8, -8, 4), (math.radians(78), 0, math.radians(45))),
    ("top", (3, -3, 16), (math.radians(10), 0, math.radians(45))),
]

out_dir = "d:/shadertoy/speedtree/exports"
os.makedirs(out_dir, exist_ok=True)

for name, loc, rot in views:
    cam.location = loc
    cam.rotation_euler = rot
    filepath = f"{out_dir}/pine_{name}.png"
    scene.render.filepath = filepath
    print(f"渲染 {name}...")
    bpy.ops.render.render(write_still=True)
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"  ✓ {filepath} ({size} bytes)")
    else:
        print(f"  ✗ 渲染失败: {filepath}")

print("全部渲染完成")
