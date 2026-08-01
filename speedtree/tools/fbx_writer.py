"""
最小二进制 FBX 写出器（FBX 7300 / FBX 2013 格式）
=================================================
不依赖 Autodesk FBX SDK / Blender。节点结构对齐参考资产
IL3DN_Tree_Pine_01_OneMesh.FBX，因此产物具备相同的导入语义：

  * 一个 Null 根节点 + 若干名为 <Base>_LOD0/1/2 的 Mesh 子节点
    （Unity 会据此自动创建 LODGroup）
  * 每个 Mesh 两个材质槽（bark / leaves）
  * LayerElementNormal / UV / Color(RGBA) / Material 四层
  * 顶点色以 RGBA 四分量写出，Alpha 承载风动画的归一化高度
"""
import struct
import zlib
import datetime

VERSION = 7300
HEAD_MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
NULL_RECORD_LEN = 13  # version < 7500

# 与参考文件配套的一组 id（二者需自洽，导入器一般不校验内容）
FILE_ID = bytes.fromhex("2db32beab724cec6b3c2b92aaf24f6fd")
FOOT_ID = bytes.fromhex("fabcae09d4c9d167b673f08c1ef8227e")
FOOT_MAGIC = bytes.fromhex("f85a8c6adef5d97eece90ce3758f290b")


# --------------------------------------------------------------------------
# 节点与属性编码
# --------------------------------------------------------------------------
class N:
    """FBX 节点。props 为 (类型字符, 值) 列表。"""

    def __init__(self, name, *props, children=None):
        self.name = name
        self.props = list(props)
        self.children = list(children or [])

    def add(self, child):
        self.children.append(child)
        return child


def _arr(code, itemsize, fmt, values):
    raw = struct.pack("<%d%s" % (len(values), fmt), *values)
    comp = zlib.compress(raw)
    if len(comp) < len(raw):
        return code.encode() + struct.pack("<III", len(values), 1, len(comp)) + comp
    return code.encode() + struct.pack("<III", len(values), 0, len(raw)) + raw


def encode_prop(t, v):
    if t == "Y":
        return b"Y" + struct.pack("<h", int(v))
    if t == "C":
        return b"C" + struct.pack("<?", bool(v))
    if t == "I":
        return b"I" + struct.pack("<i", int(v))
    if t == "F":
        return b"F" + struct.pack("<f", float(v))
    if t == "D":
        return b"D" + struct.pack("<d", float(v))
    if t == "L":
        return b"L" + struct.pack("<q", int(v))
    if t == "S":
        b = v.encode("utf-8") if isinstance(v, str) else v
        return b"S" + struct.pack("<I", len(b)) + b
    if t == "R":
        return b"R" + struct.pack("<I", len(v)) + v
    if t == "d":
        return _arr("d", 8, "d", [float(x) for x in v])
    if t == "f":
        return _arr("f", 4, "f", [float(x) for x in v])
    if t == "i":
        return _arr("i", 4, "i", [int(x) for x in v])
    if t == "l":
        return _arr("l", 8, "q", [int(x) for x in v])
    raise ValueError("未知属性类型 %r" % t)


def serialize(node, start):
    props_buf = b"".join(encode_prop(t, v) for t, v in node.props)
    name_b = node.name.encode("utf-8")
    header_len = 13 + len(name_b)

    cur = start + header_len + len(props_buf)
    child_bufs = []
    for c in node.children:
        b = serialize(c, cur)
        child_bufs.append(b)
        cur += len(b)
    if node.children:
        cur += NULL_RECORD_LEN
    end_offset = cur

    out = struct.pack("<III", end_offset, len(node.props), len(props_buf))
    out += struct.pack("<B", len(name_b)) + name_b + props_buf
    out += b"".join(child_bufs)
    if node.children:
        out += b"\x00" * NULL_RECORD_LEN
    return out


def write_file(path, top_nodes):
    buf = bytearray(HEAD_MAGIC + struct.pack("<I", VERSION))
    for n in top_nodes:
        buf += serialize(n, len(buf))
    buf += b"\x00" * NULL_RECORD_LEN
    buf += FOOT_ID
    while len(buf) % 16 != 0:
        buf += b"\x00"
    buf += b"\x00" * 4
    buf += struct.pack("<I", VERSION)
    buf += b"\x00" * 120
    buf += FOOT_MAGIC
    with open(path, "wb") as f:
        f.write(bytes(buf))
    return len(buf)


# --------------------------------------------------------------------------
# 属性表助手
# --------------------------------------------------------------------------
def P(name, type_, subtype, flags, *values):
    props = [("S", name), ("S", type_), ("S", subtype), ("S", flags)]
    for v in values:
        if isinstance(v, bool):
            props.append(("I", int(v)))
        elif isinstance(v, int):
            props.append(("I", v))
        else:
            props.append(("D", float(v)))
    return N("P", *props)


_ID = [1000000]


def new_id():
    _ID[0] += 7
    return _ID[0]


