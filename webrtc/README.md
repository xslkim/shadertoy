# WebRTC 原理教程 · 视频输入资源（上下两集）

面向有网络基础的程序员，讲透四件事：
为什么实时性高 → 底层编解码（深入码流/比特层）→ 数据包怎么封装 → 市面遥控方案对比。
内容密度高，拆成上下两集，每集约 8–12 分钟。

## 文件结构

```
webrtc/
├── B00.wav            参考音色（两集共享，voiceRef 均为 ../B00.wav）
├── ep1/               上集 · 实时性与编解码（19 块 B01–B19）
│   ├── meta.md
│   ├── script.md
│   ├── _diagrams/     技术图 HTML 源码 + theme.css + render.sh
│   └── assets/        渲染产物 PNG
└── ep2/               下集 · 数据包封装与方案对比（16 块 B01–B16）
    ├── meta.md
    ├── script.md
    ├── _diagrams/
    └── assets/
```

> 每集块 ID 各自从 B01 起独立编号（两集是两个独立 AutoVideo 工程）。

## 分集内容

- **上集（ep1）** —— 开场 + 第一幕「实时性从哪来」(UDP/RTP/拥塞控制/抗丢包/抖动缓冲) +
  第二幕「编解码」(冗余/IPB 帧/编码流水线/NAL 码流/比特层/编解码器之争/SVC/Opus)，末尾接下集预告。
- **下集（ep2）** —— 上集回顾 + 第三幕「数据包封装」(协议栈/RTP 头/打包模式/RTCP/SRTP+DTLS/DataChannel/ICE) +
  第四幕「方案对比」(遥控本质/RustDesk/Parsec·Moonlight/TeamViewer·向日葵/云游戏/横向大对比) + 系列总结。

## 视觉素材分工（每集相同思路）

- **HTML 截图**：所有精确技术图（管线、比特字段、协议栈、对比表等）。
  源码在 `ep*/_diagrams/Bxx.html`，已渲染成 `ep*/assets/Bxx.png`，脚本用 `@visual: image(./assets/Bxx.png)` 引用。
- **文生图**：开场与各幕分隔的概念海报，用 `@visual: image`，构建时由文生图 API 生成，无需本地文件。
  - 上集：B01 / B03 / B10 / B19
  - 下集：B01 / B09

## 字幕避让

技术图底部的小字（`.foot`）已上移到距底 120px（原 40px），给后期叠加的字幕让出空间，不会被遮挡。

## 重新生成截图

修改某个 HTML 后，用 headless Chrome 重渲染（需本机 Chrome），在对应集的 `_diagrams` 目录下执行：

```bash
cd ep1/_diagrams        # 或 ep2/_diagrams
bash render.sh B14 B15                            # 渲染指定块
bash render.sh $(ls *.html | sed 's/.html//')    # 全部重渲
```

输出 1920×1080、深色背景，落到 `../assets/Bxx.png`。

## 下一步

把 `ep1/` 和 `ep2/` 分别交给构建 Agent，各自按 AutoVideo `BUILD.md` 生成一集 MP4。
