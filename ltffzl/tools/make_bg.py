"""Generate a night-city bokeh background for the Heartfelt rain shader.

Outputs:
  bg.png  - reference image
  bg.raw  - 8-byte header (int32 w, int32 h, little-endian) + RGB24 data

The rain shader samples this through mip-blur, so lots of colorful out-of-focus
city lights (bokeh) read best. Everything is accumulated in normalized HDR
[0..inf) then Reinhard tone-mapped + gamma so the lights stay bright & vivid.
"""
import os
import struct
import random

import numpy as np
from PIL import Image

W = H = 1024
random.seed(11)
np.random.seed(11)

# --- base vertical gradient: deep night sky -> warm ground glow (normalized) ---
img = np.zeros((H, W, 3), dtype=np.float32)
top = np.array([0.015, 0.025, 0.06], dtype=np.float32)
bottom = np.array([0.10, 0.06, 0.05], dtype=np.float32)
for y in range(H):
    f = y / (H - 1)
    img[y, :, :] = top * (1 - f) + bottom * f

yy, xx = np.mgrid[0:H, 0:W]

palette = [
    (1.00, 0.66, 0.28),   # warm street light / sodium
    (1.00, 0.45, 0.22),   # amber
    (1.00, 0.20, 0.20),   # traffic red
    (0.35, 0.66, 1.00),   # cool blue
    (0.40, 1.00, 0.85),   # cyan/teal
    (1.00, 0.35, 0.80),   # neon magenta
    (1.00, 0.92, 0.70),   # warm white
]

def add_bokeh(cx, cy, r, color, intensity):
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    core = np.clip(1.0 - d2 / (r * r), 0.0, 1.0)
    disc = np.power(core, 0.55) * intensity          # bright flat-ish core, soft edge
    for c in range(3):
        img[:, :, c] += disc * color[c]

# --- distant building silhouettes with lit windows (lower part) ---
ground = int(H * 0.64)
x = 0
while x < W:
    bw = random.randint(45, 130)
    bh = random.randint(int(H * 0.14), int(H * 0.36))
    bx0, bx1 = x, min(W, x + bw)
    by0 = ground - bh
    img[by0:ground, bx0:bx1, :] *= 0.5               # darker building mass
    wy = by0 + 7
    while wy < ground - 6:
        wx = bx0 + 6
        while wx < bx1 - 5:
            if random.random() < 0.5:
                warm = np.array([1.0, 0.78, 0.45], dtype=np.float32)
                cool = np.array([0.55, 0.75, 1.0], dtype=np.float32)
                col = warm if random.random() < 0.72 else cool
                col = col * random.uniform(0.5, 1.6)
                img[wy:wy + 4, wx:wx + 3, :] += col
            wx += 8
        wy += 10
    x += bw + random.randint(3, 18)

# --- bokeh discs (out-of-focus city lights), additive HDR ---
for _ in range(80):                                  # big
    cx = random.uniform(0, W)
    cy = random.uniform(H * 0.22, H * 0.98)
    add_bokeh(cx, cy, random.uniform(28, 85),
              np.array(random.choice(palette), np.float32), random.uniform(0.6, 1.6))

for _ in range(360):                                 # small sharp points
    cx = random.uniform(0, W)
    cy = random.uniform(H * 0.28, H)
    add_bokeh(cx, cy, random.uniform(4, 14),
              np.array(random.choice(palette), np.float32), random.uniform(1.2, 3.0))

for _ in range(9):                                   # large soft atmosphere glows
    cx = random.uniform(0, W)
    cy = random.uniform(H * 0.4, H)
    add_bokeh(cx, cy, random.uniform(150, 280),
              np.array(random.choice(palette), np.float32), random.uniform(0.12, 0.28))

# --- Reinhard tone map (normalized HDR) + gamma ---
img = img / (1.0 + img)
img = np.power(np.clip(img, 0, 1), 1.0 / 2.2)
img = np.clip(img * 255.0, 0, 255).astype(np.uint8)

out_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
png_path = os.path.join(out_dir, "bg.png")
raw_path = os.path.join(out_dir, "bg.raw")

Image.fromarray(img, "RGB").save(png_path)
with open(raw_path, "wb") as f:
    f.write(struct.pack("<ii", W, H))
    f.write(img.tobytes())

print("wrote", png_path, "and", raw_path, img.shape)
