>>> 开场标题 #B01
@enter: fade-up
@exit: fade
@visual: image(./assets/B01.png)

--- visual ---
（本块使用预渲染图 ./assets/B01.png：标题页「用 Kalibr 标定自动驾驶多相机」，
副标题「从针孔模型到重投影误差优化」。源文件 assets/B01.html，可用 assets/build.sh 重渲染。）

--- narration ---
自动驾驶车上，往往装着十几个相机
要让它们协同工作，第一步是 **标定**
这期视频，我们用 **Kalibr** 标定多相机的内参和外参
不只教命令，更要讲清楚它背后的原理


>>> 为什么要标定 #B02
@enter: fade-up
@exit: fade
@visual: image(./assets/B02.png)

--- visual ---
（预渲染图 ./assets/B02.png：俯视图展示一辆车的环视相机 FOV，右侧列出三个理由。源文件 assets/B02.html。）

--- narration ---
为什么自动驾驶离不开标定？
**BEV 鸟瞰图**，要把多路画面拼成统一的俯视视角
**多传感器融合**，要把相机、激光雷达投到同一坐标系
而像素反算距离，依赖准确的内参和畸变
这一切的前提，是知道每个相机的内参和外参
外参差一度，五十米外就可能偏出近一米


>>> 复习：内参 #B03
@enter: fade
@exit: fade
@visual: image(./assets/B03.png)

--- visual ---
（预渲染图 ./assets/B03.png：针孔投影模型 + 内参矩阵 K 与畸变系数。源文件 assets/B03.html。）

--- narration ---
开始之前，先快速复习两个概念
**内参**，描述的是相机内部的成像几何
焦距 fx、fy，主点 cx、cy，组成内参矩阵 K
它和相机装在哪无关，只跟镜头和传感器有关
真实镜头还有畸变，会把直线拍弯
所以畸变系数，也必须一起建模


>>> 复习：外参与标定本质 #B04
@enter: fade
@exit: fade
@visual: image(./assets/B04.png)

--- visual ---
（预渲染图 ./assets/B04.png：世界系与相机系之间的 T=[R|t]，以及标定作为反问题。源文件 assets/B04.html。）

--- narration ---
**外参**，是相机相对某个参考系的位姿
一个旋转 R，加一个平移 t，合起来记作 T
那标定到底在求什么？
它本质上是一个 **反问题**
已知标定板角点的 3D 坐标，和它们在图像里的像素
反过来，求内参、畸变，和每个相机的外参


>>> Kalibr 是什么 #B05
@enter: fade-up
@exit: fade
@visual: image(./assets/B05.png)

--- visual ---
（预渲染图 ./assets/B05.png：Kalibr 能力卡片 + 核心方法「基于重投影误差的批量优化」。源文件 assets/B05.html。）

--- narration ---
这就轮到 Kalibr 出场了
它是苏黎世联邦理工 ASL 实验室开源的标定工具箱
能做多相机内外参、相机和 IMU、卷帘快门标定
这一期，我们只聚焦 **多相机的内参和外参**
它的核心方法，是基于 **重投影误差** 的批量优化
这个词先记住，下面我们一步步拆开它


>>> 标定板 AprilGrid #B06
@enter: fade
@exit: fade
@visual: image(./assets/B06.png)

--- visual ---
（预渲染图 ./assets/B06.png：白底 AprilGrid 标定板 + 三条优势说明。源文件 assets/B06.html。）

--- narration ---
标定要做的第一件事，是准备一块标定板
Kalibr 推荐用 **AprilGrid**
它由一格一格的 AprilTag 组成，每个 tag 有唯一编码
好处是，哪怕只拍到一部分，也知道是哪些角点
棋盘格必须整块可见，AprilGrid 没有这个限制
而且角点能自动检测到亚像素精度


>>> 角点检测 #B07
@enter: fade
@exit: fade
@visual: image(./assets/B07.png)

--- visual ---
（预渲染图 ./assets/B07.png：透视标定板上的绿色角点、tag ID 与亚像素放大。源文件 assets/B07.html。）

