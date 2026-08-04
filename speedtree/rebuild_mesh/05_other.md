# 05 其他自动化树木建模方案调研

> **命题**：在 ①Blender+MCP ②手写代码建模 ③开源算法库 ④AI 模型生成 之外，还有哪些可行的自动化树木建模路线？目标：批量产出与 `mesh/IL3DN_Tree_Beech_02/IL3DN_Tree_Birch_02.FBX` 同风格（卡通低模、单干细树、叶卡片冠层、双色调绿、平面着色）、形状各异、贴图复用、可进 Unity 的树。
>
> **方法**：网络调研（2026-08，附来源链接）+ 本地资产实测（复用 `tools/` 下已有的 FBX 解析器/写出器/ufbx 校验器，对 Birch_02 做了结构分析）。
>
> **一句话结论**：**"以 IL3DN_Tree_Birch_02.FBX 为母体的变体繁衍"是本项目最优路线**——它是所有方案中唯一能 100% 继承母体贴图、材质、顶点色风数据语义与 LOD 结构的做法，且项目 `tools/` 下已具备全部所需基础设施（自研 FBX 解析器 + 纯 Python FBX 写出器 + ufbx 独立校验，产物此前已通过校验并可被 Unity 导入）。商业工具（SpeedTree / Houdini / The Grove）对本项目均"杀鸡用牛刀"且风格错配；资产商店路线适合做母体池补充；Impostor 渲染路线不解决造型泛化，但可作为末端 LOD/远景放大器与主路线叠加；摄影测量与卡通风格根本错配，排除。

---

## 0. 本地资产实测（评估各方案的事实基础）

用 `tools/analyze_tree_fbx.py` 对 `IL3DN_Tree_Birch_02.FBX` 实测，结构如下（单位英寸，×2.54cm 得米；根节点带 +90° X 旋转即文件内 Z-up）：

| 节点 | 顶点 | 面 | 实测解读 |
|---|---|---|---|
| `IL3DN_Tree_Birch_02`（根 Null） | — | — | 挂全部子节点 |
| `..._Leaves_LOD0` | 8400 | 4200 三角 | **2100 张叶卡片**（每卡 4 顶点 2 三角的平整 quad） |
| `..._Leaves_LOD1/2/3` | 5600 / 2800 / 348 | 2800 / 1400 / 174 三角 | 逐级减卡：1400 / 700 / 87 张 |
| `..._Branch_LOD0` | 1002 | 762 四边形 | 树干+光秃分枝，全四边形拓扑，高 7.38m |
| `..._Branch_LOD1/2/3` | 536 / 268 / 64 | 440 / 232 / 60 四边形 | 逐级减环 |
| `..._Card` | 8 | 2 四边形 | **6m×8m 十字/双面 billboard，UV 采样预渲染图集区域——资产自带的末端 LOD impostor** |

关键语义（决定变体繁衍方案的可行性）：

- **叶卡片 UV 只有 4 个唯一角点**（U/V∈[0,1]）：每张卡整幅采样 `IL3DN_Leaf_01.png`；该贴图 RGB 为白色、**叶形全部在 alpha 通道**，绿色来自顶点色/着色器——这意味着变体天然复用同一贴图，改色不需要动贴图。
- **顶点色是风动画数据**：叶 A 通道与高度相关系数 +0.98（归一化高度=弯曲权重），枝 G 通道为逐枝随机相位、A 同样与高度相关（+0.99）。**任何形变/重排布后必须按新几何重算 A=z/H、重赋 G**，否则风动画穿帮。
- **叶卡片是离散连通分量**（4v/2tri 一卡），可用连通分量分析 100% 可靠地逐卡识别——这是"逐卡抖动/增删/重排"的技术前提。
- 文件名 `_LOD0..3` 命名约定：Unity 导入时据此自动建 LODGroup；`_Card` 即第 5 级（billboard）。

---

## 1. 方案 A：FBX 母体变体繁衍（重点论证）

### 1.1 思路

