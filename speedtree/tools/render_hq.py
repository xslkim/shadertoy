"""
高质量软件渲染器（numpy）
=========================
在 softrender.py 的基础上补齐了实际看树需要的东西：

  * 近平面裁剪（跨越相机平面的三角形要切开，否则会整块消失）
  * 透视校正的 UV 插值 + 双线性纹理采样
  * Alpha 镂空（叶卡必需，否则会渲染成实心四边形）
  * 阴影贴图（正交光源，阴影 pass 同样做 alpha 测试）
  * 半球环境光 + 平行光 + 叶片背透（伪次表面散射）
  * SSAA 超采样抗锯齿
  * 顶点色驱动的风形变（A = 弯曲权重，G = 每卡抖动相位）

不依赖 GPU 或任何 DCC。
"""
import math
import os

import numpy as np
from PIL import Image

# 顶点属性打平成一行，裁剪时可以整行线性插值：
#   [0:4] 裁剪空间坐标  [4:7] 世界坐标  [7:9] UV  [9:12] 法线
_VW = 12


# --------------------------------------------------------------------------
# 资源
# --------------------------------------------------------------------------
def load_texture(path):
    img = Image.open(path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    a = np.asarray(img, dtype=np.float32) / 255.0
    a[..., :3] = a[..., :3] ** 2.2  # sRGB -> 线性
    return a


class Material:
    def __init__(self, texture=None, color=(1, 1, 1), two_sided=False,
                 alpha_cutout=False, cutoff=0.5, translucency=0.0, spec=0.02):
        self.texture = texture
        self.color = np.array(color, dtype=np.float32)
        self.two_sided = two_sided
        self.alpha_cutout = alpha_cutout
        self.cutoff = cutoff
        self.translucency = translucency
        self.spec = spec


def sample(tex, u, v):
    """双线性采样，UV 环绕。v=0 对应图像底边。"""
    h, w = tex.shape[:2]
    x = (u % 1.0) * w - 0.5
    y = (1.0 - (v % 1.0)) * h - 0.5
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    x0 %= w
    y0 %= h
    x1 = (x0 + 1) % w
    y1 = (y0 + 1) % h
    t00, t10 = tex[y0, x0], tex[y0, x1]
    t01, t11 = tex[y1, x0], tex[y1, x1]
    return (t00 * (1 - fx) * (1 - fy) + t10 * fx * (1 - fy)
            + t01 * (1 - fx) * fy + t11 * fx * fy)


# --------------------------------------------------------------------------
# 几何容器
# --------------------------------------------------------------------------
class DrawMesh:
    """三角形化后的绘制数据。"""

    def __init__(self, pos, tris, uv, nrm, mat, vcol=None):
        self.pos = np.asarray(pos, dtype=np.float64)     # (V,3)
        self.tris = np.asarray(tris, dtype=np.int64)     # (T,3)
        self.uv = np.asarray(uv, dtype=np.float64)       # (T,3,2)
        self.nrm = np.asarray(nrm, dtype=np.float64)     # (T,3,3)
        self.mat = np.asarray(mat, dtype=np.int64)       # (T,)
        self.vcol = vcol                                 # (V,4) 顶点色，可选


def from_tree_mesh(m):
    """把 pine_gen.TreeMesh 转成 DrawMesh（扇形三角化）。"""
    pos = np.array(m.pos, dtype=np.float64)
    vcol = np.zeros((len(pos), 4), dtype=np.float64)
    tris, uvs, nrms, mats = [], [], [], []
    c = 0
    for poly, mid in zip(m.polys, m.mat_ids):
        n = len(poly)
        for k in range(n):
            vcol[poly[k]] = m.col[c + k]
        for i in range(1, n - 1):
            tris.append((poly[0], poly[i], poly[i + 1]))
            uvs.append((m.uv[c], m.uv[c + i], m.uv[c + i + 1]))
            nrms.append((m.nrm[c], m.nrm[c + i], m.nrm[c + i + 1]))
            mats.append(mid)
        c += n
    return DrawMesh(pos, tris, uvs, nrms, mats, vcol)


def from_polys(pos, polys, mat_ids, uv, nrm):
    """从参考资产解出来的原始数据构造 DrawMesh。"""
    class _T:
        pass
    t = _T()
    t.pos, t.polys, t.mat_ids, t.uv, t.nrm = pos, polys, mat_ids, uv, nrm
    t.col = [(0.0, 0.0, 0.0, 0.0)] * len(uv)
    return from_tree_mesh(t)


def ground_mesh(size=40.0, z=0.0, repeat=14.0, mat=2, div=8):
    xs = np.linspace(-size, size, div + 1)
    pos, uvg = [], {}
    for j, y in enumerate(xs):
        for i, x in enumerate(xs):
            uvg[(i, j)] = (i / div * repeat, j / div * repeat)
            pos.append((x, y, z))
    tris, uv, nrm, mats = [], [], [], []
    n = (0.0, 0.0, 1.0)

    def idx(i, j):
        return j * (div + 1) + i

    for j in range(div):
        for i in range(div):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            tris.append((a, b, c))
            uv.append((uvg[(i, j)], uvg[(i + 1, j)], uvg[(i + 1, j + 1)]))
            tris.append((a, c, d))
            uv.append((uvg[(i, j)], uvg[(i + 1, j + 1)], uvg[(i, j + 1)]))
            nrm += [(n, n, n), (n, n, n)]
            mats += [mat, mat]
    return DrawMesh(np.array(pos), tris, uv, nrm, mats)


def transform(mesh, translate=(0, 0, 0), rot_z=0.0, scale=1.0):
    c, s = math.cos(rot_z), math.sin(rot_z)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    pos = mesh.pos @ R.T * scale + np.array(translate)
    nrm = mesh.nrm.reshape(-1, 3) @ R.T
    out = DrawMesh(pos, mesh.tris, mesh.uv, nrm.reshape(mesh.nrm.shape), mesh.mat)
    out.vcol = mesh.vcol
    return out


# --------------------------------------------------------------------------
# 风形变
# --------------------------------------------------------------------------
def apply_wind(mesh, t, direction=(1.0, 0.25), amplitude=0.22, freq=1.15,
               flutter=0.055):
    """按顶点色做风形变：A = 整体弯曲权重，G = 每张叶卡的抖动相位。"""
    if mesh.vcol is None:
        return mesh
    a = mesh.vcol[:, 3]
    g = mesh.vcol[:, 1]
    d = np.array([direction[0], direction[1], 0.0], dtype=np.float64)
    d /= np.linalg.norm(d) or 1.0

    # 主弯曲：随高度权重的平方增长，两个频率叠加避免机械感
    sway = (np.sin(2 * math.pi * freq * t) * 0.75
            + np.sin(2 * math.pi * freq * 1.73 * t + 1.1) * 0.25)
    bend = (a ** 2) * amplitude * sway

    # 叶片抖动：每张卡自己的相位
    ph = 2 * math.pi * (freq * 2.6 * t + g)
    jit = (a ** 1.5)[:, None] * flutter * np.stack(
        [np.sin(ph), np.cos(ph * 1.31), np.sin(ph * 0.77) * 0.6], axis=1)

    pos = mesh.pos + bend[:, None] * d + jit
    # 弯曲时略微下沉，保持枝条长度观感
    pos[:, 2] -= (a ** 2) * amplitude * abs(sway) * 0.18

    out = DrawMesh(pos, mesh.tris, mesh.uv, mesh.nrm, mesh.mat)
    out.vcol = mesh.vcol
    return out


# --------------------------------------------------------------------------
# 矩阵
# --------------------------------------------------------------------------
def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = (np.asarray(x, dtype=np.float64) for x in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    if abs(f @ up) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    M = np.eye(4)
    M[0, :3], M[1, :3], M[2, :3] = s, u, -f
    M[:3, 3] = -M[:3, :3] @ eye
    return M


def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy) / 2)
    M = np.zeros((4, 4))
    M[0, 0] = f / aspect
    M[1, 1] = f
    M[2, 2] = (far + near) / (near - far)
    M[2, 3] = 2 * far * near / (near - far)
    M[3, 2] = -1
    return M


