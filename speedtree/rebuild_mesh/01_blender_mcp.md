# 01 · 本机 Blender + MCP 自动生成风格化树木 — 调研报告

- 日期：2026-08-03
- 项目：`d:\shadertoy\speedtree`
- 参考资产：`mesh\IL3DN_Tree_Beech_02\`（`IL3DN_Tree_Birch_02.FBX`、`IL3DN_Bark_Pine.png`、`IL3DN_Leaf_01.png`、`screenshot-1/2.png`）
- 目标风格：风格化/低多边形卡通树。单根细长略带弯曲的主干；下部 1~3 根光秃短枝；树冠由 3~5 团叶卡片（quad 面片）簇构成；叶卡片使用带 alpha 的叶贴图图集，绿色双色调渐变，平面化（flat）着色。两张 PNG 贴图的 RGB 接近白色/浅灰，**形状信息在 alpha 通道**，最终颜色由着色端（tint/渐变）赋予——这是该风格资产的关键约定。
- 目标运行时：Unity（FBX 导入）。

---

## 1. 本机环境验证结果

| 检查项 | 结果 | 说明 |
|---|---|---|
| Blender 安装 | ✅ **Blender 4.2.16 LTS** | `C:\Program Files\Blender Foundation\Blender 4.2\blender.exe`（未加入 PATH，需全路径调用） |
| blender-mcp Blender 侧插件 | ✅ 已安装且**已启用** | `C:\Users\xsl\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\blender_mcp`，bl_info 版本 **(1, 2)**（偏旧，见风险节） |
| blender-mcp Python 服务 | ✅ **blender-mcp 1.6.4** + mcp 1.27.0 | 系统 Python 3.12.10 pip 安装，含入口 `C:\Users\xsl\AppData\Local\Programs\Python\Python312\Scripts\blender-mcp.exe`；**uv 未安装**（不影响，可直接指向 exe） |
| MCP 端口 9876 | ⚠️ 当前**未监听** | `Test-NetConnection → TcpTestSucceeded: False`。正常：需先打开 Blender GUI，在 N 面板 BlenderMCP 页点 "Start MCP Server" 才会监听 |
| MTree (Modular Tree) 插件 | ✅ v5.0.0 已安装，**实测可在 4.2 启用** | 同目录 `mtree`；默认未勾选，`bpy.ops.preferences.addon_enable(module='mtree')` 后台实测成功 |
| Sapling Tree Gen | ❌ 本机不可用 | Blender 4.2 起从内置插件移除，迁移到扩展平台（extensions.blender.org/add-ons/sapling-tree-gen），需联网安装 |
| FBX 导出器 | ✅ `io_scene_fbx` 内置且已启用 | 后台实测 `bpy.ops.export_scene.fbx` 存在 |
| 无头执行 | ✅ 实测可用 | `blender -b --python-expr ...` 正常跑通 |

**结论：环境基本就绪。** 纯 bpy 脚本路线零额外安装；MCP 路线只需启动 Blender 并点一下 "Start MCP Server"，MCP 客户端配置指向已安装的 `blender-mcp.exe` 即可（无需 uv）。

---

## 2. 方案概述（四条路线对比）

### A. bpy 纯 Python 程序化建模（核心推荐）
用 `bpy` 从零生成骨架与网格：主干/枝条 = 沿折线的低段数变径圆管扫掠；树冠 = 在 3~5 个椭球叶簇团内采样放置叶卡片 quad（图集 UV + 顶点色双色调 + alpha 裁切材质）；FBX 内嵌贴图导出。
- 优点：对目标风格的**每个要素完全可控**（细长主干、光秃枝位置、卡片密度/朝向/尺寸分布）；种子驱动；可无头批量；无任何第三方依赖。
- 缺点：骨架算法要自己写（但本风格主干极简单，工作量小）；树冠形态"团块感"需要调参打磨。

### B. Sapling Tree Gen（官方老牌插件）
`Shift+A > Curve > Sapling Tree Gen`，参数化递归分枝，`show_leaves=True` 时会在枝端生成 quad 叶子网格——恰好也是"叶卡片"思路。后处理脚本：曲线转网格、替换叶子材质为我们的图集 alpha 裁切材质、把叶子 UV 重映射到图集子区域。
- 优点：分枝质量高、形态自然；有随机种子。
- 缺点：**4.2 需联网装扩展**；多年停更；叶子 UV 重映射、风格化材质仍要自写脚本（省不掉 A 的一半工作）；自带树形偏写实，要压出"细长主干+团块树冠"需调参。
- 脚本入口：装好后操作符为 `bpy.ops.curve.tree_add(...)`（参数多，建议 GUI 调好再抄参数进脚本）。

### C. MTree / Modular Tree（本机已装 v5.0.0）
节点式程序化树木生成（Trunk / Branches / Growth L-system / Crown Shape 8 种包络 / 自动叶片分布，支持自定义叶网格对象），种子可控、非破坏性。
- 优点：**本机已装且 4.2 可用**；枝干质量最高；Crown Shape（Spherical 等）天然匹配"圆团树冠"；叶片分布节点可直接用我们的叶卡片 quad 作为自定义叶对象，再整体替换材质。
- 缺点：脚本驱动要程序化搭节点树，比 A 啰嗦；其默认叶是程序化 3D 叶而非贴图卡片，需改造；批量/CI 机器上要携带插件。
- 定位：若觉得 A 的骨架不够自然，可用 MTree 出骨架 + 自写卡片/材质层。

### D. Geometry Nodes
在 A 的骨架之上用 GN 做叶卡片散布（Distribute Points + Instance on Points）可行，但"纯 GN 从零基础长树"复杂度高；FBX 导出前必须 Realize Instances。对本风格属"锦上添花"，不作为主线。

### blender-mcp 的定位
MCP 不是生成算法，而是**驱动方式**：AI 客户端 → MCP 服务 → Blender 内 socket 插件 → `execute_code` 执行任意 bpy 代码 → `get_viewport_screenshot` 截图回传形成"看效果→调参"闭环。它包裹在 A/B/C 任一路线之上，负责交互式迭代；批量生产则建议脱离 MCP 直接无头跑脚本（见 3.4）。

---

## 3. 具体实施步骤

### 3.1 MCP 工作流搭建（一次性）

1. 启动 Blender GUI（已启用 blender_mcp 插件）→ 3D 视口按 `N` → **BlenderMCP** 页 → **Start MCP Server**（默认端口 9876）。
2. MCP 客户端（Claude Desktop / Cursor / Trae 等）配置（本机无 uv，直接指向已装 exe）：
   ```json
   {
     "mcpServers": {
       "blender": {
         "command": "C:\\Users\\xsl\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\blender-mcp.exe"
       }
     }
   }
   ```
3. 验证工具：`get_scene_info`、`execute_code`、`get_viewport_screenshot` 可用即链路通。

### 3.2 生成管线（路线 A，关键 bpy API）

配套原型脚本：**`rebuild_mesh\blender_tree_gen.py`**。已在 Blender 4.2.16 无头**实测跑通**（`--seed 7`）：导出 FBX 含 900 张叶卡片（UV 层 + 顶点色层齐全）、141 面树干网格，两张贴图以内嵌（packed）形式随 FBX 回读成功；产物在 `rebuild_mesh\output\stylized_tree_seed7.fbx`。骨架如下：

```
TreeParams(种子/高度/树冠比例/枝参数/卡片数/尺寸分布/配色/alpha_cutoff)
  ├─ gen_skeleton()      主干脊线(倾斜+S弯) → 下部光秃短枝(3点折线)
  │                      → 伸入各叶簇团的 scaffold 分枝
  ├─ add_tube()          折线扫掠低段数变径圆管，圆柱 UV(接缝重复顶点)，flat 着色
  ├─ gen_clusters()      3~5 个椭球叶簇团(顶团+侧团，带种子抖动)
  ├─ build_leaf_object() 簇内采样 quad：径向偏置随机朝向、图集子区域 UV、
  │                      顶点色灰度(下暗上亮+深度假AO)
  ├─ 材质                叶: TexImage×(VertexColor→ColorRamp 双色) → Principled，
  │                      Alpha→Math(GREATER_THAN,0.5)→Principled.Alpha（硬裁切）；
  │                      4.2 EEVEE Next: surface_render_method='DITHERED'
  │                      树皮: TexImage×棕 tint
  └─ export_fbx()        use_selection / FBX_SCALE_ALL / axis(-Z,Y) /
                         path_mode='COPY' + embed_textures=True