--- narration ---
有了板子，第一步是 **角点检测**
Kalibr 先解码每个 tag，知道它是哪一格
再提取每个 tag 四个角的亚像素位置
于是每个角点，都得到一对对应关系
板上已知的 3D 点，和图像里的 2D 像素
这些对应关系，就是后面优化要用的观测数据


>>> 核心：重投影误差 #B08
@enter: zoom-in
@exit: fade
@visual: image(./assets/B08.png)

--- visual ---
（预渲染图 ./assets/B08.png：3D 点经外参、内参投影成预测像素，与实测像素的红色残差，以及最小化公式。源文件 assets/B08.html。）

--- narration ---
接下来是全片最核心的概念，**重投影误差**
我们拿板上的一个 3D 点
先用外参，把它从世界系转到相机系
再用内参和畸变，投到图像平面，得到 **预测像素**
而我们实际检测到的，是 **实测像素**
这两者之间的差，就叫重投影误差
标定的目标，就是让所有角点的重投影误差平方和最小


>>> 批量优化 #B09
@enter: fade
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 #0d1117，整体内容占画布约 88%。
顶部居中标题 "批量优化 Batch Optimization"，字号 60px，粗体 #e6edf3，距顶 70px；
标题正下方 16px 出现一条 4px 粗的 accent 横线（#58a6ff），从左扫入。

左侧约 42% 宽处是一张「未知数」卡片：背景 #161b22，边框 1px #30363d，圆角 18px，内边距 32px，标题 "待求未知数" 字号 34px。
卡片内三行，每行字号 30px，左侧有 accent 圆点：
  ① 各相机 内参 K + 畸变
  ② 各帧·各相机 位姿 T
  ③ 相机间 外参 T_cn_c0
[0s] 三行依次淡入，每行间隔 0.3s，每行右端伸出一条短箭头指向右方。

画面中部偏右是一个「优化器」圆形节点：直径约 180px，accent 描边 4px，内写 "min Σ‖e‖²"，等宽字体 28px。三条 accent 箭头从未知数卡片汇入该圆。
[1.5s] 圆形节点开始缓慢旋转（持续旋转）。

底部是一张「重投影误差」折线图，宽约 70% 画布、高约 240px：x 轴标注 "迭代次数"、y 轴标注 "误差(px)"，坐标轴颜色 #30363d。
曲线 accent 色，从左上的 2.0px 平滑下降并收敛到 0.2px 附近。
[2s] 曲线从左到右逐步绘制（约 3s 画完），末端有一个跟随的高亮圆点和数值标签，
数值随绘制从 "2.0 px" 递减到 "0.2 px"，字号 30px。
[5.5s] 收敛后，曲线末端出现绿色对勾 ✓ 与 "已收敛 0.2px" 标签（绿色 #3fb950，字号 30px）。

--- narration ---
注意，这里要调整的未知数非常多
每个相机的内参和畸变
每一帧、每个相机相对板的位姿
还有相机之间的相对外参
Kalibr 把它们全部放进 **同一个** 最小二乘问题
一起迭代，让总的重投影误差不断下降
这种联合求解，就是 **批量优化**


>>> 多相机外参怎么求 #B10
@enter: fade
@exit: fade
@visual: image(./assets/B10.png)

--- visual ---
（预渲染图 ./assets/B10.png：cam0、cam1 同时看板，位姿串联得到相机间外参 T_c1_c0。源文件 assets/B10.html。）

--- narration ---
那相机之间的外参，具体怎么算出来？
关键在于，相邻相机要 **同时** 看到同一块板
这一刻，cam0 和 cam1 各自有相对板的位姿
把这两个位姿一串联，板的位姿就被消掉了
剩下的，就是两个相机之间恒定的相对外参
所以相邻相机必须有 **重叠视野**，否则没法串联


>>> 选对畸变模型 #B11
@enter: fade
@exit: fade
@visual: image(./assets/B11.png)

--- visual ---
（预渲染图 ./assets/B11.png：radtan 桶形畸变 vs equidistant 鱼眼畸变网格，及模型选择。源文件 assets/B11.html。）

