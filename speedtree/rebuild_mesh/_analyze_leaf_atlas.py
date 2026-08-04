# -*- coding: utf-8 -*-
"""分析叶贴图 alpha 通道，输出各连通域的 UV 矩形。用法: py -3 _analyze_leaf_atlas.py [图片路径]"""
import sys

import numpy as np
from PIL import Image

TEX = sys.argv[1] if len(sys.argv) > 1 else \
    r"d:\shadertoy\speedtree\mesh\IL3DN_Tree_Beech_02\IL3DN_Leaf_01.png"
img = np.array(Image.open(TEX).convert("RGBA"))
h, w = img.shape[:2]
alpha = img[..., 3]
print("size:", w, "x", h, " alpha>128 占比: %.3f" % (np.mean(alpha > 128)))

mask = alpha > 128
# 连通域标记（优先 scipy，其次 cv2，都没有则简易 BFS）
labels, n = None, 0
try:
    from scipy import ndimage
    labels, n = ndimage.label(mask)
except ImportError:
    try:
        import cv2
        n, labels = cv2.connectedComponents(mask.astype("uint8"))
        n -= 1
    except ImportError:
        pass

rects = []
if labels is not None:
    for i in range(1, n + 1):
        ys, xs = np.where(labels == i)
        if len(xs) < 800:          # 忽略过小碎块
            continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        # 像素 -> UV（origin 左下），向内收缩 1.5% 防串色
        u0, u1 = x0 / w, (x1 + 1) / w
        v0, v1 = 1.0 - (y1 + 1) / h, 1.0 - y0 / h
        du, dv = (u1 - u0) * 0.015, (v1 - v0) * 0.015
        rects.append((u0 + du, v0 + dv, u1 - du, v1 - dv, len(xs)))
else:
    # 简易 BFS（半分辨率加速）
    small = mask[::2, ::2]
    H, W = small.shape
    seen = np.zeros_like(small, bool)
    from collections import deque
    for sy in range(H):
        for sx in range(W):
            if small[sy, sx] and not seen[sy, sx]:
                q = deque([(sy, sx)])
                seen[sy, sx] = True
                xs, ys = [], []
                while q:
                    y, x = q.popleft()
                    xs.append(x)
                    ys.append(y)
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and small[ny, nx] \
                                and not seen[ny, nx]:
                            seen[ny, nx] = True
                            q.append((ny, nx))
                if len(xs) < 200:
                    continue
                x0, x1, y0, y1 = min(xs) * 2, max(xs) * 2, min(ys) * 2, max(ys) * 2
                u0, u1 = x0 / w, (x1 + 1) / w
                v0, v1 = 1.0 - (y1 + 1) / h, 1.0 - y0 / h
                rects.append((u0, v0, u1, v1, len(xs) * 4))

rects.sort(key=lambda r: -r[4])
print("叶团数量(>阈值):", len(rects))
print("LEAF_UV_RECTS = [")
for u0, v0, u1, v1, area in rects:
    print("    (%.3f, %.3f, %.3f, %.3f),   # area=%d" %
          (u0, v0, u1, v1, area))
print("]")
