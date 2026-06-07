# 视频脚本:Vulkan 终于有了 Descriptor Heap —— 详解 `VK_EXT_descriptor_heap`

> 体裁:技术教学 / 口播 + 录屏
> 时长:约 10–12 分钟
> 配套:`video/visuals.html`(图示)、`vk_demo.exe`(实时画面)、IDE 代码片段
> 风格备注:延续你 shadertoy / SDF 系列的暗色视觉基调

---

## 分镜总览

| # | 段落 | 时长 | 主画面 |
|---|------|------|--------|
| 0 | 开场 Hook | 0:40 | demo 实时画面(SDF morph) |
| 1 | 痛点回顾:传统描述符模型 | 1:30 | visuals.html 对比图左半 |
| 2 | 演进线:indexing → buffer → heap | 1:10 | 演进时间线图 |
| 3 | 核心概念:堆 + 索引 | 1:40 | 堆布局图 + 索引访问流 |
| 4 | API 走一遍 | 2:40 | IDE 代码 + 调用流程图 |
| 5 | Demo 实战讲解 | 2:00 | demo 画面 + 控制台日志 |
| 6 | 现状 / 注意事项 | 1:10 | vulkaninfo + 双路径说明 |
| 7 | 收尾 | 0:30 | demo 画面淡出 |

---

## 0. 开场 Hook(约 0:40)

**【画面】** 全屏播放 `vk_demo.exe`:SDF 形状(球→立方→圆环→八面体)在霓虹配色间平滑 morph。

**【旁白】**
> 你在屏幕上看到的这些形状,正在不停地切换。但有意思的是——驱动这一切的,
> 每一帧 CPU 只往 GPU 传了**一个整数**。不是绑定描述符集,不是更新 uniform,
> 就是一个**索引**。
>
> 这正是图形 API 这些年一直在追的东西:**bindless**。D3D12 早就有了它的
> "descriptor heap";而现在,Vulkan 也有了官方答案——`VK_EXT_descriptor_heap`。
> 今天我们就把这个全新扩展从概念到代码讲透,并且真的把它跑起来。

**【字幕】** `VK_EXT_descriptor_heap` · Vulkan SDK 1.4.350

---

## 1. 痛点回顾:传统描述符模型为什么累(约 1:30)

**【画面】** 切到 `visuals.html` 的"传统模型 vs 堆模型"对比图,先只显示左半(传统)。

**【旁白】**
> 先回忆一下传统 Vulkan 是怎么给 shader 喂资源的。
>
> 你要先建一个 **descriptor pool**,从里面分配 **descriptor set**,这个 set 的形状
> 由 **descriptor set layout** 决定。然后用 `vkUpdateDescriptorSets` 把真正的
> 纹理、buffer 写进 set,绘制时再 `vkCmdBindDescriptorSets` 绑定上去。
>
> 问题在哪?第一,**僵硬**:资源组合一变,往往就得换一套 layout、换一个 set。
> 第二,**切换成本**:想在一帧里访问成百上千张纹理,你要么塞进巨大的数组,
> 要么频繁重绑,管线状态被切得很碎。
>
> 而现代渲染——光追、虚拟纹理、GPU-driven pipeline——恰恰需要"任意时刻、
> 随手访问任意资源"。传统模型就成了瓶颈。

**【屏幕动作】** 高亮"pool → set → layout → update → bind"这条链路,打一个红色"繁琐"标记。

---

## 2. 演进线:Vulkan 是怎么一步步走到 heap 的(约 1:10)

**【画面】** 演进时间线图(visuals.html 第二屏)。

**【旁白】**
> Vulkan 不是一步到位的,它分了三步:
>
> 第一步,**`descriptor_indexing`**(已进 1.2 核心):允许 shader 用**非一致索引**
> 访问描述符数组,bindless 的雏形有了,但描述符还是绑在 set 里。
>
> 第二步,**`descriptor_buffer`**:把描述符本身当成**普通数据**,写进一块 buffer,
> 用 GPU 地址绑定。描述符第一次"脱离" set,变成可以自由摆放的内存。
> ——这也是我们这个 demo **实际用来出画面**的扩展。
>
> 第三步,也就是今天的主角,**`descriptor_heap`**:更彻底。一块全局的"堆",
> 加一张"映射表",shader 里的 set/binding 直接由一个**索引**定位到堆中资源。
> 这就和 D3D12 的 `ResourceDescriptorHeap[]`、HLSL SM6.6 的写法对齐了。

