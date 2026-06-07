# HTML → PNG 视觉生成

把"代码窗 / 对比表 / 小结 / 流程图"这类**静态、规整**的视觉，用 HTML+CSS 写好后
截图成 PNG，再在 `script.md` 里用 `@visual: image(./assets/Bxx.png)` 引用。
相比 `@visual: animation`（Claude 生成 Remotion 组件），HTML 截图**像素级一致、可复现、零 AI 调用**。

> 概念隐喻插画（工厂、传送门、机器人那些）**不走这条路**——它们仍用 `@visual: image`
> 文生图，HTML 画不出来。

## 用法

```bash
node html/render.mjs          # 渲染全部 html/<ep>/*.html → <ep>/assets/<id>.png
node html/render.mjs ep1      # 只渲染 ep1
node html/render.mjs ep1/B08  # 只渲染单块
```

依赖：本机 Chrome 或 Edge（已检测到）。无需 npm 安装。输出固定 1920×1080。

## 目录约定

```
html/
├── theme.css          # 共享主题（配色 = AUTHORING.md theme.colors）+ 布局基元
├── render.mjs         # Chrome headless 批量截图
├── ep1/B08.html       # 文件名 = 块 ID，渲染到 ep1/assets/B08.png
└── ep2/...
```

## 写一个新块

1. 在 `html/<ep>/<Bxx>.html` 写 HTML，首行引入主题：
   `<link rel="stylesheet" href="../theme.css">`，内容放进 `<div class="stage">`。
2. 复用 `theme.css` 的基元：`.code`(代码窗) / `table`(对比表) / `.bullets`(小结) /
   `.row`+`.approx`(并排 + ≈)；语法高亮用 `.kw .str .cmt .type .accent .good .bad`。
3. `node html/render.mjs <ep>/<Bxx>` 渲染，确认 PNG。
4. 在 `script.md` 把该块的 `@visual: animation` 改成 `@visual: image(./assets/<Bxx>.png)`。
   `--- visual ---` 描述保留作文档（也是写 HTML 的依据）。

## 当前状态

所有代码/表格/卡片/流程图/小结块均已转为 HTML→PNG（`@visual: image`）：

- **ep1**: 16 块 HTML（B02,B05,B06,B08,B10,B11,B12,B13,B14,B15,B17,B18,B20,B21,B22,B24）
  + 7 张隐喻插画（B01,B04,B07,B09,B16,B19,B23，文生图本地 PNG）
  + **B03 保留 `animation`**（同步代价：线程时间轴进度条要动态变红冻结，动画即讲解）
- **ep2**: 10 块 HTML（B02,B04,B06,B08,B09,B12,B13,B14,B15,B16）
  + 6 张隐喻插画（B01,B03,B05,B07,B10,B11）。**全集零 AI 生成**。

> 注意：静态截图会**丢掉 `[Xs]` 时间轴动画**。代码/表格通常静态即可；
> 若某块强依赖逐步揭示（如 ep1 B03），保留 `animation`，或渲成短 mp4 用 `@visual: video(./path)`。
> 改 HTML 后记得重跑 `node html/render.mjs` 重新生成对应 PNG。
