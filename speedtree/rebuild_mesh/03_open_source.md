# 开源程序化树生成方案调研报告

> 调研日期：2026-08-03
> 调研方式：网络调研（GitHub API / 官方文档 / 社区论坛 / 行业媒体）
> 目标：为"风格化低多边形卡通树（单细长树干 + 下部疏枝 + 叶卡片簇树冠 + 复用同一张 alpha 叶贴图 + 双色调平涂）"寻找可复用的开源生成算法库，产出物最终进入 Unity（FBX）。

---

## 0. 目标风格要点（对照参考截图）

参考资产 `mesh/IL3DN_Tree_Beech_02/`（FBX + `IL3DN_Bark_Pine.png` 树皮 + `IL3DN_Leaf_01.png` 叶子 + 两张渲染截图）体现的风格可拆成 4 个正交要素：

| # | 风格要素 | 属于哪一层 |
|---|---------|-----------|
| A | 单根细长树干、下部少量光秃分枝、整体轮廓为阔叶树 | 枝干几何生成算法 |
| B | 树冠由**大量叶卡片（quad）簇**组成，而非逐叶分布 | 叶片分布算法 |
| C | 所有树复用**同一张带 alpha 的叶子贴图**（IL3DN_Leaf_01.png） | UV/材质约定 |
| D | 绿色双色调、平面化（卡通）着色 | 着色器，与几何生成器无关 |

评估每个库时重点看：**A 的形状可控性、B 是否接近"卡片簇"、C 是否允许自带贴图、输出格式能否进 Unity、许可证是否允许商业项目使用、以及能否接入自动化（批量 seed → FBX）流水线**。

---

## 1. 候选库总览表

Stars 数据采集自 GitHub API（2026-08 快照）。

