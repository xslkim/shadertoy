>>> 开场：回到 Unity #B01
@enter: fade
@exit: fade
@visual: image(./assets/B01.png)

--- visual ---
一张扁平矢量插画。画面主体是一个游戏开发者站在 Unity 风格的场景里，
背景有一个正在运行的 3D 游戏画面（角色、关卡、加载进度条）。
开发者面前漂浮着两条发光的路径分叉：左边一条贴着老式齿轮和 "yield" 风格的循环箭头（代表协程），
右边一条是更现代、更顺滑的蓝色 #58a6ff 光带（代表 async/await）。
开发者正在权衡该走哪条路。深色科技背景 #0d1117，扁平现代矢量风格，蓝色辉光。

--- narration ---
上集我们讲透了 async/await 的本质，还横向看了各语言
这一集回到真实战场：**Unity**
游戏里到处是异步
加载资源、等动画、等几秒、等网络
Unity 老牌的做法是 **协程**
但越来越多项目转向 async/await
这一集就讲清楚：它们的关系、用法，和那些专属的坑


>>> Unity 的老办法：协程 #B02
@enter: fade-up
@exit: fade
@visual: image(./assets/B02.png)

--- visual ---
深色背景 #0d1117。顶部标题 "协程 Coroutine：Unity 的老朋友"，字号 54px，粗体 #e6edf3，距顶 60px。
中央代码窗口占画布 74% 宽，背景 #161b22，圆角 16px，字号 28px：
```
IEnumerator LoadLevel() {
    Show("加载中...");
    yield return new WaitForSeconds(2f);   // 等 2 秒
    var op = SceneManager.LoadSceneAsync("Game");
    yield return op;                       // 等加载完
    Show("开始！");
}

StartCoroutine(LoadLevel());               // 启动
```
关键字 IEnumerator/yield/return/new/var 用 #ff7b72，类型/方法 #58a6ff，字符串 #a5d6ff，注释 #8b949e。

--- narration ---
先看协程的样子
方法返回 **IEnumerator**，靠 **yield return** 来"等"
yield return WaitForSeconds，就是等两秒
yield return 一个异步操作，就是等它完成
关键点：协程 **不阻塞** 主线程
每次 yield，控制权就交还给 Unity
下一帧再从 yield 的地方继续往下跑
是不是有点眼熟？这套"暂停再恢复"的味道


>>> 协程其实也是状态机 #B03
@enter: fade-up
@exit: fade
@visual: image(./assets/B03.png)

--- visual ---
一张扁平矢量概念插画。中央并排画两台外观相似的"齿轮状态机"装置，
左边贴标签风格暗示 "Coroutine / IEnumerator"，右边暗示 "async / await"。
两台机器内部结构几乎一样：都有几个发光的存档点节点和"暂停—恢复"的循环箭头，
中间用一个大大的约等号 "≈"（蓝色 #58a6ff）连接，传达"骨子里是同一个思路"。
但左边机器旁边画着一个小小的 "每帧驱动" 的 Unity 引擎齿轮在推动它。
深色科技背景 #0d1117，扁平现代矢量风格，蓝色辉光。

--- narration ---
其实，协程和 async/await **骨子里是一回事**
yield return 和 await 一样
都是把方法切成片段、可暂停可恢复
IEnumerator 也是编译器生成的一台状态机
区别在于 **谁来驱动它恢复**
协程是 Unity 引擎在 **每一帧** 主动来推它一下
而 async/await 是任务完成时回调来推它
理解了第一集，协程对你就不再神秘


>>> 协程的局限 #B04
@enter: fade-up
@exit: fade
@visual: image(./assets/B04.png)

