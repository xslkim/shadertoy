"""
最小 FBX 二进制解析器 —— 只为了摸清参考模型的结构，不依赖 Blender / FBX SDK。

用法: python inspect_fbx.py <file.fbx>
"""
import sys
import struct
import zlib
from collections import Counter, defaultdict


class Node:
    def __init__(self, name):
        self.name = name
        self.props = []
        self.children = []

    def find(self, name):
        return [c for c in self.children if c.name == name]

    def first(self, name):
        r = self.find(name)
        return r[0] if r else None


def read_array(f, dtype, itemsize):
    length, encoding, comp_len = struct.unpack("<III", f.read(12))
    raw = f.read(comp_len)
    if encoding == 1:
        raw = zlib.decompress(raw)
    return struct.unpack("<%d%s" % (length, dtype), raw[: length * itemsize])


def read_prop(f):
    t = f.read(1).decode("ascii")
    if t == "Y":
        return struct.unpack("<h", f.read(2))[0]
    if t == "C":
        return struct.unpack("<?", f.read(1))[0]
    if t == "I":
        return struct.unpack("<i", f.read(4))[0]
    if t == "F":
        return struct.unpack("<f", f.read(4))[0]
    if t == "D":
        return struct.unpack("<d", f.read(8))[0]
    if t == "L":
        return struct.unpack("<q", f.read(8))[0]
    if t == "f":
        return read_array(f, "f", 4)
    if t == "d":
        return read_array(f, "d", 8)
    if t == "l":
        return read_array(f, "q", 8)
    if t == "i":
        return read_array(f, "i", 4)
    if t == "b":
        return read_array(f, "b", 1)
    if t == "S":
        n = struct.unpack("<I", f.read(4))[0]
        return f.read(n).decode("utf-8", "replace")
    if t == "R":
        n = struct.unpack("<I", f.read(4))[0]
        return f.read(n)
    raise ValueError("unknown prop type %r at %d" % (t, f.tell()))


def read_node(f, version):
    if version >= 7500:
        end_off, num_props, prop_len = struct.unpack("<QQQ", f.read(24))
        name_len = struct.unpack("<B", f.read(1))[0]
        null_len = 25
    else:
        end_off, num_props, prop_len = struct.unpack("<III", f.read(12))
        name_len = struct.unpack("<B", f.read(1))[0]
        null_len = 13

    if end_off == 0:
        return None

    name = f.read(name_len).decode("utf-8", "replace")
    node = Node(name)
    for _ in range(num_props):
        node.props.append(read_prop(f))

    while f.tell() < end_off - null_len:
        child = read_node(f, version)
        if child is None:
            break
        node.children.append(child)
    f.seek(end_off)
    return node


def parse(path):
    with open(path, "rb") as f:
        header = f.read(23)
        if not header.startswith(b"Kaydara FBX Binary"):
            raise SystemExit("不是二进制 FBX（可能是 ASCII 版本）")
        version = struct.unpack("<I", f.read(4))[0]
        root = Node("__root__")
        while True:
            n = read_node(f, version)
            if n is None:
                break
            root.children.append(n)
            if f.tell() >= len(open(path, "rb").read()) - 100:
                break
    return root, version


