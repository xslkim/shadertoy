"""
深挖参考树 FBX 的建模规律：
  - 每个 LOD 的树干拓扑（是否为规则的圆柱环）
  - 叶片卡片的形状 / 尺寸 / 朝向 / UV 分布
  - 顶点色的语义（是否为风动画数据）
  - Model 节点的变换与真实尺寸

用法: python analyze_tree_fbx.py <file.fbx>
"""
import sys
import math
from collections import Counter, defaultdict

from inspect_fbx import parse


def get_name(node):
    if len(node.props) > 1 and isinstance(node.props[1], str):
        return node.props[1].split("\x00")[0]
    return "?"


def unpack_geometry(geo):
    verts = list(geo.first("Vertices").props[0])
    idx = list(geo.first("PolygonVertexIndex").props[0])
    P = [(verts[i * 3], verts[i * 3 + 1], verts[i * 3 + 2]) for i in range(len(verts) // 3)]

    polys = []
    cur = []
    for i in idx:
        if i < 0:
            cur.append(-i - 1)
            polys.append(cur)
            cur = []
        else:
            cur.append(i)

    mat_node = geo.first("LayerElementMaterial")
    mats = list(mat_node.first("Materials").props[0]) if mat_node else [0] * len(polys)
    if len(mats) == 1:
        mats = mats * len(polys)

    uv_node = geo.first("LayerElementUV")
    uvs, uv_idx = None, None
    if uv_node:
        uvs = list(uv_node.first("UV").props[0])
        ui = uv_node.first("UVIndex")
        uv_idx = list(ui.props[0]) if ui else None

    col_node = geo.first("LayerElementColor")
    cols, col_idx = None, None
    if col_node:
        c = col_node.first("Colors")
        cols = list(c.props[0]) if c else None
        ci = col_node.first("ColorIndex")
        col_idx = list(ci.props[0]) if ci else None

    return P, polys, mats, uvs, uv_idx, cols, col_idx


def poly_normal(P, poly):
    if len(poly) < 3:
        return (0, 0, 0)
    a, b, c = P[poly[0]], P[poly[1]], P[poly[2]]
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    L = math.sqrt(sum(x * x for x in n)) or 1.0
    return (n[0] / L, n[1] / L, n[2] / L)


def poly_area(P, poly):
    total = 0.0
    for i in range(1, len(poly) - 1):
        a, b, c = P[poly[0]], P[poly[i]], P[poly[i + 1]]
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        total += 0.5 * math.sqrt(sum(x * x for x in n))
    return total


def analyze(path):
    root, version = parse(path)
    objects = root.first("Objects")

    print("=" * 74)
    print("参考树建模规律分析")
    print("=" * 74)

    # Model 变换
    print("\n### Model 节点变换")
    for m in objects.find("Model"):
        p70 = m.first("Properties70")
        info = {}
        if p70:
            for prop in p70.children:
                if prop.props and prop.props[0] in ("Lcl Translation", "Lcl Rotation", "Lcl Scaling", "GeometricTranslation"):
                    info[prop.props[0]] = [round(x, 3) for x in prop.props[4:]]
        print(f"  {get_name(m):36s} {info}")

    geos = objects.find("Geometry")
    models = [get_name(m) for m in objects.find("Model") if len(m.props) > 2 and m.props[2] == "Mesh"]

    for gi, geo in enumerate(geos):
        label = models[gi] if gi < len(models) else f"Geometry[{gi}]"
        P, polys, mats, uvs, uv_idx, cols, col_idx = unpack_geometry(geo)
        print("\n" + "-" * 74)
        print(f"### {label}")
        print(f"  顶点 {len(P)}  面 {len(polys)}  三角面 {sum(len(p) - 2 for p in polys)}")

        bark = [p for p, m in zip(polys, mats) if m == 0]
        leaf = [p for p, m in zip(polys, mats) if m == 1]
        print(f"  树干面 {len(bark)}   叶片面 {len(leaf)}")

        # --- 尺寸（真实单位）---
        xs = [p[0] for p in P]
        ys = [p[1] for p in P]
        zs = [p[2] for p in P]
        scale_cm = 2.54  # UnitScaleFactor
        print(
            f"  尺寸(原始单位): X {max(xs)-min(xs):.1f}  Y {max(ys)-min(ys):.1f}  Z {max(zs)-min(zs):.1f}"
        )
        print(
            f"  尺寸(米, ×2.54cm): X {(max(xs)-min(xs))*scale_cm/100:.2f}m  "
            f"Y {(max(ys)-min(ys))*scale_cm/100:.2f}m  Z {(max(zs)-min(zs))*scale_cm/100:.2f}m"
        )

        # --- 树干拓扑：按 Z 分层统计顶点 ---
        if gi == 0:
            bark_verts = sorted({v for p in bark for v in p})
            leaf_verts = sorted({v for p in leaf for v in p})
            print(f"  树干独立顶点 {len(bark_verts)}  叶片独立顶点 {len(leaf_verts)}")

            # 树干顶点按高度聚类，看是否为环状结构
            zvals = sorted(P[v][2] for v in bark_verts)
            rings = []
            cur = [zvals[0]]
            for z in zvals[1:]:
                if z - cur[-1] < 0.5:
                    cur.append(z)
                else:
                    rings.append(cur)
                    cur = [z]
            rings.append(cur)
            ring_sizes = Counter(len(r) for r in rings)
            print(f"  树干按高度聚类得到 {len(rings)} 个环, 每环顶点数分布: {dict(ring_sizes)}")

            # 叶片卡片：连通分量
            adj = defaultdict(set)
            for p in leaf:
                for i in range(len(p)):
                    adj[p[i]].add(p[(i + 1) % len(p)])
                    adj[p[(i + 1) % len(p)]].add(p[i])
            seen = set()
            comps = []
            for v in leaf_verts:
                if v in seen:
                    continue
                stack, comp = [v], []
                seen.add(v)
                while stack:
                    x = stack.pop()
                    comp.append(x)
                    for y in adj[x]:
                        if y not in seen:
                            seen.add(y)
                            stack.append(y)
                comps.append(comp)
            print(f"  叶片连通分量(独立卡片簇) {len(comps)} 个, 顶点数分布: {dict(Counter(len(c) for c in comps))}")

        # --- 叶片卡片几何 ---
        if leaf:
            areas = [poly_area(P, p) for p in leaf]
            areas.sort()
            norms = [poly_normal(P, p) for p in leaf]
            # 与世界 Z 轴的夹角
            angles = [math.degrees(math.acos(max(-1, min(1, abs(n[2]))))) for n in norms]
            planar = 0
            for p in leaf:
                if len(p) == 4:
                    n = poly_normal(P, p)
                    a = P[p[0]]
                    d = P[p[3]]
                    dev = abs((d[0] - a[0]) * n[0] + (d[1] - a[1]) * n[1] + (d[2] - a[2]) * n[2])
                    if dev < 1e-3:
                        planar += 1
            print(
                f"  叶片面积: 中位 {areas[len(areas)//2]:.2f}  最小 {areas[0]:.2f}  最大 {areas[-1]:.2f}"
            )
            print(f"  叶片共面(平整卡片)比例: {planar}/{len(leaf)}")
            print(
                f"  叶片法线与水平面夹角: 中位 {sorted(angles)[len(angles)//2]:.0f}°  "
                f"范围 {min(angles):.0f}°~{max(angles):.0f}°"
            )

        # --- UV 分布 ---
        if uvs:
            # 按材质分开统计 UV 范围
            pv = 0
            uv_by_mat = defaultdict(list)
            for p, m in zip(polys, mats):
                for _ in p:
                    ui = uv_idx[pv] if uv_idx else pv
                    uv_by_mat[m].append((uvs[ui * 2], uvs[ui * 2 + 1]))
                    pv += 1
            for m, lst in sorted(uv_by_mat.items()):
                us = [a for a, b in lst]
                vs = [b for a, b in lst]
                mname = "Bark" if m == 0 else "Leaves"
                print(
                    f"  UV[{mname}]: U [{min(us):.3f},{max(us):.3f}]  V [{min(vs):.3f},{max(vs):.3f}]  "
                    f"唯一UV点 {len(set(lst))}"
                )
                if m == 1:
                    # 叶子 UV 是否落在图集的少数几块
                    quant = Counter((round(a, 2), round(b, 2)) for a, b in lst)
                    print(f"      叶片 UV 角点(top6): {quant.most_common(6)}")

        # --- 顶点色 ---
        if cols:
            pv = 0
            samples = []
            by_mat = defaultdict(list)
            for p, m in zip(polys, mats):
                for vi in p:
                    ci = col_idx[pv] if col_idx else pv
                    c = (cols[ci * 4], cols[ci * 4 + 1], cols[ci * 4 + 2], cols[ci * 4 + 3])
                    by_mat[m].append((c, P[vi]))
                    pv += 1
            for m, lst in sorted(by_mat.items()):
                mname = "Bark" if m == 0 else "Leaves"
                rs = [c[0] for c, _ in lst]
                gs = [c[1] for c, _ in lst]
                bs = [c[2] for c, _ in lst]
                as_ = [c[3] for c, _ in lst]
                print(
                    f"  顶点色[{mname}]: R[{min(rs):.2f},{max(rs):.2f}] G[{min(gs):.2f},{max(gs):.2f}] "
                    f"B[{min(bs):.2f},{max(bs):.2f}] A[{min(as_):.2f},{max(as_):.2f}]"
                )
                # 检查是否与高度相关（风动画的典型特征）
                for ch, name in ((0, "R"), (1, "G"), (2, "B"), (3, "A")):
                    vals = [c[ch] for c, _ in lst]
                    hs = [pos[2] for _, pos in lst]
                    if max(vals) - min(vals) < 1e-3:
                        print(f"      {name} 通道恒定 = {vals[0]:.3f}")
                        continue
                    n = len(vals)
                    mv, mh = sum(vals) / n, sum(hs) / n
                    num = sum((v - mv) * (h - mh) for v, h in zip(vals, hs))
                    den = math.sqrt(
                        sum((v - mv) ** 2 for v in vals) * sum((h - mh) ** 2 for h in hs)
                    ) or 1.0
                    print(f"      {name} 通道 与高度(Z)相关系数 = {num/den:+.3f}")


if __name__ == "__main__":
    analyze(sys.argv[1] if len(sys.argv) > 1 else "mesh/IL3DN_Tree_Pine_01_OneMesh.FBX")