# --------------------------------------------------------------------------
# 场景构建
# --------------------------------------------------------------------------
def _header_extension(creator):
    now = datetime.datetime.now()
    ts = N("CreationTimeStamp",
           children=[N("Version", ("I", 1000)), N("Year", ("I", now.year)),
                     N("Month", ("I", now.month)), N("Day", ("I", now.day)),
                     N("Hour", ("I", now.hour)), N("Minute", ("I", now.minute)),
                     N("Second", ("I", now.second)),
                     N("Millisecond", ("I", now.microsecond // 1000))])
    return N("FBXHeaderExtension", children=[
        N("FBXHeaderVersion", ("I", 1003)),
        N("FBXVersion", ("I", VERSION)),
        N("EncryptionType", ("I", 0)),
        ts,
        N("Creator", ("S", creator)),
    ])


def _global_settings(unit_scale_cm):
    """UpAxis=Y。顶点已在写出前烘焙成 Y-up，因此不需要节点级旋转。"""
    p70 = N("Properties70", children=[
        P("UpAxis", "int", "Integer", "", 1),
        P("UpAxisSign", "int", "Integer", "", 1),
        P("FrontAxis", "int", "Integer", "", 2),
        P("FrontAxisSign", "int", "Integer", "", 1),
        P("CoordAxis", "int", "Integer", "", 0),
        P("CoordAxisSign", "int", "Integer", "", 1),
        P("OriginalUpAxis", "int", "Integer", "", 1),
        P("OriginalUpAxisSign", "int", "Integer", "", 1),
        P("UnitScaleFactor", "double", "Number", "", unit_scale_cm),
        P("OriginalUnitScaleFactor", "double", "Number", "", unit_scale_cm),
        P("AmbientColor", "ColorRGB", "Color", "", 0.0, 0.0, 0.0),
        N("P", ("S", "DefaultCamera"), ("S", "KString"), ("S", ""), ("S", ""), ("S", "Producer Perspective")),
        P("TimeMode", "enum", "", "", 6),
        N("P", ("S", "TimeSpanStart"), ("S", "KTime"), ("S", "Time"), ("S", ""), ("L", 0)),
        N("P", ("S", "TimeSpanStop"), ("S", "KTime"), ("S", "Time"), ("S", ""), ("L", 46186158000)),
        P("CustomFrameRate", "double", "Number", "", -1.0),
    ])
    return N("GlobalSettings", children=[N("Version", ("I", 1000)), p70])


def _definitions(counts):
    node = N("Definitions", children=[
        N("Version", ("I", 100)),
        N("Count", ("I", sum(counts.values()) + 1)),
        N("ObjectType", ("S", "GlobalSettings"), children=[N("Count", ("I", 1))]),
    ])
    for k in ("Model", "NodeAttribute", "Geometry", "Material"):
        if counts.get(k):
            node.add(N("ObjectType", ("S", k), children=[N("Count", ("I", counts[k]))]))
    return node


def _geometry_node(gid, mesh_data):
    """mesh_data: dict(pos, polys, uv, nrm, col, mat_ids)"""
    pos = mesh_data["pos"]
    polys = mesh_data["polys"]

    verts = []
    for p in pos:
        verts.extend(p)

    pvi = []
    for poly in polys:
        for k, vi in enumerate(poly):
            pvi.append(vi if k < len(poly) - 1 else (-vi - 1))

    geo = N("Geometry", ("L", gid), ("S", "\x00\x01Geometry"), ("S", "Mesh"), children=[
        N("Properties70"),
        N("Vertices", ("d", verts)),
        N("PolygonVertexIndex", ("i", pvi)),
        N("GeometryVersion", ("I", 124)),
    ])

    # 法线（ByPolygonVertex / Direct）
    nrm = []
    for n in mesh_data["nrm"]:
        nrm.extend(n)
    geo.add(N("LayerElementNormal", ("I", 0), children=[
        N("Version", ("I", 101)),
        N("Name", ("S", "")),
        N("MappingInformationType", ("S", "ByPolygonVertex")),
        N("ReferenceInformationType", ("S", "Direct")),
        N("Normals", ("d", nrm)),
    ]))

    # 顶点色（ByPolygonVertex / IndexToDirect，RGBA 四分量）
    uniq, idx = {}, []
    flat = []
    for c in mesh_data["col"]:
        key = tuple(round(x, 6) for x in c)
        if key not in uniq:
            uniq[key] = len(uniq)
            flat.extend(c)
        idx.append(uniq[key])
    geo.add(N("LayerElementColor", ("I", 0), children=[
        N("Version", ("I", 101)),
        N("Name", ("S", "WindData")),
        N("MappingInformationType", ("S", "ByPolygonVertex")),
        N("ReferenceInformationType", ("S", "IndexToDirect")),
        N("Colors", ("d", flat)),
        N("ColorIndex", ("i", idx)),
    ]))

    # UV
    uuniq, uidx, uflat = {}, [], []
    for uv in mesh_data["uv"]:
        key = (round(uv[0], 6), round(uv[1], 6))
        if key not in uuniq:
            uuniq[key] = len(uuniq)
            uflat.extend(key)
        uidx.append(uuniq[key])
    geo.add(N("LayerElementUV", ("I", 0), children=[
        N("Version", ("I", 101)),
        N("Name", ("S", "UVChannel_1")),
        N("MappingInformationType", ("S", "ByPolygonVertex")),
        N("ReferenceInformationType", ("S", "IndexToDirect")),
        N("UV", ("d", uflat)),
        N("UVIndex", ("i", uidx)),
    ]))

    # 材质（ByPolygon / IndexToDirect）
    geo.add(N("LayerElementMaterial", ("I", 0), children=[
        N("Version", ("I", 101)),
        N("Name", ("S", "")),
        N("MappingInformationType", ("S", "ByPolygon")),
        N("ReferenceInformationType", ("S", "IndexToDirect")),
        N("Materials", ("i", list(mesh_data["mat_ids"]))),
    ]))

    layer = N("Layer", ("I", 0), children=[N("Version", ("I", 100))])
    for t in ("LayerElementNormal", "LayerElementColor", "LayerElementUV", "LayerElementMaterial"):
        layer.add(N("LayerElement", children=[N("Type", ("S", t)), N("TypedIndex", ("I", 0))]))
    geo.add(layer)
    return geo


def _model_node(mid, name, kind):
    p70 = N("Properties70", children=[
        P("Lcl Translation", "Lcl Translation", "", "A", 0.0, 0.0, 0.0),
        P("Lcl Rotation", "Lcl Rotation", "", "A", 0.0, 0.0, 0.0),
        P("Lcl Scaling", "Lcl Scaling", "", "A", 1.0, 1.0, 1.0),
        P("DefaultAttributeIndex", "int", "Integer", "", 0),
    ])
    return N("Model", ("L", mid), ("S", name + "\x00\x01Model"), ("S", kind), children=[
        N("Version", ("I", 232)),
        p70,
        N("Shading", ("C", True)),
        N("Culling", ("S", "CullingOff")),
    ])


def _material_node(mid, name, diffuse):
    p70 = N("Properties70", children=[
        N("P", ("S", "ShadingModel"), ("S", "KString"), ("S", ""), ("S", ""), ("S", "phong")),
        P("DiffuseColor", "Color", "", "A", *diffuse),
        P("SpecularColor", "Color", "", "A", 0.1, 0.1, 0.1),
        P("SpecularFactor", "Number", "", "A", 0.05),
        P("ShininessExponent", "Number", "", "A", 8.0),
        P("Opacity", "Number", "", "A", 1.0),
    ])
    return N("Material", ("L", mid), ("S", name + "\x00\x01Material"), ("S", ""), children=[
        N("Version", ("I", 102)),
        N("ShadingModel", ("S", "phong")),
        N("MultiLayer", ("I", 0)),
        p70,
    ])


def export_lod_fbx(path, base_name, lod_meshes, materials, unit_scale_cm=1.0,
                   creator="procedural-pine (pure python fbx writer)"):
    """写出含多级 LOD 的 FBX。

    lod_meshes : [dict(pos, polys, uv, nrm, col, mat_ids)]，索引即 LOD 级别
    materials  : [(名称, (r,g,b))]
    """
    objects = N("Objects")
    connections = N("Connections")

    root_id = new_id()
    attr_id = new_id()
    objects.add(N("NodeAttribute", ("L", attr_id), ("S", "\x00\x01NodeAttribute"), ("S", "Null"),
                  children=[N("TypeFlags", ("S", "Null"))]))
    objects.add(_model_node(root_id, base_name, "Null"))
    connections.add(N("C", ("S", "OO"), ("L", root_id), ("L", 0)))
    connections.add(N("C", ("S", "OO"), ("L", attr_id), ("L", root_id)))

    mat_ids = []
    for name, rgb in materials:
        m = new_id()
        mat_ids.append(m)
        objects.add(_material_node(m, name, rgb))

    for i, md in enumerate(lod_meshes):
        gid = new_id()
        mid = new_id()
        objects.add(_geometry_node(gid, md))
        objects.add(_model_node(mid, f"{base_name}_LOD{i}", "Mesh"))
        connections.add(N("C", ("S", "OO"), ("L", mid), ("L", root_id)))
        connections.add(N("C", ("S", "OO"), ("L", gid), ("L", mid)))
        for m in mat_ids:
            connections.add(N("C", ("S", "OO"), ("L", m), ("L", mid)))

    counts = dict(Model=1 + len(lod_meshes), NodeAttribute=1,
                  Geometry=len(lod_meshes), Material=len(materials))

    top = [
        _header_extension(creator),
        N("FileId", ("R", FILE_ID)),
        N("CreationTime", ("S", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S:000"))),
        N("Creator", ("S", creator)),
        _global_settings(unit_scale_cm),
        N("Documents", children=[
            N("Count", ("I", 1)),
            N("Document", ("L", new_id()), ("S", ""), ("S", "Scene"),
              children=[N("Properties70"), N("RootNode", ("L", 0))]),
        ]),
        N("References"),
        _definitions(counts),
        objects,
        connections,
    ]
    return write_file(path, top)
