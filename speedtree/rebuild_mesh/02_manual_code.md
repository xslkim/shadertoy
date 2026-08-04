# 手写代码程序化建模：风格化树木自动生成调研报告

> 目标：不依赖任何 DCC 软件，纯代码生成 IL3DN_Tree_Beech_02 类型的风格化阔叶树——
> 细长主干、下部少量光秃分枝、树冠由大量叶卡片（quad）簇组成、双色调绿、alpha cutout。
> 同目录附带可运行原型 `procedural_tree.py`（纯 Python + numpy，输出 OBJ+MTL）。

## 0. 参考资产实测结论

对 `mesh/IL3DN_Tree_Beech_02/` 的贴图与截图做了实测分析，直接决定算法设计：

| 实测项 | 结论 | 对算法的影响 |
|---|---|---|
| `screenshot-1/2.png` | 单根细长深棕树干，约 45% 高度以下光秃（带 2~3 根短枯枝），树冠为若干云状叶团 | 骨架需支持"下部裸露 + 顶部爆冠"拓扑 |
| `IL3DN_Leaf_01.png`（RGBA 1024²） | **RGB 通道纯白**，叶团形状全部存在 alpha 通道（不透明像素约占 31%，全图散布几十团叶形） | 叶色必须来自**顶点色 / 材质染色**，不能用贴图本色；一张 quad 整幅映射即可得到"一簇叶团" |
| `IL3DN_Bark_Pine.png` | 灰白树皮纹理 | 树皮颜色靠材质 Kd 染成深棕 |
| 项目历史 | `tools/pine_gen.py` + `tools/fbx_writer.py` 曾纯 Python 复现 IL3DN 松树（4 级 LOD、FBX 导出、面数校验通过） | 证明"纯 Python 生成"路线在本项目可行，本报告阔叶树方案沿用同一思路 |

## 1. 技术选型对比

| 方案 | 链路 | 依赖 | 优点 | 缺点 | 适用阶段 |
|---|---|---|---|---|---|
| A. 纯 Python → OBJ/glTF | 算法直接写网格文件 | trimesh / pygltflib（OBJ 可零依赖手写） | 迭代最快、零 DCC、易 diff、种子可复现 | OBJ 顶点色是非标扩展、Unity 不原生导入 OBJ；需二次转换 | **算法原型/参数调优** |
| B. 纯 Python → FBX | Python 生成后自写 FBX（参考 `tools/fbx_writer.py`）或经 FBX2glTF / Blender headless 转换 | 自写 writer 或转换器 | Unity 原生导入、保留顶点色/LOD | 转换链多一环，调试成本高 | 批量产出的中间方案 |
| C. Unity C# Editor 脚本直接生成 Mesh | 算法移植为 C#，`new Mesh()` + `AssetDatabase` | Unity 本体 | 无转换损耗；顶点色、subMesh（树皮/叶双材质）、LODGroup、风数据（额外 UV 通道）全部直写；可运行时/编辑器内生成变体 | 算法需移植一遍；预览要在 Unity 里看 | **量产/最终落地（目标运行时是 Unity，推荐）** |
| D. Blender headless Python | `blender -b -P script.py` 用 bpy 建模导出 | Blender 安装 | 有成熟网格 API、可直接渲染校验 | 仍是外部 DCC 依赖，部署重 | 需要高质量离线渲染校验时 |
| E. Houdini / SpeedTree | 商业 DCC 程序化建模 | 商业软件 | 功能最强 | 违反"不依赖 DCC"约束 | 不考虑 |

**推荐组合：A（现在，本报告原型）→ C（落地 Unity 时移植同一套算法）。**
理由：算法与数据结构与出口格式无关（骨架→管状扫掠→卡片摆放，输出无非是顶点/面/UV/顶点色数组），先用 Python 把参数表和风格调到位，落地时把 `generate()` 平移成 C# 即可；若希望留在 Python 管线，则走 B（glTF 优先于 FBX，见第 5 节）。

## 2. 算法设计

### 2.1 树干骨架：三种候选算法对比

