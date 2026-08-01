"""
用第三方 FBX 加载器 ufbx 独立校验生成的 FBX。
ufbx 与本项目的解析器/写出器完全无关，能证明产物是真正合法的 FBX。

已知的绑定库缺陷（参考资产同样触发，与被检文件无关）：
  * node.parent、mesh.instances[i] 返回悬空 Node，访问其属性会段错误
  * 同一进程内连续 load 多个文件会段错误
因此本脚本每次只处理一个文件，且只走从 root_node 向下遍历的安全路径。

用法: python tools/validate_with_ufbx.py <file.fbx>
"""
import sys

import ufbx


def collect(node, out, depth=0):
    if not node.is_root:
        out.append((depth, node.name, node.mesh))
    for i in range(len(node.children)):
        collect(node.children[i], out, depth + (0 if node.is_root else 1))


def dump_mesh(name, m):
    faces = len(m.faces)
    quads = sum(1 for fi in range(faces) if m.faces[fi].num_indices == 4)
    print(f"\n  [{name}]")
    print(f"    顶点 {len(m.vertices)}  面 {faces}（四边形 {quads}）  三角面 {m.num_triangles}")
    print(f"    UV 层 {len(m.uv_sets)}  顶点色层 {len(m.color_sets)}  "
          f"法线 {'有' if m.vertex_normal.exists else '无'}  材质槽 {len(m.materials)}")

    slots = [m.material_parts[i].num_faces for i in range(len(m.material_parts))]
    print(f"    各材质槽面数: {slots}")

    if len(m.uv_sets):
        uv = m.uv_sets[0].vertex_uv
        us = [uv.values[i].x for i in range(len(uv.values))]
        vs = [uv.values[i].y for i in range(len(uv.values))]
        print(f"    UV 范围 U[{min(us):.3f},{max(us):.3f}] V[{min(vs):.3f},{max(vs):.3f}]")

    if not len(m.color_sets):
        return
    vc = m.color_sets[0].vertex_color
    vp = m.vertex_position
    print(f"    顶点色 value_reals={vc.value_reals}（4 = RGBA，Alpha 保留）")

    ys, chans = [], {c: [] for c in "RGBA"}
    for fi in range(faces):
        f = m.faces[fi]
        for k in range(f.num_indices):
            idx = f.index_begin + k
            ys.append(vp.values[vp.indices[idx]].y)
            c = vc.values[vc.indices[idx]]
            chans["R"].append(c.x)
            chans["G"].append(c.y)
            chans["B"].append(c.z)
            chans["A"].append(c.w)
    for nm in "RGBA":
        v = chans[nm]
        print(f"      {nm}: [{min(v):.3f}, {max(v):.3f}]")

    a = chans["A"]
    n_ = len(ys)
    my, ma = sum(ys) / n_, sum(a) / n_
    num = sum((x - my) * (y - ma) for x, y in zip(ys, a))
    den = (sum((x - my) ** 2 for x in ys) * sum((y - ma) ** 2 for y in a)) ** 0.5
    print(f"      Alpha 与高度 Y 的相关系数 = {num / den:+.4f}（1.0 = 完美的风弯曲权重梯度）")


def main(path):
    print("=" * 72)
    print("ufbx 独立校验:", path)
    scene = ufbx.load_file(path)

    md = scene.metadata
    print(f"  FBX 版本 {md.version}  ASCII={md.ascii}")
    print(f"  Creator: {md.creator}")
    print(f"  >>> 解析警告数: {len(md.warnings)}")
    for i in range(min(len(md.warnings), 8)):
        print("      !", md.warnings[i].description)

    s = scene.settings
    print(f"  单位: 1 单位 = {s.unit_meters} 米")
    print(f"  坐标轴: up={s.axes.up.name} front={s.axes.front.name} right={s.axes.right.name}")
    print(f"  节点 {len(scene.nodes)}  网格 {len(scene.meshes)}  材质 {len(scene.materials)}")

    nodes = []
    collect(scene.root_node, nodes)
    print("  层级:")
    for depth, name, mesh in nodes:
        print("    " + "  " * depth + f"- {name}  [{'MESH' if mesh is not None else 'NULL'}]")

    for _, name, mesh in nodes:
        if mesh is not None:
            dump_mesh(name, mesh)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "exports/ProcPine_03.fbx")
