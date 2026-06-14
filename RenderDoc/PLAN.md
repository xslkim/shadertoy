# RenderDoc 系列视频教程 — 任务计划

> 目标：教会**已具备基础渲染知识**的程序员使用 [RenderDoc](https://github.com/baldurk/renderdoc) 对渲染帧进行分析。
> 讲解用例取自 `D:\code\Vulkan-Samples`（可运行 + 截图/录屏对比）。
> 产出形式遵循 `D:\shadertoy\AUTHORING.md`（AutoVideo：每集一个目录，含 `meta.md` + `script.md`）。
>
> **本文件只是计划，不含视频脚本。** 等资源与细节确认后再逐集写脚本。

---

## 1. 受众与教学目标

- **受众画像**：会写/读渲染代码（懂管线、drawcall、纹理、shader、framebuffer 等概念），但**没用过或不熟 RenderDoc**。
- **不教**：图形学基础、Vulkan API 教学（只在解释 RenderDoc 面板时顺带对照）。
- **要教会的核心能力**：
  1. 抓一帧（capture）并打开分析
  2. 看懂一帧的结构（Event Browser / 时间线）
  3. 用 Texture Viewer 检查每个 pass 的输入输出
  4. 用 Pipeline State 沿管线各阶段排查绑定的资源
  5. 用 Mesh Viewer 看顶点输入/输出与几何
  6. 调试 shader、实时改 shader 看效果
  7. 检查 buffer / constant buffer / compute 资源
  8. 做性能分析（计数器、drawcall 计时）
  9. （可选）用 RenderDoc 观察资源状态 / barrier

---

## 2. 资源清单（现状 / 缺口）

| 资源 | 状态 | 备注 / 待办 |
|------|------|-------------|
| Vulkan-Samples 源码 | ✅ `D:\code\Vulkan-Samples` | 完整 sample 目录 |
| Vulkan-Samples 已构建 | ✅ | `build\app\bin\debug\AMD64\vulkan_samples.exe`；运行：`vulkan_samples sample <name>` |
| AutoVideo 编写规范 | ✅ | `D:\shadertoy\AUTHORING.md` |
| 参考音色 `B00.wav` | ⚠️ 需复制 | 现有于 `ocean\`、`sync\`；需放到 `D:\shadertoy\RenderDoc\B00.wav` 供 `voiceRef` 用 |
| **RenderDoc 本体** | ❌ **未安装** | 未找到 `qrenderdoc.exe` / `renderdoccmd`。**必须先安装**（否则无法产出 UI 截图/录屏，也无法抓 .rdc） |
| 各 sample 的 `.rdc` 抓帧文件 | ❌ 待生成 | 每集用到的 sample 需在 RenderDoc 下抓帧，保存为 `.rdc` 复用 |
| RenderDoc UI 截图 / 录屏 | ❌ 待生成 | 每集的核心素材，见 §5 |
| 发布版 release 构建（可选） | ❓ | 目前是 Debug 构建；性能集（EP8）建议用 Release 抓帧更真实 |

> **首要前置任务**：安装 RenderDoc（建议官网/GitHub release 稳定版），确认能 launch `vulkan_samples.exe` 并 F12 抓帧。

---

## 3. 系列大纲（提案，待定稿）

每集 5–9 分钟，循序渐进。"主用例"是讲解时实际抓帧的 sample。

| 集 | 标题（暂定） | 教学焦点 | 主用例（Vulkan-Samples） | 对照/进阶用例 |
|----|-------------|---------|--------------------------|--------------|
| **EP1** | RenderDoc 是什么 & 抓你的第一帧 | 价值、工作流；launch app、F12 抓帧、打开 capture、UI 全景 | `hello_triangle` | — |
| **EP2** | 看懂一帧：Event Browser 与时间线 | action/API 事件、EID、debug marker、一帧的结构 | `hello_triangle` → `hdr`(多 pass) | `subpasses` |
| **EP3** | Texture Viewer 精讲 | RT/输入纹理、RGBA 通道、range、mip/slice/sample、深度模板、overlay（wireframe/overdraw/depth test）、自定义可视化 shader | `texture_loading` | `texture_mipmap_generation` |
| **EP4** | Pipeline State 精讲 | 沿 IA→VS→Tess→GS→RS→FS→OM 各阶段看绑定资源、descriptor set、uniform buffer、视口/混合/深度状态 | `hello_triangle` | `terrain_tessellation`(细分阶段) |
| **EP5** | Mesh Viewer：顶点数据与几何 | VS 输入 vs 输出、几何预览相机、拾取顶点、instancing | `instancing` | — |
| **EP6** | Shader 调试与实时编辑 | 调试像素/顶点/compute 调用、单步与 watch、实时改 shader 并 apply | `hello_triangle`(像素调试) | `texture_loading` |
| **EP7** | Buffer / 资源检查 & Compute | Resource Inspector、buffer 格式化查看、constant buffer、SSBO、compute dispatch 输入输出 | `compute_nbody` | — |
| **EP8** | 性能分析：计数器与计时 | Performance counter viewer、drawcall 计时、pipeline statistics、与 app 内 timestamp query 对照 | `timestamp_queries` | `terrain_tessellation` / `hdr` |
| **EP9**（可选） | 用 RenderDoc 看同步与资源状态 | 资源生命周期、layout transition、pipeline barrier 在帧里的体现、Resource Usage | `pipeline_barriers` | `layout_transitions` |

> **范围决策点**：是做精简版（合并为 ~6 集）还是完整 8–9 集？见 §7 待决策。

---

## 4. 制作流程（每集）

1. 选定 sample → 用 RenderDoc launch + F12 抓帧 → 保存 `<sample>.rdc`
2. 在 RenderDoc 中按脚本走查，**录屏**（核心操作）+ **截关键帧图**（讲解定格）
3. 录屏裁剪为 1920×1080 / H.264 / yuv420p 的 mp4，放入该集 `assets/`
4. 写 `script.md`：
   - 概念讲解 / 标题页 → `@visual: animation`（AI 生成动画）
   - RenderDoc 操作演示 → `@visual: video(./assets/xxx.mp4)`
   - 关键界面定格讲解 → `@visual: image(./assets/xxx.png)`
   - sample 源码片段 → animation 块内引用代码行
5. 写 `meta.md`（标题/slug/voiceRef）
6. 交给构建 Agent 按 `BUILD.md` 生成 MP4

### 建议目录结构

```
D:\shadertoy\RenderDoc\
├── PLAN.md                      ← 本文件
├── B00.wav                      ← 待复制（voiceRef）
├── captures\                    ← 各 sample 的 .rdc 抓帧（复用）
│   ├── hello_triangle.rdc
│   ├── texture_loading.rdc
│   └── ...
├── ep1-intro-first-capture\
│   ├── meta.md
│   ├── script.md
│   └── assets\                  ← 该集录屏/截图
├── ep2-event-browser\
│   └── ...
└── ...
```

---

## 5. 每集需准备的 RenderDoc 素材（录屏/截图清单）

> 这些**无法由 AI 自动生成**，需在装好 RenderDoc 后手动（或用 computer-use 驱动桌面）采集。先列清单，正式写脚本时再细化分镜。

- **EP1**：launch `hello_triangle`、F12 抓帧的过程录屏；capture 打开后的 UI 全景截图（标注各面板）。
- **EP2**：Event Browser 展开/折叠、点击不同 event 时其它面板联动的录屏；多 pass（hdr）的事件树截图。
- **EP3**：Texture Viewer 切换 RT/输入、调 range、看 mip、开各种 overlay 的录屏；depth buffer 可视化截图。
- **EP4**：Pipeline State 各阶段点击、查看绑定资源/descriptor 的录屏；细分管线阶段截图。
- **EP5**：Mesh Viewer VS in/out 切换、旋转几何预览、instancing 的录屏。
- **EP6**：右键像素 → Debug、单步、watch 面板的录屏；实时改 FS 颜色 → apply → 画面变化的录屏。
- **EP7**：Resource Inspector、buffer 按格式查看、compute SSBO 前后对比的录屏。
- **EP8**：开 counter viewer、选计数器、查看每 drawcall 耗时表的录屏；统计结果截图。
- **EP9**：Resource Usage / barrier 相关面板录屏。

---

## 6. 风险与注意点

- **RenderDoc 未安装**是当前最大阻塞，需先解决。
- Debug 构建性能不真实——EP8 建议单独出 Release 构建抓帧。
- 录屏质量（分辨率、字体清晰度、帧率）直接影响成片观感；建议 1080p、UI 字体适当放大。
- 部分高级面板（shader 调试、counter）依赖 GPU/驱动支持，需先在本机验证可用。
- 录屏时长与块时长由旁白决定——长录屏建议拆段，或用 `@duration` 对齐。

---

## 7. 已确认决策

1. **系列范围**：先做 **EP1 试点**，走通整条流水线（抓帧→录屏→截图→脚本→构建），验证可行后再批量做后续集。
2. **演示形式**：**录屏 + 截图混合**——导航/连续操作用 `video(./assets/*.mp4)`，关键界面定格讲解用 `image(./assets/*.png)`。
3. **采集方式**：由我用 **computer-use** 驱动桌面完成 RenderDoc 安装、launch sample、F12 抓帧、录屏、截图。
4. **语言**：中文旁白（与现有系列一致）。
5. **每集时长**：5–9 分钟（EP1 偏短，约 5–6 分钟即可）。

---

## 8. EP1 试点：详细方案

**标题（暂定）**：《RenderDoc 是什么 & 抓你的第一帧》
**slug**：`renderdoc-ep1-first-capture` ｜ **目录**：`D:\shadertoy\RenderDoc\ep1-first-capture\`
**主用例**：`hello_triangle`（最简单、单 drawcall，适合首集）

### 8.1 分镜（block 提案，正式写脚本时细化）

| 块 | 内容 | @visual |
|----|------|---------|
| B01 | 开场标题 | animation |
| B02 | RenderDoc 是什么 & 为什么要做帧分析 | animation（概念图）|
| B03 | 工作流总览：launch app → 抓帧 → 打开分析 | animation（流程图）|
| B04 | **演示**：用 RenderDoc 启动 hello_triangle，F12 抓帧，打开 capture | video → 素材 A1 |
| B05 | capture UI 全景：各面板各管什么 | image（标注截图）→ 素材 S1 |
| B06 | Event Browser：找到那次 drawcall | video → 素材 A2 |
| B07 | Texture Viewer：看到三角形的输出 | video/image → 素材 S2/A3 |
| B08 | 小结 + 下集预告（Event Browser 精讲）| animation |

### 8.2 EP1 需采集的素材（computer-use 产出）

| 编号 | 类型 | 内容 | 用于块 |
|------|------|------|--------|
| `hello_triangle.rdc` | 抓帧 | hello_triangle 的帧抓取，存 `captures\` 复用 | — |
| A1 | 录屏 | 从 RenderDoc 启动 sample → F12 抓帧 → 打开 capture（~20–40s）| B04 |
| S1 | 截图 | capture 打开后的 UI 全景（用于叠加标注）| B05 |
| A2 | 录屏 | 点击 Event Browser 中的 drawcall，面板联动 | B06 |
| S2/A3 | 截图/录屏 | Texture Viewer 显示三角形输出 | B07 |

> 录屏统一裁剪为 1920×1080 / H.264 / yuv420p mp4，放入 `ep1-first-capture\assets\`。

### 8.3 EP1 执行步骤（computer-use）

1. **安装 RenderDoc**：下载官方稳定版安装包并安装（需你在场逐个授权应用访问）。
2. 用 RenderDoc launch `vulkan_samples.exe sample hello_triangle`，F12 抓帧，保存 `hello_triangle.rdc`。
3. 按 8.2 清单录屏 + 截图。
4. 复制 `B00.wav` 到 `D:\shadertoy\RenderDoc\B00.wav`。
5. 写 `meta.md` + `script.md`，引用 assets。
6. 交构建 Agent 出 MP4，回看校对。

> ⚠️ computer-use 需要你在机器旁逐个授权应用（浏览器下载、安装程序、RenderDoc）。安装软件属不可逆操作，开始前我会再确认一次。

---

> 下一步：确认 EP1 方案 → 安装 RenderDoc（computer-use）→ 采集素材 → 写 EP1 脚本 → 构建。