--- visual ---
深色背景 #0d1117。顶部标题 "协程能做，也有它做不到的"，字号 52px，粗体 #e6edf3，距顶 60px。
中央并排两列卡片，各占画布约 42% 宽，间距 48px，高度约 360px，圆角 16px，内边距 32px。
左卡背景 #161b22，顶部标签 "✓ 擅长" 绿色，字号 32px，下方三行要点 30px #e6edf3：
• 按帧推进的时序逻辑
• 简单的等待与序列
• 和 Unity 生命周期天然贴合
右卡背景 #161b22，顶部标签 "✗ 短板" 红色 #ff7b72，字号 32px，下方三行要点 30px #e6edf3：
• 不能 return 返回值
• 不能用 try-catch 包住 yield
• 嵌套组合、取消都很别扭

--- narration ---
协程很好用，但有几条硬伤
第一，它 **不能返回值**
想拿协程算出的结果，得自己用回调或字段绕
第二，它 **不能用 try-catch** 把 yield 包起来
异常处理很笨拙
第三，多个协程嵌套、组合、取消，写起来都很别扭
这些，恰恰是 async/await 的强项


>>> Unity 是单线程的 #B05
@enter: fade-up
@exit: fade
@visual: image(./assets/B05.png)

--- visual ---
一张扁平矢量概念插画。画面中央是一条环形的传送带流水线，标注感暗示它叫 "PlayerLoop"。
传送带上依次排着循环节点：输入 → 物理 → 脚本 Update → 渲染，循环往复，
每个节点都由 **同一个** 高亮的蓝色 #58a6ff 工人（代表"主线程"）独自处理。
画面一角有几个后台齿轮工人（线程池），但他们和传送带之间隔着一道写着
"只有主线程能碰 Unity API" 的发光栅栏。深色科技背景 #0d1117，扁平现代矢量风格。

--- narration ---
要用好 async，必须先记住 Unity 的一条铁律
几乎所有 Unity API **只能在主线程调用**
碰 Transform、GameObject、UI，都必须在主线程
Unity 的整个游戏循环叫 **PlayerLoop**
输入、物理、脚本、渲染，每帧由主线程顺序跑一遍
后台线程可以做计算，但 **不能碰 Unity 对象**
这条铁律，是后面所有坑的根源


>>> 在 Unity 里直接写 async #B06
@enter: fade-up
@exit: fade
@visual: image(./assets/B06.png)

--- visual ---
深色背景 #0d1117。顶部标题 "好消息：async 直接能用"，字号 54px，粗体 #e6edf3，距顶 60px。
中央代码窗口占画布 74% 宽，背景 #161b22，圆角 16px，字号 28px：
```
async void Start() {           // 事件式入口，可用 async void
    Show("加载中...");
    await Task.Delay(2000);    // 等 2 秒，不卡主线程
    transform.position = spawn; // 仍在主线程？关键问题
    Show("开始！");
}
```
关键字 async/void/await 用 #ff7b72，类型/方法 #58a6ff，字符串 #a5d6ff，注释 #8b949e。
"仍在主线程？关键问题" 这行注释用红色 #ff7b72 高亮。

--- narration ---
好消息是，C# 的 async/await 在 Unity 里 **直接能写**
Start 里加 async，await 一个 Task.Delay
界面不会卡，逻辑也很顺
但这里有个要命的问题
await 之后的这行，去改了 transform
它 **还在主线程上吗**
如果不在，这行就会直接报错
答案，藏在一个叫同步上下文的东西里


>>> UnitySynchronizationContext #B07
@enter: fade-up
@exit: fade
@visual: image(./assets/B07.png)

--- visual ---
一张扁平矢量概念插画。画面中心是一个发光的蓝色 #58a6ff 传送门装置，
标注感暗示它叫 "UnitySynchronizationContext"。一条 await 任务光带从右侧后台线程池出发，
穿过传送门后，被精准送回左侧那条 "PlayerLoop 主线程传送带" 上继续运行，
主线程工人接住它继续处理。传送门上有一个小小的 Unity 立方体 logo 暗示这是 Unity 装好的。
深色科技背景 #0d1117，扁平现代矢量风格，强对比，蓝色辉光。

