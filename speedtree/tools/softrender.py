"""
零依赖软件渲染器（numpy z-buffer 光栅化），用来把树网格画成 PNG。
只为快速视觉对比，不追求画质。

提供:
    Mesh(verts, faces, mat_ids)  -> 简单网格容器
    render(meshes, ...)          -> 返回 HxWx3 uint8 图像
"""
import numpy as np


class Mesh:
    def __init__(self, verts, faces, mat_ids=None):
        self.verts = np.asarray(verts, dtype=np.float64)
        self.faces = faces  # list[list[int]]，允许 quad
        self.mat_ids = mat_ids if mat_ids is not None else [0] * len(faces)

    def triangles(self):
        """扇形三角化，返回 (tri_indices, tri_mat)。"""
        tris, mats = [], []
        for f, m in zip(self.faces, self.mat_ids):
            for i in range(1, len(f) - 1):
                tris.append((f[0], f[i], f[i + 1]))
                mats.append(m)
        return np.array(tris, dtype=np.int64), np.array(mats, dtype=np.int64)


def look_at(eye, target, up=(0, 0, 1)):
    eye = np.asarray(eye, float)
    target = np.asarray(target, float)
    up = np.asarray(up, float)
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    M = np.eye(4)
    M[0, :3], M[1, :3], M[2, :3] = s, u, -f
    M[:3, 3] = -M[:3, :3] @ eye
    return M


def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fovy_deg) / 2)
    M = np.zeros((4, 4))
    M[0, 0] = f / aspect
    M[1, 1] = f
    M[2, 2] = (far + near) / (near - far)
    M[2, 3] = 2 * far * near / (near - far)
    M[3, 2] = -1
    return M


# 材质 0 = 树皮, 1 = 叶片
PALETTE = np.array(
    [
        [0.42, 0.28, 0.18],  # bark
        [0.20, 0.45, 0.16],  # leaves
    ]
)


def render(
    meshes,
    width=900,
    height=1100,
    azimuth=35.0,
    elevation=8.0,
    bg=(0.05, 0.06, 0.08),
    palette=None,
    light_dir=(-0.5, -0.7, 0.55),
    fit_margin=1.12,
    two_sided=True,
):
    """渲染若干 Mesh（Z-up 世界坐标），相机自动框住全部内容。"""
    palette = PALETTE if palette is None else np.asarray(palette)

    allv = np.vstack([m.verts for m in meshes])
    lo, hi = allv.min(0), allv.max(0)
    center = (lo + hi) / 2
    radius = np.linalg.norm(hi - lo) / 2 * fit_margin

    az, el = np.radians(azimuth), np.radians(elevation)
    dist = radius / np.tan(np.radians(32.0) / 2)
    eye = center + dist * np.array(
        [np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)]
    )
    V = look_at(eye, center)
    P = perspective(32.0, width / height, dist * 0.02, dist * 4)
    MVP = P @ V

    color = np.zeros((height, width, 3), dtype=np.float64)
    color[:] = bg
    zbuf = np.full((height, width), np.inf)

    L = np.asarray(light_dir, float)
    L /= np.linalg.norm(L)

    for mesh in meshes:
        tris, tmats = mesh.triangles()
        if len(tris) == 0:
            continue
        vw = mesh.verts
        vh = np.hstack([vw, np.ones((len(vw), 1))])
        clip = vh @ MVP.T
        w = clip[:, 3].copy()
        w[np.abs(w) < 1e-9] = 1e-9
        ndc = clip[:, :3] / w[:, None]
        sx = (ndc[:, 0] * 0.5 + 0.5) * width
        sy = (1 - (ndc[:, 1] * 0.5 + 0.5)) * height
        depth = np.linalg.norm(vw - eye, axis=1)

        # 面法线与光照（在世界空间算）
        a, b, c = vw[tris[:, 0]], vw[tris[:, 1]], vw[tris[:, 2]]
        n = np.cross(b - a, c - a)
        nl = np.linalg.norm(n, axis=1)
        nl[nl == 0] = 1
        n /= nl[:, None]
        ndl = n @ L
        if two_sided:
            ndl = np.abs(ndl)
        shade = 0.28 + 0.72 * np.clip(ndl, 0, 1)

        base = palette[np.clip(tmats, 0, len(palette) - 1)]
        # 叶片按面积略微扰动亮度，增加层次
        rng = np.random.default_rng(7)
        tint = 1.0 + 0.14 * (rng.random(len(tris)) - 0.5)
        tri_color = np.clip(base * shade[:, None] * tint[:, None], 0, 1)

        # 逐三角形扫描（面数只有几千，够用）
        X = sx[tris]
        Y = sy[tris]
        Z = depth[tris]
        behind = (w[tris] <= 0).any(axis=1)

        for i in range(len(tris)):
            if behind[i]:
                continue
            x0, x1, x2 = X[i]
            y0, y1, y2 = Y[i]
            minx = max(int(np.floor(min(x0, x1, x2))), 0)
            maxx = min(int(np.ceil(max(x0, x1, x2))), width - 1)
            miny = max(int(np.floor(min(y0, y1, y2))), 0)
            maxy = min(int(np.ceil(max(y0, y1, y2))), height - 1)
            if minx > maxx or miny > maxy:
                continue
            det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(det) < 1e-12:
                continue
            xs = np.arange(minx, maxx + 1)
            ys = np.arange(miny, maxy + 1)
            gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
            l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / det
            l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / det
            l2 = 1 - l0 - l1
            inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not inside.any():
                continue
            z = l0 * Z[i, 0] + l1 * Z[i, 1] + l2 * Z[i, 2]
            sub_z = zbuf[miny : maxy + 1, minx : maxx + 1]
            m = inside & (z < sub_z)
            if not m.any():
                continue
            sub_z[m] = z[m]
            color[miny : maxy + 1, minx : maxx + 1][m] = tri_color[i]

    img = np.clip(color, 0, 1) ** (1 / 2.2)
    return (img * 255).astype(np.uint8)


def save_png(img, path):
    from PIL import Image

    Image.fromarray(img).save(path)


def hstack_labeled(images, labels, pad=14, bg=(13, 17, 23)):
    """把多张图并排，顶部留标签条。"""
    from PIL import Image, ImageDraw

    h = max(i.shape[0] for i in images)
    w = sum(i.shape[1] for i in images) + pad * (len(images) + 1)
    canvas = Image.new("RGB", (w, h + 52), bg)
    d = ImageDraw.Draw(canvas)
    x = pad
    for img, label in zip(images, labels):
        canvas.paste(Image.fromarray(img), (x, 46))
        d.text((x + 8, 16), label, fill=(230, 237, 243))
        x += img.shape[1] + pad
    return np.array(canvas)