| 名称 | 链接 | 许可证 | Stars | 维护状态 |
|------|------|--------|-------|---------|
| MTree / Modular Tree | [github.com/MaximeHerpin/modular_tree](https://github.com/MaximeHerpin/modular_tree) | 插件部分 GPL-3.0，C++ 库部分 MIT | 1288 | **停更**（master 最后提交 2021-12-13，110+ 未结 issue；Blender 4.1+ 不可用） |
| tree-gen (Charlie Hewitt) | [github.com/friggog/tree-gen](https://github.com/friggog/tree-gen) | GPL-3.0（作者明示：生成的模型可自由使用，唯禁止直接作为资产出售） | 943 | 低活跃（最后推送 2025-07-11） |
| proctree.js (Paul Brunt) | [github.com/supereggbert/proctree.js](https://github.com/supereggbert/proctree.js) | BSD 3-Clause（源码头部声明） | 192 | **停更**（2017 最后提交） |
| proctree C++ 端口 (jarikomppa) | [github.com/jarikomppa/proctree](https://github.com/jarikomppa/proctree) | BSD 3-Clause（生成器本体） | 212 | **停更**（2015 最后提交） |
| Blender Sapling Tree Gen | [Blender 手册](https://docs.blender.org/manual/en/2.92/addons/add_curve/sapling.html) / [Extensions 平台](https://extensions.blender.org/) | GPL（Blender 官方扩展） | —（随 Blender 分发） | **官方维护**；4.2 起从内置 addon 迁移到 Extensions 平台 |
| mattatz/unity-procedural-tree | [github.com/mattatz/unity-procedural-tree](https://github.com/mattatz/unity-procedural-tree) | MIT | 427 | 停更（最后推送 2022-12-16） |
| Unity 其他 L-System 仓库 | [dilmerv/UnityLSystemEssentials](https://awesomeopensource.com/project/dilmerv/UnityLSystemEssentials)、[pboechat/LSystemsInUnity](https://awesomeopensource.com/project/pboechat/LSystemsInUnity)、[manuelpagliuca/l-system](https://git.codeproxy.net/manuelpagliuca/l-system)（MIT） | MIT 等 | 教学级小仓库 | 基本停更，质量为教程/课程作业级 |
| Unity 内置 Tree Creator | [Unity 6 官方文档](https://docs.unity3d.com/6000.7/Documentation/Manual/tree-FirstTree.html) | Unity 引擎内置功能（闭源） | — | 持续可用（Unity 6 文档仍在），但**无公开脚本 API** |
| Arbaro | [arbaro.sourceforge.net](http://arbaro.sourceforge.net/) / [SourceForge 项目](https://sourceforge.net/projects/arbaro/) | GPL（开源） | —（SourceForge 时代项目） | **停更**（1.9.x，约 2014 年后无实质更新） |
| ngPlant | [ngplant.org](http://ngplant.org/) / [SourceForge 项目](https://sourceforge.net/projects/ngplant/) | 建模工具 GPL，核心库（libngpcore 等）BSD | — | **停更**（最后更新 2016-07-15） |
| The Grove 3D | [thegrove3d.com](https://www.thegrove3d.com/buy/) | **商业软件**（Starter €99 / Indie €199 / Studio €799；EULA 禁止转售生成的树模型） | — | 活跃（2.3 版，2026-02 发布，支持 Blender 5 / Houdini） |
| TreeGen-LLM（2025 新工具） | [github.com/YuutoSeki/treegen-llm](https://github.com/YuutoSeki/treegen-llm) | README 声称 MIT（仓库无 LICENSE 文件，GitHub API 未检出） | 3 | 2025-09 新建，实验性 |
| Trees-With-Geometry-Nodes-Blender | [github.com/IRCSS/Trees-With-Geometry-Nodes-Blender](https://gitmemories.com/index.php/IRCSS/Trees-With-Geometry-Nodes-Blender) | 未明确标注 | 小 | 2022 年 Blender 3.2 Alpha 时期示例仓库 |

---

## 2. 详细评估

### 2.1 MTree / Modular Tree（Blender 插件 + C++ 库）

- **能力**：模块化 `TreeFunction` 链（Trunk→Branch→Branch…）递归生成枝干，`ManifoldMesher` 输出平滑拓扑网格；叶片通过 "twig"（小枝）机制实例化——用户自建一个带贴图的 twig 网格/平面，由粒子系统（旧版）或 Geometry Nodes（4.x 代码中的 `resources/geo_node` leaves distribution）分布到枝梢。曾是最接近 SpeedTree 体验的开源 Blender 方案。([README](https://github.com/MaximeHerpin/modular_tree))
- **许可证**：双轨——Blender 插件 Python 部分 GPL-3.0，独立 C++ 库 MIT（[README License 节](https://github.com/MaximeHerpin/modular_tree#license)）。仓库整体标记 GPL-3.0（[GitHub API](https://api.github.com/repos/MaximeHerpin/modular_tree)）。
- **输出格式**：Blender 内网格 → 可经 Blender 导出 FBX/glTF；C++ 库直接给顶点/三角形数组，可自写导出器。
- **自定义叶贴图/叶卡片**：✅ twig 是用户自建网格，天然支持自带 alpha 叶贴图卡片，且 twig 实例的形态就是"小簇"，与目标风格的卡片簇较接近。
- **风格匹配度**：枝干算法偏写实但参数（长度/角度/半径/随机性）可控，细长单干+疏枝可以调出来；叶片侧最匹配要素 B。
- **泛化能力**：seed + 全参数化，官方定位即"快速生成大量不同树"。
- **流水线难度**：**高**。
  - 致命问题：**已停更**（2021-12），官方 release V4_0_2 仅支持 Blender 2.93/3.x；社区实测 Blender 4.1/4.2 上插件无法启用，只能靠 steven-ray 等 fork 在 4.0 上运行，或"在 3.0 里生成再转移到 4.x"（[BlenderArtists 长帖](https://blenderartists.org/t/modular-tree/674043/1203)）。在当前 Blender 5.x 时代基本不可用。
  - 若走 C++ 库路线则需要自行编译（CMake）并自写 mesh 导出与叶分布逻辑，工作量接近自研。
- **结论**：算法设计优秀但工程状态差。**不建议直接采用**；其 twig 实例化思想可作为自研叶簇分布的参考。

### 2.2 proctree.js（Paul Brunt）及 C++ 端口

- **能力**：经典单文件 JS 库（约千行），输入 ~20 个参数（seed、levels、branchFactor、clumpMax/Min、twigScale、trunkLength、taperRate……），输出**两套独立顶点流**：`verts/faces/UV`（枝干）和 `vertsTwig/facesTwig/uvsTwig`（twig 卡片）。([README 用法示例](https://github.com/supereggbert/proctree.js))
- **许可证**：BSD 3-Clause，声明于源码头部（[proctree.js 源文件](https://raw.githubusercontent.com/supereggbert/proctree.js/master/proctree.js)）。C++ 端口 [jarikomppa/proctree](https://github.com/jarikomppa/proctree) 同为 BSD 3-Clause，且修复了 UV 映射、快几个数量级，附 HappyTree 编辑器（CC0 贴图包）。在线 demo：[snappytree.com](http://snappytree.com/)。
- **输出格式**：纯内存顶点/面/UV 数组——**格式无关**，可自行序列化为 OBJ/FBX/glTF 或直接喂给任何引擎。C++ 端口"设计为可插入任何项目、无依赖"。
- **自定义叶贴图/叶卡片**：✅ twig 网格就是带 UV 的 quad 集合，材质完全由使用方指定——把 UV 对齐到 IL3DN_Leaf_01.png 的图集区域即可，是全部候选里对要素 C 支持最干净的（几何与贴图解耦）。
- **风格匹配度**：
  - 枝干：`clumpMax/clumpMin` 控制分枝向父枝聚拢，`twigScale` 控制叶簇大小——可逼近"细长干+簇状冠"，但默认形态偏写实、叶片沿枝均匀撒布，**树冠"成簇的 blob 感"需要调参或二次开发**（如限制 twig 只长在末级枝梢并加大 twigScale）。
  - 截图级相似度参考：snappytree demo 树 + 卡通着色后与本项目目标风格属同一谱系。
- **泛化能力**：seed 驱动、参数少而正交，非常适合"同风格、不同形状"批量变体。
- **流水线难度**：**低**。JS 单文件可直接跑在 Node 批量产 OBJ；或移植 C#（已有多个民间 Unity 移植）在 Unity 编辑器/运行时生成；C++ 端口可嵌任何工具链。无需 Blender。
- **结论**：**二次开发首选基底**。代码老（2012–2017）但稳定、许可最宽松、输出最贴叶卡片模型。

### 2.3 Blender Sapling Tree Gen（官方扩展）

- **能力**：Blender 官方随附的参数化树生成器。9+ 预设（white_birch、quaking_aspen、small_pine、willow……），参数覆盖：枝干形状（Shape/Custom Shape）、分枝层级与分布（Branch Distribution/Rings）、剪枝（Pruning 系列）、**叶片（Show Leaves，矩形/六边形叶片 quad，数量/缩放/分布）**、Curvature、Vertical Attraction、Random Seed，还支持骨架绑定与风动画。([Blender 2.92 手册](https://docs.blender.org/manual/en/2.92/addons/add_curve/sapling.html)、[参数详解（日文）](https://horohorori.com/blender-note/about-add-curve-sapling-tree-gen/amp/))
- **许可证**：GPL（Blender 官方 addon）。注意 GPL 约束的是插件代码本身；**生成出的模型是输出数据，归用户所有**（Blender 一贯立场，与 tree-gen 作者的明示一致，见 2.4）。
- **输出格式**：Blender Curve/Mesh → `bpy.ops.export_scene.fbx` 直出 FBX，与项目现有 Blender 自动化工具体系（`tools/blender_client.py` 等）完全同构。
- **自定义叶贴图/叶卡片**：⚠️ 部分支持。叶片是**逐叶小 quad**，默认贴 UV 到单叶纹理；社区教程演示了给叶片指定自定义 alpha 贴图 + 调 UV 的完整流程（[kemarii.com 教程](https://kemarii.com/blog/cg/sapling-tree-gen/)）。但它是"每片叶一张卡"，不是目标的"一簇叶团一张卡"；要得到截图那种卡片簇，需要后处理（按空间聚类合并/替换为卡片）或自写分布。
- **风格匹配度**：white_birch 预设的"细长干+上部冠"骨架与要素 A 高度吻合（参考资产本身就是 Birch）；叶片侧匹配要素 C、不匹配要素 B。
- **泛化能力**：Random Seed + 全参数可脚本读写，预设可作为"风格锚点"保证变体间风格统一。
- **流水线难度**：**低**。纯 `bpy` Python，`bpy.ops.curve.tree_add(...)` 全参数可传，headless（`blender -b -P script.py`）批量 seed → FBX 是成熟做法；项目仓库已有 `tools/try_sapling.py`、`tools/get_sapling_params.py` 的先行经验。
- **维护状态**：Blender 4.2 起官方 addon 从安装包剥离、迁移到 Extensions 平台，一键安装后续用（[Blender 4.2 社区讨论](https://blenderartists.org/t/the-new-blender-4-2/1540634)、[4.3 安装实测](https://jinhima.com/?p=33335)），仍属官方维护，是**唯一保证跟随 Blender 版本演进的方案**。
- **结论**：**离线批量流水线首选**（骨架生成），叶簇环节需补一个"叶片聚簇→卡片化"后处理。

### 2.4 tree-gen（friggog，Blender 插件）

- **能力**：Charlie Hewitt 本科论文项目（[论文 PDF](https://chewitt.me/Papers/CTH-Dissertation-2017.pdf)），Weber & Penn 参数化模型 + L-System 思路改进，完整自定义 UI；内置 quaking_aspen 等参数预设（`tree-gen.parametric.tree_params.*`），全部参数（含 seed）暴露在 Blender 场景属性上。([GitHub](https://github.com/friggog/tree-gen))
- **许可证**：GPL-3.0；作者特别声明"**生成的模型可在任何场景自由使用，唯禁止直接作为资产出售**"（[README](https://github.com/friggog/tree-gen/blob/master/README.md)）——若产出物会进入 Unity  Asset Store 类商店，这是明确的法律障碍；仅作游戏内资产则无妨。
- **Stars/维护**：943★，最后推送 2025-07-11，偶有维护（[GitHub API](https://api.github.com/repos/friggog/tree-gen)）。
- **输出格式**：Blender Curve → 转 Mesh → FBX/glTF；已有第三方 gist 演示**完全 headless 批量生成 + GLB 导出**（[auto_gen_tree.py](https://gist.github.com/ShaoxiongYao/8259cf495e1776b42579bead812ba44e)），证明自动化可行。
- **自定义叶贴图/叶卡片**：⚠️ 与 Sapling 同级——生成叶片 quad + UV，可在 Blender 内换贴图；同样是逐叶分布而非卡片簇。
- **风格匹配度**：Weber-Penn 骨架形态质量高（"50m 外看非常真实"是该算法一脉的口碑），细长干形态可调；叶片侧同 2.3 的问题。
- **流水线难度**：中低（同 Sapling 的 bpy 路线，但第三方插件需随 Blender 版本验证兼容性）。
- **结论**：**骨架形状质量的备选/对照组**。与 Sapling 二选一即可，二者算法同源（Weber-Penn）。

### 2.5 Unity 生态：开源仓库与内置 Tree Creator

**mattatz/unity-procedural-tree**（427★，MIT，[GitHub](https://github.com/mattatz/unity-procedural-tree)）
- Unity 原生 C# 程序化树 builder，编辑器内调参实时预览，生成树干网格 + 叶片网格（可指定叶材质/贴图），直接产出 Unity `Mesh`，省掉 FBX 环节。
- 最后推送 2022-12-16（[GitHub API](https://api.github.com/repos/mattatz/unity-procedural-tree)），停更但代码自洽。
- 叶片分布仍非"卡片簇"；网格质量/UV 需按项目标准验收。
- 价值：**若希望生成逻辑下沉到 Unity 编辑器内（关卡内程序化摆放/运行时变体），这是最成熟的开源起点**。

**其他 L-System 仓库**：[dilmerv/UnityLSystemEssentials](https://awesomeopensource.com/project/dilmerv/UnityLSystemEssentials)（YouTube 教程配套，LineRenderer 为主）、[pboechat/LSystemsInUnity](https://awesomeopensource.com/project/pboechat/LSystemsInUnity)（文本定义 axiom/规则）、[manuelpagliuca/l-system](https://git.codeproxy.net/manuelpagliuca/l-system)（MIT，2022 课程项目）——均为教学级，L-System 文法能产出丰富形状，但网格化（管状枝干、叶卡片、UV）都要自己补，**只建议借算法，不建议直接入库**。

**Unity 内置 Tree Creator（Tree Editor）**
- Unity 6 文档仍在维护该功能（[Design a tree](https://docs.unity3d.com/6000.7/Documentation/Manual/tree-FirstTree.html)）：Branch Group / Leaf Group 层级、Frequency/Growth Angle/Seek Sun 等程序化参数；叶组可用自定义材质，甚至可用导入 mesh 作叶（[Create trees and leaves from meshes](https://docs.unity3d.com/6000.7/Documentation/Manual/terrain-Tree-From-Mesh.html)）；支持 LOD、风区、地形刷树与远处 billboard。
- **关键缺陷**：它是**编辑器手工工具**——官方脚本 API 中没有暴露 Tree 资产数据，无法以代码驱动其参数化生成（手动编辑还会使程序化属性失效，[日版文档说明](https://docs.unity3d.com/jp/current/Manual/tree-FirstTree.html)）。**不满足"自动化批量生成"这一硬需求**，仅适合手工做一两棵样板树。
- 附注：Maxime Herpin 曾发售 Unity 版 **Mtree – Tree Creation**（2019 Unity Awards 最佳艺术工具提名，[80.lv 报道](https://80.lv/articles/mtree-tree-creation-in-unity)），但**已从 Asset Store 下架废弃**（[Asset Store 页面](https://assetstore.unity.com/packages/tools/modeling/mtree-tree-creation-132433)），商业路线也不可得。

### 2.6 遗留开源工具：Arbaro 与 ngPlant

**Arbaro**（[官网](http://arbaro.sourceforge.net/)）
- Weber & Penn 论文的 Java 实现，XML 参数文件输入 → 输出 POV-Ray / DXF / **Wavefront OBJ**（枝干与叶片分两个 mesh 声明，[导出细节](https://www.f-lohmueller.de/pov_tut/plants/plants_500f.htm)）。
- GPL、开源、免费；16 个树种示例 XML（quaking aspen、black oak、weeping willow……）。
- 叶片为独立 quad mesh 带 UV，导入 DCC 后可换任意叶贴图。
- 问题：约 2014 年后无实质更新；Java 应用、无 FBX（需 OBJ→FBX 中转）；叶片分布写实向、无卡片簇概念；无 GPU/游戏向优化。
- 结论：算法经典、可命令行批处理，但工程链路老旧。**仅作 Weber-Penn 参数参考**，不建议进流水线。

**ngPlant**（[官网](http://ngplant.org/)、[SourceForge](https://sourceforge.net/projects/ngplant/)）
- C++ 交互式植物建模套件：工具 GPL，**核心库 libngpcore/libngput/pywrapper 为 BSD**，理论上可把生成库嵌入自有工具；导出 **OBJ / COLLADA(.dae)**；支持 LOD 参数、材质/透明度控制、Lua 脚本。
- 最后更新 2016-07-15，wxWidgets 老 UI，Windows/Linux/BSD。
- 结论：BSD 核心库是唯一亮点，但代码年代久远、文档薄弱，移植成本高于收益。**不推荐**。

### 2.7 The Grove 3D（商业，非开源——作为基准列出）

- F12（Wybren van Keulen）开发，**纯商业**：Starter €99 / Indie €199 / Studio €799，Twig（带叶小枝资产包）另售 €9.69/个（[购买页](https://www.thegrove3d.com/buy/)）。
- 2026-02 发布 2.3：支持 Blender 5 / Houdini（含 Houdini Indie）、新增整树绘制、分枝细分、面向实时引擎优化的网格结构（[CGChannel 报道](https://www.cgchannel.com/2026/02/f12-releases-the-grove-2-3-for-blender-and-houdini/)）。
- 生长模拟被公认为"CG 中最自然的树形"，twig 实例系统与目标风格的卡片簇思路一致，且允许自制低多边形 twig 来控面数（[FAQ](https://www.thegrove3d.com/learn-more/frequently-asked-questions/)）。
- **两条硬性排除理由**：① 非开源；② EULA 明确"Made for creators, not sellers — **不得出售/分发用 The Grove 长成的树模型**"，与"可泛化资产产出"目标冲突。另官方自述无 LOD 等游戏向工具。
- 结论：仅作质量基准与 twig 设计参考，**不进入选型**。

### 2.8 2024–2026 新出现的工具

- **TreeGen-LLM**（[github.com/YuutoSeki/treegen-llm](https://github.com/YuutoSeki/treegen-llm)，2025-09 创建，3★）：Blender 4.3+ 插件，用本地轻量 LLM（llama.cpp/GGUF）把自然语言 prompt 翻译成 Geometry Nodes 参数来生成树，支持滑杆微调与重试机制（[介绍文章](https://xn--bl-8ia.com/add-ons/treegen-llm-genera-alberi-procedurali-in-blender-con-prompt-testuali-e-geometry-nodes/)）。README 声称 MIT 但仓库无 LICENSE 文件。**实验性极强、无社区验证**，仅作前沿动向记录。
- **IRCSS/Trees-With-Geometry-Nodes-Blender**（2022）：纯 Geometry Nodes 树生成节点组（含 Low Poly Tree 组：曲线主干噪声扰动 + 实例化分枝 + 叶片），展示了 GN 路线的可行性；但作者自述"apply 后 UV 丢失、需脚本转 attribute"等已知问题（[仓库 README](https://gitmemories.com/index.php/IRCSS/Trees-With-Geometry-Nodes-Blender)）。许可证未标注。作为**自研 GN 生成器的技术参考**价值大于直接使用价值。
- 行业背景：Blender 5.0 于 2025-11 发布，商业侧（The Grove 2.3、Blender Market 上的 Stylized Tree Generator 等）均在向 Geometry Nodes 迁移；开源侧尚未出现维护良好、面向游戏资产的 GN 树生成器——**这正是本项目自研补位的空间**。

---

## 3. 与目标风格的匹配分析

按第 0 节的四要素打分（● 好 / ◐ 中 / ○ 差）：

| 方案 | A 枝干形态 | B 卡片簇 | C 自带叶贴图 | D* | 输出进 Unity | 自动化 | 许可证风险 |
|------|-----------|---------|-------------|----|-------------|--------|-----------|
| MTree (modular_tree) | ● | ●（twig 实例即小簇） | ● | — | ◐（FBX 经 Blender） | ○（插件在新版 Blender 坏） | 插件 GPL / 库 MIT |
| proctree.js / C++ 端口 | ◐ | ◐（twig quad 需聚簇调参） | ●（几何贴图全解耦） | — | ●（格式无关） | ● | **BSD，最低** |
| Sapling Tree Gen | ●（birch 预设即参考原型） | ○（逐叶 quad） | ◐（换贴图+调 UV） | — | ●（FBX 直出） | ●（bpy headless） | GPL（产出物不受限） |
| tree-gen | ● | ○（逐叶 quad） | ◐ | — | ● | ●（已有 headless 范例） | GPL + **禁售条款** |
| mattatz/unity-procedural-tree | ◐ | ○ | ◐ | — | ●（原生 Mesh，免 FBX） | ●（编辑器脚本） | MIT，最低 |
| Unity Tree Creator | ◐ | ◐（叶组+自定义 mesh 叶可拼簇） | ● | — | ●（原生） | ○（**无脚本 API**） | 无 |
| Arbaro | ● | ○ | ◐（OBJ 导入后换贴图） | — | ◐（OBJ→FBX 中转） | ◐（CLI+XML 可批） | GPL（产出物不受限） |
| ngPlant | ◐ | ○ | ◐ | — | ◐（OBJ/DAE） | ◐ | 工具 GPL / 库 BSD |
| The Grove | ● | ●（twig 系统） | ◐（官方 twig 另售，可自制） | — | ●（FBX/USD/glTF） | ◐ | **商业 + 禁售产出** |
| TreeGen-LLM | ◐ | ？ | ？ | — | ● | ◐ | 许可证文件缺失 |

\* D（双色调平涂）在任何方案中都由项目自己的卡通着色器承担，与几何生成器选型解耦，故不展开。

**关键差距分析（所有开源方案的共性短板）**：没有之一开箱即出"截图那种大团卡片簇树冠"——MTree/proctree/The Grove 的 twig/小枝实例最接近（一实例=一小簇），Sapling/tree-gen/Arbaro/ngPlant 都是逐叶分布。因此无论选哪个，**"叶片聚簇化"都是必须补的一层**：要么在生成参数上把叶集中到末级枝梢并放大卡片（proctree 调 twigScale/clump 路线），要么生成后按空间聚类把叶 quad 合并/重投影为大卡片（后处理路线），要么干脆自研分布（以枝梢为球心、在椭球壳上撒卡片——即 SpeedTree "leaf cluster"的经典做法）。

---

## 4. Top 3 推荐及理由

### 🥇 推荐 1：Blender Sapling Tree Gen —— 离线批量流水线主干

**理由**
1. 与项目现有基建零摩擦：仓库已有 Blender headless 自动化体系与 Sapling 先行脚本（`tools/try_sapling.py`、`get_sapling_params.py`），seed → 参数 → FBX 的链路今天就能跑。
2. **唯一官方持续维护**的开源方案，Blender 4.2+ / 5.x 经 Extensions 平台可用，不存在 MTree 那种版本断头路。
3. white_birch 预设的骨架与参考资产（IL3DN Birch）同源同型，要素 A 几乎开箱即得；GPL 不影响生成模型的使用权。
4. 全参数 bpy 可读写 → "同风格不同形状"的变体泛化就是 for-loop 换 seed + 参数域随机化。

**需要自研补齐**：叶片聚簇→卡片化后处理（生成后按枝梢聚类，把叶 quad 合并为对准 IL3DN_Leaf_01.png 图集的大卡片），以及卡通材质指定。

### 🥈 推荐 2：proctree.js（或 jarikomppa C++ 端口）—— 引擎内嵌 / 深度定制基底

**理由**
1. **BSD 3-Clause**，全部候选中法律风险最低，可随意改、嵌、再分发。
2. 输出天然分"枝干 + twig 卡片"双流，UV 全自带——**自带贴图复用（要素 C）实现成本最低**；代码千行级，吃透+改造成"卡片簇分布"（限制 twig 只在末级枝梢生成、调 clump/twigScale）的工作量以天计。
3. 语言无关：JS 可在 Node 批产网格；C++ 端口可嵌桌面工具；亦可移植 C# 直接在 Unity 编辑器/运行时生成（要素"目标运行时大概率是 Unity"的终局形态）。
4. 参数少而正交，变体风格统一性最容易控制。

**代价**：需自建 FBX 导出（或 OBJ→FBX 中转）与材质绑定环节；仓库停更（但代码成熟稳定，issue 仅 2 个）。

### 🥉 推荐 3：friggog/tree-gen —— 高质量骨架备选/对照组

**理由**
1. Weber & Penn 参数化实现里**开源中形态质量最好**的一档（943★，社区验证充分），预设丰富，与 Sapling 形成对照，可用于 A/B 验证骨架质量。
2. 自动化已被第三方验证（headless + GLB 导出 gist），接入现有 Blender 流水线成本低。
3. 仍有零星维护（2025-07），比 MTree/Arbaro 健康。

**注意**：GPL-3.0 + 作者"禁止直接出售生成模型"条款——若未来产出物有上架资产商店的可能，此方案只能用于内部生成、不能卖树模型本身。

> 备选观察位：mattatz/unity-procedural-tree（若决定把生成器下沉进 Unity 编辑器，优先评估它）；MTree 的 twig 实例化设计与 The Grove 的 twig 资产结构，作为自研叶簇系统的参考阅读。

---

## 5. 风险清单

| 风险 | 影响 | 缓解 |
|------|------|------|
| **共性短板：无开箱"卡片簇树冠"** | 直接生成的树与截图风格有肉眼差距 | 立项时即规划"叶簇化"一层（参数聚簇 / 后处理合并 / 自研椭球壳撒卡片），见第 3 节 |
| Blender 插件版本兼容（MTree 在 4.1+ 不可用；Sapling 4.2 起需 Extensions 安装） | 流水线环境锁定 | 在 CI 脚本中固定 Blender 版本；Sapling 安装步骤写进环境初始化脚本 |
| GPL 传染性误读 | 法律顾虑 | 明确认知：GPL 约束插件代码，**生成物（模型）版权归属使用者**（tree-gen README 明示、Blender 一贯立场）；不要把插件源码改一改嵌进闭源工具 |
| tree-gen "禁售生成资产"条款 | 若走资产商店分发则违规 | 该方案限定内部使用；有售卖计划则排除 tree-gen，用 BSD 的 proctree 路线 |
| proctree.js 停更 + 无 FBX 导出 | 需自写序列化与材质绑定 | 工作量可控（单文件库）；或直接用 jarikomppa C++ 端口 |
| Unity Tree Creator 无脚本 API | 无法自动化批量生成 | 仅作手工样板工具，不进自动化链路 |
| FBX 导出细节（alpha 贴图、材质槽、单位缩放） | 进 Unity 后材质丢失/错位 | 导出脚本显式指定材质与贴图路径，用 ufbx 校验（项目已有 `tools/validate_with_ufbx.py` 先例） |
| TreeGen-LLM 等新工具许可证文件缺失 | 法律状态不明 | 不采用，仅跟踪 |
| 双色调卡通渲染与几何解耦 | 误以为选好生成器就有截图效果 | 着色器（双色调 + alpha cutout + 法线压平）需单独立项，与生成器并行开发 |

---

## 6. 主要来源

**仓库与官方数据**
- [MaximeHerpin/modular_tree](https://github.com/MaximeHerpin/modular_tree) ｜ [GitHub API 元数据](https://api.github.com/repos/MaximeHerpin/modular_tree) ｜ [BlenderArtists 兼容性讨论](https://blenderartists.org/t/modular-tree/674043/1203)
- [supereggbert/proctree.js](https://github.com/supereggbert/proctree.js) ｜ [源码许可证头](https://raw.githubusercontent.com/supereggbert/proctree.js/master/proctree.js) ｜ [jarikomppa/proctree（C++ 端口）](https://github.com/jarikomppa/proctree)
- [friggog/tree-gen](https://github.com/friggog/tree-gen) ｜ [GitHub API 元数据](https://api.github.com/repos/friggog/tree-gen) ｜ [headless 自动化 gist](https://gist.github.com/ShaoxiongYao/8259cf495e1776b42579bead812ba44e) ｜ [论文](https://chewitt.me/Papers/CTH-Dissertation-2017.pdf)
- [mattatz/unity-procedural-tree](https://github.com/mattatz/unity-procedural-tree) ｜ [GitHub API 元数据](https://api.github.com/repos/mattatz/unity-procedural-tree)
- [YuutoSeki/treegen-llm](https://github.com/YuutoSeki/treegen-llm)

**文档**
- [Sapling Tree Gen — Blender 手册](https://docs.blender.org/manual/en/2.92/addons/add_curve/sapling.html) ｜ [Blender 4.3 扩展安装实测](https://jinhima.com/?p=33335) ｜ [Blender 4.2 插件迁移讨论](https://blenderartists.org/t/the-new-blender-4-2/1540634)
- [Unity 6 — Design a tree (Tree Editor)](https://docs.unity3d.com/6000.7/Documentation/Manual/tree-FirstTree.html) ｜ [Unity — Create trees and leaves from meshes](https://docs.unity3d.com/6000.7/Documentation/Manual/terrain-Tree-From-Mesh.html)
- [Arbaro 官网](http://arbaro.sourceforge.net/) ｜ [ngPlant 官网](http://ngplant.org/) ｜ [ngPlant SourceForge](https://sourceforge.net/projects/ngplant/)
- [The Grove 购买页/许可](https://www.thegrove3d.com/buy/) ｜ [The Grove FAQ（游戏引擎适用性）](https://www.thegrove3d.com/learn-more/frequently-asked-questions/)

**媒体与社区**
- [CGChannel — The Grove 2.3 发布（2026-02）](https://www.cgchannel.com/2026/02/f12-releases-the-grove-2-3-for-blender-and-houdini/)
- [80.lv — Mtree Unity 版报道](https://80.lv/articles/mtree-tree-creation-in-unity) ｜ [Unity Asset Store — Mtree 已下架](https://assetstore.unity.com/packages/tools/modeling/mtree-tree-creation-132433)
- [Weber & Penn — Creation and Rendering of Realistic Trees（论文）](http://www.cs.duke.edu/courses/cps124/spring08/assign/07_papers/p119-weber.pdf)
