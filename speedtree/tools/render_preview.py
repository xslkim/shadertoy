"""调整视口视角并渲染预览图。"""
import bpy
import math

# 确保相机存在且是活动相机
cam = bpy.context.scene.camera
if cam is None:
    # 找场景里的相机
    for o in bpy.data.objects:
        if o.type == 'CAMERA':
            cam = o
            bpy.context.scene.camera = cam
            break

if cam:
    # 调整相机位置和角度，让它能完整拍到松树
    # 松树高 10m，底部在原点，所以相机应该在 (12, -12, 6) 左右看向 (0,0,5)
    cam.location = (13, -13, 6)
    cam.rotation_euler = (math.radians(75), 0, math.radians(45))
    cam.data.lens = 45
    print(f"相机: {cam.name}, loc={list(cam.location)}, lens={cam.data.lens}")
else:
    print("没有相机！")

# 设置渲染
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = "d:/shadertoy/speedtree/exports/pine_lod0_render.png"

# 渲染
print("开始渲染...")
bpy.ops.render.render(write_still=True)
print(f"渲染完成: {scene.render.filepath}")

# 同时把视口切到相机视角并截图
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for region in area.regions:
            if region.type == 'WINDOW':
                # 切换到相机视角
                override = bpy.context.copy()
                override['area'] = area
                override['region'] = region
                with bpy.context.temp_override(**override):
                    bpy.ops.view3d.view_camera()
                break
        break

print("视口已切换到相机视角")