--- narration ---
答案是：默认情况下，**还在主线程**，可以放心
因为 Unity 在启动时，装了一个专属的同步上下文
叫 **UnitySynchronizationContext**
还记得第一集吗，await 默认会捕获当前上下文
所以 await 之后的后半段
会被这个上下文 **送回主线程** 执行
这就是为什么你能在 await 之后安全地碰 Unity 对象
这是 Unity 用 async 最重要的一条保障


>>> 跨线程的坑：Task.Run #B08
@enter: fade-up
@exit: fade
@visual: image(./assets/B08.png)

--- visual ---
深色背景 #0d1117。顶部标题 "坑：在后台线程碰 Unity API", 字号 50px，粗体，红色 #ff7b72，距顶 60px。
中央代码窗口占画布 76% 宽，背景 #161b22，圆角 16px，字号 27px：
```
await Task.Run(() => {
    var result = HeavyCompute();   // ✓ 后台算，没问题
    transform.position = result;   // ✗ 崩！这里是线程池线程
});

// 正确：算在后台，改在 await 之后（已回主线程）
var result = await Task.Run(() => HeavyCompute());
transform.position = result;       // ✓ 安全
```
✗ 行红色 #ff7b72 高亮，✓ 行绿色标记。关键字 await/var 用 #ff7b72，方法 #58a6ff，注释 #8b949e。

--- narration ---
但只要你主动跳到后台线程，铁律就回来了
用 **Task.Run** 把重计算丢到线程池，很好
可如果在那个 lambda 里面去碰 transform
就是在 **后台线程** 碰 Unity API，直接崩
正确姿势是：让后台 **只做纯计算**，返回结果
计算完，await 帮你 **回到主线程**
再在主线程上把结果赋给 transform
一句话：**算在后台，改在主线程**


>>> 协程 vs async 对比 #B09
@enter: fade-up
@exit: fade
@visual: image(./assets/B09.png)

--- visual ---
深色背景 #0d1117。顶部标题 "协程 vs async/await", 字号 56px，粗体 #e6edf3，距顶 50px。
中央一张三列对比表，占画布 88% 宽，行高约 56px，字号 28px。
表头三列："维度" / "协程 Coroutine" / "async/await"，表头背景 #1f6feb 风格条，白字。
行内容（左维度 #8b949e，中右两列 #e6edf3，async 列优势项用 accent 色 #58a6ff）：
返回值        | 不支持        | 支持 Task<T>
异常处理      | 不能 try-catch | 正常 try-catch
取消          | 手动停        | CancellationToken
跨线程计算    | 不行          | Task.Run + 回主线程
驱动者        | 引擎每帧推    | 任务完成回调
依附对象      | 需 MonoBehaviour | 不需要
表格用细分隔线 #30363d。

--- narration ---
把两者摆一起对比，差别就很清楚了
协程不能返回值、不能 try-catch、取消要手动
而 async 这些全都自然支持
协程必须依附在一个 **MonoBehaviour** 上才能启动
async 方法则不受这个限制
协程的长处是和帧循环贴得紧
但论表达力和组合能力，async 全面胜出
那是不是直接全用 C# 原生 async 就行？还不够


>>> 为什么需要 UniTask #B10
@enter: fade-up
@exit: fade
@visual: image(./assets/B10.png)

--- visual ---
一张扁平矢量概念插画。画面左边是 C# 原生 Task，被画成一个略显笨重、
不断掉落小垃圾（代表 GC 内存垃圾）的箱子，旁边漂着几片 "GC" 碎屑，气氛略沉重。
画面右边是一个轻盈、发光的蓝色 #58a6ff 纸飞机，机身写着风格化的 "UniTask"，
零碎屑、干净利落，正贴着 Unity 的 PlayerLoop 传送带高效飞行。
中间一个箭头从笨重箱子指向轻盈飞机，暗示"为 Unity 量身优化"。
深色科技背景 #0d1117，扁平现代矢量风格，蓝色辉光。