不改风格、只改形状：把 Birch_02 当作"基因母体"，用脚本对其施加**有统计护栏的随机变换**——树干做弯曲/扭转/锥度/缩放形变，叶卡片做逐卡抖动（刚体变换）、增删（密度重采样）、重排布（冠层包络内重新分布），每个随机种子产出一棵"形状不同、风格基因完全不变"的新树，批量离线生成 FBX 变体库（或在 Unity 编辑器/运行时内直接生成 Mesh 变体）。

**为什么它是风格统一性最强的路线**：变体继承母体的全部"风格载体"——同一张叶贴图与树皮贴图、同样的材质槽结构、同样的顶点色风数据约定、同样的 LOD 组织、同样的卡片尺寸/朝向分布族。风格统一不依赖"生成得准"，而依赖"根本没换零件"。泛化能力则来自变换参数域的大小，可通过放开参数逐步扩大。

### 1.2 本地可行性证据（基础设施已就绪）

| 能力 | 现状 |
|---|---|
| FBX 解析 | `tools/inspect_fbx.py`：自研纯 Python FBX 7300 二进制解析器，已完整逆向过同包的 Pine_01（顶点/UV/顶点色/材质/连接图全覆盖） |
| FBX 写出 | `tools/fbx_writer.py`：自研纯 Python 最小 FBX 7300 写出器，支持 Null 根 + `_LOD0/1/2` 命名（Unity 自动建 LODGroup）、双材质槽、Normal/UV/**RGBA 顶点色**/Material 四层 |
| 第三方校验 | `tools/validate_with_ufbx.py`：用 ufbx 独立校验产物，此前生成的 ProcPine FBX 已 0 警告通过 |
| Python 环境 | 本机 Python 3.12 + `ufbx` 0.0.5（PyPI 绑定）已安装可用 |

即：变体繁衍所需的"读 → 改 → 写 → 验"闭环**已经在本项目里跑通过一次**（此前是"从零生成"，本次换成"读入母体再变换"，解析与写出两端完全复用）。

### 1.3 FBX 解析/写回手段对比

