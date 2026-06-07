>>> 开场：SDF Bindless 渲染 #B01
@enter: fade
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 (#0a0a12)。画面展示 2×2 网格，四张真实 GPU 渲染的 SDF raymarching 截图，
整体网格居中，总宽度 1760px，总高度 880px，网格间距 12px，每格圆角 12px，无边框。
四张图片分别为：
  左上 ./assets/shot_0.png，右上 ./assets/shot_1.png
  左下 ./assets/shot_2.png，右下 ./assets/shot_3.png

[0s] 四格同时从透明渐显（opacity 0→1，持续 0.8s）。

[1s] 画面中央叠加一个半透明文字条（不遮挡图片，只影响中心带状区域）：
  背景: rgba(10,10,18,0.72)，宽 1440px，高 96px，垂直居中于整个画布。
  文字内容："CPU 每帧只 push 一个整数索引，屏幕上的一切都动了"
  字号 36px，颜色 #e8e8f0，居中，等待 [1.2s] 后淡入。

[2s] 右下角出现小标签"VK_EXT_descriptor_heap"，字号 22px，颜色 #5ac8ff，
  等宽字体，背景 rgba(10,10,18,0.8)，内边距 8px 16px，圆角 8px，距右 40px 距底 40px。

--- narration ---
你在屏幕上看到这些形状，正在不停地切换
但驱动这一切的，CPU 每帧只往 GPU 传了一个整数
不是重新绑定描述符集，不是更新 uniform
就是一个**索引**
这正是图形 API 一直追求的东西：**bindless**
D3D12 早就有了它，现在 Vulkan 也有了官方答案


>>> 标题卡 #B02
@enter: fade-up
@exit: fade
@visual: image(./assets/v0_title.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v0_title.png 图片文件）
标题卡：顶部小字 "VULKAN SDK 1.4.350 · 全新扩展详解"，
主标题 "Vulkan 终于有了"（白色大字）+ "Descriptor Heap"（accent 红色），
副标题 "一块堆 · 一个索引 · 海量资源随手可取 —— 把 D3D12 风格的 bindless 带进 Vulkan"，
右下角三张 SDF 渲染缩略图作为背景装饰。

--- narration ---
今天我们把这个全新扩展从概念到代码讲透
**VK_EXT_descriptor_heap**，Vulkan SDK 1.4.350，spec v1


>>> 传统描述符模型的痛点 #B03
@enter: fade
@exit: fade
@visual: image(./assets/v1_pain.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v1_pain.png 图片文件）
左右对比图：左侧"传统模型·绑定时代"展示 Pool→Set→Layout→Update→Bind 四步链路；
右侧"堆模型·索引时代"展示一块堆+一个索引的简洁流程。
背景深色，左侧标注"资源组合一变换 layout/set 和重绑成本高"，右侧标注"一帧内随手访问任意资源"。

--- narration ---
先回忆传统 Vulkan 是怎么给 shader 喂资源的
先建一个 **descriptor pool**
从里面分配 **descriptor set**
set 的形状由 **descriptor set layout** 决定
再用 vkUpdateDescriptorSets 把资源写进 set
绘制时 vkCmdBindDescriptorSets 绑上去
问题在哪？
第一，**僵硬**
资源组合一变，往往就要换一套 layout
第二，**切换成本高**
想在一帧里访问大量纹理
要么塞进巨大的数组，要么频繁重绑
管线状态被切得很碎
现代渲染需要"随时访问任意资源"的能力
传统模型就成了瓶颈


>>> Vulkan 走向 Bindless 的三步 #B04
@enter: slide-left
@exit: fade
@visual: image(./assets/v2_evolution.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v2_evolution.png 图片文件）
横向三栏演进时间线图：
  第一步 "descriptor_indexing"（蓝色，VULKAN 1.2 CORE）
  → 第二步 "descriptor_buffer"（金色，VK_EXT）
  → 第三步 "descriptor_heap"（红色高亮边框，VK_EXT，标注"本期主角"）
每栏有对应技术说明文字。

--- narration ---
Vulkan 走向 bindless 分了三步
**第一步，descriptor_indexing**，已进 1.2 核心
允许 shader 用**非一致索引**访问描述符数组
bindless 的雏形有了，但描述符还在 set 里
**第二步，descriptor_buffer**
把描述符本身当成**普通数据**，写进一块 buffer
描述符第一次脱离 set，变成可自由摆放的内存
这也是我们 demo **实际用来出画面**的扩展
**第三步，descriptor_heap**，今天的主角
一块全局的堆加一张映射表
shader 里的 set/binding 由一个**索引**直接定位
这就和 D3D12 的 ResourceDescriptorHeap 对齐了


>>> 核心概念：堆内存模型 #B05
@enter: fade-up
@exit: fade
@visual: image(./assets/v3_heap_layout.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v3_heap_layout.png 图片文件）
堆布局图：6 个槽位（#0~#5）横向排列，每槽 emoji 图标 + 类型标签；
底部水平轴线标注"偏移 0 → Resource Heap (GPU 内存)"；
下方注释文字："每个槽位 = 一个描述符，uniformBufferDescriptorSize = 8 字节"。

--- narration ---
把 descriptor_heap 的脑内模型建立起来
想象一块连续的 GPU 内存，这就是**堆**
每个资源的描述符按固定尺寸紧密排列
第 0 槽、第 1 槽、第 2 槽……
本 demo 里，**uniformBufferDescriptorSize = 8 字节**
这个数字由 vkGetPhysicalDeviceDescriptorSizeEXT 查得
6 个场景就是堆里 6 个 8 字节的槽位
第 i 个资源 → 堆基址 + i × 描述符尺寸


>>> 核心概念：索引访问流 #B06
@enter: slide-left
@exit: fade
@visual: image(./assets/v4_index_flow.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v4_index_flow.png 图片文件）
三步流程图：① CPU 每帧 push 索引数字 "2" via vkCmdPushDataEXT
→ ② GPU shader heap[2] 命中第 2 槽（高亮）
→ ③ scene 2 被渲染输出画面（缩略图）。
底部注释："没有重建描述符、没有重绑 set —— 只是换了个索引"。

--- narration ---
shader 要用某个资源时，不绑定任何东西
而是拿一个**整数索引**，比如 index = 2
直接去堆里第 2 槽取描述符
索引从哪来？这正是 descriptor_heap 灵活的地方
它定义了一张**映射表**
VkDescriptorSetAndBindingMappingEXT
指定索引来自：push 常量、间接 buffer、或 shader record
我们用最直观的：**HEAP_WITH_PUSH_INDEX**
CPU 每帧 push 一个索引，GPU 自己去堆里取
传统模型是 CPU **绑定**资源，shader 被动接受
堆模型是 shader 拿**索引**，自己主动去取


>>> API 六步完整走查 #B07
@enter: fade
@exit: fade
@visual: image(./assets/v5_api_steps.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v5_api_steps.png 图片文件）
六步 API 流程图（竖向列表，每步一行）：
1 开启特性 VkPhysicalDeviceDescriptorHeapFeaturesEXT.descriptorHeap = VK_TRUE
2 查描述符尺寸 vkGetPhysicalDeviceDescriptorSizeEXT
3 创建 buffer usage = VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT
4 写描述符进堆 vkWriteResourceDescriptorsEXT / vkWriteSamplerDescriptorsEXT
5 建映射表（灵魂）VkDescriptorSetAndBindingMappingEXT → source = HEAP_WITH_PUSH_INDEX
6 录命令 vkCmdBindResourceHeapEXT + vkCmdPushDataEXT + vkCmdDraw

--- narration ---
来看真实 API，整个流程六步
**第一步：开特性**
VkPhysicalDeviceDescriptorHeapFeaturesEXT
把 descriptorHeap 设为 VK_TRUE，挂到 vkCreateDevice
**第二步：查描述符尺寸**
vkGetPhysicalDeviceDescriptorSizeEXT
返回每种描述符占多少字节
堆的大小 = 资源数 × 尺寸，再按对齐取整
**第三步：建堆 buffer**
普通 vkCreateBuffer
usage 是新的 VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT
采样器用独立的 sampler 堆，机制一样
**第四步：写描述符进堆**
vkWriteResourceDescriptorsEXT
把第 i 个资源的描述符写进堆里第 i 个槽位
本质就是往映射内存里写数据
**第五步：建映射表**，这是整套 API 的灵魂
VkDescriptorSetAndBindingMappingEXT
告诉驱动：shader 的 set=0 binding=0
索引来源是 **HEAP_WITH_PUSH_INDEX_EXT**
**第六步：录命令**
vkCmdBindResourceHeapEXT 整帧绑一次堆
vkCmdPushDataEXT 把当前索引推进去
然后照常 vkCmdDraw


>>> buffer vs heap 对照 #B08
@enter: slide-left
@exit: fade
@visual: image(./assets/v6_compare_table.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v6_compare_table.png 图片文件）
左右对照表：descriptor_buffer vs descriptor_heap，
逐行对应：绑堆、写描述符、录命令三个维度；
底部注释"heap 是 buffer 的逻辑延续，心智模型一致"。

--- narration ---
注意这套 API 和 descriptor_buffer 几乎一一对应
绑堆 ↔ vkCmdBindDescriptorBuffersEXT
push 索引 ↔ vkCmdPushConstants
descriptor_heap 只是把绑定和偏移
统一成了"绑一整块堆 + push 一个索引"
更接近 D3D12，更适合一帧内切换海量资源
理解了 buffer，heap 几乎**零成本**上手


>>> Demo 代码：bindless 核心 #B09
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 (#0a0a12)。左右两栏代码块布局，内容区域占画布约 90% 宽度，顶部留 120px 标题区。

标题区（高 100px，内边距水平 60px）：
  左侧小标签 "SHADER · sdf_bindless.frag"，颜色 #5ac8ff，字号 24px，等宽字体；
  右侧小标签 "main.cpp · CPU 侧"，颜色 #ff5a8a，字号 24px，等宽字体。

左侧代码块（宽 880px，高 660px，背景 #0d1117，圆角 16px，内边距 40px，等宽字体字号 26px，左对齐）：
  [0s] 注释行 "// GPU · bindless 访问"，颜色 #8b949e，淡入。
  [0.4s] 空行。
  [0.6s] 行1: keyword(#ff7b72)"layout" " (set=0, binding=0)" 颜色#e6edf3 "uniform" keyword。
  [0.9s] 行2: type(#a5d6ff)"SceneParams" " scenes" "[]" comment(#8b949e)" // 描述符数组"。
  [1.2s] 空行。
  [1.4s] 行3: type(#a5d6ff)"SceneParams" " sp ="，颜色 #e6edf3。
  [1.7s] 行4（缩进 2 格）: accent(#ff5a8a) + 粗体 "scenes[nonuniformEXT(idx)].s"，字号 26px。
  行4下方 [1.9s] 出现 2px 粗的 #ff5a8a 底部高亮横条（宽度贴合文字，从左扫入 0.3s）。
  [2.1s] 行5: comment(#8b949e)" // ← 按索引取堆中资源"。

右侧代码块（宽 820px，高 660px，同样式，[0.2s] 后开始）：
  [0.2s] 注释行 "// CPU · 每帧推索引"，颜色 #8b949e，淡入。
  [0.6s] 注释行 "// 由时间算出当前场景索引"，颜色 #8b949e。
  [0.9s] 行1: type(#a5d6ff)"PushConsts" " pcv = computePush(...);"，颜色 #e6edf3。
  [1.2s] 空行。
  [1.4s] 行2: "pcv.sceneA = " accent2(#5ac8ff)"a" ";"  comment" // 场景 A 索引"。
  [1.7s] 行3: "pcv.sceneB = " accent2(#5ac8ff)"b" ";"  comment" // 场景 B（过渡用）"。
  [2.0s] 空行。
  [2.2s] 行4（accent2 + 粗体 #5ac8ff）: "vkCmdPushConstants(..., &pcv);"，字号 26px。
  [2.4s] 行4 下方同样出现 2px 粗 #5ac8ff 高亮横条。

[2.8s] 从右侧代码块的 vkCmdPushConstants 行，向左延伸出一条 accent2 色弧形箭头，
  指向左侧代码块的 nonuniformEXT 行，箭头线 2px，末端实心三角。动画：从右到左绘制，0.4s 完成。

--- narration ---
回到能真正跑的版本，看关键代码
**frag shader** 里这行是 bindless 的核心
scenes[nonuniformEXT(idx)].s
一个描述符数组，用**非一致索引**随机访问
idx 是几，就取堆里第几个场景的参数
**main.cpp** 里，CPU 这边每帧算出当前索引
pcv.sceneA 是场景 A 的索引
pcv.sceneB 是过渡目标场景的索引
vkCmdPushConstants 把这两个数推给 shader
屏幕上每次形状切换，背后就是这个索引在变
没有重建描述符，没有重绑 set
所有场景描述符一开始就静静躺在堆里


>>> Demo 启动日志 #B10
@enter: fade
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 (#0a0a12)。画面中央展示一个终端窗口，
宽 1600px，背景 #0d1117，圆角 20px，内边距 56px 64px，
顶部左对齐三个圆点（红 #ff5f57 / 黄 #febc2e / 绿 #28c840，直径 16px，间距 10px，距顶内边距内）。

等宽字体，字号 30px，行高 1.8。每行在对应时间点 [Xs] 从左侧淡入（opacity 0→1，持续 0.2s）：

[0s]   颜色 #8b949e: "PS> .\\vk_demo.exe"
[0.3s] 颜色 #30363d: "─────────────────────────────────────────────"
[0.6s] 颜色 #e6edf3: "GPU  :  NVIDIA GeForce RTX 5090"
[0.9s] 颜色 #28c840: "descriptor_buffer  :  ✓  SUPPORTED  (渲染路径)"
[1.2s] 颜色 #ff9f0a: "descriptor_heap    :  ✗  not exposed by driver"
[1.5s] 颜色 #a5d6ff: "uniformBufferDescriptorSize  =  8  bytes"
[1.8s] 颜色 #a5d6ff: "descriptorSetLayout  size    =  256  bytes"
[2.1s] 颜色 #28c840: "wrote  6  descriptors  to  heap   ✓"
[2.4s] 颜色 #30363d: "─────────────────────────────────────────────"
[2.6s] 颜色 #8b949e: "rendering...  [ESC]  to  exit  ▋"  （▋ 做 1Hz 闪烁动画）

descriptor_heap 那行 [1.2s] 出现后，右侧 [1.4s] 浮出一个注释气泡：
  绝对定位，距终端窗口右边缘 -360px，同行垂直对齐；
  背景 #1a0a05，边框 1px solid #ff9f0a，圆角 10px，内边距 14px 22px；
  文字 "走教学降级路径"，颜色 #ff9f0a，字号 24px；
  气泡左侧 6px 粗竖线，颜色 #ff9f0a。

--- narration ---
启动时控制台打印了几个关键信息
GPU 是 RTX 5090
descriptor_buffer 支持，用它实际渲染
descriptor_heap 当前驱动还**不支持**，走教学降级
单个 uniform 描述符 **8 字节**
整个描述符集布局 **256 字节**
已经把 **6 个描述符**写进了堆


>>> 现状与注意事项 #B11
@enter: fade
@exit: fade
@visual: image(./assets/v7_status.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/v7_status.png 图片文件）
标题"它很新 —— 现在该怎么上手"，三栏卡片：
  ⚠ spec v1 · 等驱动（当前 vkCreateDevice 会因扩展不支持失败）
  ✓ 现在可预演（用 descriptor_buffer 实现 bindless，先跑通心智模型）
  ↗ 延续关系（理解了 buffer，迁移到 heap 几乎零成本）
底部标注"底座 descriptor_buffer → 未来 descriptor_heap"。

--- narration ---
几个现实问题要交代清楚
**第一，它很新**
spec version 1，SDK 1.4.350 头文件已就绪
但**桌面驱动目前还没暴露这个扩展**
所以 descriptor_heap 代码能编译
运行时 vkCreateDevice 会因扩展不支持而失败
这也是 demo 用 descriptor_buffer 出画面的原因
**第二，两者是延续关系，不是互斥**
理解了 buffer，heap 几乎零成本迁移
**第三，注意三个细节**
堆的尺寸和对齐要按查询值来
sampler 堆和 resource 堆要分开管理
capture-replay 调试需要额外声明支持


>>> 收尾 #B12
@enter: fade
@exit: fade
@visual: image(./assets/shot_3.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/shot_3.png 图片文件）
SDF raymarching 真实渲染截图：scene 3，霓虹紫色八面体在暗色背景中发光，
圆滑反光，画面构图居中，渲染质感真实。

--- narration ---
总结一句
descriptor_heap 让 Vulkan 从"绑定时代"走向"索引时代"
一块堆，一个索引，海量资源随手可取
等驱动跟上，它会成为 GPU-driven 渲染的默认姿势
工程代码和图示都在仓库里
自己跑一跑，改改索引，体会最深