| 算法 | 原理 | 拓扑可控性 | 参数直觉性 | 适合形态 | 结论 |
|---|---|---|---|---|---|
| **递归分枝**（Weber-Penn 风格） | 每根枝条在节点上按概率派生子枝，长度/半径按比例衰减，递归到深度上限 | 高：主干 = depth 0 特例，可直接规定"第几节以下不准长叶枝" | 高：树高、冠幅、分枝角、衰减率直接对应美术语言 | 单主干 + 清晰层级的树 | **采用** |
| L-system | 字符串改写 + 龟解释 | 中：改写法擅长重复自相似结构，对"一根干净主干 + 一团冠"反而要绕弯 | 低：产生式规则不直观 | 蕨类、灌木、规则分形 | 不采用 |
| 空间殖民（space colonization） | 树冠包络内撒吸引点，枝干朝点竞争生长 | 中低：自然舒展但中间分叉多，主干不够"干净细长"，枯枝形态不可控 | 中：吸引点分布即冠形，但细节（枯枝、裸干比例）难指定 | 自然形态的皇冠形大树 | 不采用（可作为后续扩展：用吸引点决定叶簇位置） |

**选择递归分枝的关键原因**：目标拓扑是"主干为绝对主角、分枝只是冠内填充"，递归分枝把主干写成 depth=0 的特例，用 `crown_start` 一个参数就能切开"下部光秃 / 上部生枝"，再单独补 `dead_branches` 根短枯枝还原截图中的细节——这正是 L-system 和空间殖民都不直觉的地方。

### 2.2 骨架生成伪代码

```
build_skeleton(params, rng):
    # 1) 主干：垂直折线 + 平滑随机弯曲，半径线性 taper
    trunk = spine(从(0,0,0)到(0,H,0), 偏移 = 随机游走 * trunk_lean)
    trunk.radii = trunk_radius * (1 - trunk_taper * h/H)

    # 2) 树冠 scaffold 分枝：主干 crown_start*H 以上的节点中取 scaffold_count 个
    for node in sample(主干上高于 crown_start 的节点, scaffold_count):
        grow(起点=node, 方向=主干方向偏转 branch_angle, depth=1)

    # 3) 下部光秃短枝：crown_start 以下节点随机生 dead_branches 根短枝（leafy=False）

grow(origin, dir, length, radius, depth):
    spine = 折线(方向每步抖动 wiggle + 轻微向上偏向)      # 自然弯曲
    if depth >= max_depth: 标记 leafy; return
    for 每个节点 i（跳过根部）:
        if rng() < branch_child_prob 或 i 是末端:
            生 1~2 根子枝: 方向 = 父方向绕随机垂直轴偏转 branch_angle±jitter
                          长度 = 父剩余长度 * branch_length_ratio ± jitter
                          半径 = 父半径 * branch_radius_ratio
    if 没生出任何子枝: 标记 leafy                          # 末端细枝也长叶
```

### 2.3 树干网格：低段数变径圆柱扫掠

- 每根枝条沿 spine 折线扫掠：每个节点由方向构造正交基，按 `radii[i]` 放样圆环，相邻环连成四边形条带。
- **圆周段数刻意压低**（主干 7、枝条 5）——低段数带来的棱角正是风格化/低多边形语言的一部分。
- 主干根部半径 → 顶部按 `trunk_taper` 线性收细；枝条末端半径压到 35%。
- **平面化着色**：面与面不共享顶点（或等价地每面写法线），渲染出来即硬边面片，无需平滑法线。
- 树皮 UV：`u = 圆周角度比例`，`v = 累计弧长 / 周长`——按真实比例平铺，粗细不同的枝干 texel 密度一致。

### 2.4 叶卡片簇

```
add_leaves():
    for 每根 leafy 细枝:
        若末端在树冠椭球包络内: 末端放 1 簇; 末段中点 50% 概率再放 1 簇
    for i in extra_clusters:                                  # 填充簇补空洞
        在椭球壳层(半径 0.55~0.95 倍包络)随机撒点放簇

_add_cluster(center):
    accent = rng() < accent_prob                              # 整簇提亮?
    for cards_per_cluster 张卡片:
        c = center + 随机偏移(半径 cluster_radius, Y 压扁 0.75)   # 扁团块
        _add_card(c, 颜色 = 双色调插值(c))

_add_card(center, color):
    size = card_size * (1 ± card_size_jitter)
    朝向 d = 随机单位向量(略偏上) ; 绕 d 随机 roll
    quad = center ± side*size/2 ± up*size/2
    UV = (0,0)-(1,1)                                          # 整幅映射叶贴图
    顶点色: 上两顶点 = color, 下两顶点 = color * 0.72            # 卡片内明暗
```

**双色调绿的实现**（关键，源于贴图实测）：叶贴图 RGB 为纯白，颜色全部来自顶点色——

```
t = 0.25 + 0.55 * (卡片高度在冠内的相对位置) + 随机抖动(±0.18)
color = lerp(color_dark, color_light, clamp(t))              # 下深上浅
accent 簇: t = 0.80~1.00                                     # 高光团块
```