def ortho(half, near, far):
    M = np.eye(4)
    M[0, 0] = 1.0 / half
    M[1, 1] = 1.0 / half
    M[2, 2] = -2.0 / (far - near)
    M[2, 3] = -(far + near) / (far - near)
    return M


# --------------------------------------------------------------------------
# 光栅化
# --------------------------------------------------------------------------
def _clip_space(pos, MVP):
    return np.hstack([pos, np.ones((len(pos), 1))]) @ MVP.T


def _gather(clipv, mesh, i):
    idx = mesh.tris[i]
    vt = np.empty((3, _VW))
    vt[:, 0:4] = clipv[idx]
    vt[:, 4:7] = mesh.pos[idx]
    vt[:, 7:9] = mesh.uv[i]
    vt[:, 9:12] = mesh.nrm[i]
    return vt


def _clip_near(vt, eps):
    """对 w = eps 平面做 Sutherland-Hodgman 裁剪，返回若干三角形。"""
    w = vt[:, 3]
    if (w >= eps).all():
        return (vt,)
    if (w < eps).all():
        return ()
    poly = []
    for i in range(3):
        a, b = vt[i], vt[(i + 1) % 3]
        ina, inb = a[3] >= eps, b[3] >= eps
        if ina:
            poly.append(a)
        if ina != inb:
            t = (eps - a[3]) / (b[3] - a[3])
            poly.append(a + (b - a) * t)
    return tuple(np.stack([poly[0], poly[k], poly[k + 1]])
                 for k in range(1, len(poly) - 1))