--- narration ---
还有一个容易翻车的点，**畸变模型**
普通前视、窄角相机，用 pinhole-radtan
自动驾驶常见的鱼眼、环视相机，要用 pinhole-equi
视场角特别大的，可以选 ds 或者 eucm
模型选错，边缘的重投影误差永远压不下去
命令里用 models 参数，给每个相机各指定一个


>>> 动手①：安装 Kalibr #B12
@enter: slide-left
@exit: fade
@visual: image(./assets/B12.png)

--- visual ---
（预渲染图 ./assets/B12.png：Docker 安装三步命令 + 说明卡片。源文件 assets/B12.html。）

--- narration ---
原理讲完了，我们来真正跑一次
第一步，装好 Kalibr
它基于 ROS，依赖比较复杂
强烈建议直接用官方的 Docker 镜像
clone 源码，build 镜像，再 run 进容器
最后用 -v，把存数据的目录挂载进去就行


>>> 动手②：准备标定板 #B13
@enter: fade
@exit: fade
@visual: image(./assets/B13.png)

--- visual ---
（预渲染图 ./assets/B13.png：create_target_pdf 命令 + aprilgrid.yaml + 三条注意事项。源文件 assets/B13.html。）

--- narration ---
第二步，准备标定板
用 kalibr_create_target_pdf 生成可打印的 PDF
再写一个 yaml，告诉 Kalibr 板子的真实尺寸
这里有个大坑：打印通常会缩放
一定要用尺子量出实际 tagSize，再填进 yaml
板子还要贴在硬板上，平整、哑光、不反光


>>> 动手③：采集现场 #B14
@enter: fade
@exit: fade
@visual: image

--- visual ---
一张写实风格的照片：一名工程师站在一辆白色自动驾驶测试车前方，
双手举着一块大号 AprilGrid 标定板（黑白方格图案，平整地贴在硬质铝板上），
正缓慢地在车头的多颗环视与前视摄像头前方移动、展示标定板。
车身和车顶可见若干小型摄像头和传感器模块。
场景是室内停车场或实验场，光线均匀柔和，没有强反光和高光。
背景轻微虚化，主体清晰，整体科技感、真实摄影质感。

--- narration ---
第三步，采集数据
实际操作其实很朴素：有人举着标定板
在每一颗相机前方，缓慢地移动、变换姿态
让相机从不同距离、不同角度都能拍到它
那到底怎么动才算到位？我们看下一页


>>> 采集要点 #B15
@enter: fade-up
@exit: fade
@visual: image(./assets/B15.png)

--- visual ---
（预渲染图 ./assets/B15.png：DO / DON'T 两栏对照 + rosbag 录制命令。源文件 assets/B15.html。）

--- narration ---
这一步看似简单，却往往决定成败
要让角点铺满整个画面，覆盖不同距离和角度
缓慢移动，并让相邻相机充分共视
千万别只在画面中心晃，也别快速挥动
过曝和反光，会让 tag 直接解码失败
最后用 rosbag，把所有相机的话题一起录下来


>>> 动手④：跑标定命令 #B16
@enter: slide-left
@exit: fade
@visual: image(./assets/B16.png)

--- visual ---
（预渲染图 ./assets/B16.png：kalibr_calibrate_cameras 命令逐项注释 + 三张说明卡。源文件 assets/B16.html。）

--- narration ---
数据有了，剩下的就是一条命令
kalibr_calibrate_cameras
指定数据包、每个相机的话题、畸变模型和标定板
注意 topics 和 models 的顺序，要一一对应
它会先各自估内参，再联合优化外参
跑完，产出 camchain.yaml 和报告 PDF


>>> 运行与收敛 #B17
@enter: fade
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 #0d1117，模拟 Kalibr 的运行过程，整体内容占画布约 88%。
顶部居中标题 "运行中：检测 → 优化 → 收敛"，字号 56px，粗体 #e6edf3，距顶 64px，下方 accent 横线。