**【字幕】** indexing(雏形) → buffer(描述符即数据) → **heap(堆 + 索引)**

---

## 3. 核心概念:一个堆,一个索引(约 1:40)

**【画面】** 堆内存布局图 + 索引访问流(visuals.html 第三屏)。

**【旁白】**
> 把 descriptor_heap 的脑内模型建立起来,后面代码就很顺了。
>
> 想象一块连续的 GPU 内存,这就是**堆(heap)**。每个资源的描述符按固定尺寸
> 紧密排在里面——第 0 槽、第 1 槽、第 2 槽……我们的 demo 里,
> `uniformBufferDescriptorSize` 是 **8 字节**,所以 6 个场景就是堆里 6 个 8 字节的槽位。
>
> shader 要用某个资源时,它**不绑定**任何东西,而是拿一个**整数索引**,
> 比如 `index = 2`,直接去堆里第 2 槽取描述符。
>
> 索引从哪来?这正是 descriptor_heap 灵活的地方——它定义了一张**映射表**
> (`VkDescriptorSetAndBindingMappingEXT`),可以指定索引来自:
> push 常量、间接 buffer、shader record……我们用最直观的一种:
> **`HEAP_WITH_PUSH_INDEX`**——CPU 每帧 push 一个索引进去。

**【屏幕动作】** 动画演示:CPU 推一个数字 `2` → 箭头指到堆第 2 槽 → 取出纹理 → shader 用它上色。

**【关键字幕】**
> 传统:**绑定**资源 → shader 用
> 堆模型:shader 拿**索引** → 自己去堆里取

---

## 4. API 走一遍(约 2:40)

**【画面】** IDE 里打开 `descriptor_heap_reference.cpp`,跟着旁白滚动;旁边放调用流程图。

**【旁白】**
> 来看真实 API。整个流程六步,我对着代码讲。

**【屏幕动作 + 旁白分步】**

1. **开特性**
   > `VkPhysicalDeviceDescriptorHeapFeaturesEXT.descriptorHeap = VK_TRUE`,挂到 `vkCreateDevice`。

2. **查描述符尺寸**
   > `vkGetPhysicalDeviceDescriptorSizeEXT(phys, type)` 告诉你一个采样图像 / buffer 描述符
   > 占多少字节。堆的大小 = 资源数 × 尺寸,再按对齐取整。

3. **建堆 buffer**
   > 普通 `vkCreateBuffer`,但 usage 是新的 **`VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT`**
   > (采样器用独立的 sampler 堆,机制一样)。

4. **写描述符进堆**
   > `vkWriteResourceDescriptorsEXT` / `vkWriteSamplerDescriptorsEXT`,
   > 把第 i 个资源的描述符写进堆里第 i 个槽位——本质就是往映射内存里写数据。

5. **建映射表**(灵魂)
   > `VkDescriptorSetAndBindingMappingEXT`:告诉驱动"shader 的 set=0 binding=0
   > 这个采样图像,索引从 **push 数据**里取"。
   > `source = HEAP_WITH_PUSH_INDEX_EXT`。

6. **录命令:绑堆 + push 索引 + draw**
   > `vkCmdBindResourceHeapEXT(cmd, &bindInfo)` 整帧绑一次堆;
   > `vkCmdPushDataEXT(cmd, &pushInfo)` 把当前索引推进去;
   > 然后照常 `vkCmdDraw`。

**【旁白·对照】**
> 注意看,这套和我们 demo 里实际跑的 `descriptor_buffer` 几乎一一对应:
> 绑堆 ↔ `vkCmdBindDescriptorBuffersEXT`,push 索引 ↔ `vkCmdPushConstants`。
> descriptor_heap 只是把"绑定 + 偏移"进一步统一成了"绑一整块堆 + push 一个索引",
> 更接近 D3D12,也更适合一帧内无缝切换海量资源。