| 手段 | 读 | 写 | 评估 |
|---|---|---|---|
| **项目自研解析器+写出器** | ✅ 已验证 | ✅ 已验证 | **首选**。零新依赖、完全可控、与参考资产格式逐字节对齐过；已知边界（FBX 7300 二进制、无骨骼动画）与本资产完全匹配 |
| **ufbx（C 库 + Python 绑定）** | ✅ 强 | ❌ 只读 | 单文件 C99、MIT/公有领域、经过大量 fuzz 测试，Blender 4.5 的新 FBX 导入器即基于它（[ufbx 官网](https://ufbx.github.io/)、[aras-p 博客](https://aras-p.info/blog/2025/05/08/Blender-FBX-importer-via-ufbx/)）。适合做读取交叉验证。已知坑：本项目的绑定版本（0.0.5）`node.parent` 返回悬空对象、同进程连续 load 多文件会段错误——**批处理时每个文件起独立进程**（`tools/validate_with_ufbx.py` 注释中已有记录） |
| **Autodesk FBX Python SDK** | ✅ 官方 | ✅ 官方 | 免费但官方 wheel 锁死 Python 3.10（2020.3.x，[APS 下载页](https://aps.autodesk.com/developer/overview/fbx-sdk?rel=outbound)），本机 3.12 需另建 venv 或用[社区编译 wheel](https://www.tech-artists.org/t/fbx-sdk-2020-3-9-for-python-3-7-3-9-3-11/18335)；Autodesk 自 2020 年后基本停更。**不必要**，自研写出器已够 |
| **Unity C#（Mesh API + FBX Exporter）** | ✅ 导入即得 | ✅ 官方包 | Unity 导入 FBX 后 `Mesh` 类直接读写顶点/UV/顶点色；写回 FBX 用官方免费包 [com.unity.formats.fbx](https://docs.unity3d.com/Packages/com.unity.formats.fbx@4.2/manual/index.html)（`ModelExporter` API，支持顶点色、四边形、8 套 UV；默认编辑器限定，运行时导出需 `FBXSDK_RUNTIME` 且仅 64 位桌面播放器，[API 文档](https://docs.unity3d.com/Packages/com.unity.formats.fbx@5.1/api/index.html)）。**与最终管线零距离的备选**，适合"变体直接在 Unity 工程内产出为 .asset/prefab" |

### 1.4 形变算法（树干 + 分枝）

Branch 网格全四边形、环状拓扑规则，适合整体位移场（只动顶点位置，UV/拓扑不动，不会破面）：

1. **建立主干参数轴**：按高度聚类顶点环（分析器已实现），拟合主干中心线 C(z)，z∈[0,H]，H≈7.4m。
2. **弯曲 bend**：施加横向位移场 `Δ(z) = A · f(z/H)`，f 取单调递增曲线（二次/三次或正弦半波），方向随机方位角。f 取 z² 时得到自然的风压弯。幅度 A 设上限（如 ≤0.15H）防塌。
3. **扭转 twist**：绕 C(z) 旋转 `θ(z) = θmax · (z/H)^k`，让分枝方位角沿高度螺旋变化——对"下部光秃分枝"的观感影响极大，是最便宜的多样化来源。
4. **锥度/粗细 scale**：径向缩放场 `s(z)`（整体胖瘦 ±20%）；整体高度缩放 ±25%（7.4m → 5.5~9.3m），配合冠层等比或拉伸。
5. **分枝级扰动**：按连通分量分离各分枝管，以分枝根部为 pivot 做小角度随机偏转（±10°），或随机删除 1~2 根下部分枝（截图中下部本来就只有 1~3 根秃枝，删枝即得明显新轮廓）。
6. **重算顶点色**：形变后 A = z'/H'（逐顶点），G 保持（逐枝相位随分枝分量拷贝）。

### 1.5 叶卡片重排布策略（核心）

先以连通分量把 Leaves_LOD0 拆成 2100 张独立卡片（每卡记录：中心、法向、尺寸、所属簇），然后按强度分三档：

- **L1 抖动（必做，最安全）**：每张卡施加刚体变换——平移 ±0.3m、绕随机轴 ±15°、缩放 0.8~1.2；G 相位重赋随机。轮廓微变，风格零风险。
- **L2 增删（推荐）**：按冠层密度函数抽稀（删 10~30%）或复制加密（+10~30%，复制卡重赋相位），并可按"簇"整体增删——先对卡片中心做聚类（参考截图：树冠由 3~5 团明显分离的叶簇构成），随机删除一整团或复制一团错位摆放，得到"三团冠 vs 四团冠"的显著形状差异。各 LOD 按各自卡片预算（1400/700/87）在同包络内同分布抽样。
- **L3 重排布（进阶）**：估计母体冠层包络（实测 Leaves 包围盒约 10~11m，分簇建模为若干椭球/ metaball 包络），在包络内重新撒卡，卡片倾角/法向/尺寸的**统计分布从母体采样**（而非均匀随机），保证"新摆法、旧味道"。卡片挂枝启发式：以 Branch 网格高端点（z>0.5H 的环）为锚点聚类，卡片优先分布在锚点周围——维持"叶随枝走"的结构合理性。
- **风格护栏**：所有随机量的分布参数（卡片尺寸直方图、倾角范围、簇间距、簇体积比）从母体统计得到，变体=在同一分布内重新抽样。这是"形状不同但一眼同族"的数学保证。

### 1.6 LOD 链与末端 billboard 一致性

- Branch/Leaves 的 LOD0~3 在母体内是**同拓扑族**（减环/减卡但布局一致），对每一级施加**同一组确定性变换参数**（同种子、同位移场、同增删种子）即可保持级间一致，避免 LOD 切换 popping。
- `_Card` billboard 末端 LOD：风格化平色渲染下，6×8m 十字卡足够通用，**不必每变体重烘**；若要精确，可在 Unity 里对变体截图重烘小图集（或直接用 §4 的 Amplify Impostors）。

### 1.7 两种落地形态

| 形态 | 做法 | 适用 |
|---|---|---|
| **离线批量（推荐先做）** | Python：自研解析器读母体 → numpy 变换 → 自研写出器写 N 个变体 FBX → ufbx 逐文件校验 → 人工/vision 评审挑库 | 产出固定资产库，进 Unity 即常规 Model Prefab，零运行时成本 |
| **Unity 编辑器/运行时** | C# 编辑器脚本读导入后的 Mesh 做同样变换，存 `.asset` mesh + prefab；或直接运行时 seeded 生成 | 想要"每局游戏树都不一样"时用运行时版；编辑器版免 Python 环境 |

### 1.8 该路线风险

- 形变幅度过大破坏风格（护栏+评审兜底，项目已有 `vision_judge.py` 视觉评审思路可复用）；
- 变体是母体资产的演绎作品——**游戏内使用没问题，但不能把变体库当资产包再分发**（详见 §6 授权风险）；
- 顶点色忘重算导致风穿帮（ checklist 固化）。

---

## 2. 方案 B：商业程序化工具

### 2.1 SpeedTree（Unity 旗下，行业标准）

- **定位**：行业标准植被建模套件（2021 年 Unity 收购 IDV 获得，[Unity 收购公告](https://investors.unity.com/news/news-details/2021/Unity-Acquires-Interactive-Data-Visualization-Inc.-IDV-Creators-of-SpeedTree-Environment-Creation-Suite/default.aspx)）；2026-01-01 起账号体系迁移至 unity.com（[Unity 支持页](https://support.unity.com/hc/ja/articles/15723241438228)）。当前版本 SpeedTree 10（[官网/下载](https://speedtree.com)）。
- **价格（2026 现价）**：Indie **$19/月**（年营收 <$100K，[订单页](https://service-store.unity.com/order/create?currency=USD&product=SPTR-INDIE)）；Pro **$899/年**（营收 <$1M）；资产库 SpeedTree Library **+$999/年** 订阅且不再单卖（[Unity 支持页](https://support.unity.com/hc/en-us/articles/49699142648980)）；Enterprise 定制。**Learning Edition 免费但禁止导出**，且其文件不能在其他版本打开（[支持页](https://support.unity.com/hc/ja/articles/15723241438228)）。
- **对本项目的适配性**：SpeedTree 强项是写实植被（奥斯卡/艾美奖、3A 管线）；其随机化（种子变体）能力确实强，Unity 集成好（单次绘制调用、直接导出、轻量风，[官网 FAQ](https://speedtree.com)）。但：①风格需要从零调教到 IL3DN 这种平面双色调，工作量不亚于自建；②最小可用成本 $19/月（导出需付费档）；③产物的风数据走 SpeedTree 自有约定，与 IL3DN 顶点色语义不一致，混用需改 shader。**结论：风格与成本双重错配，不推荐。**

### 2.2 Houdini 程序化（SideFX）

- **Apprentice（免费版）硬限制**（[官方功能对比表](https://www.sidefx.com/products/compare/)、[Apprentice FAQ](https://www.sidefx.com/ja/faq/apprentice/)）：仅非商用；场景/资产存专有 `.hipnc`/`.hdanc`；**FBX 只进不出（Import only）**；渲染带水印且分辨率封顶 1920×1080；**Apprentice 制作的 HDA 不能在 Houdini Engine 中使用**；授权 30 天一续需联网。→ 对"给 Unity 供 FBX 资产"的目标，Apprentice 等于不可用，只能用于学习原型。
- **付费档**：Indie **$299/年**（或 $449/2 年，营收 <$100K，全功能含 FBX 导出）；Core $1,995 永久 / FX $4,495 永久（[官方价格表](https://www.sidefx.com/products/compare/)）。Houdini Engine Indie 免费，可在 Unity 里跑 HDA（Houdini Engine for Unity 插件）。
- **对本项目的适配性**：节点式程序化确实能做出"参数化树生成器 HDA 进 Unity"的优雅管线，但学习曲线是 3D 软件里最陡的一档（6~12 个月才能达到生产力，社区共识），且同样需要从零复刻 IL3DN 风格。**结论：投入产出比过低，仅当团队已有 Houdini 经验时考虑。**

### 2.3 The Grove 3D（Blender/Houdini 生长模拟）

- **价格**：Starter **€99** / Indie **€199** / Studio **€799**，终身授权（[官方购买页](https://www.thegrove3d.com/buy/)）。
- **自动化限制**：**Python 自动化导出（USD/OBJ）锁在 €799 Studio 档**（[版本对比](https://www.thegrove3d.com/compare/)），且不含 FBX——进 Unity 还要再过一道转换。
- **授权限制**：许可明确"Made for creators, not sellers"——**禁止出售/分发用 The Grove 生成的树模型**，游戏分发权需单独联系（[购买页脚注](https://www.thegrove3d.com/buy/)）。
- **对本项目的适配性**：生长模拟出的是写实自然树形，与卡通双色调目标相反；项目前序调研已判"不推荐"，本次复核维持原判。

### 2.4 商业工具小结

| 工具 | 最小可用成本 | 自动化 | 风格适配 | 结论 |
|---|---|---|---|---|
| SpeedTree 10 | $19/月（Indie） | 种子随机+SDK | 需从零调教写实→卡通 | 不推荐 |
| Houdini | $299/年（Indie，免费版不可产出） | HDA/节点全程序化 | 同左 | 仅团队有经验时考虑 |
| The Grove 3D | €799（自动化档） | Python 仅 USD/OBJ | 写实生长模拟 | 不推荐 |

---

## 3. 方案 C：资产商店购买 + 脚本随机化

### 3.1 供给现状

- **Unity Asset Store / Marketplace**（2025 年起迁至 marketplace.unity.com）：风格化树包供给充足且便宜——如 Stylized Nature Bundle（Two Theories，**$20**：4 种树 × 8 种叶色变体 + 枯树版，带 LOD 与风 shader，[商店页](https://assetstore.unity.com/packages/3d/vegetation/trees/stylized-nature-bundle-135352)）、Low Poly Stylized Nature（**$4.99**，[商店页](https://marketplace.unity.com/packages/3d/environments/low-poly-stylized-nature-281338)）等。
- **重要发现**：本项目参考资产的出处已定位——`IL3DN_` 前缀即 Unity Asset Store 上的 **The Illustrated Nature**（Artkovski，**$40**，[商店页](https://assetstore.unity.com/packages/3d/vegetation/the-illustrated-nature-153939)；第三方模型索引把 `IL3DN_Tree_Birch_02_OneMesh` 直接归于该包，评论中也出现 `IL3DN_ColorController_Editor.cs`）。注意该包 **仅支持 Built-in 管线**（官方评论回复确认）。也就是说：同族"姊妹树"（同包还有多个树种/草/花）可以 $40 全部入手，**直接扩充母体池**。
- **Fab（Epic，2024-10-22 上线，合并 UE Marketplace/Sketchfab Store/Quixel）**：Fab Standard License 允许资产用于**任何引擎/工具（含 Unity）**（[Fab 发布博客](https://sketchfab.com/blogs/community/epics-unified-marketplace-fab-launches-today/)、[Fab EULA](https://www.fab.com/eula)）。有现成的"模块化树"包，如 Stylized Trees Pack（MadeFun3D，€52.20：**含独立树干 + 多组叶簇模块，官方明确支持自行拼装变体**，[Fab 页](https://www.fab.com/listings/f09236d3-fcdc-44ca-b242-d6d1ca795969)）——与"脚本随机化组合"的思路天然契合。注意很多 Fab 资产只有 UE 工程格式，需筛 Unity/FBX 格式。

### 3.2 玩法与评估

- **玩法 A（扩充母体池）**：买下 The Illustrated Nature（$40），把同包的 Birch_01/03、Pine_01~03 等全部变成 §1 变体繁衍的母体——成本最低、风格锁死（同一作者同一贴图约定）。**强烈推荐与方案 A 叠加。**
- **玩法 B（跨包随机组合）**：买多个风格化包，用脚本做"树干 × 树冠 × 配色"混搭 + 变换抖动。风险是跨作者资产的风格差（拓扑密度、贴图粒度、着色约定）需要 shader 层统一（如全部套同一套 toon shader + 调色板约束），否则会"拼"感明显。
- **授权边界**：Unity Asset Store 标准 EULA 允许修改资产并用于自己的游戏成品，但**禁止将（含修改后的）源资产以资产形式再分发**；Fab Standard License 同理（[Unity AS Terms](https://unity.com/legal/as-terms)、[Fab EULA](https://www.fab.com/eula)）。即"买来随机化给自己游戏用"合法，"随机化后打包出售/分享"违法。

---

## 4. 方案 D：纯渲染层路线（billboard / impostor / shader 树）

### 4.1 技术谱系与现状

- **Billboard / 十字卡**：最古老的远景树方案。**本项目参考资产自带实证**——`_Card` 节点（8 顶点 2 四边形、6×8m、UV 采样预渲染图集）就是 IL3DN 的末端 LOD billboard。说明该风格下 billboard 与实体的视觉断裂很小（平色、无复杂光照，烘焙图与实体渲染几乎一致）。
- **八面体 Impostor（Octahedral Impostor）**：预烘多视角图集到一张 quad/低模上按视角采样，由 Epic 的 Ryan Brucks 在 Fortnite 中大规模用于树（[shaderbits.com 技术文](https://shaderbits.com/blog/octahedral-impostors)，UE 插件 [ImpostorBaker](https://github.com/ictusbrucks/ImpostorBaker)）；树通常用 Hemi-Octahedron 布局（地平线过采样）。
- **Unity 现成工具**：**Amplify Impostors $60**（一键烘焙、八面体/球面、LODGroup 兼容、URP/HDRP；注意标准烘焙要求 shader 暴露 Deferred 路径，自定义 toon shader 需走 Custom Baking，[商店页](https://assetstore.unity.com/packages/tools/utilities/amplify-impostors-119877)）；Unity 官方 Pixyz Asset Transformer SDK 也内置 impostor 生成（[文档](https://docs.unity3d.com/Packages/com.unity.pixyz.unity-sdk@5.0/manual/features/impostors.html)）。
- **纯 shader 树 / billboard cloud**：不做实体网格、完全在着色器里用公告牌云/程序噪声拼树形。学术与 demo 场景有实践，但可控造型能力弱，近景经不起看。

### 4.2 对本项目的适用性判断

**它解决的是"渲染开销与远景数量"，不解决"造型泛化"**——无法替代建模路线；但作为**放大器**与方案 A 绝配：

1. 变体繁衍产出 N 棵实体树（近景 LOD0~3）；
2. 每棵变体烘一张 impostor/billboard 当末端 LOD（或复用 `_Card` 式十字卡），远景成本压到每棵 2~4 三角；
3. IL3DN 的平面化着色使烘焙图与实体渲染差异极小，是本技术最友好的画风。

结论：**推荐作为方案 A 的第二层（末端 LOD / 远景林），不推荐单独作为造型方案。**

---

## 5. 方案 E：摄影测量 / 扫描——不适合，排除

- 摄影测量产出的是**写实资产**：原始扫描"重、乱、拓扑脏"，必须重拓扑+清理才能进引擎（[Kevuru Games 管线文](https://kevurugames.com/blog/photorealism-vs-stylization-how-3d-art-outsourcing-studios-adapt-to-trends/)）。同一来源亦指出：风格化项目的生产逻辑恰恰相反——"不扫材料，而是先定义视觉语言规则（剪影、调色板、可读材质、简化几何）"。
- 对本项目目标（双色调绿、quad 叶卡、alpha 贴图、7k 三角以内），扫描提供的每一片真实叶脉都是要**亲手删掉**的信息；学界虽有"风格化摄影测量"探索（如 [DAE Howest 的毕业研究](https://www.artstation.com/artwork/R3bVze)），但属学术实验而非生产管线。
- 成本（外拍+设备+RealityCapture 类软件）与收益完全倒挂。**结论：排除。**

---

## 6. 横向对比表

评估维度：风格统一保障 / 泛化能力 / 自动化程度 / 成本 / Unity 管线兼容性（★1~5）。

| 方案 | 风格统一 | 泛化能力 | 自动化 | 成本 | Unity 兼容 | 总评 |
|---|---|---|---|---|---|---|
| **A. FBX 母体变体繁衍** | ★★★★★（零件零更换） | ★★★★（参数域内无限，形状族受限） | ★★★★★（脚本批量，基础设施已就绪） | ★★★★★（$0，复用已有资产+自研工具） | ★★★★★（FBX 直入 / C# 原生） | **主推** |
| B1. SpeedTree 10 | ★★（需从零复刻风格） | ★★★★★（任意树种） | ★★★（种子+SDK，但调风格靠人工） | ★★（$19/月起，库 +$999/年） | ★★★★★（Unity 亲儿子） | 风格成本双错配 |
| B2. Houdini | ★★（同左） | ★★★★★ | ★★★★（HDA 管线，学习曲线陡） | ★★（$299/年起；免费版不可产出） | ★★★★（HEngine 插件） | 团队无经验则排除 |
| B3. The Grove 3D | ★（写实生长模拟） | ★★★★ | ★★（Python 锁 €799 且仅 USD/OBJ） | ★（€799 + 授权限制） | ★★（需格式转换） | 不推荐 |
| C. 资产商店+随机化 | ★★★★（同包内）/★★（跨包） | ★★★（取决于包数量） | ★★★★（脚本组合） | ★★★★（$5~$50 一次性） | ★★★★★（原生 Unity 资产） | **推荐作 A 的母体池补充** |
| D. Impostor/渲染层 | ★★★★（烘焙自变体则一致） | ★（不产新造型） | ★★★★（一键烘焙） | ★★★★（$0~$60） | ★★★★★（LODGroup 原生） | **推荐作 A 的末端 LOD 放大器** |
| E. 摄影测量 | ☆（风格根本错配） | ★★ | ★★（重拓扑靠人工） | ★（设备+软件+人工） | ★★★ | 排除 |

---

## 7. Top 推荐

1. **主推：FBX 母体变体繁衍（方案 A）**。分两期：
   - 一期（1~2 天量级）：树干弯曲/扭转/缩放 + 叶卡 L1 抖动 + 顶点色重算 + ufbx 校验闭环，产 20~50 棵变体建库；
   - 二期：叶卡 L2 增删（簇级）→ L3 包络重排布，拉开形状差异；同步做 LOD 链同种子变换。
   落地优先用项目自研解析器+写出器（零新依赖）；若希望与 Unity 工程零距离，用 C# Mesh API + 官方 FBX Exporter 复刻同一套变换。
2. **叠加：Impostor 末端 LOD（方案 D 的引用部分）**。直接沿用母体 `_Card` 思路（十字卡+小图集），需要更高质量时上 Amplify Impostors（$60）。
3. **补充：扩充母体池（方案 C 玩法 A）**。$40 买下 The Illustrated Nature 整包，把同族树种全部变成变体母体——比任何"生成"都便宜且风格 100% 一致。
4. **明确不做**：SpeedTree/Houdini/The Grove（成本与风格双错配）、摄影测量（风格根本错配）、纯 shader 树（造型不可控）。

## 8. 风险清单

| 风险 | 等级 | 说明与对策 |
|---|---|---|
| 授权：变体=演绎作品 | 中 | IL3DN 资产（Unity AS EULA）可修改后用于**自己的游戏**，但**不得将变体库作为资产再分发/出售**；若未来需要无顾虑地分发，改用项目已验证的纯代码自生成母体（ProcPine 路线）当母本 |
| 风格漂移 | 中 | 形变/重排布参数必须从母体统计分布采样并设硬护栏；批量产出后人工或 vision 评审淘汰（可复用 `tools/vision_judge.py` 思路） |
| 风动画穿帮 | 中 | 任何几何变动后强制重算顶点色（A=z/H、G 重赋相位），写入流水线 checklist |
| LOD popping | 低 | 各级 LOD 用同一种子/同一位移场变换；切换距离沿用母体配置 |
| ufbx 绑定缺陷 | 低 | 已知 `node.parent` 悬空、同进程多文件段错误——批量校验逐文件起独立进程（`tools/validate_with_ufbx.py` 已有记录） |
| Unity FBX Exporter 限制 | 低 | 默认编辑器限定；运行时导出仅 64 位 Win/Mac/Linux 播放器且需 `FBXSDK_RUNTIME`（[官方文档](https://docs.unity3d.com/Packages/com.unity.formats.fbx@5.1/api/index.html)） |
| 管线色彩空间 | 低 | The Illustrated Nature 官方仅支持 Built-in RP；若项目用 URP，叶/树皮 shader 需自行迁移（变体路线不受影响，材质在 Unity 侧指定） |

## 9. 主要来源

- SpeedTree：[Unity 收购 IDV 公告](https://investors.unity.com/news/news-details/2021/Unity-Acquires-Interactive-Data-Visualization-Inc.-IDV-Creators-of-SpeedTree-Environment-Creation-Suite/default.aspx) · [官网/定价](https://speedtree.com) · [Learning/Indie/Pro/Enterprise 区别（Unity 支持）](https://support.unity.com/hc/ja/articles/15723241438228) · [SpeedTree Library $999/年订阅（Unity 支持）](https://support.unity.com/hc/en-us/articles/49699142648980) · [Indie $19/月订单页](https://service-store.unity.com/order/create?currency=USD&product=SPTR-INDIE)
- Houdini：[官方功能/价格对比表](https://www.sidefx.com/products/compare/) · [Apprentice 限制 FAQ](https://www.sidefx.com/ja/faq/apprentice/)
- The Grove 3D：[购买页（€99/199/799）](https://www.thegrove3d.com/buy/) · [版本对比（Python 自动化锁 Studio）](https://www.thegrove3d.com/compare/)
- 资产商店：[Stylized Nature Bundle $20](https://assetstore.unity.com/packages/3d/vegetation/trees/stylized-nature-bundle-135352) · [Low Poly Stylized Nature $4.99](https://marketplace.unity.com/packages/3d/environments/low-poly-stylized-nature-281338) · [The Illustrated Nature $40（IL3DN 出处）](https://assetstore.unity.com/packages/3d/vegetation/the-illustrated-nature-153939) · [Unity AS Terms](https://unity.com/legal/as-terms)
- Fab：[上线公告（Standard License 跨引擎）](https://sketchfab.com/blogs/community/epics-unified-marketplace-fab-launches-today/) · [Fab EULA](https://www.fab.com/eula) · [Stylized Trees Pack（模块化可拼装）](https://www.fab.com/listings/f09236d3-fcdc-44ca-b242-d6d1ca795969)
- Impostor：[Ryan Brucks: Octahedral Impostors（Fortnite）](https://shaderbits.com/blog/octahedral-impostors) · [Amplify Impostors $60](https://assetstore.unity.com/packages/tools/utilities/amplify-impostors-119877) · [Unity Pixyz Impostors 文档](https://docs.unity3d.com/Packages/com.unity.pixyz.unity-sdk@5.0/manual/features/impostors.html)
- 摄影测量：[Kevuru: Photorealism vs Stylization 管线对比](https://kevurugames.com/blog/photorealism-vs-stylization-how-3d-art-outsourcing-studios-adapt-to-trends/)
- FBX 工具链：[ufbx 官网](https://ufbx.github.io/) · [pyufbx on PyPI](https://pypi.org/project/pyufbx/) · [aras-p：Blender 4.5 基于 ufbx 的 FBX 导入器](https://aras-p.info/blog/2025/05/08/Blender-FBX-importer-via-ufbx/) · [Autodesk FBX SDK 下载页](https://aps.autodesk.com/developer/overview/fbx-sdk?rel=outbound) · [Unity FBX Exporter 文档](https://docs.unity3d.com/Packages/com.unity.formats.fbx@4.2/manual/index.html) · [FBX Exporter API](https://docs.unity3d.com/Packages/com.unity.formats.fbx@5.1/api/index.html)