左侧约 45% 宽是一个「检测可视化」窗口：背景 #0d1117，边框 1px #30363d，圆角 14px。
窗口内是一块透视摆放的标定板网格（灰色细线 #8b949e），网格交点是绿色角点（#3fb950）。
窗口左上角有等宽小字 "cam0   detected: 0 pts"，字号 22px。
[0s–2s] 绿色角点从上到下一行行依次亮起、轻微闪动，左上角的 detected 数字从 0 递增到约 168。

右侧约 50% 宽是一个「终端」卡片：背景 #161b22，边框 1px #30363d，圆角 14px，
等宽字体 JetBrains Mono，字号 26px，行距 1.7，逐行打字机式出现：
  Initializing ...
  Extracting corners ...
  iter 0    reproj err: 1.84 px
  iter 1    reproj err: 0.97 px
  iter 2    reproj err: 0.41 px
  iter 3    reproj err: 0.23 px
  Converged ✓
[2s–6s] 日志逐行出现，每行间隔约 0.6s；其中 "reproj err" 后的数字用 accent 色，
误差数值逐行递减；最后一行 "Converged ✓" 用绿色 #3fb950 高亮加粗。

底部居中是一条进度条，宽约 70% 画布、高 14px、圆角：
[2s–6s] 从 0 平滑填充到 100%，颜色 accent，填满后整体变绿色 #3fb950。

--- narration ---
运行时，Kalibr 会弹出一个检测可视化窗口
你能看到角点被一帧一帧地标记出来
然后进入优化，终端里打印出每次迭代
重投影误差，从一两个像素一路往下掉
直到收敛，稳定在零点几个像素
到这里，标定就算跑完了


>>> 看懂输出 #B18
@enter: fade
@exit: fade
@visual: image(./assets/B18.png)

--- visual ---
（预渲染图 ./assets/B18.png：camchain.yaml 结构与 intrinsics / distortion / T_cn_cnm1 解读。源文件 assets/B18.html。）

--- narration ---
最重要的产物，是 camchain.yaml
每个相机都有 intrinsics，也就是内参
还有 distortion_coeffs，畸变系数
而 T_cn_cnm1，就是相机之间的外参
它是一个四乘四的齐次矩阵
这正是 BEV 拼接和多传感器融合要用的东西


>>> 判断标定好坏 #B19
@enter: fade
@exit: fade
@visual: image(./assets/B19.png)

--- visual ---
（预渲染图 ./assets/B19.png：好 vs 差 的重投影误差散点对比 + 阈值参考。源文件 assets/B19.html。）

--- narration ---
那怎么判断这次标定好不好？
看报告里的重投影误差散点图
好的标定，点又小又均匀，围着原点像随机噪声
一般小于零点三个像素，就算优秀
如果误差偏大，或出现明显的结构和偏置
那就是模型或数据有问题，别凑合，重新来


>>> 常见的坑 #B20
@enter: fade-up
@exit: fade
@visual: image(./assets/B20.png)

--- visual ---
（预渲染图 ./assets/B20.png：五张常见错误卡片 + 排查口诀。源文件 assets/B20.html。）

--- narration ---
最后，列几个最常见的坑
挥得太快导致运动模糊，角点就糊了
相邻相机共视不足，外参就算不出来
tagSize 量错，整个尺度会系统性偏差
鱼眼相机用错畸变模型，边缘误差会爆炸
姿态太单一，参数会欠约束
排查时，先看角点检测，再看模型，最后看覆盖


>>> 回顾与下一步 #B21
@enter: fade-up
@exit: fade
@visual: image(./assets/B21.png)

--- visual ---
（预渲染图 ./assets/B21.png：整条标定链路回顾 + 自己动手 / 进阶方向。源文件 assets/B21.html。）

--- narration ---
我们快速回顾一下整条链路
从 AprilGrid 和角点检测，到重投影误差建模
再到批量优化，解出内参和外参
最后拿到 camchain.yaml，并用误差来验收
现在，你完全可以自己动手跑一遍
想进阶，下一步可以挑战相机和 IMU 的标定
那就要用到连续时间的 B 样条优化了，我们下期再聊
