"""
生成植被 alpha 纹理（PIL）
==========================
产出到 blender/textures/：
  needle_bundle.png   松针束（扇形针叶簇 + alpha）
  grass_tuft.png      草簇（多根草叶扇形 + alpha）
  petal.png           花瓣（杏仁形 + alpha）
  flower_center.png   花心（圆形 + alpha）

全部 RGBA，alpha 软边（超采样 + 高斯模糊）。
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageOps

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender", "textures")
OUT = os.path.normpath(OUT)
os.makedirs(OUT, exist_ok=True)

SS = 2  # 超采样倍数


def tapered_poly(centerline, widths):
    """沿中心线生成带宽度变化的封闭多边形。centerline: [(x,y)...], widths: [w...]"""
    left, right = [], []
    n = len(centerline)
    for i in range(n):
        if i < n - 1:
            dx = centerline[i + 1][0] - centerline[i][0]
            dy = centerline[i + 1][1] - centerline[i][1]
        else:
            dx = centerline[i][0] - centerline[i - 1][0]
            dy = centerline[i][1] - centerline[i - 1][1]
        L = math.hypot(dx, dy)
        if L == 0:
            continue
        px, py = -dy / L, dx / L
        w = widths[i]
        cx, cy = centerline[i]
        left.append((cx + px * w / 2, cy + py * w / 2))
        right.append((cx - px * w / 2, cy - py * w / 2))
    return left + list(reversed(right))


def needle_centerline(cx, cy, length, angle, droop=0.12, steps=22):
    """一条微微下垂的针叶中心线。图像坐标 y 向下，angle=0 向右，-pi/2 向上。"""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = angle + t * droop
        x = cx + math.cos(a) * length * t
        y = cy + math.sin(a) * length * t
        pts.append((x, y))
    return pts


def draw_needle(d, cx, cy, length, angle, base_w, tip_w, color, droop=0.12):
    cl = needle_centerline(cx, cy, length, angle, droop)
    n = len(cl)
    widths = [base_w * (1 - t) + tip_w * t for t in (i / (n - 1) for i in range(n))]
    poly = tapered_poly(cl, widths)
    d.polygon(poly, fill=color)


# ---------------- 松针束（下垂形态）----------------
def make_needle_bundle():
    S = 512 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S * 0.12  # 束心在顶部，针叶向下扇形（松针下垂）
    greens = [(0x15, 0x34, 0x15, 255), (0x20, 0x44, 0x1f, 255), (0x2c, 0x56, 0x28, 255)]
    needles = []
    for i in range(46):
        spread = -0.75 + i * 0.033
        ang = math.pi / 2 + spread
        length = S * (0.42 + 0.12 * (i % 3))
        base_w = S * (0.016 + 0.004 * (i % 3))
        needles.append((length, ang, base_w))
    # 底层深色（实心填充）
    for ln, ang, bw in needles:
        draw_needle(d, cx, cy, ln, ang, bw, bw * 0.14, greens[0], droop=-0.04)
    # 上层亮色
    for i, (ln, ang, bw) in enumerate(needles):
        draw_needle(d, cx, cy, ln, ang, bw, bw * 0.14, greens[1 + i % 2], droop=-0.04)
    # 内层短针叶（大幅加密，形成实心 tuft）
    for i in range(50):
        spread = -0.62 + i * 0.025
        ang = math.pi / 2 + spread
        ln = S * (0.22 + 0.08 * (i % 3))
        draw_needle(d, cx, cy, ln, ang, S * 0.015, S * 0.0025, greens[2], droop=-0.02)
    img = img.resize((512, 512), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(0.9))
    img.putalpha(a)
    path = os.path.join(OUT, "needle_bundle.png")
    img.save(path)
    print("saved", path)


# ---------------- 草簇（渐变 + 枯黄）----------------
def draw_needle_gradient(d, cx, cy, length, angle, base_w, tip_w, base_color, tip_color, droop, tip_frac=0.5):
    """两段渐变针叶：基半段 base_color，尖半段 tip_color。"""
    half = length * (1 - tip_frac)
    draw_needle(d, cx, cy, length, angle, base_w, tip_w, base_color, droop)
    # 尖端段
    cx2 = cx + math.cos(angle) * half
    cy2 = cy + math.sin(angle) * half
    draw_needle(d, cx2, cy2, length - half, angle, base_w * 0.55, tip_w, tip_color, droop)


def make_grass_tuft():
    S = 512 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    bx, by = S / 2, S * 0.9  # 草根在底部
    deep = (0x26, 0x50, 0x1c, 255)
    mid = (0x3e, 0x72, 0x28, 255)     # 更亮的中绿
    light = (0x52, 0x88, 0x33, 255)   # 亮绿
    blades = []
    for i in range(42):
        spread = -0.40 + i * 0.0195
        ang = -math.pi / 2 + spread
        length = S * (0.30 + 0.10 * (i % 4))
        base_w = S * (0.014 + 0.0025 * (i % 3))
        blades.append((length, ang, base_w))
    for ln, ang, bw in blades:
        draw_needle(d, bx, by, ln, ang, bw, bw * 0.1, deep, droop=0.18)
    for i, (ln, ang, bw) in enumerate(blades):
        c = mid if i % 2 else light
        draw_needle(d, bx, by, ln, ang, bw, bw * 0.1, c, droop=0.18)
    # 少量嫩黄新草
    for _ in range(5):
        i = random.randrange(len(blades))
        ln, ang, bw = blades[i]
        draw_needle(d, bx, by, ln * 0.9, ang + random.uniform(-0.06, 0.06), bw, bw * 0.1,
                    (0x82, 0xa8, 0x3a, 255), droop=0.22)
    img = img.resize((512, 512), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(1.0))
    img.putalpha(a)
    path = os.path.join(OUT, "grass_tuft.png")
    img.save(path)
    print("saved", path)


# ---------------- 花叶（宽叶，带叶脉）----------------
def make_leaf():
    S = 256 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S * 0.6
    L = S * 0.42
    W = S * 0.18
    poly = []
    steps = 36
    for i in range(steps + 1):
        t = i / steps
        yy = cy - L * math.cos(math.pi * t)
        w = W * math.sin(math.pi * t) ** 0.7
        poly.append((cx + w * 0.5, yy))
    for i in range(steps + 1):
        t = 1 - i / steps
        yy = cy - L * math.cos(math.pi * t)
        w = W * math.sin(math.pi * t) ** 0.7
        poly.append((cx - w * 0.5, yy))
    d.polygon(poly, fill=(0x2e, 0x66, 0x20, 255))
    inner = [(x * 0.72 + cx * 0.28, y * 0.72 + cy * 0.28) for x, y in poly]
    d.polygon(inner, fill=(0x3c, 0x7c, 0x28, 255))
    # 中脉
    mid_pts = [(cx, cy - L * math.cos(math.pi * t)) for t in [i / 20 for i in range(21)]]
    d.line(mid_pts, fill=(0x2a, 0x58, 0x1c, 255), width=max(2, int(S * 0.008)))
    img = img.resize((256, 256), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(0.7))
    img.putalpha(a)
    path = os.path.join(OUT, "leaf.png")
    img.save(path)
    print("saved", path)


# ---------------- 花瓣 ----------------
def make_petal():
    S = 256 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S * 0.60
    L = S * 0.38       # 花瓣长度
    W = S * 0.24       # 最大宽度（更宽，避免细条感）
    # 圆润花瓣：参数 t: 0=顶部钝尖, 1=基部圆；中部最宽，两端收窄
    poly = []
    steps = 44
    for i in range(steps + 1):
        t = i / steps
        yy = cy - L * math.cos(math.pi * t)  # 顶部(cy-L) 到 基部(cy+L)
        w = W * math.sin(math.pi * t) ** 0.62
        xoff = W * 0.22 * math.sin(math.pi * t) ** 2
        poly.append((cx + xoff + w * 0.5, yy))
    for i in range(steps + 1):
        t = 1 - i / steps
        yy = cy - L * math.cos(math.pi * t)
        w = W * math.sin(math.pi * t) ** 0.62
        xoff = W * 0.22 * math.sin(math.pi * t) ** 2
        poly.append((cx + xoff - w * 0.5, yy))
    # 底色 + 高光（更鲜艳的粉）
    d.polygon(poly, fill=(0xFF, 0x2D, 0x7B, 255))
    inner = [(x * 0.72 + cx * 0.28, y * 0.72 + cy * 0.28) for x, y in poly]
    d.polygon(inner, fill=(0xFF, 0x6B, 0xA5, 255))
    core = [(x * 0.4 + cx * 0.6, y * 0.4 + cy * 0.6) for x, y in poly]
    d.polygon(core, fill=(0xFF, 0xB3, 0xC7, 255))
    img = img.resize((256, 256), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(0.8))
    img.putalpha(a)
    path = os.path.join(OUT, "petal.png")
    img.save(path)
    print("saved", path)


# ---------------- 花心 ----------------
def make_flower_center():
    S = 128 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S / 2
    r = S * 0.30
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0xFF, 0xB3, 0x00, 255))
    # 质感点
    for _ in range(40):
        import random
        random.seed(42)
        a = random.uniform(0, math.tau)
        rr = random.uniform(0, r * 0.85)
        x = cx + math.cos(a) * rr
        y = cy + math.sin(a) * rr
        d.ellipse([x - 3 * SS, y - 3 * SS, x + 3 * SS, y + 3 * SS], fill=(0xD8, 0x8F, 0x00, 255))
    img = img.resize((128, 128), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(0.6))
    img.putalpha(a)
    path = os.path.join(OUT, "flower_center.png")
    img.save(path)
    print("saved", path)


# ---------------- 树皮（竖向裂纹，PIL 噪声 + 各向异性模糊）----------------
def make_bark():
    S = 512
    import random as _r
    _r.seed(11)
    img = Image.new("L", (S, S))
    px = img.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = _r.randint(0, 255)
    img = img.filter(ImageFilter.GaussianBlur((0.8, 7)))
    img = img.filter(ImageFilter.GaussianBlur((1.0, 4)))
    img = ImageOps.autocontrast(img, cutoff=2)          # 提对比
    d = ImageDraw.Draw(img)
    for _ in range(18):
        x = _r.randint(0, S - 1)
        y0 = _r.randint(0, S - 1)
        for i in range(_r.randint(4, 10)):
            yy = (y0 + i * _r.randint(6, 14)) % S
            d.line([(x - 2, yy), (x + 2, yy)], fill=18, width=_r.randint(1, 3))
    lut = []
    for i in range(256):
        t = i / 255
        # 更亮、脊/沟对比更强：沟槽深棕 -> 脊红棕
        lut.append((int((0.13 + 0.30 * t) * 255),
                    int((0.085 + 0.21 * t) * 255),
                    int((0.045 + 0.11 * t) * 255)))
    rgb = img.convert("RGB")
    rp = rgb.load()
    for y in range(S):
        for x in range(S):
            rp[x, y] = lut[px[x, y]]
    rgb.save(os.path.join(OUT, "bark.png"))
    img.save(os.path.join(OUT, "bark_bump.png"))
    print("saved bark.png")


# ---------------- 全方位针叶簇（卡片随机朝向也能读成树冠）----------------
def make_foliage_tuft():
    S = 512 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S / 2, S / 2
    greens = [(0x17, 0x38, 0x17, 255), (0x20, 0x44, 0x1f, 255), (0x2c, 0x56, 0x28, 255)]
    # 外层长针叶，全方位放射
    for i in range(40):
        ang = 2 * math.pi * i / 40 + random.uniform(-0.05, 0.05)
        length = S * (0.30 + 0.10 * random.random())
        bw = S * (0.014 + 0.004 * random.random())
        draw_needle(d, cx, cy, length, ang, bw, bw * 0.15, greens[0], droop=-0.02)
    for i in range(40):
        ang = 2 * math.pi * i / 40 + random.uniform(-0.05, 0.05)
        length = S * (0.26 + 0.09 * random.random())
        bw = S * (0.014 + 0.004 * random.random())
        draw_needle(d, cx, cy, length, ang, bw, bw * 0.15, greens[1 + i % 2], droop=-0.02)
    # 内层短针叶填实
    for i in range(40):
        ang = 2 * math.pi * i / 40 + random.uniform(-0.05, 0.05)
        length = S * (0.14 + 0.06 * random.random())
        bw = S * (0.015 + 0.003 * random.random())
        draw_needle(d, cx, cy, length, ang, bw, bw * 0.15, greens[2], droop=-0.02)
    img = img.resize((512, 512), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(0.8))
    img.putalpha(a)
    path = os.path.join(OUT, "foliage_tuft.png")
    img.save(path)
    print("saved foliage_tuft.png")


if __name__ == "__main__":
    make_needle_bundle()
    make_grass_tuft()
    make_petal()
    make_flower_center()
    make_leaf()
    make_bark()
    make_foliage_tuft()
    print("ALL DONE ->", OUT)