def _screen(vt, W, H):
    w = vt[:, 3].copy()
    w[np.abs(w) < 1e-9] = 1e-9
    ndc = vt[:, 0:3] / w[:, None]
    sx = (ndc[:, 0] * 0.5 + 0.5) * W
    sy = (1 - (ndc[:, 1] * 0.5 + 0.5)) * H
    return sx, sy, w, ndc[:, 2]


def _bary(sx, sy, W, H):
    """返回 (mask, l0, l1, l2, x0, y0) —— 若三角形不可见则返回 None。"""
    minx = max(int(min(sx)), 0)
    maxx = min(int(max(sx)) + 1, W - 1)
    miny = max(int(min(sy)), 0)
    maxy = min(int(max(sy)) + 1, H - 1)
    if minx > maxx or miny > maxy:
        return None
    x0, x1, x2 = sx
    y0, y1, y2 = sy
    det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(det) < 1e-12:
        return None
    gx, gy = np.meshgrid(np.arange(minx, maxx + 1) + 0.5,
                         np.arange(miny, maxy + 1) + 0.5)
    l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / det
    l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / det
    l2 = 1 - l0 - l1
    m = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
    if not m.any():
        return None
    return m, l0, l1, l2, (minx, maxx, miny, maxy)


def _shadow_pass(meshes, materials, MVP, res, eps):
    depth = np.full((res, res), np.inf)
    for mesh in meshes:
        clipv = _clip_space(mesh.pos, MVP)
        for i in range(len(mesh.tris)):
            mat = materials[mesh.mat[i]]
            for vt in _clip_near(_gather(clipv, mesh, i), eps):
                sx, sy, _w, ndcz = _screen(vt, res, res)
                r = _bary(sx, sy, res, res)
                if r is None:
                    continue
                m, l0, l1, l2, (minx, maxx, miny, maxy) = r
                z = l0 * ndcz[0] + l1 * ndcz[1] + l2 * ndcz[2]
                if mat.alpha_cutout and mat.texture is not None:
                    u = l0 * vt[0, 7] + l1 * vt[1, 7] + l2 * vt[2, 7]
                    v = l0 * vt[0, 8] + l1 * vt[1, 8] + l2 * vt[2, 8]
                    m &= sample(mat.texture, u, v)[..., 3] > mat.cutoff
                    if not m.any():
                        continue
                sub = depth[miny:maxy + 1, minx:maxx + 1]
                hit = m & (z < sub)
                sub[hit] = z[hit]
    return depth


