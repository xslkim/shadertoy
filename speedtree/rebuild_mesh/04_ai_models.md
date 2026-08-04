# AI 模型生成 3D 树木调研报告（2026-08 最新状态）

> **命题**：能不能用"AI 生成 3D 模型"的路线，自动产出 `mesh/IL3DN_Tree_Beech_02/` 这类风格化树——单根细长树干 + 大量叶卡片（quad）簇 + 带 alpha 的叶子贴图 + 绿色双色调平面着色，且多棵树形状不同、风格统一、复用同一张 `IL3DN_Leaf_01.png`，最终落地 Unity。
>
> **一句话结论**：截至 2026 年 8 月，**没有任何 AI 3D 模型能直接生成"叶卡片 + 指定贴图"结构的树**——所有主流模型输出的都是实心网格 + 烘焙贴图，叶冠会被生成成"一坨实心体"。**可行路线是"AI + 程序化混合管线"：AI 只负责出树干/树冠包络，叶卡片沿用项目现有的程序化散射逻辑挂接**。这与学术界最新的树木生成研究方向（骨架 AI 生成、叶片程序化添加）完全一致。
>
> 调研以网络资料为主，关键结论附来源链接。价格信息采集于 2026-07~08，云服务定价变动频繁，使用前请以官网为准。

---

## 1. 候选工具总览

### 1.1 云服务（图生 3D / 文生 3D）

