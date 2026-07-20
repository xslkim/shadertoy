# 交付说明（给构建机器）

## 目录结构
```
dds/
├── B00.wav              ← 参考音色（已从 sync/ 复制）
├── ep1/
│   ├── meta.md          ← slug: ad-middleware-ep1-principles
│   └── script.md        ← B01–B24（24 块）
├── ep2/
│   ├── meta.md          ← slug: ad-middleware-ep2-production
│   └── script.md        ← B25–B46（22 块）
└── assets/
    ├── base.css         ← 共享样式（GitHub Dark 风格）
    ├── build.sh         ← HTML → PNG 截图脚本
    ├── B10.html … B43.html   ← 13 个预渲染图源文件
    └── （B10.png … B43.png）  ← build.sh 生成，目前还没跑
```

## 构建前必做：跑一次 build.sh
13 个块用了 HTML 渲染（中文 100% 准确），需要先生成 PNG：

```bash
cd dds/assets
bash build.sh          # 渲染全部 13 个 HTML
# 或单个: bash build.sh B23
```

要求：本机有 `chromium-browser` / `chromium` / `google-chrome` / `chrome` 之一。
生成后会得到 13 个 1920×1080 的 PNG，脚本里的 `@visual: image(./assets/Bxx.png)` 才能正常引用。

跑完 build.sh 后，再按 BUILD.md 走 AutoVideo 主流程即可。

## 视觉模式分布
- **HTML 预渲染图（13 块）**：B10、B16、B23、B24（EP1）；B27、B28、B29、B30、B31、B32、B41、B42、B43（EP2）
  - 全部是「清单 / 对比表 / 层级图 / 决策树」等文字密集块，用 HTML 保证中文不乱码
- **文生图 image（33 块）**：其余块，走 SenseNova-U1 / OpenAI 兼容 API
  - prompt 已统一加「底部 15% 区域留空不放任何文字」（避免被字幕遮挡）

## ⚠️ 构建后重点抽听（TTS 发音风险词）
以下词在旁白中出现，TTS 读法不可控，建议构建后逐处抽听，必要时改写：

| 风险词 | 出现位置 | 担心点 |
|--------|---------|--------|
| `SOME/IP` | B22、B40、B44 | 斜杠可能读成「some 斜杠 ip」 |
| `rmw_zenoh` | B20 | 下划线读法 |
| `PREEMPT_RT` | B33 | 下划线 + 大小写 |
| `ISO 26262` / `ISO 21434` | B28、B29 | 数字串读法 |
| `ASIL-D` | B28、B33 等 | 连字符 |
| `gPTP` | B34 | 连读字母 |
| `ros2 bag` | B37、B42 | 大小写 + 空格 |
| `CyberRT` / `Zenoh` | 多处 | 专有名词发音 |
| `O(n²)` 相关 | B16 | 旁白已改写为「元数据交换量爆炸」，无需读符号 |

## 内容时效性
- B19 Zenoh 版本号**只留在旁白**（「截至 2026 年已到 1.9 版」），没有烧进图片
- 如发布时 Zenoh 已更新版本，只需重录 B19 旁白这一句，图片无需重生成

## 两集切分
- **EP1（B01–B24）**：原理 + 五大方案横评，以「选型决策树」自收尾
- **EP2（B25–B46）**：商业化逻辑 + 量产工程 + 总结，承接 EP1 的悬念问题
- 块 ID 跨文件全局连续（B01–B46），符合 AUTHORING.md §6
