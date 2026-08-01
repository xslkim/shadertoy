"""
为程序化松树生成配套贴图。

叶片贴图针对 pine_gen 的 V 形卡片 UV 布局设计：
  v=0 是脊线（对折边），v=1 是翼的自由边，u 沿脊线方向。
  因此针叶从图像底边生根、向上扇形展开，两个翼共用同一块贴图。

输出到 exports/textures/：
  needle_card.png  RGBA 针叶簇（alpha 镂空）
  bark_pine.png    RGB  树皮
  ground.png       RGB  地面
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "exports", "textures")
os.makedirs(OUT, exist_ok=True)

SS = 3  # 超采样倍数


def _norm01(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo if hi > lo else 1.0)


def _tapered(cl, widths):
    left, right = [], []
    n = len(cl)
    for i in range(n):
        j = min(i + 1, n - 1)
        k = max(i - 1, 0)
        dx, dy = cl[j][0] - cl[k][0], cl[j][1] - cl[k][1]
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        w = widths[i]
        left.append((cl[i][0] + px * w / 2, cl[i][1] + py * w / 2))
        right.append((cl[i][0] - px * w / 2, cl[i][1] - py * w / 2))
    return left + list(reversed(right))


def _needle(d, x0, y0, length, angle, base_w, color, curve=0.0, steps=14):
    cl = []
    for i in range(steps + 1):
        t = i / steps
        a = angle + curve * t
        cl.append((x0 + math.cos(a) * length * t, y0 + math.sin(a) * length * t))
    widths = [base_w * (1 - 0.9 * (i / steps)) for i in range(steps + 1)]
    d.polygon(_tapered(cl, widths), fill=color)


def make_needle_card(seed=5):
    """针叶簇：从底边生根，向上扇形展开。"""
    S = 512 * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(seed)

    dark = (0x25, 0x4a, 0x20, 255)
    mid = (0x38, 0x68, 0x2b, 255)
    lite = (0x51, 0x88, 0x38, 255)
    tip = (0x71, 0xa8, 0x48, 255)

    root_y = S * 0.995

    def layer(n, lo, hi, color, wmul, spread):
        for i in range(n):
            f = (i + 0.5) / n
            x0 = S * (0.03 + 0.94 * f) + rng.uniform(-1, 1) * S * 0.012
            # 靠边的针叶更斜、中间的更竖，整体呈扇形
            ang = -math.pi / 2 + (f - 0.5) * spread + rng.uniform(-0.10, 0.10)
            ln = S * rng.uniform(lo, hi)
            _needle(d, x0, root_y, ln, ang, S * 0.011 * wmul, color,
                    curve=rng.uniform(-0.12, 0.12))

    layer(70, 0.55, 0.92, dark, 1.25, 1.55)
    layer(70, 0.42, 0.80, mid, 1.05, 1.45)
    layer(60, 0.30, 0.62, lite, 0.95, 1.30)
    layer(46, 0.16, 0.38, tip, 0.85, 1.10)
    # 根部加密，保证脊线附近不透光（否则对折处会漏出背景）
    layer(90, 0.06, 0.16, mid, 0.9, 2.10)

    img = img.resize((512, 512), Image.LANCZOS)
    a = img.split()[3].filter(ImageFilter.GaussianBlur(0.6))
    img.putalpha(a)
    path = os.path.join(OUT, "needle_card.png")
    img.save(path)
    print("saved", path)


def make_bark(seed=11):
    """树皮：竖向拉伸的噪声 + 裂纹。"""
    S = 512
    rng = np.random.default_rng(seed)
    n = rng.random((S, S)).astype(np.float32)
    img = Image.fromarray((n * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.GaussianBlur((1.0, 9)))
    img = img.filter(ImageFilter.GaussianBlur((1.6, 4)))
    a = _norm01(np.asarray(img, dtype=np.float32))

    xs = np.arange(S)
    for _ in range(26):
        x = rng.integers(0, S)
        w = rng.uniform(1.5, 5.0)
        depth = rng.uniform(0.25, 0.6)
        wob = np.sin(np.arange(S) / rng.uniform(18, 60) + rng.uniform(0, 6)) * rng.uniform(2, 9)
        for y in range(S):
            cx = (x + wob[y]) % S
            a[y] -= np.exp(-((xs - cx) ** 2) / (2 * w * w)) * depth
    a = np.clip(a, 0, 1) ** 0.85

    lo = np.array([0.185, 0.130, 0.088])
    hi = np.array([0.600, 0.445, 0.290])
    rgb = lo + (hi - lo) * a[..., None]
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(
        os.path.join(OUT, "bark_pine.png"))
    print("saved bark_pine.png")


def make_ground(seed=3):
    S = 512
    rng = np.random.default_rng(seed)
    n = rng.random((S, S)).astype(np.float32)
    a = _norm01(np.asarray(
        Image.fromarray((n * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2.5)),
        dtype=np.float32))
    n2 = rng.random((S, S)).astype(np.float32)
    b = np.asarray(
        Image.fromarray((n2 * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(0.8)),
        dtype=np.float32) / 255.0

    base = np.array([0.205, 0.240, 0.140])
    warm = np.array([0.370, 0.360, 0.205])
    rgb = base + (warm - base) * (0.55 * a + 0.45 * b)[..., None]
    Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(
        os.path.join(OUT, "ground.png"))
    print("saved ground.png")


if __name__ == "__main__":
    make_needle_card()
    make_bark()
    make_ground()
    print("贴图输出目录:", OUT)