def render(meshes, materials, width=900, height=1200, ss=2,
           azimuth=35.0, elevation=8.0, fov=32.0, dist_mul=1.0,
           target=None, radius=None,
           sun_dir=(-0.55, -0.72, 0.55), sun_color=(2.05, 1.84, 1.46),
           sky_color=(0.34, 0.47, 0.72), ground_color=(0.19, 0.17, 0.11),
           bg_top=(0.048, 0.090, 0.185), bg_bottom=(0.40, 0.48, 0.585),
           ambient=0.44,
           shadows=True, shadow_res=1200, exposure=1.0, fog=0.0,
           shadow_bounds=None, shadow_strength=0.22):
    W, H = width * ss, height * ss

    allv = np.vstack([m.pos for m in meshes if len(m.pos)])
    lo, hi = allv.min(0), allv.max(0)
    if target is None:
        target = (lo + hi) / 2
    target = np.asarray(target, dtype=np.float64)
    if radius is None:
        radius = float(np.linalg.norm(hi - lo) / 2 * 1.10)

    az, el = math.radians(azimuth), math.radians(elevation)
    dist = radius / math.tan(math.radians(fov) / 2) * dist_mul
    eye = target + dist * np.array([math.cos(el) * math.cos(az),
                                    math.cos(el) * math.sin(az),
                                    math.sin(el)])
    near = max(dist * 0.01, 1e-3)
    V = look_at(eye, target)
    P = perspective(fov, W / H, near, dist * 8)
    MVP = P @ V

    L = np.asarray(sun_dir, dtype=np.float64)
    L /= np.linalg.norm(L)

    shadow_map = shadow_MVP = None
    if shadows:
        # 正交阴影体积默认覆盖整个场景，但巨大的地面会把分辨率耗光，
        # 所以允许调用方只给主体的包围盒。
        slo, shi = (lo, hi) if shadow_bounds is None else shadow_bounds
        slo = np.asarray(slo, dtype=np.float64)
        shi = np.asarray(shi, dtype=np.float64)
        sc = (slo + shi) / 2
        srad = float(np.linalg.norm(shi - slo) / 2 * 1.05)
        SV = look_at(sc + L * srad * 2.5, sc)
        SP = ortho(srad, 0.01, srad * 6)
        shadow_MVP = SP @ SV
        shadow_map = _shadow_pass(meshes, materials, shadow_MVP, shadow_res, -1e9)

    color = np.empty((H, W, 3), dtype=np.float64)
    t = (np.arange(H) / (H - 1))[:, None, None]
    color[:] = np.array(bg_top) * (1 - t) + np.array(bg_bottom) * t
    zbuf = np.full((H, W), np.inf)

    sun_c = np.asarray(sun_color)
    sky_c = np.asarray(sky_color)
    gnd_c = np.asarray(ground_color)

    for mesh in meshes:
        clipv = _clip_space(mesh.pos, MVP)
        for i in range(len(mesh.tris)):
            mat = materials[mesh.mat[i]]
            for vt in _clip_near(_gather(clipv, mesh, i), near):
                sx, sy, w, _ndcz = _screen(vt, W, H)
                r = _bary(sx, sy, W, H)
                if r is None:
                    continue
                m, l0, l1, l2, (minx, maxx, miny, maxy) = r

                invw = 1.0 / w
                denom = l0 * invw[0] + l1 * invw[1] + l2 * invw[2]
                denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
                depth = 1.0 / denom
                sub_z = zbuf[miny:maxy + 1, minx:maxx + 1]
                m &= depth < sub_z
                if not m.any():
                    continue

                b0 = l0 * invw[0] / denom
                b1 = l1 * invw[1] / denom
                b2 = 1.0 - b0 - b1

                u = b0 * vt[0, 7] + b1 * vt[1, 7] + b2 * vt[2, 7]
                v = b0 * vt[0, 8] + b1 * vt[1, 8] + b2 * vt[2, 8]

                if mat.texture is not None:
                    texel = sample(mat.texture, u, v)
                    if mat.alpha_cutout:
                        m &= texel[..., 3] > mat.cutoff
                        if not m.any():
                            continue
                    albedo = texel[..., :3] * mat.color
                else:
                    albedo = np.broadcast_to(mat.color, l0.shape + (3,)).copy()

                N = (b0[..., None] * vt[0, 9:12] + b1[..., None] * vt[1, 9:12]
                     + b2[..., None] * vt[2, 9:12])
                N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-9)

                pw = (b0[..., None] * vt[0, 4:7] + b1[..., None] * vt[1, 4:7]
                      + b2[..., None] * vt[2, 4:7])

                ndl_raw = N @ L
                if mat.two_sided:
                    Nf = np.where((ndl_raw < 0)[..., None], -N, N)
                    ndl = np.abs(ndl_raw)
                else:
                    Nf = N
                    ndl = np.clip(ndl_raw, 0, 1)

                shadow = 1.0
                if shadow_map is not None:
                    ph = np.concatenate([pw, np.ones(pw.shape[:-1] + (1,))], axis=-1)
                    sc4 = ph @ shadow_MVP.T
                    sw = np.where(np.abs(sc4[..., 3]) < 1e-9, 1e-9, sc4[..., 3])
                    sndc = np.nan_to_num(sc4[..., :3] / sw[..., None], nan=1e9,
                                         posinf=1e9, neginf=-1e9)
                    fx = np.clip((sndc[..., 0] * 0.5 + 0.5) * shadow_res, -1.0, shadow_res + 1.0)
                    fy = np.clip((1 - (sndc[..., 1] * 0.5 + 0.5)) * shadow_res,
                                 -1.0, shadow_res + 1.0)
                    outside = (fx < 0) | (fx >= shadow_res) | (fy < 0) | (fy >= shadow_res)
                    xi = fx.astype(np.int32)
                    yi = fy.astype(np.int32)
                    bias = 0.0022 + 0.009 * (1.0 - ndl)
                    ref = sndc[..., 2] - bias
                    # 3x3 PCF，软化叶片自阴影的锯齿
                    acc = np.zeros_like(fx)
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            xs = np.clip(xi + dx, 0, shadow_res - 1)
                            ys = np.clip(yi + dy, 0, shadow_res - 1)
                            acc += shadow_map[ys, xs] >= ref
                    vis = acc / 9.0
                    vis = np.where(outside, 1.0, vis)
                    shadow = (shadow_strength + (1.0 - shadow_strength) * vis)[..., None]

                hemi = 0.5 + 0.5 * Nf[..., 2]
                amb = gnd_c + (sky_c - gnd_c) * hemi[..., None]
                lit_col = albedo * (amb * ambient + sun_c * (ndl[..., None] * shadow))

                if mat.translucency > 0:
                    back = np.clip(-(N @ L), 0, 1)[..., None]
                    lit_col += albedo * sun_c * back * mat.translucency * shadow

                if mat.spec > 0:
                    Vv = eye - pw
                    Vv /= np.maximum(np.linalg.norm(Vv, axis=-1, keepdims=True), 1e-9)
                    Hh = Vv + L
                    Hh /= np.maximum(np.linalg.norm(Hh, axis=-1, keepdims=True), 1e-9)
                    nh = np.clip(np.sum(Nf * Hh, axis=-1), 0, 1)
                    lit_col += sun_c * (nh ** 24)[..., None] * mat.spec * shadow

                if fog > 0:
                    f = 1.0 - np.exp(-np.clip(depth, 0.0, 1e4) * fog)
                    lit_col = lit_col * (1 - f[..., None]) + np.array(bg_bottom) * f[..., None]

                sub_c = color[miny:maxy + 1, minx:maxx + 1]
                sub_c[m] = lit_col[m]
                sub_z[m] = depth[m]

    img = np.clip(color * exposure, 0, None)
    img = img / (1.0 + img)                 # Reinhard 色调映射
    img = np.clip(img, 0, 1) ** (1 / 2.2)   # 线性 -> sRGB
    out = (img * 255).astype(np.uint8)
    if ss > 1:
        out = np.array(Image.fromarray(out).resize((width, height), Image.LANCZOS))
    return out


def save_png(img, path):
    Image.fromarray(img).save(path)
    return path


def label_grid(images, labels, cols=None, pad=16, bg=(13, 17, 23), band=40,
               font_size=17):
    from PIL import ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", font_size)
    except OSError:
        font = ImageFont.load_default()
    cols = cols or len(images)
    rows = (len(images) + cols - 1) // cols
    cw = max(i.shape[1] for i in images)
    ch = max(i.shape[0] for i in images)
    W = cols * cw + pad * (cols + 1)
    H = rows * (ch + band + pad) + pad
    canvas = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(canvas)
    for k, (img, lab) in enumerate(zip(images, labels)):
        r, c = divmod(k, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + band + pad)
        d.text((x + 3, y + 10), lab, fill=(226, 234, 242), font=font)
        canvas.paste(Image.fromarray(img), (x, y + band))
    return np.array(canvas)