---

## 5. Demo 实战讲解(约 2:00)

**【画面】** 左边 demo 实时画面,右边控制台日志 + `sdf_bindless.frag` 代码。

**【旁白】**
> 回到我们能真跑的版本。启动时控制台打印了几个关键信息:
> GPU 是 RTX 5090;`descriptor_buffer` 支持,用它渲染;`descriptor_heap` 当前
> 驱动还不支持,所以走教学降级。还告诉我们:单个 uniform 描述符 **8 字节**,
> 整个描述符集布局 **256 字节**,已经把 **6 个描述符写进了堆**。

**【屏幕动作】** 高亮 frag shader 里:
```glsl
SceneParams sp = scenes[nonuniformEXT(idx)].s;   // 按索引取堆中资源
```
和 main.cpp 里:
```cpp
pcv.sceneA = a;                 // CPU 算出当前索引
vkCmdPushConstants(..., &pcv);  // push 给 shader
```

**【旁白】**
> 看,屏幕上每一次形状的切换,背后就是这个 `sceneA` 索引在 0 到 5 之间走。
> 我们没有重建任何描述符、没有重绑任何 set——所有 6 个场景的描述符一开始就
> 静静躺在堆里,运行时只是**换了个索引**。这就是 bindless 的爽点。

**【可选演示】** 临时把场景切换速度调快 / 调成手动按键切换,强调"索引驱动画面"。

---

## 6. 现状与注意事项(约 1:10)

**【画面】** `vulkaninfo` 输出(grep descriptor)+ README 的双路径表格。

**【旁白】**
> 几个要交代清楚的现实问题:
>
> 一,**它很新**。spec version 1,SDK 1.4.350 里头文件齐全,但**桌面驱动目前
> 还没暴露它**。所以你现在写的 descriptor_heap 代码能编译,运行时 `vkCreateDevice`
> 会因为扩展不被支持而失败。这也是我们这个 demo 用 `descriptor_buffer` 出画面、
> 把 descriptor_heap 作为"未来形态"并排讲解的原因。
>
> 二,**它和 descriptor_buffer 是延续关系**,不是互斥。理解了 buffer,heap 几乎零成本上手。
>
> 三,**关注点**:堆的尺寸 / 对齐、capture-replay(调试器抓帧需要)、
> 以及 sampler 堆和 resource 堆分开管理。这些 SDK 头文件里都有对应字段。

**【字幕】** spec v1 · 头文件就绪 · 等驱动 · 现在可用 descriptor_buffer 预演

---

## 7. 收尾(约 0:30)

**【画面】** demo 画面回到全屏,缓慢 morph,逐渐淡出。

**【旁白】**
> 总结一句:`descriptor_heap` 让 Vulkan 的资源访问从"绑定时代"走向"索引时代"。
> 一块堆,一个索引,海量资源随手可取。等驱动跟上,它会成为 GPU-driven 渲染的默认姿势。
>
> 工程代码、脚本、图示都在仓库里,自己跑一跑、改改索引,体会最深。
> 我是 ___,我们下期见。

**【字幕】** 代码 / 图示见仓库 · 点赞关注

---

## 录制清单(checklist)

- [ ] `vk_demo.exe` 全屏录一段干净的 SDF morph(开场 + 收尾用);静帧已备 `video/shot_0..3.png`
- [ ] 控制台启动日志录屏(第 5 段)
- [ ] **成品视觉元素帧已就绪**:`video/frames/v0..v7_*.png`(1920×1080),直接排进时间线 ——
      v0 开场 / v1 段1 / v2 段2 / v3+v4 段3 / v5 段4 / v6 段4·6 / v7 段6
- [ ] IDE 滚动 `descriptor_heap_reference.cpp`(第 4 段)
- [ ] `vulkaninfo | findstr descriptor` 终端画面(第 6 段)
- [ ] (可选)`video/visuals.html` 第 3 屏有索引访问动画,需要动态效果时录这一屏
