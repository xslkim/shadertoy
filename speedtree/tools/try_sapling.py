"""尝试调用 Sapling 生成默认树。"""
import bpy
import traceback

# 清空场景
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
print("场景已清空")

# 尝试调用 Sapling
try:
    print("尝试调用 bpy.ops.curve.sapling_3d()...")
    # 先用默认参数
    bpy.ops.curve.sapling_3d()
    print("✓ Sapling 调用成功")
    # 列出生成的对象
    for obj in bpy.data.objects:
        print(f"  生成对象: {obj.name} ({obj.type})")
except Exception as e:
    print(f"✗ 调用失败: {e}")
    traceback.print_exc()
    # 如果失败，尝试列出 operator 的实际参数
    print("---尝试获取 operator 信息---")
    try:
        op = bpy.ops.curve.sapling_3d
        print(f"  op exists: {op is not None}")
        print(f"  op idname: {op.idname()}")
        # 尝试 poll
        print(f"  op poll: {op.poll()}")
    except Exception as e2:
        print(f"  获取信息也失败: {e2}")