三个层次叠加出截图效果：① 树冠底部/内部深绿、顶部/外侧浅绿的垂直渐变；② `accent_prob` 概率整簇浅绿，模拟受光的云状团块亮面；③ 单卡内上亮下暗。着色用 unlit/顶点色 shader 即平面化卡通感。

**朝向策略**：簇内随机法向 + 随机 roll（略偏上 +0.35 让冠顶更"蓬松"）。静态烘焙即够；若要运行时 billboard 可在 C# 版里改成 shader 面向相机，离线则不必。

### 2.5 UV 与材质

| 部件 | 贴图 | UV | 颜色来源 | alpha |
|---|---|---|---|---|
| 叶卡片 | `IL3DN_Leaf_01.png` | quad 整幅 (0,0)-(1,1)，一张卡 = 一团叶簇 | 顶点色双色调绿（Kd 保持白色） | 贴图 alpha 通道 → cutout（OBJ 用 `map_d`，Unity 用 Cutout shader） |
| 树干/枝 | `IL3DN_Bark_Pine.png` | 圆柱映射，v 按弧长/周长平铺 | MTL `Kd` 深棕（0.23, 0.16, 0.13）染灰白纹理 | 无 |

### 2.6 整体流程图

```
参数表 TreeParams + seed
        │
        ▼
递归分枝骨架（主干 / scaffold 枝 / 枯枝）   ← 树冠椭球包络约束
        │
        ├───────────────┬────────────────┐
        ▼               ▼                ▼
  变径圆柱扫掠      末端细枝 → 叶簇    包络壳层 → 填充叶簇
  (bark 材质)       (leaf 材质)        (leaf 材质)
        │               │                │
        └───────┬───────┴────────────────┘
                ▼
   顶点数组(位置/UV/顶点色/面法线) + 材质分组
                ▼
        OBJ+MTL（原型）/ glTF / Unity Mesh
```

## 3. 风格统一手段

1. **参数表即风格**：同一套 `TreeParams` 生成任意多种子，形状各异但风格一致；要换一种风格（如更矮胖的树）就另存一份参数表，而不是改代码。
2. **单随机流可复现**：全程一个 `random.Random(seed)`，同种子字节级复现，便于回归对比与"挑到好树就固定种子"。
3. **固定调色板**：全树绿色都从 `color_dark ↔ color_light` 两色插值，树干统一 `bark_color`——色板即风格锚点，不会出现第三种绿。
4. **同一套贴图**：所有树共用 `IL3DN_Leaf_01.png` / `IL3DN_Bark_Pine.png`，几何上只改 UV 与顶点色，贴图零新增。
5. **统一几何语言**：圆周段数（7/5）、卡片与冠幅比例（card_size ≈ crown_radius/2）、分枝角范围固定，低多边形密度全树一致。
6. **批量筛选闭环**：批量生成 N 个种子 → 软渲染缩略图（本项目 `tools/softrender.py` 零依赖可用）→ 人工/自动挑出最优种子入库。

## 4. 泛化参数表

原型 `TreeParams` 全参数（默认值即本报告样例）：

| 分组 | 参数 | 默认 | 含义 / 调大效果 |
|---|---|---|---|
| 整体 | `seed` | 7 | 随机种子，同参数下同种子完全复现 |
| | `height` | 6.0 | 树高 (m) |
| | `crown_start` | 0.45 | 树冠起始相对高度，越大裸露主干越长 |
| | `crown_radius` / `crown_height` | 2.1 / 3.2 | 树冠椭球包络，控制冠幅与冠形（圆/椭） |
| 主干 | `trunk_radius` / `trunk_taper` | 0.09 / 0.60 | 根部半径 / 收细比例 |
| | `trunk_lean` | 0.25 | 主干弯曲幅度，越大越"S"形 |
| | `trunk_sides` | 7 | 圆周段数（风格化棱角） |
| 分枝 | `scaffold_count` | 6 | 冠内一级分枝数，越多冠内枝干越密 |
| | `branch_angle` ± `jitter` | 50°±18° | 子枝张开角，大=横向舒展，小=收拢向上 |
| | `branch_length_ratio` | 0.60 | 子枝/父枝长度比 |
| | `branch_child_prob` / `max_depth` | 0.85 / 3 | 分枝密度 / 细碎程度 |
| | `dead_branches` | 3 | 下部光秃短枝数（截图特征细节） |
| 叶簇 | `cards_per_cluster` | 7 | 叶密度主参数 |
| | `cluster_radius` / `card_size` | 0.55 / 1.05 | 簇大小 / 卡片大小（≈冠幅一半最像参考） |
| | `extra_clusters` | 22 | 填充簇数，补细枝没长到的空洞 |
| 配色 | `color_dark` / `color_light` | (0.16,0.33,0.13) / (0.48,0.68,0.25) | 双色调绿两端 |
| | `accent_prob` | 0.22 | 高光簇比例 |
| | `bark_color` | (0.23,0.16,0.13) | 树皮染色 |

