>>> 开场：真实渲染画面 #B01
@enter: fade
@exit: fade
@visual: video(./assets/hero.mp4)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/hero.mp4 视频文件）
Raymarching 程序的真实运行录屏：相机环绕一个 SDF 场景缓慢旋转，
场景中有 25 种几何体（球、盒子、圆环、胶囊、棱柱、金字塔等），
带柔和阴影、光滑反光、棋盘格地板，1920×1080 实时渲染。

--- narration ---
先看这个画面
一个旋转的 3D 场景，二十多种几何体
柔和的阴影，光滑的反光，通透的边缘
看起来像一个普通的 3D 渲染器
但它没有加载任何 3D 模型
没有一个三角形，没有一个顶点
整个画面，全靠 **数学函数** 实时算出来


>>> 标题 #B02
@enter: fade-up
@exit: fade
@visual: image(./assets/B02.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B02.png 图片文件）
标题卡：小标签 "SDF RAYMARCHING"，主标题 "不需要一个三角形"，
副标题 "只用数学函数，渲染完整的 3D 世界"，
下方三个数字卡片 25+ 几何体种类 / 4 光源组合 / 0 三角形网格。

--- narration ---
这种技术叫 **SDF Raymarching**
它把整个 3D 世界写成数学公式
接下来，我们从零拆解它的每个核心环节
看完你就能写出自己的 SDF 场景


>>> 整体架构：全屏三角形 #B03
@enter: fade-up
@exit: fade
@visual: image(./assets/B03.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B03.png 图片文件）
三步流程图：全屏三角形 → Fragment Shader → 输出像素颜色，
下方为每个像素执行逻辑的伪代码块。

--- narration ---
宿主程序（C++）只做一件事
画一个覆盖全屏的 **三角形**
这个三角形触发 GPU 为每个像素执行 **fragment shader**
shader 里，每个像素独立计算一条从相机出发的 **射线**
射线步进求交，再做光照，输出那个像素的颜色
整个 3D 场景都在这一个 shader 函数里


>>> SDF：用距离函数描述几何体 #B04
@enter: fade-up
@exit: fade
@visual: image(./assets/B04.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B04.png 图片文件）
左侧 SDF 定义与正负号含义（外部 / 表面 / 内部），
右侧距离场可视化：圆形物体、同心距离环、内外采样点与安全步进箭头。

--- narration ---
SDF，全称 **有符号距离函数**
给定空间中任意一点 p
它返回 p 到最近表面的 **有符号距离**
正数在外部，负数在内部，零在表面上
"有符号" 让它既描述距离，也描述内外关系
这个距离值就是 Sphere Tracing **步进的依据**


>>> 球的 SDF：最简单的例子 #B05
@enter: fade
@exit: fade
@visual: image(./assets/B05.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B05.png 图片文件）
左侧球 SDF 公式 |p|−r、代码、文字说明，
右侧坐标系中的球、半径箭头、内外采样点与平移示意。

--- narration ---
球的 SDF 只有一行代码
**length(p) − r**
length(p) 是点 p 到原点的距离
减去半径 r，结果就是到球面的有符号距离
要把球放到任意位置 center
只需传入 **p − center** 就完成平移
这个"坐标偏移等于平移"的技巧
贯穿整个 shader 的所有几何体


>>> 盒子的 SDF：利用对称性 #B06
@enter: fade-up
@exit: fade
@visual: image(./assets/B06.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B06.png 图片文件）
左侧 sdBox 代码与三步推导（对称性折叠 / 超出量 / 内外合并），
右侧方块几何：外部点的 dx/dy 投影与欧氏距离、内部点的负距离。

--- narration ---
盒子 SDF 用了一个关键技巧：**对称性折叠**
先用 abs(p) 把问题折叠到第一象限
这样无论点在哪个方向，计算完全一样
然后 d = abs(p) - b 是各轴方向超出盒子的量
点在盒子**外部**：取到最近角点的欧氏距离
点在盒子**内部**：取到最近面的负距离
两部分相加，始终只有一项非零


>>> 圆环的 SDF：降维思路 #B07
@enter: fade-up
@exit: fade
@visual: image(./assets/B07.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B07.png 图片文件）
左侧 sdTorus 代码与三步降维推导，
右侧圆环正视截面图：y 轴、xz 平面、两个管道截面、主半径 R 与管道半径 r。

--- narration ---
圆环 SDF 用了一个巧妙的 **降维** 思路
圆环是绕 y 轴旋转一圈形成的
所以旋转方向上情况完全对称
先算到 y 轴的水平距离，减去主半径
这就把 3D 问题降成了一个 **1D 距离**
再配上 y 坐标，组成 **2D 截面坐标**
最后对这个截面做一个普通的圆 SDF
这种利用旋转对称性 **降维** 的思路
在很多复杂 SDF 中都会用到


>>> SDF 组合操作 #B08
@enter: fade-up
@exit: fade
@visual: image(./assets/B08.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B08.png 图片文件）
三个操作卡片：并集 / 差集 / 交集，各带集合示意图与代码，
底部为携带材质 ID 的增强版并集 opU。

--- narration ---
多个 SDF 可以用三种方式组合
**并集 Union**：min(d1, d2)，两个物体都存在
**差集 Subtraction**：max(d1, −d2)，从一个里挖掉另一个
**交集 Intersection**：max(d1, d2)，只保留重叠部分
shader 里用了增强版并集 opU
返回值是 vec2，x 存距离，y 存 **材质 ID**
合并时，哪个更近就取哪个，材质也跟着传递


>>> Sphere Tracing：步进求交算法 #B09
@enter: fade-up
@exit: fade
@visual: image(./assets/B09.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B09.png 图片文件）
上方为 Sphere Tracing 步进示意：相机、射线、逐步收缩的安全圆、命中点，
下方为步进循环代码。

--- narration ---
Sphere Tracing 是 Raymarching 的 **核心算法**
从相机出发，沿射线方向步进
每一步先查询当前位置的 SDF 值 d
d 就是 "在半径 d 内绝对安全" 的保证
所以直接跳过 d 的距离，再次查询
离表面越近，步长越小，自然收敛
当 SDF 小于阈值 ε，就找到了 **交点**
最多步进 70 次，大多数射线 20 步内收敛


>>> 场景构建与包围盒加速 #B10
@enter: fade-up
@exit: fade
@visual: image(./assets/B10.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B10.png 图片文件）
左侧 map() 树状结构（5 组物体、命中 / 跳过标记）与包围盒加速说明，
右侧 map() 函数代码。

--- narration ---
map() 是整个渲染器的 **场景描述函数**
它返回 vec2：x 是到最近表面的距离，y 是 **材质 ID**
场景里 25 个几何体按位置分成 5 组
每组外面套一个 **包围盒（AABB）** 测试
如果该点到包围盒的距离已经大于当前最近距离
整组直接跳过，一个 SDF 都不用算
一次 map() 调用最多只算少数几组
这让 70 次迭代的性能开销大幅降低


>>> 法线：从 SDF 提取表面朝向 #B11
@enter: fade-up
@exit: fade
@visual: image(./assets/B11.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B11.png 图片文件）
左侧四面体差分采样示意图（4 个方向 + 法线），
右侧 calcNormal 代码与两条注解（防内联 / 地板优化）。

--- narration ---
没有顶点数据，法线从哪来？
答案是从 SDF 的 **梯度方向** 中提取
SDF 增长最快的方向，就是法线方向
代码在表面点附近取 **四面体的 4 个方向**
各偏移 0.0005，查询 SDF 值，加权求和后归一化
数学上完全等价于计算梯度
用循环而不展开，是防止 map() 被 **内联 4 次**
map() 体积很大，内联会严重拖累性能


>>> 基础光照：漫反射与高光 #B12
@enter: fade-up
@exit: fade
@visual: image(./assets/B12.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B12.png 图片文件）
左侧光照几何图（法线 n、光方向 l、视线 v、半向量 h），
右侧三个公式块：Lambert 漫反射 / Blinn-Phong 高光 / Schlick Fresnel。

--- narration ---
光照从两个最基础的分量讲起
**漫反射 Lambert**：光照强度正比于法线与光方向的夹角余弦
表面越正对着光，值越大，越亮
**高光 Blinn-Phong**：用法线与 **半向量** h 的夹角来计算
h 是光方向和视线方向的角平分线
**Schlick Fresnel** 模拟掠射角时高光增强的效果
物体边缘斜着看时，高光会更强
这三个分量组合，是实时渲染的 **基础光照模型**


>>> 四光源系统 #B13
@enter: fade-up
@exit: fade
@visual: image(./assets/B13.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B13.png 图片文件）
四个光源卡片：太阳光 / 天空光 / 背光 / SSS，各带特性列表，
底部为四光源叠加的组合公式。

--- narration ---
shader 用四个光源模拟真实光照
**太阳光** 是主光，带软阴影和高光
**天空光** 是半球形环境光，模拟天空散射
受到 AO 遮蔽的区域，天空光也会减弱
**背光** 从反方向补亮，防止背面全黑
**SSS** 近似次表面散射，让边缘通透
四者叠加覆盖了自然光照的主要特征
是实时渲染里常见的 **多光源合成** 思路


>>> 软阴影：真实对比 #B14
@enter: fade
@exit: fade
@visual: video(./assets/softshadow.mp4)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/softshadow.mp4 视频文件）
左右分屏对比的真实渲染录屏：同一个 SDF 场景，相机环绕旋转。
画面左半部分关闭了阴影计算，右半部分开启软阴影。
中间有一条白色竖线分隔，可清晰看出软阴影对画面真实感的贡献。

--- narration ---
画面左边关掉了阴影，右边打开了软阴影
没有阴影时，物体像浮在空中
软阴影让物体真正"落"在地面上
实现的关键是沿光线方向做 **锥形步进**
记录每一步 SDF 值与距离的比值 **h/t**
这个比值近似了遮挡物的张角
取整条光线上的最小值，就是阴影浓度
系数越小，阴影边缘过渡越柔和


>>> 环境光遮蔽：真实对比 #B15
@enter: fade
@exit: fade
@visual: video(./assets/ao.mp4)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/ao.mp4 视频文件）
左右分屏对比的真实渲染录屏：同一个 SDF 场景，相机环绕旋转。
画面左半部分关闭了环境光遮蔽（AO），右半部分开启 AO。
中间白色竖线分隔，可看出物体缝隙、接触处与凹陷在开启 AO 后变暗。

--- narration ---
再看 AO，也就是环境光遮蔽
左边关掉 AO，右边打开
注意物体之间的缝隙和接触的地方
打开 AO 后，这些角落明显变暗了
算法是沿法线方向取几个采样点
比较期望距离和实际 SDF 值
差得越多，说明这个方向被挡得越厉害
这些细节让画面看起来更有体积感


>>> 相机系统：正交基与射线生成 #B16
@enter: fade-up
@exit: fade
@visual: image(./assets/B16.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B16.png 图片文件）
左侧相机正交基坐标系示意图（forward / right / up 三轴、屏幕平面、射线），
右侧 lookAt 相机构建代码。

--- narration ---
相机系统需要构建 **正交基坐标系**
先算出相机到目标的方向 ww（forward）
用世界 **up 向量** 和 ww 叉积，得到右方向 uu
再叉积一次，得到严格正交的上方向 vv
这三个向量组成相机的 **局部坐标系**
每个像素的射线 = 像素偏移 × uu/vv + ww
这是所有 **lookAt 相机** 的通用做法
代码里用 iTime 让相机绕场景做圆周运动


>>> C++ 宿主程序 #B17
@enter: fade-up
@exit: fade
@visual: image(./assets/B17.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B17.png 图片文件）
四个步骤卡片：初始化 GLFW/OpenGL、全屏三角形 trick、
每帧上传 Uniform、热重载 Shader，各带代码片段。

--- narration ---
C++ 宿主程序只做 4 件事
第一，初始化 **GLFW** 和 OpenGL 上下文
第二，用 **全屏三角形 trick**：完全不需要顶点缓冲
直接 glDrawArrays 3 个顶点
vertex shader 用 gl_VertexID 自动生成坐标
第三，每帧上传 **Uniform 变量** 给 shader
分辨率、时间、鼠标位置等实时数据
第四，监测 shader 文件变化，**热重载** 编译
改完 shader 立刻看到效果，开发体验很好


>>> 抗锯齿、雾效与 Gamma 校正 #B18
@enter: fade-up
@exit: fade
@visual: image(./assets/B18.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B18.png 图片文件）
三个后处理区块：超采样抗锯齿 / 大气透视雾效 / Gamma 校正，
各带说明文字与代码。

--- narration ---
最后三步后处理
**超采样抗锯齿**：每个像素在子像素位置采样 2×2 次
AA 宏控制质量，低端硬件可以关闭
**大气透视雾效**：用距离 t 的三次方做指数衰减
远处物体自然消隐，边缘不会有生硬的截断
**Gamma 校正**：光照计算在线性空间进行
最后要做 pow(x, 1/2.2) 转换到 **sRGB**
因为显示器假设输入是 gamma 2.2 编码
不做这步，画面会偏暗，颜色也不准确


>>> 总结 #B19
@enter: fade-up
@exit: fade
@visual: image(./assets/B19.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B19.png 图片文件）
两栏总结：核心技术（8 项）与工程实践（6 项），
底部为深入学习的参考资源链接。

--- narration ---
我们从头走完了一个完整的 SDF 渲染器
核心是 **SDF + Sphere Tracing** 的组合
没有三角形，纯数学求交
法线从梯度提取，阴影用锥形步进近似
四光源叠加模拟真实光照
如果想深入，推荐去 **IQ 的网站**
那里有每一种 SDF 的推导和可视化
把代码 clone 下来，自己加一个几何体试试
最好的学习方式，永远是 **动手改代码**
