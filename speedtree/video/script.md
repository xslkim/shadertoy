>>> 开场标题 #B01
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 (#0d1117)。画面垂直居中布局，内容占画布约 80% 宽度：
[0s] 主标题 "SpeedTree 树木渲染" 淡入，白色 (#e6edf3)，粗体，字号 96px，居中。
[0.6s] 主标题下方 32px 出现副标题 "渲染原理与 Blender MCP 替代方案"，颜色 #8b949e，字号 36px。
[1.2s] 副标题下方 20px 出现一条 4px 粗的 accent 色 (#58a6ff) 横线，宽度等于主标题，从左向右扫入，耗时 0.8s。
[2s] 横线下方 48px 出现小字 "面向技术美术 · 基于实际项目实现"，颜色 #8b949e，字号 28px。

--- narration ---
大家好
这期视频我们来深入理解 **SpeedTree** 这个树木渲染工具
重点讲它的 **渲染原理** 和优缺点
然后我们用 **Blender 加 MCP** 实际实现一棵松树
作为替代方案的验证


>>> SpeedTree 是什么 #B02
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "SpeedTree 是什么"，字号 64px，粗体，颜色 #e6edf3，距顶 60px。
下方内容分左右两栏，总宽占画布 90%，间距 48px：
左栏（占 45%）：[0.5s] 文字卡片，背景 #161b22，圆角 16px，内边距 32px：
  - "植被建模与渲染中间件" 字号 36px accent 色
  - "2002 年由 IDV 发布" 字号 28px #8b949e
  - "2021 年被 Unity 收购" 字号 28px #8b949e
  - "2015 年获奥斯卡科技奖" 字号 28px #8b949e
右栏（占 45%）：[1.5s] 三个客户 Logo 文字卡片纵向排列，每个卡片背景 #161b22，高 100px：
  - "3A 游戏：巫师3 / 对马岛之魂 / 战地4" 字号 28px
  - "影视：阿凡达 / 钢铁侠3 / 少年派" 字号 28px
  - "建筑可视化与军事仿真" 字号 28px

--- narration ---
SpeedTree 是业界标准的 **植被建模与渲染中间件**
2002 年由 IDV 公司发布
2021 年被 Unity 收购
它在 2015 年获得了 **奥斯卡科学技术奖**
被数百款 3A 游戏和四十多部电影采用
包括巫师三、对马岛之魂和阿凡达


>>> SpeedTree 解决的核心问题 #B03
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "它解决什么问题"，字号 64px，粗体，距顶 60px。
下方三张卡片横向等距排列，总宽占画布 90%，间距 40px，每张卡片高 320px，圆角 16px，背景 #161b22：
[0.5s] 卡片1 从左滑入：顶部图标 "LOD"（字号 48px accent 色），标题 "多级细节" 字号 40px，描述 "远近距离自动切换精度" 字号 28px #8b949e
[1s] 卡片2 从下滑入：顶部图标 "WIND"（字号 48px accent 色），标题 "实时风动画" 字号 40px，描述 "顶点着色器驱动自然摆动" 字号 28px #8b949e
[1.5s] 卡片3 从右滑入：顶部图标 "GPU"（字号 48px accent 色），标题 "批量实例化" 字号 40px，描述 "万棵树一次绘制" 字号 28px #8b949e

--- narration ---
SpeedTree 核心解决三个问题
第一是 **LOD 多级细节** 系统
让远处的树自动降低精度
第二是 **实时风动画**
用顶点着色器让树木自然摆动
第三是 **GPU 批量实例化**
把上万棵树用极少的绘制调用渲染出来


>>> 渲染原理：LOD 系统 #B04
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "渲染原理：LOD 多级细节"，字号 56px，粗体，距顶 50px。
[0.5s] 画面中央横向排列三个树模型示意，总宽占画布 85%：
  左侧：高精度松树（用线框示意，密集三角形），下方标签 "LOD0 · 8万面" 字号 32px accent 色
  中间：中精度松树（线框较稀疏），下方标签 "LOD1 · 2万面" 字号 32px #e6edf3
  右侧：低精度松树（极简线框），下方标签 "LOD2 · 3千面" 字号 32px #8b949e
[3s] 三棵树上方出现屏占比进度条（宽占画布 70%），从左到右标注 "100% → 25% → 12.5% → 1%"，字号 28px
[5s] 进度条上出现移动光标，经过 25% 阈值时左树淡出、中树淡入，经过 12.5% 时中树淡出、右树淡入

--- narration ---
LOD 系统是 SpeedTree 性能的关键
同一棵树预生成 **三到六个不同精度** 的版本
LOD0 是高精度模型有八万面
LOD1 降到两万面
LOD2 只有三千面
引擎根据 **屏幕占比** 自动切换
树在画面里占 25% 以上用 LOD0
降到 12.5% 切换到 LOD1
降到 1% 用 LOD2
这样远处的树几乎不消耗性能


>>> 渲染原理：风动画数学 #B05
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "渲染原理：风动画"，字号 56px，粗体，距顶 50px。
[0.5s] 画面左侧（占 45%）显示代码块，背景 #161b22，圆角 12px，内边距 28px，等宽字体字号 28px：
  "float TriangleWave(float x) {"
  "  return abs(frac(x+0.5)*2.0 - 1.0);"
  "}"
  "float CubicSmooth(float x) {"
  "  return x*x*(3.0 - 2.0*x);"
  "}"
  "// 逼近 sin，速度快数倍"
  "float wind = TrigApprox(t) * height;"
关键字用 #ff7b72 色，注释用 #8b949e 色，函数名用 #58a6ff 色
[2s] 画面右侧（占 45%）显示松树摆动示意：树根固定，树顶随时间左右摆动，用 accent 色虚线标出摆动轨迹。下方标注 "高度越高摆动越大" 字号 28px
[4s] 右侧叠加一条曲线对比图：accent 色实线 = TrigApprox，灰色虚线 = sin，标注 "几乎重合" 字号 24px

--- narration ---
风动画是 SpeedTree 最巧妙的设计
它不用物理模拟
而是在 **顶点着色器** 里用数学函数逼近正弦波
关键是这两个函数
TriangleWave 用 frac 和 abs 近似三角波
CubicSmooth 把它平滑成类似正弦的曲线
比原生 sin 快数倍
风强度随顶点高度增加
树根不动、树顶摆动最大
这就是 SpeedTree 的 **Global Motion** 技巧


>>> 渲染原理：GPU Instancing #B06
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "渲染原理：GPU Instancing"，字号 56px，粗体，距顶 50px。
[0.5s] 画面左侧（占 40%）显示对比卡片，背景 #161b22，圆角 12px：
  上方红色文字 "不用 Instancing" 字号 36px，下方 "1000 棵树 = 1000 次 Draw Call" 字号 28px #8b949e
  下方 accent 色文字 "用 Instancing" 字号 36px，下方 "1000 棵树 = 1 次 Draw Call" 字号 28px
[2s] 画面右侧（占 50%）显示 3x3 网格的松树实例，每棵树用简单图标表示，全部用 accent 色边框连接到中心的 "GPU" 标签，表示一次提交
[4s] 右侧网格扩展为更多树（5x5），标注 "实例数据包含：位置 / 旋转 / 缩放" 字号 28px

--- narration ---
GPU Instancing 解决的是 **大规模植被** 的性能问题
不用 Instancing 时
一千棵树需要一千次绘制调用
每次都有 CPU 到 GPU 的通信开销
开启 Instancing 后
把同一棵树的网格和材质提交一次
用 **实例数据数组** 告诉 GPU 每棵树的位置和旋转
一千棵树只需 **一次绘制调用**
这是开放世界游戏能渲染百万棵树的关键


>>> 优缺点总结 #B07
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "优缺点总结"，字号 64px，粗体，距顶 50px。
下方左右两栏，总宽占画布 90%，间距 48px：
左栏（占 45%）[0.5s]：标题 "优势" 字号 40px accent 色，下方四条列表，每条字号 32px #e6edf3：
  "✓ 行业标准，生态成熟"
  "✓ LOD + 风 + Instancing 一体"
  "✓ PBR Library 资产丰富"
  "✓ 跨引擎导出"
右栏（占 45%）[1.5s]：标题 "劣势" 字号 40px #ff7b72 色，下方四条列表，每条字号 32px #e6edf3：
  "✗ 纯订阅制，价格较高"
  "✗ 资产不可再分发"
  "✗ 与 Houdini 程序化生态弱"
  "✗ Nanite 协作需额外工具"

--- narration ---
总结一下 SpeedTree 的优缺点
优势是 **行业标准** 生态成熟
LOD、风动画、实例化一体化
PBR 资产库丰富
而且跨引擎导出
劣势是纯订阅制定价较高
制作的模型 **不可再销售**
与 Houdini 的程序化生态集成较弱
和 UE5 Nanite 配合需要额外转换工具


>>> 适用范围与选型 #B08
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "适用范围与选型建议"，字号 56px，粗体，距顶 50px。
[0.5s] 画面中央三栏卡片横向排列，总宽占画布 90%，每栏高 380px，圆角 16px：
卡片1（背景 #161b22）：[0.8s] 标题 "推荐用 SpeedTree" 字号 36px accent 色，列表字号 28px：
  "· 3A 商业项目"
  "· 需要快速出成品"
  "· 团队无 Houdini TA"
  "· 跨引擎协作"
卡片2（背景 #161b22）：[1.5s] 标题 "推荐 Houdini 路线" 字号 36px #e6edf3，列表字号 28px：
  "· 开放世界大场景"
  "· 需要深度程序化"
  "· 自研引擎团队"
卡片3（背景 #161b22）：[2.2s] 标题 "推荐 Blender 路线" 字号 36px #e6edf3，列表字号 28px：
  "· 独立游戏 / 原型"
  "· 预算敏感"
  "· 已有 Blender 流程"

--- narration ---
选型建议分三种情况
商业 3A 项目、需要快速出成品的团队
推荐直接用 SpeedTree
开放世界大场景、需要深度程序化控制的团队
推荐 Houdini 路线
独立游戏、原型验证、预算敏感的项目
可以考虑 Blender 路线
接下来我们就 **实际验证** 一下 Blender 路线是否可行


>>> Blender + MCP 可行性 #B09
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "Blender + MCP 可行性分析"，字号 56px，粗体，距顶 50px。
[0.5s] 画面中央显示流程图，总宽占画布 85%：
三个圆角矩形横向排列，用 accent 色箭头连接：
  方框1（背景 #161b22）："AI Agent" 字号 36px，下方 "理解需求 + 生成代码" 字号 24px #8b949e
  → 方框2（背景 #161b22）："Blender MCP" 字号 36px，下方 "Socket 通信执行 Python" 字号 24px #8b949e
  → 方框3（背景 #161b22）："Blender" 字号 36px，下方 "bmesh 程序化建模" 字号 24px #8b949e
[3s] 流程图下方出现结论卡片，背景 #161b22，圆角 12px，内边距 28px：
  "可行 ✓" 字号 48px accent 色
  "能完成：建模 / LOD / 导出 / 渲染" 字号 32px
  "差距：无现成 Library / 无运行时 SDK" 字号 28px #8b949e

--- narration ---
Blender 加 MCP 的方案是否可行
答案是 **可行**
流程是 AI Agent 理解需求后生成 Python 代码
通过 MCP 协议的 Socket 通信发给 Blender
Blender 用 bmesh API 程序化建模
能完成建模、LOD 生成、FBX 导出和渲染
但和 SpeedTree 相比
没有现成的 PBR 资产库
也没有运行时 SDK
适合 **原型验证和独立项目**


>>> 实施方案：整体流程 #B10
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "实施方案：五步流程"，字号 56px，粗体，距顶 50px。
[0.5s] 画面中央竖向排列五个步骤卡片，每个卡片高 90px，宽占画布 80%，圆角 12px，背景 #161b22，间距 16px：
[0.8s] 步骤1：左侧 accent 色圆形数字 "1"（字号 36px），右侧 "L-system 程序化生成松树主干与枝条" 字号 32px
[1.3s] 步骤2：左侧 "2"，右侧 "针叶束生成（模拟黑松三针一束）" 字号 32px
[1.8s] 步骤3：左侧 "3"，右侧 "参数化生成 LOD0 / LOD1 / LOD2" 字号 32px
[2.3s] 步骤4：左侧 "4"，右侧 "FBX 导出（含 3 个 LOD mesh）" 字号 32px
[2.8s] 步骤5：左侧 "5"，右侧 "Unity 集成（LODGroup + 风shader + Instancing）" 字号 32px

--- narration ---
具体实施方案分五步
第一步用 **L-system** 程序化生成松树的主干和枝条
第二步生成针叶束，模拟黑松的三针一束
第三步用不同参数生成三个 LOD 版本
第四步导出含三个 mesh 的 FBX 文件
第五步在 Unity 里配置 LODGroup
绑定风着色器并开启 GPU Instancing


>>> 实际实现：L-system 建模 #B11
@enter: fade-up
@exit: fade
@visual: image(../exports/pine_angle.png)

--- visual ---
（使用 ../exports/pine_angle.png 实际渲染图）
写实松树的斜侧面渲染图，深色背景，松树居中展示，可见主干轮生枝条和针叶细节

--- narration ---
这是我们实际生成的写实松树
高十米，八万三角面
主干用 L-system 递归生成
每隔零点八米一圈 **轮生枝**
模拟松树的自然生长特征
每个一级枝分叉出六个二级枝
每个二级枝末端生成针叶束


>>> 实际实现：多视角展示 #B12
@enter: fade
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。四宫格展示松树多视角，总宽占画布 90%：
[0.3s] 左上格：图片 ../exports/pine_front.png，下方标签 "正视图" 字号 28px
[0.6s] 右上格：图片 ../exports/pine_side.png，下方标签 "侧视图" 字号 28px
[0.9s] 左下格：图片 ../exports/pine_top.png，下方标签 "顶视图" 字号 28px
[1.2s] 右下格：图片 ../exports/pine_stylized_render.png，下方标签 "风格化版本" 字号 28px

--- narration ---
从多个视角看一下这棵树
正视图能看到典型的 **松塔形** 树冠
侧视图可见枝条向下倾斜的自然姿态
顶视图呈现轮生枝的放射结构
我们还生成了一个 **风格化版本**
只有八十六面，适合卡通渲染项目


>>> 实际实现：Unity 集成 #B13
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "Unity 集成架构"，字号 56px，粗体，距顶 50px。
[0.5s] 画面中央显示层级结构图，总宽占画布 80%：
根节点 "PineTree (LODGroup)" 字号 36px accent 色，背景 #161b22，圆角 8px
下方三个子节点竖向缩进排列：
  "├─ LOD0 · MeshRenderer · 8万面" 字号 28px，标注 "屏占比 > 25%"
  "├─ LOD1 · MeshRenderer · 2万面" 字号 28px，标注 "12.5% - 25%"
  "└─ LOD2 · MeshRenderer · 3千面" 字号 28px，标注 "1% - 12.5%"
[3s] 右侧出现材质卡片，背景 #161b22，圆角 12px：
  "材质0：PineBark (Custom/PineWind)" 字号 28px
  "材质1：PineNeedle (Custom/PineWind)" 字号 28px
  "GPU Instancing: ✓" 字号 28px accent 色

--- narration ---
Unity 集成的核心是 LODGroup 组件
根节点挂 LODGroup
三个子节点分别是 LOD0、LOD1、LOD2
屏占比阈值和 FBX 导入设置一致
材质用我们写的 **PineWind 着色器**
树皮材质单面渲染
针叶材质双面渲染
都开启了 GPU Instancing
九棵松树实例只需极少的绘制调用


>>> 渲染效果展示 #B14
@enter: fade
@exit: fade
@visual: image(../exports/pine_lod0_render.png)

--- visual ---
（使用 ../exports/pine_lod0_render.png 实际渲染图）
LOD0 高精度松树的最终渲染效果，可见树皮纹理、针叶细节和自然光照

--- narration ---
这是 LOD0 高精度版本的最终渲染效果
可以看到树干的 **渐变锥度**
枝条的自然弯曲
以及针叶束的体积感
风动画在运行时会驱动顶点摆动
树顶摆动幅度最大，根部保持稳定


>>> 总结与选型建议 #B15
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 (#0d1117)。顶部居中标题 "总结"，字号 64px，粗体，距顶 60px。
[0.5s] 画面中央三栏对比表，总宽占画布 90%，圆角 16px，背景 #161b22：
表头字号 32px accent 色：SpeedTree / Houdini / Blender+MCP
第一行 "建模能力" 字号 28px：强 / 极强 / 中
第二行 "LOD 系统" 字号 28px：内置 SDK / 需自建 / 需自建
第三行 "风动画" 字号 28px：内置 SDK / 需自建 / 已实现 ✓
第四行 "GPU Instancing" 字号 28px：内置 / 引擎侧 / 已实现 ✓
第五行 "成本" 字号 28px：订阅制 / 高 / 免费
第六行 "适用规模" 字号 28px：3A 商业 / 开放世界 / 独立原型
[4s] 底部居中出现文字 "选择适合你团队的方案" 字号 36px accent 色

--- narration ---
最后总结三条路线的对比
SpeedTree 建模强、SDK 成熟，适合 3A 商业项目
Houdini 程序化能力极强，适合开放世界大场景
Blender 加 MCP **免费且灵活**
我们已经实现了 LOD、风动画和 GPU Instancing
适合独立游戏和原型验证
希望这期视频帮你 **选择合适的树木渲染方案**
感谢观看
