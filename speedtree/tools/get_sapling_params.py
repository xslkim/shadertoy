"""获取 Sapling operator 的参数（通过 get_rna_type）。"""
import bpy

# 方法1: 通过 operator 的 get_rna_type
try:
    rna = bpy.ops.curve.sapling_3d.get_rna_type()
    print(f"RNA_TYPE: {rna}")
    print(f"IDENTIFIER: {rna.identifier}")
    props_count = 0
    for prop_name, prop in rna.properties.items():
        if prop_name in ('rna_type', 'bl_idname', 'bl_label', 'bl_description', 'bl_options', 'bl_region', 'bl_context'):
            continue
        try:
            default = prop.default
        except:
            default = "?"
        ptype = prop.type
        # 对 enum 类型，获取 items
        items_info = ""
        if ptype == 'ENUM':
            try:
                items = [item.identifier for item in prop.enum_items]
                items_info = f" | enum={items}"
            except:
                pass
        # 对 float_array 等，获取长度
        if hasattr(prop, 'array_length') and prop.array_length > 0:
            items_info += f" | array_len={prop.array_length}"
        print(f"PROP: {prop_name} | type={ptype} | default={default}{items_info}")
        props_count += 1
    print(f"TOTAL_PROPS: {props_count}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")

# 方法2: 列出所有 curve.* operator
print("---CURVE_OPERATORS---")
for op_name in dir(bpy.ops.curve):
    if 'sapling' in op_name.lower() or 'tree' in op_name.lower():
        print(f"OP: curve.{op_name}")
