"""检查 Blender 环境：场景对象、可用 addons、Sapling 是否可用。"""
import bpy

# 1. 场景对象
scene_objects = [{"name": o.name, "type": o.type, "location": list(o.location)} for o in bpy.data.objects]
print(f"OBJECTS: {scene_objects}")

# 2. 检查启用的 addons
enabled_addons = [a.module for a in bpy.context.preferences.addons]
print(f"ENABLED_ADDONS: {enabled_addons}")

# 3. 检查 Sapling
has_sapling = hasattr(bpy.ops.curve, "sapling_3d")
print(f"SAPLING_AVAILABLE: {has_sapling}")

# 4. 检查可用 addons（在文件系统里）
import os
addon_paths = [
    os.path.join(bpy.utils.resource_path('USER'), 'scripts', 'addons'),
    os.path.join(bpy.utils.resource_path('LOCAL'), 'scripts', 'addons'),
]
found_addons = []
for p in addon_paths:
    if os.path.exists(p):
        for item in os.listdir(p):
            full = os.path.join(p, item)
            if os.path.isdir(full) and not item.startswith('.'):
                found_addons.append(item)
print(f"INSTALLED_ADDONS: {found_addons}")

# 5. Blender 版本
print(f"BLENDER_VERSION: {bpy.app.version_string}")

# 6. 检查 Geometry Nodes 可用性
has_geo_nodes = hasattr(bpy.ops.node, "add_node")
print(f"GEO_NODES_AVAILABLE: {has_geo_nodes}")
