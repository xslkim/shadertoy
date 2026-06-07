# VK_EXT_descriptor_heap 教学 Demo

一个可运行的 Vulkan demo,用来讲解 Vulkan 最新的 **`VK_EXT_descriptor_heap`** 扩展
(把 D3D12 风格的 descriptor heap / bindless 统一模型带进 Vulkan)。

画面是 shadertoy 风格的 **SDF raymarching**:6 个"场景"参数被放进一个
**描述符数组(堆)**,CPU 每帧只 push 一个**索引**,shader 按索引从堆里取资源,
在场景之间连续 morph —— 直观展示"一个堆、海量资源、按索引访问"。

## 双路径设计(重要)

`VK_EXT_descriptor_heap` 是 spec v1 的全新扩展。截至制作时,**桌面驱动尚未暴露它**
(本机 RTX 5090 / 驱动 577.00 的 `vulkaninfo` 里没有该扩展)。因此本工程采用双路径:

| 用途 | 实现 | 文件 |
|------|------|------|
| **真实渲染**(给视频出画面) | `VK_EXT_descriptor_buffer`(本机支持,它是 heap 的直接前身,心智模型几乎一致) | `src/main.cpp` |
| **新扩展教学主角** | `VK_EXT_descriptor_heap` 的真实 API 走查(可编译;运行时若不支持则优雅降级讲解) | `src/descriptor_heap_reference.cpp` |

程序启动时会打印本机对两个扩展的支持状态。一旦将来驱动支持 descriptor_heap,
`descriptor_heap_reference.cpp` 里注释的工作流即可直接落地。

## 构建

需要:Visual Studio 2022(MSVC)、CMake ≥ 3.20、Vulkan SDK(默认 `C:/VulkanSDK/1.4.350.0`,
或设置环境变量 `VULKAN_SDK`)。

```powershell
$env:VULKAN_SDK = "C:\VulkanSDK\1.4.350.0"
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
.\build\Release\vk_demo.exe        # ESC 退出
```

着色器(`shaders/*.vert/.frag`)在构建时由 `glslc` 自动编译为 SPIR-V 到 `build/shaders/`。

## 关键代码导览

- `shaders/sdf_bindless.frag` — `scenes[16]` 描述符数组 + `nonuniformEXT(index)` 按索引取场景。
- `src/main.cpp`
  - `createPipeline()` — set layout 带 `DESCRIPTOR_BUFFER_BIT`,pipeline 带 `DESCRIPTOR_BUFFER_BIT`。
  - `createDescriptorBuffer()` — `vkGetDescriptorEXT` 把 6 个 uniform 描述符写进"堆"。
  - `drawFrame()` — `vkCmdBindDescriptorBuffersEXT` + `vkCmdSetDescriptorBufferOffsetsEXT` + `vkCmdPushConstants(索引)`。
- `src/descriptor_heap_reference.cpp` — descriptor_heap 的完整 API 工作流(查尺寸→建堆→写描述符→映射表→bind heap + push index)。

## 视频素材

- `video/script.md` — 中文口播脚本(分镜 + 旁白 + 屏幕动作)。
- `video/visuals.html` — 教学图示(对比图、堆布局、索引访问流、演进时间线);浏览器打开即可录屏/截图。
- `video/shot_0..3.png` — demo 离屏渲染的成品静帧(可直接作开场/封面)。
- `video/frames/v0..v7_*.png` — **成品视觉元素帧(1920×1080)**,对应脚本各教学要点,可直接拖进剪辑时间线:
  | 帧 | 内容 | 脚本段 |
  |----|------|--------|
  | v0_title | 标题卡(含真实渲染缩略图) | 开场 |
  | v1_pain | 传统模型 vs 堆模型 对比 | 01 痛点 |
  | v2_evolution | indexing → buffer → heap 演进 | 02 演进 |
  | v3_heap_layout | 堆内存布局(8 字节槽位) | 03 核心 |
  | v4_index_flow | CPU push 索引 → heap → 画面(含真实渲染) | 03 核心 |
  | v5_api_steps | descriptor_heap API 六步 | 04 API |
  | v6_compare_table | descriptor_buffer ↔ descriptor_heap 对照 | 04/06 |
  | v7_status | 现状 / 双路径上手卡 | 06 现状 |

  源文件是 `video/frames/v*.html` + `frame.css`。
- `video/thumbnails/cover_youtube.png`(1280×720)、`cover_bilibili.png`(1146×717) — **视频封面/缩略图**(大字 + 真实渲染背景 + NEW 角标)。
- `video/anim/` — **逐帧动画序列**(元素渐进出现,可在剪辑里当动画播放):
  - `evo_0..3.png` — 演进线逐步揭示(indexing → buffer → heap)
  - `heap_0..7.png` — 堆槽位逐个出现 → 点亮 #2 → 标注
  - `index_0..4.png` — push 索引 → heap 命中 → 出画面 → 结论
  源文件 `video/anim/anim_*.html` 通过 URL 参数 `?step=N` 控制揭示进度。

> **一键重生成所有 PNG**:改任意 HTML/CSS 后,运行 `video/render_all.ps1`(用无头 Edge 光栅化教学帧 + 封面 + 动画序列)。

### 离屏截图(无需窗口可见 / 桌面控制)

```powershell
.\build\Release\vk_demo.exe --shot
```

会在 `video/` 下渲染 4 张不同时刻(不同场景/过渡)的 `shot_*.bmp`(1280×720)。
原理:渲染到离屏 image → `vkCmdCopyImageToBuffer` 拷回 host 内存 → 写 32bpp BMP
(格式用 `B8G8R8A8`,正好对应 BMP 的 BGRA 字节序)。转 PNG 可用:
`Add-Type -AssemblyName System.Drawing` 后 `Image.FromFile(bmp).Save(png, Png)`。