```

关键 API 速查：

| 用途 | API |
|---|---|
| 网格构建 | `bpy.data.meshes.new()` + `mesh.from_pydata(verts, [], faces)` |
| UV 写入 | `mesh.uv_layers.new(name="UVMap")`，按 `poly.loop_indices` 写 `uv_layer.data[i].uv` |
| 顶点色 | `mesh.color_attributes.new(name="Color", type='FLOAT_COLOR', domain='CORNER')` |
| 材质节点 | `ShaderNodeBsdfPrincipled` / `ShaderNodeTexImage` / `ShaderNodeVertexColor` / `ShaderNodeValToRGB` / `ShaderNodeMath(GREATER_THAN)` / `ShaderNodeMixRGB(MULTIPLY)` |
| alpha 裁切 | 节点硬裁切（与渲染器无关）；4.2 用 `mat.surface_render_method='DITHERED'`（旧版 `blend_method='CLIP'` 已移除，脚本内做了兼容回退） |
| FBX 导出 | `bpy.ops.export_scene.fbx(filepath, use_selection=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y', mesh_smooth_type='FACE', path_mode='COPY', embed_textures=True)`。⚠️ 实测坑：导出器**只识别直连到 Principled BSDF Base Color/Alpha 的贴图节点**，经 MixRGB 调色则贴图丢失——脚本导出时临时切换为"直连版材质"，导出后恢复 |
| 插件启用 | `bpy.ops.preferences.addon_enable(module='mtree')`（实测 4.2 OK） |

Unity 端注意：FBX 只可靠携带**贴图引用 + UV + 顶点色**；双色调/alpha 裁切需在 Unity 重建一个 Cutout 双面 shader（`clip(alpha-0.5)`，`lerp(darkGreen, lightGreen, vColor)` 乘贴图）。若 Unity 用单面 shader，把脚本 `leaf_double_sided` 置 True 复制翻面三角形。

### 3.3 AI 经 MCP 驱动的迭代循环

1. AI 客户端 `execute_code`：`exec(compile(open(r"...\blender_tree_gen.py", encoding="utf-8").read(), __file__, 'exec'))`（先跑通，再让 AI 改 `TreeParams` 字段重跑）。
2. `get_viewport_screenshot` 回传渲染/视口图 → AI 对比参考截图 → 调整参数（簇位置、卡片密度、尺寸、配色）→ 重跑。
3. 形态满意后固定参数表，进入批量阶段。

### 3.4 批量生产（建议脱离 MCP）

```
"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" ^
  --background --factory-startup ^
  --python blender_tree_gen.py -- --seed 100 --count 20 --outdir D:\out\trees
```
种子递增产出 20 棵同风格变体 FBX，全程无 UI、可进 CI。

---

## 4. 风格统一手段（多棵树如何"一看就是一套"）

| 维度 | 手段 |
|---|---|
| 贴图 | 全部变体加载**同一绝对路径**的 `IL3DN_Leaf_01.png` / `IL3DN_Bark_Pine.png`；共享同一材质 datablock；FBX 内嵌同源贴图 |
| 叶卡片尺寸 | 固定基准 `leaf_card_size` × 固定抖动区间 ±30%；宽度按图集子区域宽高比钳制（0.7~1.9），分布全体变体一致 |
| 图集取样 | 卡片 UV 仅从固定的 `LEAF_UV_RECTS` 集合抽取（同一套 alpha 形状语言） |
| 配色 | 双色绿写死为常量（`#2E6234` / `#8AC162`，取样自参考截图）；双色调因子走顶点色灰度（下暗上亮 + 深度假 AO），每卡仅 ±5% 明度抖动 |
| 形态语言 | 比例约束参数化：光秃树干占 48%、树冠 3~5 团、主干半径/树高比、枝与竖直夹角 50~72° 等全部集中在 `TreeParams`，变体只抖数值不改区间 |
| 渲染/导出 | 统一 flat 着色（`mesh_smooth_type='FACE'`）、统一单位与轴向、统一 alpha_cutoff=0.5；Unity 侧同一 shader |
| 随机性 | 唯一随机源 `random.Random(seed)`——同种子同树，风格由参数表保证而非随机运气 |

## 5. 泛化能力

- **种子泛化**：`--seed N --count M` 批量产出形状各异、风格一致的变体；可复现（同种子同结果），便于筛选入库。
- **参数泛化**：`TreeParams` 即"树种描述文件"——改高度/树冠半径/簇数/卡片密度可出桦树、山毛榉等同风格不同种；参数可 JSON 化供外部工具生成。
- **图集泛化**：`LEAF_UV_RECTS` 换成别的叶图集子区域即换叶形（如春叶/秋叶换 tint 常量即可出季节变体）。
- **管线泛化**：脚本可跑 GUI / 无头 / MCP 三种模式；MTree、Sapling 骨架可替换 `gen_skeleton()` 插入（接口就是"折线+半径列表"）。

## 6. 优缺点

**优点**
- 环境零新增安装即可开工（Blender 4.2.16 + blender-mcp 插件/服务均已就位）。
- 纯 bpy 路线对该风格**要素级可控**、种子可复现、可无头批量、可进 CI。
- MCP 提供"执行→截图→对比→调参"的 AI 视觉闭环，调风格效率高。
- 本机还有 MTree v5.0.0 作为高质量骨架后备方案。

**缺点**
- MCP 链路多一层（GUI 常开、手动 Start Server、socket 协议），批量生产反而是负担。
- 插件/服务版本错配（见风险）；AI 现场写 bpy 代码的错误率高于运行审阅过的固定脚本。
- Unity 端材质需手工/脚本重建一次（FBX 不携带 Blender 节点语义），属一次性成本。

## 7. 风险

| 风险 | 等级 | 说明与缓解 |
|---|---|---|
| blender_mcp 插件版本旧 (1,2) vs 服务 1.6.4 | 中 | 核心 `execute_code`/`get_scene_info` 协议稳定可用；截图等新工具可能不兼容。建议从 GitHub ahujasid/blender-mcp 下载最新 `addon.py` 覆盖安装 |
| 9876 端口未认证 | 中 | 本机任意进程可驱动 Blender 执行任意 Python；仅在需要时 Start Server，用完即关，勿绑定到非 localhost |
| `execute_code` 执行 AI 生成代码出错/死循环 | 中 | 长任务会冻结 Blender UI（单线程）导致 MCP 超时。缓解：生成逻辑固化在 `blender_tree_gen.py`，MCP 只负责触发与截图；重活走无头模式 |
| 无头模式无截图 | 低 | `get_viewport_screenshot` 依赖 GUI 视口；批量阶段不需要视觉反馈 |
| Sapling 需联网装扩展 | 低 | 路线 B 的前置条件；且操作符参数需以 4.2 扩展版实测为准 |
| 图集 UV 矩形为目测估算 | 低 | `LEAF_UV_RECTS` 已标注需对照渲染微调；也可用图像处理精确提取 alpha 连通域后回填 |
| EEVEE Next 材质 API 变更 | 低 | 4.2 移除 `blend_method`，脚本已做 `surface_render_method`/`blend_method` 双兼容 |

## 8. 推荐程度

| 方案 | 评分 | 一句话 |
|---|---|---|
| **bpy 纯脚本（无头批量）** | ★★★★★ | 对本风格要素级可控、可复现、零依赖，生产主力 |
| **bpy 脚本 + blender-mcp 交互调参** | ★★★★☆ | 环境已通、视觉闭环高效；扣一星：版本错配 + 需常开 GUI |
| MTree 骨架 + 自写卡片/材质 | ★★★☆☆ | 本机可用、骨架质量高，但节点树脚本化改造量不小 |
| Sapling + 后处理 | ★★☆☆☆ | 需联网装扩展且停更，叶卡片/材质仍要自写 |
| 纯 Geometry Nodes | ★★☆☆☆ | 仅适合做散布层，不适合做该风格主生成器 |

**总体建议**：以 `blender_tree_gen.py`（路线 A）为生产管线，无头批量出变体；前期用 blender-mcp 做 1~2 轮"截图对比调参"确定 `TreeParams` 与 `LEAF_UV_RECTS`；骨架自然度不够时再引入 MTree。

---

## 参考资料

- blender-mcp（GitHub，ahujasid）：架构（Blender 插件 socket 服务 :9876 + Python MCP 服务）、execute_code / 截图 / 资产集成能力 — https://github.com/ahujasid/blender-mcp ，镜像说明 https://glama.ai/mcp/servers/@ahujasid/blender-mcp
- PyPI blender-mcp（本机同版 1.6.4，含入口点与配置示例） — https://pypi.org/project/blender-mcp/
- Sapling Tree Gen 在 4.2 起迁移为扩展 — https://extensions.blender.org/add-ons/sapling-tree-gen/ ，安装方式说明 https://addons.cgdive.com/tools/sapling-tree-gen-pre-installed-addon
- Blender 4.2 扩展机制变更（内置插件迁移 Get Extensions） — https://blenderartists.org/t/addons-dont-work-in-blender-4-2/1543096
- MTree / Modular Tree（节点式程序化树，Crown Shape、L-system、自定义叶对象、种子） — https://github.com/MaximeHerpin/modular_tree ，v5 功能说明 https://desirefx.me/3d_models/blender/modular-tree-v5-5-0-for-blender/
- 项目内已有纯 Python 对照实现（无 DCC、OBJ 输出）：`rebuild_mesh\procedural_tree.py`
