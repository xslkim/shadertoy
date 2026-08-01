"""参数网格渲染，用于快速收敛到接近参考的外观。"""
import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pine_gen import PineParams, generate
from softrender import Mesh, render, save_png, hstack_labeled
from preview_pine import reference_mesh

OUT = "exports"
os.makedirs(OUT, exist_ok=True)

# 每个变体: (标签, 参数覆盖 dict)
BASE = dict(card_fold=34.0, card_len=0.56, card_wing=0.32,
            branch_droop=30.0, branch_droop_tip=10.0,
            crown_radius=1.42, whorl_start=0.20, cards_base=5.6,
            card_roll_jitter=45.0, card_span_start=0.12, card_pitch=0.35)

VARIANTS = [
    ("F 上一轮最佳", BASE),
    ("H F+下部更宽", dict(BASE, crown_taper=0.70, crown_radius=1.50)),
    ("I H+更不规则", dict(BASE, crown_taper=0.70, crown_radius=1.50,
                           card_size_jitter=0.42, whorl_jitter=0.05)),
    ("J I+卡片更大", dict(BASE, crown_taper=0.70, crown_radius=1.50,
                           card_size_jitter=0.42, whorl_jitter=0.05,
                           card_len=0.62, card_wing=0.35)),
]


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    imgs, labels = [], []

    ref = reference_mesh(0)
    imgs.append(render([ref], width=460, height=660, azimuth=35, elevation=6))
    labels.append("REFERENCE 2076 tris")

    for name, over in VARIANTS:
        p = replace(PineParams(seed=seed), **over)
        m = generate(p, 0)
        st = m.stats()
        mesh = Mesh(np.array(m.pos), m.polys, m.mat_ids)
        imgs.append(render([mesh], width=460, height=660, azimuth=35, elevation=6))
        labels.append(f"{name}  {st['tris']} tris  {st['leaf_polys']//2} cards")
        print(name, st)

    save_png(hstack_labeled(imgs, labels), os.path.join(OUT, "tune_grid.png"))
    print("已输出", os.path.join(OUT, "tune_grid.png"))


if __name__ == "__main__":
    main()
