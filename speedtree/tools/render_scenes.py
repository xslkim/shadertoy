"""
出图脚本：用 render_hq 渲染生成的松树。

    python tools/render_scenes.py hero      单棵英雄图
    python tools/render_scenes.py compare   参考 vs 生成（同贴图同光照）
    python tools/render_scenes.py lods      三级 LOD
    python tools/render_scenes.py forest    小树林
    python tools/render_scenes.py turntable 多角度
    python tools/render_scenes.py wind      顶点色驱动的风动画 mp4
    python tools/render_scenes.py all
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_hq as R
from pine_gen import PineParams, generate, generate_lods
from inspect_fbx import parse
from analyze_tree_fbx import unpack_geometry

OUT = "exports"
TEX = os.path.join(OUT, "textures")
os.makedirs(OUT, exist_ok=True)

BARK, LEAF, GROUND = 0, 1, 2


def materials():
    return [
        R.Material(R.load_texture(os.path.join(TEX, "bark_pine.png")),
                   color=(1.0, 0.95, 0.88), spec=0.03),
        R.Material(R.load_texture(os.path.join(TEX, "needle_card.png")),
                   two_sided=True, alpha_cutout=True, cutoff=0.45,
                   translucency=0.55, spec=0.015),
        R.Material(R.load_texture(os.path.join(TEX, "ground.png")), spec=0.0),
    ]


def tree(seed=3, lod=0):
    return R.from_tree_mesh(generate(PineParams(seed=seed), lod))


def reference_draw(lod=0):
    """参考资产：叶卡 UV 布局与生成器一致，可以套同一张针叶贴图。"""
    root, _ = parse("mesh/IL3DN_Tree_Pine_01_OneMesh.FBX")
    geo = root.first("Objects").find("Geometry")[lod]
    P, polys, mats, uvs, uv_idx, cols, col_idx = unpack_geometry(geo)

    v = np.array(P)
    v[:, 0] -= (v[:, 0].min() + v[:, 0].max()) / 2
    v[:, 1] -= (v[:, 1].min() + v[:, 1].max()) / 2
    v[:, 2] -= v[:, 2].min()
    v *= 2.54 / 100.0

    uv_list, nrm_list = [], []
    pv = 0
    for poly in polys:
        # 参考资产的法线是 ByPolygonVertex，这里直接用面法线，足够看形
        a, b, c = v[poly[0]], v[poly[1]], v[poly[2]]
        n = np.cross(b - a, c - a)
        n /= np.linalg.norm(n) or 1.0
        for _ in poly:
            i = uv_idx[pv] if uv_idx else pv
            uv_list.append((uvs[i * 2], uvs[i * 2 + 1]))
            nrm_list.append(tuple(n))
            pv += 1
    return R.from_polys(v, polys, mats, uv_list, nrm_list)


def scene(meshes, ground_size=120.0, repeat=70.0):
    return list(meshes) + [R.ground_mesh(size=ground_size, mat=GROUND, repeat=repeat, div=24)]


LOOK = dict(ss=2, azimuth=38, elevation=7, target=(0, 0, 2.5), radius=3.1,
            fog=0.0028, exposure=1.5, shadow_strength=0.30)


def bounds(meshes, pad=0.6):
    """主体包围盒，用来收紧阴影贴图的正交范围（不含地面）。"""
    v = np.vstack([m.pos for m in meshes])
    lo, hi = v.min(0) - pad, v.max(0) + pad
    lo[2] = min(lo[2], -0.05)
    return lo, hi


# --------------------------------------------------------------------------
def do_hero():
    m = materials()
    t = tree(3)
    img = R.render(scene([t]), m, width=880, height=1150, shadow_res=1400,
                   shadow_bounds=bounds([t]), **LOOK)
    print("->", R.save_png(img, os.path.join(OUT, "hq_hero.png")))


def do_compare():
    m = materials()
    imgs, labs = [], []
    ref = reference_draw(0)
    gen = tree(3)
    for mesh, lab in ((ref, f"参考 IL3DN_Tree_Pine_01  LOD0  {len(ref.tris)} tris"),
                      (gen, f"程序化生成 seed=3  LOD0  {len(gen.tris)} tris")):
        imgs.append(R.render(scene([mesh]), m, width=620, height=880, shadow_res=1200,
                             shadow_bounds=bounds([mesh]), **LOOK))
        labs.append(lab)
    print("->", R.save_png(R.label_grid(imgs, labs), os.path.join(OUT, "hq_compare.png")))


def do_lods():
    m = materials()
    imgs, labs = [], []
    for i, lm in enumerate(generate_lods(PineParams(seed=3))):
        st = lm.stats()
        dm = R.from_tree_mesh(lm)
        imgs.append(R.render(scene([dm]), m, width=520, height=760, shadow_res=1100,
                             shadow_bounds=bounds([dm]), **LOOK))
        labs.append(f"LOD{i}   {st['tris']} 三角面   "
                    f"树皮 {st['bark_polys']} / 叶卡 {st['leaf_polys'] // 2} 张")
    print("->", R.save_png(R.label_grid(imgs, labs), os.path.join(OUT, "hq_lods.png")))


def do_forest():
    """一次生成 18 棵各不相同的树摆成小树林：同一套参数，只换 seed 和缩放。"""
    m = materials()
    rng = np.random.default_rng(12)
    cache = {}
    meshes = []
    layout = [
        (-5.2, -3.0, 1.05), (4.6, -1.6, 0.98), (-1.6, 1.4, 1.12),
        (7.4, 3.0, 0.86), (-7.8, 4.2, 0.92), (1.9, 5.4, 1.00),
        (-3.6, 7.0, 0.80), (6.2, 8.2, 0.90), (-9.0, 9.6, 0.74),
        (0.6, 10.4, 0.84), (9.6, 11.2, 0.78), (-5.4, 12.8, 0.70),
        (3.8, 14.0, 0.76), (-10.5, 15.5, 0.68), (8.2, 17.0, 0.72),
        (-2.0, 18.2, 0.66), (12.0, 20.0, 0.70), (-7.0, 21.5, 0.64),
    ]
    for k, (x, y, s) in enumerate(layout):
        sd = 3 + k * 7
        if sd not in cache:
            cache[sd] = R.from_tree_mesh(generate(PineParams(seed=sd), 0))
        meshes.append(R.transform(cache[sd], translate=(x, y, 0),
                                  rot_z=rng.uniform(0, 6.28),
                                  scale=s * rng.uniform(0.92, 1.08)))
    img = R.render(scene(meshes), m, width=1500, height=860, ss=2,
                   azimuth=-90, elevation=1.5, fov=46, target=(0, 4.5, 3.0),
                   radius=6.4, shadow_res=2000, fog=0.006, exposure=1.5,
                   shadow_strength=0.28, shadow_bounds=bounds(meshes, pad=1.0))
    print("->", R.save_png(img, os.path.join(OUT, "hq_forest.png")))


def do_turntable():
    m = materials()
    imgs, labs = [], []
    for k, sd in enumerate((3, 7, 11, 19, 23, 31)):
        t = tree(sd)
        look = dict(LOOK, azimuth=25 + k * 13)
        imgs.append(R.render(scene([t]), m, width=430, height=640, shadow_res=1000,
                             shadow_bounds=bounds([t]), **look))
        labs.append(f"seed={sd}   {len(t.tris)} 三角面")
    print("->", R.save_png(R.label_grid(imgs, labs, cols=6),
                           os.path.join(OUT, "hq_variants.png")))


def do_wind(frames=40, fps=20, amplitude=0.48, flutter=0.085):
    """顶点色驱动的风摆：A 通道控制弯曲权重，G 通道给每张叶卡独立抖动相位。
    输出 mp4 + gif，外加一张关键帧对比图。"""
    import imageio.v2 as imageio

    m = materials()
    base = R.from_tree_mesh(generate(PineParams(seed=3), 0))
    gm = R.ground_mesh(size=120.0, mat=GROUND, repeat=70.0, div=24)
    sb = bounds([base], pad=1.2 + amplitude)

    look = dict(LOOK, azimuth=20)
    shots = []
    for f in range(frames):
        # freq=1.15，跑满 1/1.15 秒的整数倍才能首尾无缝
        t = f / frames * (2.0 / 1.15)
        wm = R.apply_wind(base, t, amplitude=amplitude, flutter=flutter)
        img = R.render([wm, gm], m, width=560, height=760,
                       shadow_res=900, shadow_bounds=sb, **look)
        shots.append(img)
        print(f"  帧 {f + 1}/{frames}", flush=True)

    mp4 = os.path.join(OUT, "hq_wind.mp4")
    w = imageio.get_writer(mp4, fps=fps, quality=8, macro_block_size=1)
    for img in shots:
        w.append_data(img)
    w.close()
    print("->", mp4)

    gif = os.path.join(OUT, "hq_wind.gif")
    imageio.mimsave(gif, shots[::2], duration=1000 / fps * 2, loop=0)
    print("->", gif)

    # 取四分之一相位处的帧：整数分之一处正好落在摆动的过零点上，看不出差别
    k = [frames // 8, frames * 3 // 8, frames * 5 // 8, frames * 7 // 8]
    labs = []
    for i in k:
        t = i / frames * (2.0 / 1.15)
        wm = R.apply_wind(base, t, amplitude=amplitude, flutter=flutter)
        tip = wm.pos[:, 2].argmax()
        dx = wm.pos[tip, 0] - base.pos[tip, 0]
        labs.append(f"t = {t:.2f}s    树梢横向偏移 {dx:+.2f} m")
    sheet = R.label_grid([shots[i] for i in k], labs, cols=4)
    print("->", R.save_png(sheet, os.path.join(OUT, "hq_wind_sheet.png")))


SCENES = dict(hero=do_hero, compare=do_compare, lods=do_lods, forest=do_forest,
              variants=do_turntable, wind=do_wind)

if __name__ == "__main__":
    which = sys.argv[1:] or ["hero"]
    if which == ["all"]:
        which = ["hero", "compare", "lods", "variants", "forest", "wind"]
    for k in which:
        print("=== 渲染", k, "===")
        SCENES[k]()