--- narration ---
C# 原生的 Task 是为服务器、为多线程设计的
搬到游戏里有两个水土不服
第一，每个 Task 都是一个 **堆对象**
高频 await 会制造大量 **GC 垃圾**，游戏最怕卡顿
第二，它对 Unity 的帧时机、生命周期一无所知
于是社区做了一个专门方案：**UniTask**
它几乎零内存分配，还和 Unity 深度集成
现在已经是 Unity 异步的事实标准


>>> UniTask 的核心优势 #B11
@enter: fade-up
@exit: fade
@visual: image(./assets/B11.png)

--- visual ---
一张扁平矢量概念插画。画面分三个发光的图标卡片横向排列（不含大段文字，靠图形表意）：
① 一个干净的回收符号 + 数字 "0" 的辉光，暗示"零 GC 分配"；
② 一个齿轮咬合进 Unity 的 PlayerLoop 环形传送带，暗示"原生集成帧循环"；
③ 一个发光的 await 符号融合进 Unity 的各种操作图标（加载条、计时器、按钮），暗示"什么都能 await"。
三个图标用蓝色 #58a6ff 辉光统一，深色科技背景 #0d1117，扁平现代矢量风格。

--- narration ---
UniTask 凭什么成为标准，主要三点
第一，**零 GC 分配**
它用结构体而不是堆对象，避免制造垃圾
第二，它把自己 **挂进了 PlayerLoop**
能精确地在某个帧时机恢复，不靠线程池
第三，它让几乎所有 Unity 操作都能被 await
等加载、等动画、等几帧、等按钮点击，全都统一成 await


>>> UniTask 代码示例 #B12
@enter: fade-up
@exit: fade
@visual: image(./assets/B12.png)

--- visual ---
深色背景 #0d1117。顶部标题 "UniTask：一切皆可 await", 字号 52px，粗体 #e6edf3，距顶 50px。
中央代码窗口占画布 80% 宽、可用高度 70%，背景 #161b22，圆角 16px，字号 26px：
```
async UniTask LoadLevelAsync() {
    await UniTask.Delay(2000);                 // 等 2 秒
    await SceneManager.LoadSceneAsync("Game"); // 直接 await 加载
    await UniTask.NextFrame();                 // 等下一帧
    await UniTask.WaitUntil(() => isReady);    // 等条件成立

    // 并发：一起加载，等全部完成
    await UniTask.WhenAll(LoadA(), LoadB(), LoadC());
}
```
关键字 async/await 用 #ff7b72，类型 UniTask/方法 #58a6ff，字符串 #a5d6ff，注释 #8b949e。

--- narration ---
来看实际写法，注意返回类型是 **UniTask**
await UniTask.Delay，等两秒，零分配
场景加载操作可以 **直接 await**，不用 yield
还能 await 下一帧，await 直到某个条件成立
这些都是协程时代要绕一大圈才能做到的
并发也很自然，**WhenAll** 让多个加载同时进行
代码读起来就像同步逻辑，但全程不卡主线程


>>> 生命周期与取消 #B13
@enter: fade-up
@exit: fade
@visual: image(./assets/B13.png)

--- visual ---
深色背景 #0d1117。顶部标题 "对象销毁了，任务要自动停", 字号 50px，粗体 #e6edf3，距顶 50px。
中央代码窗口占画布 78% 宽，背景 #161b22，圆角 16px，字号 27px：
```
async UniTaskVoid Start() {
    var token = this.GetCancellationTokenOnDestroy();
    // 对象被 Destroy 时，这个 token 自动取消
    await UniTask.Delay(5000, cancellationToken: token);
    transform.position = spawn; // 安全：对象没了就不会执行到
}
```
关键字 async/var/await 用 #ff7b72，类型/方法 #58a6ff，注释 #8b949e。
"对象被 Destroy 时，这个 token 自动取消" 注释用 accent 色 #58a6ff 高亮。