def summarize(path):
    root, version = parse(path)
    print("=" * 70)
    print("FBX 文件:", path)
    print("FBX 版本:", version)

    # --- 创建者信息 ---
    for section in ("FBXHeaderExtension", "Creator"):
        n = root.first(section)
        if n:
            if section == "Creator":
                print("Creator:", n.props)
            else:
                cr = n.first("Creator")
                if cr:
                    print("Creator:", cr.props)
                app = n.first("SceneInfo")
                if app:
                    for p in app.children:
                        if p.name == "Properties70":
                            for prop in p.children:
                                if prop.props and prop.props[0] in (
                                    "Original|ApplicationName",
                                    "LastSaved|ApplicationName",
                                    "Original|ApplicationVendor",
                                    "Original|FileName",
                                ):
                                    print("  ", prop.props[0], "=", prop.props[-1])

    # --- 单位 ---
    gs = root.first("GlobalSettings")
    if gs:
        p70 = gs.first("Properties70")
        if p70:
            for prop in p70.children:
                if prop.props and prop.props[0] in ("UnitScaleFactor", "UpAxis", "FrontAxis"):
                    print("GlobalSetting:", prop.props[0], "=", prop.props[-1])

    objects = root.first("Objects")
    if objects is None:
        print("没有 Objects 节点")
        return

    kinds = Counter(c.name for c in objects.children)
    print("\n--- Objects 统计 ---")
    for k, v in kinds.most_common():
        print(f"  {k}: {v}")

    # --- 几何体 ---
    print("\n--- Geometry 详情 ---")
    total_tris = 0
    for geo in objects.find("Geometry"):
        gname = geo.props[1].split("\x00")[0] if len(geo.props) > 1 else "?"
        verts = geo.first("Vertices")
        idx = geo.first("PolygonVertexIndex")
        nv = len(verts.props[0]) // 3 if verts else 0
        polys = 0
        tri = 0
        quad = 0
        ngon = 0
        if idx:
            arr = idx.props[0]
            count = 0
            for i in arr:
                count += 1
                if i < 0:
                    polys += 1
                    if count == 3:
                        tri += 1
                    elif count == 4:
                        quad += 1
                    else:
                        ngon += 1
                    total_tris += count - 2
                    count = 0
        print(f"  [{gname}] 顶点={nv}  面={polys} (tri={tri} quad={quad} ngon={ngon})")

        uvs = geo.find("LayerElementUV")
        for u in uvs:
            uname = u.first("Name")
            uvarr = u.first("UV")
            mapping = u.first("MappingInformationType")
            print(
                f"      UV层 '{uname.props[0] if uname else '?'}': "
                f"{len(uvarr.props[0]) // 2 if uvarr else 0} 个UV, "
                f"mapping={mapping.props[0] if mapping else '?'}"
            )
        mat = geo.first("LayerElementMaterial")
        if mat:
            mi = mat.first("Materials")
            mm = mat.first("MappingInformationType")
            if mi:
                c = Counter(mi.props[0])
                print(f"      材质分配: mapping={mm.props[0] if mm else '?'} 槽位分布={dict(c)}")
        nrm = geo.first("LayerElementNormal")
        if nrm:
            mm = nrm.first("MappingInformationType")
            print(f"      法线: mapping={mm.props[0] if mm else '?'}")
        col = geo.first("LayerElementColor")
        if col:
            mm = col.first("MappingInformationType")
            print(f"      顶点色: 存在, mapping={mm.props[0] if mm else '?'}")

        # 包围盒
        if verts:
            v = verts.props[0]
            xs = v[0::3]
            ys = v[1::3]
            zs = v[2::3]
            print(
                f"      包围盒: X[{min(xs):.2f},{max(xs):.2f}] "
                f"Y[{min(ys):.2f},{max(ys):.2f}] Z[{min(zs):.2f},{max(zs):.2f}]"
            )
    print(f"  合计三角面: {total_tris}")

    # --- 模型层级 ---
    print("\n--- Model 列表 ---")
    for m in objects.find("Model"):
        mname = m.props[1].split("\x00")[0] if len(m.props) > 1 else "?"
        mtype = m.props[2] if len(m.props) > 2 else "?"
        print(f"  {mname}  ({mtype})")

    # --- 材质 ---
    print("\n--- Material 列表 ---")
    for mt in objects.find("Material"):
        mname = mt.props[1].split("\x00")[0] if len(mt.props) > 1 else "?"
        shading = mt.first("ShadingModel")
        print(f"  {mname}  shading={shading.props[0] if shading else '?'}")
        p70 = mt.first("Properties70")
        if p70:
            for prop in p70.children:
                if prop.props and prop.props[0] in (
                    "DiffuseColor",
                    "SpecularColor",
                    "TransparencyFactor",
                    "Opacity",
                    "EmissiveColor",
                ):
                    print("      ", prop.props[0], "=", prop.props[4:])

    # --- 贴图 ---
    print("\n--- Texture / Video 列表 ---")
    for tx in objects.find("Texture"):
        tname = tx.props[1].split("\x00")[0] if len(tx.props) > 1 else "?"
        rel = tx.first("RelativeFilename")
        print(f"  Texture {tname}: {rel.props[0] if rel else '?'}")
    for vd in objects.find("Video"):
        vname = vd.props[1].split("\x00")[0] if len(vd.props) > 1 else "?"
        rel = vd.first("RelativeFilename")
        content = vd.first("Content")
        emb = len(content.props[0]) if content and content.props else 0
        print(f"  Video {vname}: {rel.props[0] if rel else '?'} 内嵌={emb} 字节")

    # --- 变形/骨骼 ---
    for kind in ("Deformer", "AnimationCurve", "AnimationStack", "NodeAttribute"):
        n = kinds.get(kind, 0)
        if n:
            print(f"\n{kind} 数量: {n}")


if __name__ == "__main__":
    summarize(sys.argv[1] if len(sys.argv) > 1 else "mesh/IL3DN_Tree_Pine_01_OneMesh.FBX")