| 名称 | 公司 | 当前模型 | 批量 API | 参考价格 | 导出格式 | 链接 |
|---|---|---|---|---|---|---|
| **Tripo AI** | VAST | v3.1 / H3.1（2026-02） | ✅ 官方 API + 多家第三方聚合 | 订阅：免费 300 积分/月；专业版 ¥150/月（国内）/ $19.90（国际）；第三方 API 约 $0.3~0.4/次 | GLB/FBX/OBJ/USD/STL/3MF | [官网](https://www.tripo3d.ai/) / [API 定价参考](https://wavespeed.ai/docs/docs-api/tripo3d/tripo3d-h3.1-image-to-3d) |
| **Meshy** | Meshy | Meshy 6 | ✅ 官方 API（积分制） | 免费 100 积分/月；Pro ~$20/月；API 图生 3D 30 积分/次（带纹理），实测约合 $0.6~2/棵 | GLB/FBX/OBJ/USDZ/STL/3MF | [官网](https://www.meshy.ai/) / [API 定价](https://docs.meshy.ai/en/api/pricing) |
| **Hyper3D Rodin** | Deemos/影眸 | Gen-2（10B，2025-10）/ Gen-2.5 | ✅ 完整 API 需商业版（120-240 RPM） | 创作者 €30/月；商业 €120/月；标准生成 0.5 积分/次；第三方 API $0.4/次起 | GLB/FBX/OBJ/USDZ/STL | [官网](https://hyper3d.ai/) / [定价分析](https://www.cnblogs.com/2025-html/p/21970702) |
| **Luma Genie** | Luma AI | Genie 2（2025-12） | ❌ 无公开批量 API（Web 为主，Luma 官方 API 重心在视频模型） | 免费 5 次/天；Pro ~$25~30/月 | GLB/FBX/OBJ | [官网](https://lumalabs.ai/genie) / [Genie 2 信息](https://aisavr.com/tools/luma-genie-2/) |
| **腾讯混元生 3D（云）** | 腾讯 | 3.0（1536³，2025-09） | ✅ 腾讯云 API（专业版/极速版），2025-11 已开放国际站 | 积分制约 0.1 元/积分，新用户免费 100 积分；单棵成本约 ¥1.8~2.4 量级 | GLB/FBX/OBJ 等 | [官网](https://3d.hunyuan.tencent.com/) / [计费文档](https://cloud.tencent.cn/document/product/1804/123461) |
| **Sloyd**（参数化+AI 混合） | Sloyd | — | ✅（企业版） | 免费档；Pro ~$15/月 | GLB/FBX/OBJ/STL，多 LOD | [官网](https://www.sloyd.ai/) |
| **Stable Fast 3D API** | Stability AI | SF3D | ✅ 官方 REST API | 2 积分/次 | GLB | [API 文档](https://platform.stability.ai/docs/api-reference#tag/3D) |

### 1.2 本地可部署开源模型

| 名称 | 出品 | 参数/协议 | VRAM | 输出 | 备注 | 链接 |
|---|---|---|---|---|---|---|
| **Hunyuan3D-2.1** | 腾讯 | 3.3B shape + 2B paint；**腾讯混元社区许可**（排除 EU/UK/韩国，有 MAU 限制） | 形状 6 GB；官方全管线 ~29 GB；社区 GP 分支可压到 6 GB | GLB（PBR 贴图） | 2025-06 完全开源（含训练代码），生态最成熟（ComfyUI/Blender 插件/WinPortable） | [GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) |
| **Hunyuan3D 2.5 / 3.0** | 腾讯 | 10B（2.5）| — | — | **权重未开源**（截至 2026-04 仅有技术报告），只能走云服务 | [2.5 技术报告](https://arxiv.org/abs/2506.16504) |
| **Hunyuan3D-Part / Omni** | 腾讯 | 开源（2025-09） | 同 2.1 系列 | 部件级网格 | **对本项目最有价值的衍生件**：P3-SAM 语义分割 + X-Part 部件生成，可把整树拆成"树干/树冠"等独立部件；Omni 支持 bbox/体素/点云多条件控制 | [介绍](https://www.aifun.cc/tencent-hybrid-3d-model-released-and-open-source.html) |
| **Hunyuan3D-PolyGen** | 腾讯 | 开源（2025-07） | — | 四边/三角面 | 自回归"美术级拓扑"网格模型，输出干净布线 | 见 [Hunyuan 3D 版本沿革](https://aiwiki.ai/wiki/hunyuan_3d) |
| **TRELLIS.2** | Microsoft Research | 4B；**MIT** | 16 GB 起步，24 GB+ 推荐 | GLB/OBJ/PLY + PBR；也出 3D Gaussian | 2025-12 发布，O-Voxel 架构支持开表面/任意拓扑，开源里几何质量最高；ComfyUI 节点成熟 | [项目页](https://microsoft.github.io/TRELLIS/) / [HF](https://huggingface.co/microsoft/TRELLIS.2-4B) |
| **TRELLIS（初代）** | Microsoft Research | 1.2B/2B；MIT | 官方 16 GB，社区 fp16 优化到 8 GB | GLB/Gaussian/辐射场 | 2024-12 发布，老但轻量 | [GitHub](https://github.com/microsoft/TRELLIS) |
| **TripoSG** | VAST | 1.5B；MIT | ~6 GB | 仅几何（无纹理） | rectified flow 单图生形状，需另配 MV-Adapter 做贴图 | [GitHub](https://github.com/VAST-AI-Research/TripoSG) |
| **TripoSR** | VAST + Stability | —；MIT | ~6 GB，<0.5 s/棵 | OBJ（顶点色，无 UV 贴图） | 前馈极速但质量粗糙，只配当草稿 | [GitHub](https://github.com/VAST-AI-Research/TripoSR) |
| **Stable Fast 3D（本地）** | Stability AI | —；**Stability 社区许可**（年营收 <$1M 免费商用） | ~7 GB，0.5 s/棵 | UV 展开贴图 + 材质参数 + 去光照 | 速度快、自带 UV，适合批量出候选 | [GitHub](https://github.com/Stability-AI/stable-fast-3d) |

---

## 2. 详细评估

### 2.1 云服务

**Tripo AI（VAST）**
- 能力链最完整：文生/图生/多视图生 3D，最高 200 万面，内置智能拓扑（2 秒出干净布线）、自定义面数重拓扑、部件拆分、一键绑骨、AI 生图（平台内集成生图模型，可先做风格化概念图再转 3D）。导出 GLB/FBX/OBJ/USD/STL/3MF，带 PBR 贴图包。([官方帮助页](https://studio.tripo3d.com/help.html))
- API：官方企业级 API + Runware/WaveSpeed 等聚合商按次计费（文生 $0.3、图生 $0.4、quad 拓扑 +$0.05），支持 webhook、批量并发（numberResults 最多 4 个变体）。([Runware 文档](https://runware.ai/docs/models/tripo-v3-1))
- 一致性：有 seed/风格强度参数；第三方 API（Scenario）暴露 `textureSeed`，同 seed 可复现相同贴图。([Tripo 官方博客讲提示词漂移](https://www.tripo3d.ai/zh/blog/explore/ai-3d-model-generator-and-prompt-drift-across-iterations))
- 值得注意：Tripo 官方写的"如何制作 3D 树木模型"教程，推荐的依然是**传统做法**——"为树种创建 2-3 个叶片卡片（带 alpha 纹理的交叉多边形或简单平面），用粒子系统/散射工具/几何节点填充树冠体积"，而不是让 AI 直接生成整树。([Tripo 官方博客](https://www.tripo3d.ai/zh/blog/explore/how-to-make-a-tree-3d-model))

**Meshy**
- 有专门的 **Low Poly（Meshy T1）** 模式面向游戏低模资产，以及 **Smart Topology（T2）** 重拓扑；可配置拓扑类型（三角/四边）与目标面数。Meshy 6 的自动重拓扑已能产出四边主导网格与基本干净的 UV。([API 定价](https://docs.meshy.ai/en/api/pricing)、[2026 横评](https://ziva.sh/blogs/best-ai-3d-asset-generators))
- 风格一致性是其卖点：官方提倡"风格锚点"提示词法（固定色调/材质/轮廓描述词跨资产复用），Web 端 3D Agent 支持批量概念图生成并保持批次内风格一致——但**该能力在 Web 端对话流程里，API 层没有等价的"风格锁定"参数**。([Meshy 风格一致性案例](https://www.meshy.ai/ko/blog/3D-prompt-engineering)、[3D Agent 文档](https://docs.meshy.ai/en/webapp/3d-agent))
- 集成：Blender/Unity 官方插件，API 支持 webhook；图生 3D 带纹理 30 积分/次（8K 35 积分）。

**Hyper3D Rodin**
- Gen-2（10B 参数 BANG 架构，2025-10）在四边主导网格、面数档位（4K~50K quad / 2K~500K tri）、bbox 尺寸约束上控制粒度最细；横评中有机物体精度最高（适合树干这类有机曲面）。([Runware Rodin Gen-2](https://runware.ai/docs/models/hyper3d-rodin-gen-2)、[ziva 横评](https://ziva.sh/blogs/best-ai-3d-asset-generators))
- 有一个对本项目有意思的参数：**`use_original_alpha`——保留输入图像的透明通道**，理论上可让带 alpha 的叶子参考图在生成中保留透明信息（效果如何需实测）。([WaveSpeed Rodin v2.5 参数表](https://wavespeed.ai/docs/docs-api/hyper3d/hyper3d-rodin-v2.5-image-to-3d))
- 商业模式独特："先看预览满意再扣费"；但**完整 API 只在 €120/月商业版**（120-240 RPM），免费版生成物不可商用。

**Luma Genie**
- Genie 2（2025-12）质量有提升（干净拓扑、PBR、多平台面数优化、GLB/FBX 导出），但**没有公开批量 API**，Luma 公司 2026 年战略重心在 Dream Machine 视频模型与 3DGS 捕捉，Genie 定位偏"快速预览/玩具"。不适合自动化管线。([aiwiki Luma AI](https://aiwiki.ai/wiki/luma_ai))

**腾讯混元生 3D（云服务）**
- 3.0 模型几何分辨率 1536³，面向游戏引擎直用；腾讯云 API 分专业版/极速版，积分制（资源包约 0.1 元/积分，后付费 0.12 元/积分，新用户 100 积分免费），另有智能拓扑、纹理生成、**组件生成**、UV 展开、模型格式转换等独立后处理接口——后处理接口可单独调用，适合嵌入混合管线。([计费文档](https://cloud.tencent.cn/document/product/1804/123461)、[Hunyuan 3D 沿革](https://aiwiki.ai/wiki/hunyuan_3d))
- 生态背书：Unity 中国、Bambu Lab 等 150+ 企业集成；2025-11 起开放国际站英文 API。

**Sloyd（参数化 + AI 混合，参照系）**
- 不是扩散模型路线，而是"参数化模板库 + AI 把文本映射到模板参数"，输出天然游戏就绪（干净拓扑、LOD、自动 UV），模板库含植物/植被类。这恰好证明了"程序化骨架 + AI 做参数/引导"的工程价值；但其模板风格无法定制成 IL3DN 的双色调叶卡片风格，对本项目只是方法论参照。([Sloyd 评测](https://tooliverse.ai/tools/sloyd)、[Sloyd 官方](https://www.sloyd.ai/text-to-3d))

### 2.2 本地开源模型

**Hunyuan3D-2.1（腾讯，2025-06）——本地首选基线**
- 当前**最后一个完全开源的版本**（推理代码 + 训练代码 + PBR 纹理管线 + 权重全放）；2.5（10B，1024³ 几何）与 3.0（1536³）截至 2026-04 未开放权重，只能走云。([GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)、[Codersera 2026 安装指南](https://codersera.com/blog/set-up-hunyuan3d-2-on-windows-a-step-by-step-guide/))
- 资源占用：形状生成 6 GB VRAM 即可（2GP 社区分支最低 4~6 GB），官方 2.1 全管线约 29 GB，RTX 4090 上单棵 8~20 秒（2.5 报告口径）。输出 trimesh/GLB。
- 对本项目的特殊价值不在基模型本身，而在衍生件：
  - **Hunyuan3D-Part**（2025-09 开源）：P3-SAM 原生 3D 语义分割 + X-Part 部件生成，可把生成的整树自动拆成 50+ 语义部件——**有望直接分离"树干部件"与"树冠部件"**，这正是混合管线需要的剪刀。([发布介绍](https://www.aifun.cc/tencent-hybrid-3d-model-released-and-open-source.html))
  - **Hunyuan3D-Omni**：bbox/体素/点云/骨骼多条件控制，可用 bbox 约束树的高宽比，解决单图生成"纸片树"问题。
  - **Hunyuan3D-PolyGen**：自回归干净拓扑（quad/tri），可作为重拓扑环节。
- ⚠️ 许可：**腾讯混元社区许可而非 Apache/MIT**——商业使用有 MAU 限制且明确排除 EU/UK/韩国用户。国内团队自用/商用一般无碍，但出海产品需注意。([aiwiki 许可条目](https://aiwiki.ai/wiki/hunyuan_3d))

**TRELLIS.2（微软，2025-12）——开源几何质量上限**
- 4B 参数，O-Voxel 表示法原生支持开表面、非流形、内部结构——理论上比 SDF+Marching Cubes 路线更适合"薄片状"几何；PBR 材质（BaseColor/Roughness/Metallic/**Opacity**），GLB/OBJ/PLY 导出，MIT 协议可自由商用。([TRELLIS.2 介绍](https://trellis-2.org/)、[ComfyUI 指南](https://trellis2.app/blog/comfyui-3d-model-generator-microsoft))
- 门槛：16 GB VRAM 起步、24 GB+ 推荐（H100 上 512³ 约 3 秒，1536³ 约 60 秒）；ComfyUI 节点（ComfyUI-TRELLIS2）已成熟，可编排"生图→几何→贴图→导出 GLB"批量流。
- 注意：Opacity 通道输出 ≠ 叶卡片结构，只是把薄片画透明；网格本体仍是实心提取物。

**TripoSG / TripoSR / SF3D——轻量快速档**
- TripoSG（MIT，6 GB）：只出几何不出纹理，恰好契合"AI 只出形状、贴图程序化"的思路，但模型是 2025-02 的，几何质量已落后于 TRELLIS.2/Hunyuan3D。([GitHub](https://github.com/VAST-AI-Research/TripoSG))
- SF3D（0.5 s/棵，7 GB，自带 UV 展开 + 去光照 + 粗糙度/金属度）：速度无敌，适合批量出几百个树干候选再筛选；许可有 $1M 年营收门槛。([HF 模型卡](https://huggingface.co/stabilityai/stable-fast-3d))
- TripoSR 已过时（顶点色、无 UV、质量糙），仅作历史参照。

### 2.3 植被/树木专项 AI 研究（2025-2026）

学术界没有在做"端到端生成带叶卡片的游戏树"，主流方向惊人一致地走向 **"AI 出骨架/包络 + 程序化挂叶"**：

| 工作 | 来源 | 做法 | 与本项目的关系 |
|---|---|---|---|
| **HourglassTree** | KAUST/CASIA，arXiv 2502.04762（2025-02） | hourglass transformer 自回归生成树骨架，支持无条件生成、生长模拟、点云/草图条件生成；**"Our method generates the tree skeleton while leaves are added procedurally"（骨架靠生成，叶片程序化添加）** | 直接验证混合管线的学术合理性 |
| **Tree-D Fusion** | Purdue 等，ECCV 2025 | 单张街景图 → 双扩散模型蒸馏出 3D 树冠包络（envelope）→ **空间殖民算法（space colonization）在包络内估计枝干结构** → 仿真就绪树模型 | "AI 出冠形包络 → 程序化长骨架"正是本报告建议的 A2 方案 |
| **Learning to Infer Parameterized Representations of Plants from 3D Scans** | CVPR 2026 | 从 3D 扫描反推 L-system（L-String）参数化表示 | AI 反推程序化参数，另一形态的"AI+程序化" |
| 林业方向（AAE 树种点云生成、ForestGen3D LiDAR 扩散） | WSL/LANL 等 | 生成真实树种点云用于森林可视化 | 偏科研/林业，与游戏资产无关，仅说明领域热度 |

结论：**"树叶 = alpha 卡片散射"在 AI 时代依然是工程标准答案**，连 Tripo 官方教程和顶会论文都这么做。AI 的价值定位是"形状先验的提供者"，不是"完整资产的交付者"。

---

## 3. 与本项目目标的四个关键差距

### 3.1 风格统一性：部分可控，但达不到"严格同一风格"

- **能控的**：图生 3D 模式下喂同一张风格化参考图（如 screenshot-1.png），多棵树的几何风格会大致同源；Tripo 的 seed/`textureSeed`、风格强度参数可复现单次结果；Meshy 的"风格锚点"提示词法可约束色调与材质关键词。
- **控不住的**：扩散模型每次重新"画"贴图，跨生成存在色彩漂移——做不到每棵树都是精确的"同一组绿色双色调"；文生 3D 的随机性更大（prompt drift 是公认问题，Tripo 官方博客专门讲怎么缓解）。
- **根本解法**：把"风格"从 AI 手里拿走——AI 只出几何，颜色和贴图全部程序化指定（见 §4）。

### 3.2 贴图复用：不能直接强制，只能绕

- 所有 AI 3D 模型的贴图都是"多视角扩散绘制 → 烘焙到自动展开的 UV"产物，**没有任何 API 支持"用我给的 IL3DN_Leaf_01.png 当叶贴图"**。UV 布局每棵树随机，贴图内容每棵树新画。
- 最接近的两个特例：Rodin 的 `use_original_alpha`（保留输入图透明通道）；Hunyuan3D-Paint / SF3D 的"给已有网格重新画贴图"模式（可反向用于：把 AI 生成的树干丢给它画皮——但画出来仍不是指定的 Bark_Pine.png）。
- **替代思路（推荐）**：AI 几何 + 程序化材质。树干用柱状 UV 重投影后贴 `IL3DN_Bark_Pine.png`；叶卡片直接复用项目现有散射逻辑贴 `IL3DN_Leaf_01.png`。贴图复用问题转化为"根本不让 AI 管贴图"。

### 3.3 拓扑与结构：实心叶团 vs 叶卡片，这是本质差距

- 主流模型（Hunyuan3D/TRELLIS/Tripo/Meshy/Rodin）的几何表示都是隐式场（SDF/occupancy）+ Marching Cubes/DMTet 表面提取，**输出必然是封闭实心表面**。树叶在这种表示里只能是一团实心"绿坨"，不可能生成"镂空 quad + alpha 贴图"的卡片结构——训练数据和监督信号（单图/多视图 2D 投影）都不包含这种结构信息。TRELLIS.2 的 O-Voxel 支持开表面是最接近的，但也只是"薄片"，不是"共享贴图的卡片实例"。
- 原始输出面数几十万~上百万三角面，必须重拓扑：Tripo 智能拓扑（自定义面数/四边化）、Meshy Remesh/T2、Rodin 面数档位、混元智能拓扑 API、本地 Blender/Instant Meshes 都能解决**面数**问题；但重拓扑解决不了**结构**问题——减面后的实心叶团依然不是叶卡片，侧看没有轮廓层次，也无法用一张共享叶贴图。
- 游戏实时性：重拓扑到几千面后树干完全可用；叶部若保留 AI 几何则无论多少面都不符合本项目渲染风格（平面化、双色调、alpha 裁剪）。

### 3.4 成本与自动化友好度

| 路线 | 单棵成本 | 批量自动化 | 备注 |
|---|---|---|---|
| 混元云 API | ~¥0.2~2.4 | ✅ 积分制 + webhook | 国内最便宜，后处理接口可拆用 |
| Tripo API | ~$0.3~0.4（¥2~3） | ✅ 并发 4 变体 + webhook | 第三方聚合商免订阅按次付 |
| Meshy API | 30 积分/次（约 $0.6~2） | ✅ 20 RPS | 订阅制积分 |
| Rodin API | 0.5 积分/次（约 €0.5），但 API 门槛 €120/月 | ⚠️ RPM 120-240 | "预览满意才扣费"降低浪费 |
| 本地（TRELLIS.2/Hunyuan3D-2.1/SF3D） | 电费可忽略，单棵 0.5 秒~2 分钟 | ✅ 完全自控 | 需 6~24 GB VRAM 的 N 卡 |

结论：**批量生 100 棵候选树的预算在 ¥0（本地）~ ¥300（云端）之间，成本不是瓶颈**，瓶颈是 §3.1~3.3 的质量差距。

---

## 4. "AI + 程序化混合管线"可行性分析（核心建议）

项目已有完整的程序化能力（`tools/pine_gen.py` 的叶卡散射、`fbx_writer.py`、顶点色风数据约定、Blender MCP 渲染验证），混合管线是把 AI 嵌进现有管线的"形状来源"位置，而非另起炉灶。

### 方案 A1：AI 出树干 → 程序化挂叶（首选，改动最小）

```
风格化参考图（截图/AI 生图）
  → 图生 3D（关纹理，只要几何；本地 Hunyuan3D-2.1 / TRELLIS.2 或云 API）
  → Hunyuan3D-Part / Meshy 部件拆分，分离"树干+枝"部件（或直接生成时 prompt 只要 bare trunk）
  → 重拓扑减面到 1~3k 面（Tripo/混元智能拓扑 或 Blender）
  → 柱状 UV 重投影 → 复用 IL3DN_Bark_Pine.png
  → 程序化分析枝干端点/冠层区域（连通分量 + 骨架化，tools 已有类似分析器）
  → 现有叶卡散射逻辑在枝端/冠层挂 quad → 复用 IL3DN_Leaf_01.png
  → 写入顶点色风数据（沿用项目 A=高度、G=相位 约定）→ FBX → Unity
```

- 风格统一性来源：贴图与着色 100% 程序化指定，AI 只影响"树的形状"——这正是目标（形状不同、风格统一）。
- 可行性：每个环节都有现成工具；最大不确定点是 **AI 生成的树干形态是否符合"细长卡通干"审美**（AI 训练分布偏写实粗干），需要实测筛选或用 prompt/参考图约束。

### 方案 A2：AI 出整树 → 提取冠层包络 → 程序化重建（Tree-D Fusion 思路）

```
图生 3D 出整树（实心叶团）
  → 体素化/凸包提取树冠包络 + 树干区域
  → 树干部分按 A1 处理；冠层包络内用空间殖民/随机散射填充叶卡片
  → AI 几何的叶部整体丢弃，只当"冠形参考"
```

- 适合"想要 AI 设计树冠整体造型（团块分布、疏密），但渲染用叶卡片"的场景；比 A1 多一步包络分析，工程上不复杂（项目已有 FBX 分析器可改造）。

### 方案 B：风格概念前置——AI 生图 → 图生 3D

把"风格统一"问题转移到最成熟的 2D 环节：先用文生图（同 LoRA/同风格提示词）批量产出风格统一的卡通树概念图，挑图走图生 3D 进方案 A1。Tripo 平台内已集成生图模型支持此流；Meshy 3D Agent 的"批量概念图 + 风格一致"也是同一思路（但仅 Web 端）。

### 方案 C：纯程序化（现状延续）+ AI 做辅助分析

延续现有程序化生成，仅用 AI 做：① 概念图生成（给程序化参数调方向）；② vision_judge.py 式的自动审美筛选。零新风险，但形状多样性上限低于 A1。

### 推荐路线

**A1 为主，B 为前置增强，C 为保底**。先做小规模实测（10~20 棵）：本地 TRELLIS.2 或 Hunyuan3D-2.1 出树干 + 现有挂叶逻辑，验证"AI 树干形态可用率"；若可用率 >50%，批量成本即可接受（云服务 ¥2~3/棵 × 筛选率，或本地零边际成本）。

---

## 5. 推荐程度（1-5 星，针对本项目目标）

| 工具/路线 | 推荐度 | 理由 |
|---|---|---|
| **混合管线 A1（AI 树干 + 程序化挂叶）** | ★★★★★ | 唯一能同时满足"形状多样 + 风格严格统一 + 贴图复用 + Unity 落地"的路线，且有学术先例 |
| 腾讯混元 3D（云 API + Hunyuan3D-2.1/Part 本地） | ★★★★☆ | 成本最低、开源生态最全、Part 部件拆分正中需求；扣一星：许可限制 EU/UK/韩国、树干审美需实测 |
| TRELLIS.2（本地） | ★★★★☆ | MIT 许可干净、开源几何质量最高、ComfyUI 批量流成熟；扣一星：24 GB VRAM 门槛 |
| Tripo AI（云） | ★★★☆☆ | 能力链完整、第三方 API 按次付费灵活、seed 可控；直出整树不可用，只能当形状来源 |
| Meshy（云） | ★★★☆☆ | Low Poly 模式 + Unity 插件友好；风格锁定能力在 Web 端，API 层弱 |
| Hyper3D Rodin（云） | ★★★☆☆ | 有机体精度最高、面数/bbox 控制细、`use_original_alpha` 值得试；API 捆绑 €120/月商业版 |
| SF3D / TripoSG（本地轻量） | ★★★☆☆ | 批量出树干候选的低成本选项；几何质量一般 |
| 专项研究（HourglassTree / Tree-D Fusion） | ★★★☆☆ | 方向性验证价值高；权重/代码工程化成本未知，不宜直接依赖 |
| Luma Genie | ★★☆☆☆ | 无批量 API，公司重心已转向视频 |
| Sloyd | ★★☆☆☆ | 方法论参照（参数化+AI），风格不可定制 |
| TripoSR | ★☆☆☆☆ | 已过时 |
| **任何"AI 直出整树直接用"的方案** | ★☆☆☆☆ | 实心叶团 + 随机烘焙贴图，与目标风格三重冲突（结构/贴图/色调） |

---

## 6. 风险清单

1. **许可风险**
   - Hunyuan3D 全家族是腾讯混元社区许可：有 MAU 限制、**明确排除 EU/UK/韩国**——若产品出海欧洲需谨慎。([aiwiki](https://aiwiki.ai/wiki/hunyuan_3d))
   - SF3D：年营收 ≥$1M 需企业许可。([HF 模型卡](https://huggingface.co/stabilityai/stable-fast-3d))
   - Rodin 免费/创作者档生成物商用受限；各云平台免费档普遍禁止商用或要求署名，批量前核对条款。([Rodin 定价分析](https://www.cnblogs.com/2025-html/p/21970702))
   - 干净选择：TRELLIS.2 / TripoSG / TripoSR（MIT）。
2. **信息可靠性**：本次调研中大量价格/参数来自第三方聚合站（wavespeed、runware、fairstack）与非官方镜像站（trellis-2.org、hunyuan3d.dev、tripoai3d.com 等，存在夸大宣传），**签约/充值前务必以官方文档为准**。
3. **风格适配风险**：AI 3D 模型训练分布偏写实，"细长卡通树干"的生成成功率未知；可能需要在参考图（用 AI 生图定制）和 prompt 上反复调，或直接退化为方案 C。
4. **树皮贴图复用需额外工序**：AI 树干的自动 UV 与 `IL3DN_Bark_Pine.png` 的柱面展开方式不同，需程序化柱状重投影，树皮纹理密度/接缝要调。
5. **部件拆分不确定性**：Hunyuan3D-Part 在"树"上的分割语义（能否稳定分出树干 vs 树冠）未经实测；备选是生成阶段就 prompt "bare tree trunk, no leaves"。
6. **API 稳定性与限流**：云服务均有 RPM/并发限制，批量生成需队列化 + 失败重试；订阅价格与积分规则变动频繁（本报告价格仅 2026-08 快照）。
7. **研究代码落地风险**：HourglassTree/Tree-D Fusion 等论文代码的权重可得性、license、工程化难度均未验证，仅作方法论参考。

---

## 7. 附：主要信息来源

**云服务**
- Tripo：[官方帮助/价格](https://studio.tripo3d.com/help.html)、[Runware Tripo v3.1 API](https://runware.ai/docs/models/tripo-v3-1)、[WaveSpeed Tripo H3.1 图生3D](https://wavespeed.ai/docs/docs-api/tripo3d/tripo3d-h3.1-image-to-3d)、[国际版价格（非官方整理）](https://www.tripoai3d.com/)
- Meshy：[API 定价](https://docs.meshy.ai/en/api/pricing)、[图生3D API 教程](https://www.meshy.ai/tutorials/api-quickstart-image-to-3d)、[风格一致性用户案例](https://www.meshy.ai/ko/blog/3D-prompt-engineering)、[3D Agent](https://docs.meshy.ai/en/webapp/3d-agent)、[FairStack Meshy V6 比价](https://fairstack.ai/models/meshy-v6-i23d)
- Rodin：[Runware Rodin Gen-2](https://runware.ai/docs/models/hyper3d-rodin-gen-2)、[WaveSpeed Rodin v2.5](https://wavespeed.ai/docs/docs-api/hyper3d/hyper3d-rodin-v2.5-image-to-3d)、[定价与商用授权分析](https://www.cnblogs.com/2025-html/p/21970702)
- Luma：[aiwiki Luma AI](https://aiwiki.ai/wiki/luma_ai)、[Genie 2 工具页（非官方）](https://aisavr.com/tools/luma-genie-2/)
- 混元云：[计费文档](https://cloud.tencent.cn/document/product/1804/123461)、[Hunyuan 3D 版本沿革](https://aiwiki.ai/wiki/hunyuan_3d)、[全球发布](https://www.atlascloud.ai/providers/tencent)
- 横评：[2026 九款 AI 3D 生成器游戏向横评](https://ziva.sh/blogs/best-ai-3d-asset-generators)

**本地开源**
- [Hunyuan3D-2 GitHub](https://github.com/Tencent-Hunyuan/Hunyuan3D-2)、[2026 Windows 安装指南（VRAM 实测）](https://codersera.com/blog/set-up-hunyuan3d-2-on-windows-a-step-by-step-guide/)、[Hunyuan3D 2.5 技术报告](https://arxiv.org/abs/2506.16504)、[混元3D-Omni/Part 发布](https://www.aifun.cc/tencent-hybrid-3d-model-released-and-open-source.html)
- [TRELLIS.2 项目页](https://microsoft.github.io/TRELLIS/)、[TRELLIS.2-4B HF](https://huggingface.co/microsoft/TRELLIS.2-4B)、[ComfyUI 指南（非官方）](https://trellis2.app/blog/comfyui-3d-model-generator-microsoft)、[初代 TRELLIS 8GB 优化](https://habr.com/ru/articles/876636/)
- [TripoSG](https://github.com/VAST-AI-Research/TripoSG)、[TripoSR](https://github.com/VAST-AI-Research/TripoSR)、[SF3D HF](https://huggingface.co/stabilityai/stable-fast-3d)、[SF3D CVPR 2025 论文](https://openaccess.thecvf.com/content/CVPR2025/papers/Boss_SF3D_Stable_Fast_3D_Mesh_Reconstruction_with_UV-unwrapping_and_Illumination_CVPR_2025_paper.pdf)

**树木专项研究**
- [HourglassTree（arXiv 2502.04762）](https://arxiv.org/pdf/2502.04762)
- [Tree-D Fusion（ECCV 2025）](https://www.cs.purdue.edu/cgvlab/www/resources/papers/Lee-ECCV-2025-TreeDFusion.pdf)
- [CVPR 2026 植物参数化推断](https://openaccess.thecvf.com/content/CVPR2026/papers/Ghrer_Learning_to_Infer_Parameterized_Representations_of_Plants_from_3D_Scans_CVPR_2026_paper.pdf)
- [ForestGen3D（arXiv 2509.16346）](https://arxiv.org/html/2509.16346v2/)

**叶卡片做法佐证**
- [Tripo 官方：如何制作 3D 树木模型（推荐卡片散射）](https://www.tripo3d.ai/zh/blog/explore/how-to-make-a-tree-3d-model)