--- narration ---
游戏里最容易出事的，是 **对象生命周期**
一个异步任务跑到一半，物体被销毁了怎么办
UniTask 给了一个利器
**GetCancellationTokenOnDestroy**
它返回一个会在对象销毁时 **自动取消** 的 token
把它传给每个 await
对象一旦没了，整条异步链就自动停下
你再也不会在已销毁对象上误操作


>>> 经典坑：销毁后继续执行 #B14
@enter: fade-up
@exit: fade
@visual: image(./assets/B14.png)

--- visual ---
深色背景 #0d1117。顶部标题 "没传 token 的下场", 字号 52px，粗体，红色 #ff7b72，距顶 60px。
中央代码窗口占画布 74% 宽，背景 #161b22，圆角 16px，字号 27px：
```
async void Start() {
    await Task.Delay(5000);          // 5 秒里对象可能已被销毁
    gameObject.SetActive(false);     // ✗ MissingReferenceException
}
```
✗ 行红色 #ff7b72 高亮。下方一行说明 30px #8b949e：
"对象已 Destroy，但任务没人取消 → 恢复时访问空对象 → 抛异常"。

--- narration ---
反过来，如果你 **没做** 取消，就会踩这个经典坑
await 等了五秒，这五秒里对象被销毁了
五秒后任务恢复，去访问 gameObject
但它已经不存在了
于是抛出 **MissingReferenceException**
原生 Task 不知道 Unity 的生命周期，不会自动停
所以在 Unity 里，**取消 token 不是可选项，是必需品**


>>> 该用协程还是 async #B15
@enter: fade-up
@exit: fade
@visual: image(./assets/B15.png)

--- visual ---
深色背景 #0d1117。顶部标题 "怎么选？一张决策图", 字号 54px，粗体 #e6edf3，距顶 50px。
中央一个简洁决策流程图，占画布 85% 宽，节点圆角矩形，连线 accent 色 #58a6ff，字号 28px：
顶部问题框 "需要返回值 / 异常处理 / 取消 / 跨线程计算？"。
→ "是" 分支指向绿色框 "用 async + UniTask"。
→ "否，只是简单按帧的时序" 分支指向蓝色框 "协程也够用"。
底部一行小结 32px #e6edf3："新项目优先 async + UniTask，老项目协程可共存"。

--- narration ---
那到底怎么选
如果你需要返回值、异常处理、取消，或跨线程计算
毫不犹豫，**async 加 UniTask**
如果只是很简单的、按帧推进的小时序
老协程也完全够用，没必要重写
现实中两者常常 **共存**
但对于新代码，业界的共识是优先 async 加 UniTask


>>> 全系列总结 #B16
@enter: fade-up
@exit: fade
@visual: image(./assets/B16.png)

--- visual ---
深色背景 #0d1117。顶部居中标题 "两集回顾 · 你的异步心智模型", 字号 54px，粗体 #e6edf3，距顶 50px。
下方两张横向卡片，各占画布约 42% 宽，间距 48px，高约 360px，圆角 16px，背景 #161b22，内边距 32px。
每卡顶部集数标签 accent 色 #58a6ff 30px + 标题 36px + 三行要点 28px #8b949e：
卡①「上集 · 本质与全景」：async≠多线程，是状态机 / 同步上下文，别用 .Result / 各语言本质都是续体
卡②「下集 · Unity 实战」：主线程铁律是一切坑的根源 / UniTask 零 GC、集成 PlayerLoop / 永远传取消 token
底部一行 30px #e6edf3："会用，更要懂它为什么这么设计"。

--- narration ---
两集到这里就讲完了，我们回顾一下
上集，**async 不是多线程**，是编译器生成的状态机
各语言语法统一、底层各异，共同本质是 **续体**
下集，在 Unity 里守住 **主线程铁律**
高频异步用 UniTask，永远传取消 token
异步编程不难
难的是从"会用"到真正 **懂它为什么这么设计**
希望这两集，帮你跨过了这道坎
我们下个系列再见