泛化方式：换 `seed` → 同风格不同形状；调参数表 → 不同风格（如 `crown_start` 0.2 + `crown_radius` 3.5 得矮胖阔冠树）；换配色两色 → 秋色/樱花树。

## 5. 输出格式与 Unity 导入链路

原型输出 OBJ+MTL（`sample_tree.obj`，含 `v x y z r g b` 顶点色、`usemtl bark/leaf` 双材质、贴图相对路径 `../mesh/IL3DN_Tree_Beech_02/*.png`）。OBJ 仅用于算法验证——Unity 不原生导入 OBJ，且 OBJ 顶点色是非标扩展。量产有两条链路：

**链路 A（推荐）：算法移植 Unity C# Editor 脚本**
`procedural_tree.py` 的 `generate()` 直接平移为 C#：同样的骨架/扫掠/卡片代码，输出改为 `Mesh.vertices / uv / colors / triangles`，bark 与 leaf 分两个 subMesh；`AssetDatabase.CreateAsset` 存为 prefab。顶点色、LODGroup、风动画数据（可写进 `uv2/uv3` 通道，参考 `tools/pine_gen.py` 的做法）全部无损，还能在编辑器内做种子滑动条实时预览变体。

**链路 B：留在 Python，走 glTF 2.0**
用 pygltflib 写 glTF：叶/皮分 primitive（天然多材质）、`COLOR_0` 顶点色、叶材质 `alphaMode: MASK` + `baseColorTexture`——glTF 是该需求的标准载体，Unity 经 glTFast 导入。需要 FBX 时可 FBX2glTF 或 Blender headless 转换，或复用本项目已验证的 `tools/fbx_writer.py` 直写 FBX。

**Unity 侧材质**：leaf = 顶点色 × cutout（Unlit/Graph：`Vertex Color * MainTex`，Alpha Clip）；bark = Standard/Unlit 深棕 tint × 树皮贴图。贴图直接复用参考资产两张 PNG。

## 6. 优缺点

**优点**
- 零 DCC 依赖，纯代码可进 CI，批量生成任意数量变体；
- 全参数化 + 种子可复现，风格统一性由参数表与色板强约束；
- 面数/LOD/顶点数据（风、AO、渐变）精确可控，本项目已有成功先例（松树生成器）；
- 与 Unity 落地链路短（算法平移 C# 或 glTF）。

**缺点**
- 美术微调不如 DCC 直观，必须配"生成→软渲染缩略图→挑种"的闭环（本项目已有 `tools/softrender.py` 可复用）；
- 递归分枝对极端形态（板根、藤蔓缠绕、破损树）表达力有限，需额外算法模块；
- OBJ 顶点色是非标扩展，跨查看器显示不一致，验证时需注意；
- 随机生成存在一定比例的"丑树"，量产需要筛选环节。

## 7. 原型验证

`procedural_tree.py` 已在本机（Python 3.12.10 + numpy 2.4.4）实际跑通：

```
python procedural_tree.py --seed 7
→ sample_tree.obj / sample_tree.mtl
→ stats: 2692 verts, 673 faces (1346 tris), bark 358 / leaf 315
```

并用项目既有零依赖软渲染器做了视觉校验（`sample_preview.png`）：细长深棕主干、中部短枯枝、顶部叶卡片簇树冠、上浅下深的双色调绿，形态与参考截图一致（软渲染未应用 alpha cutout，引擎内叠加叶贴图 alpha 后即为叶团效果）。另测 `--seed 12`、`--seed 42 --height 7 --cards 8` 均正常生成且形态各异，泛化有效。

## 8. 推荐程度

**★★★★☆（4/5）**

对本场景——风格化低模树、贴图复用、目标 Unity、明确不依赖 DCC——"手写代码程序化建模"是匹配度最高的路线：树的形态规则简单（主干+卡片簇），代码表达力绰绰有余，且风格统一与批量变体是 DCC 手工流难以做到的。扣一星在于缺少直观的美术迭代界面、极端形态需要扩展算法模块，以及量产需配筛选闭环。
