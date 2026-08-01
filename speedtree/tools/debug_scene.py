"""调试：检查 Blender 所有数据。"""
import bpy

print(f"=== SCENE ===")
print(f"Scene name: {bpy.context.scene.name}")
print(f"Scene objects: {len(bpy.context.scene.objects)}")
for o in bpy.context.scene.objects:
    print(f"  {o.name} ({o.type})")

print(f"=== ALL OBJECTS (bpy.data) ===")
print(f"Count: {len(bpy.data.objects)}")
for o in bpy.data.objects:
    print(f"  {o.name} ({o.type}) loc={list(o.location)}")

print(f"=== MESHES ===")
print(f"Count: {len(bpy.data.meshes)}")
for m in bpy.data.meshes:
    print(f"  {m.name}: verts={len(m.vertices)} polys={len(m.polygons)}")

print(f"=== MATERIALS ===")
print(f"Count: {len(bpy.data.materials)}")
for mat in bpy.data.materials:
    print(f"  {mat.name}")

print(f"=== COLLECTIONS ===")
print(f"Count: {len(bpy.data.collections)}")
for c in bpy.data.collections:
    print(f"  {c.name}: {len(c.objects)} objects")
    for o in c.objects:
        print(f"    - {o.name}")

print(f"=== BLEND FILE PATH ===")
print(f"Current: {bpy.data.filepath}")

print(f"=== ACTIVE OBJECT ===")
print(f"Active: {bpy.context.active_object}")
print(f"Selected: {bpy.context.selected_objects}")
