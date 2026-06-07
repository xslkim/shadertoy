>>> 开场：卡住的程序 #B01
@enter: fade
@exit: fade
@visual: image(./assets/B01.png)

--- visual ---
一张扁平矢量插画。画面左右分屏对比。
左半边（冷色、灰暗）：一个程序员坐在电脑前，屏幕上是一个巨大的旋转加载圈，
程序员僵住不动，身后排着一长队半透明、被冻结的任务卡片，整体压抑、停滞。
右半边（明亮、蓝色 #58a6ff 辉光）：同一个程序员表情轻松，
正同时抛接好几张发光的任务卡片，行云流水，背景有流动的光线。
深色科技背景 #0d1117，扁平现代矢量风格，强对比，画面干净，几乎无文字。

--- narration ---
你的程序又卡住了
界面冻结，转着圈，点什么都没反应
其实它没崩溃
它只是在 **等** 一件事做完
等网络回包，等磁盘读完，等数据库查完
这一集，我们从根上把这件事讲透


>>> 标题卡 #B02
@enter: fade-up
@exit: fade
@visual: image(./assets/B02.png)

--- visual ---
全屏深色背景 #0d1117，垂直居中布局，内容占画布约 80% 宽度。
[0s] 顶部小标签 "C# 异步编程 · 上集"，字号 26px，颜色 #58a6ff，字母间距加宽，淡入。
[0.4s] 主标题 "async / await 的本质与全景"，字号 100px，粗体，白色 #e6edf3，居中，伴随 32px 上移淡入。
[1.1s] 主标题下方 36px 处副标题 "从原理到跨语言，建立完整心智模型"，字号 40px，颜色 #8b949e。
[1.6s] 主标题正下方 16px 处出现 4px 粗、accent 色 #58a6ff 横线，宽度等于主标题宽度，从左向右扫入。

--- narration ---
这是异步编程系列的上集
我们先把最核心的两个关键字讲透
**async 和 await** 到底做了什么
讲完你会发现，它和你以为的完全不一样
然后跳出 C#，横向看看整个世界


>>> 同步阻塞的代价 #B03
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部居中标题 "同步：一行卡住，全线等待"，字号 56px，粗体 #e6edf3，距顶 70px。
中央偏左是一个代码窗口，宽度占画布 60%，圆角 16px，背景 #161b22，等宽字体，字号 30px：
```
string DownloadData() {
    var data = client.Download(url); // 阻塞 3 秒
    return Parse(data);
}
```
关键字（string/return）用 #ff7b72，字符串/url 用 #a5d6ff，注释用 #8b949e。
代码窗口右侧是一条竖直的 "线程时间轴"，宽度占画布 25%：
[0s] 标注 "调用线程"，下方一根竖向进度条开始往下走。
[1.5s] 进度条走到 client.Download 这一行时变红并停住，旁边出现 "❄ 冻结 3 秒" 标签，字号 30px，红色。
[4s] 进度条恢复蓝色继续往下走，标签变成 "线程白白等了 3 秒"。

--- narration ---
先看最朴素的同步写法
这个函数要下载数据再解析
问题出在中间这一行
**client.Download** 要花三秒
在这三秒里，调用它的线程什么也做不了
它被 **死死地占住**，只能干等
如果这是 UI 线程，界面就直接冻住了


>>> 多线程不是答案 #B04
@enter: fade-up
@exit: fade
@visual: image(./assets/B04.png)

--- visual ---
一张扁平矢量概念插画。画面中央是一座工厂车间。
做法一（左侧，标注感的红色调）：为每个任务都雇一个工人，
十几个工人各自坐在沉重的大办公桌前，大部分却在打瞌睡、无所事事，
桌子上贴着 "1MB 栈" 的便签，整体显得臃肿、昂贵、浪费。
做法二（右侧，蓝色 #58a6ff 高效调）：只有一两个工人，
却在多张发光的任务桌之间灵活穿梭、同时推进很多任务，轻盈高效。
深色科技背景 #0d1117，扁平现代矢量风格，强对比。

--- narration ---
你可能会说，那开个线程不就行了
等的活丢给别的线程去等
但线程很贵
每个线程要一兆左右的栈内存
创建、切换、调度都有开销
开几百个线程，机器就被拖垮了
而且大多数等待，线程只是在 **空等**
我们要的不是更多线程，是别让线程空等


>>> 核心观点：async 不等于多线程 #B05
@enter: zoom-in
@exit: fade
@visual: image(./assets/B05.png)

--- visual ---
全屏深色背景 #0d1117，画面垂直居中，内容占画布约 85% 宽度。
[0s] 中央一行大字 "async ≠ 多线程"，字号 96px，粗体，"≠" 用红色 #ff7b72，其余白色，整体淡入并轻微放大。
[1.2s] 下方 48px 处出现一行 "await 不会开新线程，它只是 —— 暂停并交还控制权"，字号 40px，颜色 #8b949e，"暂停并交还控制权" 用 accent 色 #58a6ff 高亮。
[2.5s] 再下方 40px 出现一行小字 "线程在等待期间可以去干别的事"，字号 30px，颜色 #8b949e。

--- narration ---
记住这句话，它是整集的地基
**async 不等于多线程**
await 不会帮你开新线程
它做的事只有一个
在需要等待的地方 **暂停** 当前方法
然后把线程 **交还** 出去
让这根线程在等待期间去干别的活


>>> Task：一张取餐小票 #B06
@enter: fade-up
@exit: fade
@visual: image(./assets/B06.png)

--- visual ---
深色背景 #0d1117。顶部标题 "Task：一张取餐小票"，字号 56px，粗体 #e6edf3，距顶 70px。
左侧代码窗口宽度占画布 55%，背景 #161b22，圆角 16px，字号 30px：
```
async Task<string> DownloadAsync() {
    var data = await client.DownloadAsync(url);
    return Parse(data);
}
```
关键字 async/await/return 用 #ff7b72，类型 Task/string 用 #58a6ff，字符串用 #a5d6ff。
右侧是一张拟物化 "取餐小票" 图标（占画布 30%），票面上画一个沙漏图标 + "结果稍后送达"，
小票从代码的 Task<string> 处用一条 accent 色虚线连出来。

--- narration ---
异步方法不直接返回结果
它返回一个 **Task**
你可以把 Task 想成一张取餐小票
方法立刻把小票给你，让你先去忙别的
等后厨做好了，结果会填进这张小票
**Task of string** 就是"未来会有一个字符串"
而 await，就是凭这张小票去取餐


>>> await：切成两半的状态机 #B07
@enter: fade-up
@exit: fade
@visual: image(./assets/B07.png)

--- visual ---
一张扁平矢量概念插画。主体是一卷电影胶片或一条带有多个存档点的游戏关卡轨道，
轨道上有几个清晰的发光 "存档点 / checkpoint" 节点，用蓝色 #58a6ff 标记。
一个小机器人角色站在某个存档点上，旁边有一个发光的状态指示牌显示着箭头循环，
暗示"可以暂停、保存进度、之后从同一点恢复"。整体传达"可暂停可恢复的进度机"的概念。
深色科技背景 #0d1117，扁平现代矢量风格，蓝色辉光点缀。

--- narration ---
await 真正神奇的地方在这里
它把一个方法从中间 **切成两半**
await 之前的代码，正常同步执行
执行到 await，如果结果还没好
方法就在这里 **暂停**，并且 return 出去
注意，是 return，不是阻塞，线程被交还
那它怎么记住停在哪、变量又存在哪
答案是：**编译器** 把它改写成一台状态机
每个 await 就是一个 **存档点**
暂停时存档，恢复时读档，从同一点继续


>>> 状态机长什么样 #B08
@enter: fade-up
@exit: fade
@visual: image(./assets/B08.png)

--- visual ---
深色背景 #0d1117。顶部标题 "你写的几行，被改写成这样"，字号 52px，粗体 #e6edf3，距顶 60px。
中央一个宽代码窗口，占画布 80% 宽、可用高度 70%，背景 #161b22，圆角 16px，字号 26px（简化伪代码）：
```
class StateMachine {
    int state = 0;            // 当前停在哪个存档点
    string data;              // 被保存的局部变量

    void MoveNext() {
        if (state == 0) {
            awaiter = client.DownloadAsync(url).GetAwaiter();
            state = 1;
            awaiter.OnCompleted(MoveNext); // 结果好了再回来
            return;                        // ← 暂停，线程交还
        }
        // state == 1：恢复，读取结果
        data = awaiter.GetResult();
        result = Parse(data);
    }
}
```
关键字 class/int/string/void/if/return 用 #ff7b72，方法名 #58a6ff，注释 #8b949e。
注释 "← 暂停，线程交还" 用 accent 色高亮强调。

--- narration ---
这就是编译器生成的状态机，简化后大概长这样
**state** 字段记着当前停在哪个存档点
局部变量 data 被提升成字段保存起来
第一次进来，发起下载，把状态设成 1
然后注册一个回调：结果好了就再调一次 MoveNext
接着直接 return，线程就被交还了
等结果到了，MoveNext 被再次调用
这次走 state 等于 1 的分支，读出结果，继续往下
async/await 的全部魔法，就是这台状态机


>>> await 之后，回到哪个线程 #B09
@enter: fade-up
@exit: fade
@visual: image(./assets/B09.png)

--- visual ---
一张扁平矢量概念插画。画面中心是一个发光的蓝色 #58a6ff "调度员 / 传送门" 装置，
标注感地暗示它叫 "SynchronizationContext"。一条任务光带从右侧的"后台线程池"区域
（画着几个齿轮工人）出发，经过这个传送门，被精准送回左侧高亮的 "UI 主线程" 讲台上，
讲台上有一个负责画界面的角色在等待。传送门的作用是"把后半段送回原来的线程"。
深色科技背景 #0d1117，扁平现代矢量风格，强对比，蓝色辉光。

--- narration ---
这里有个关键细节，很多人栽过跟头
方法的后半段，到底在 **哪个线程** 上恢复
默认情况下，await 会捕获当前的 **同步上下文**
在 UI 程序里，这个上下文代表 UI 线程
所以后半段会被 **送回 UI 线程** 执行
这很贴心，因为你恢复后往往要更新界面
但在某些场景，它也会带来性能甚至死锁问题


>>> ConfigureAwait(false) #B10
@enter: fade-up
@exit: fade
@visual: image(./assets/B10.png)

--- visual ---
深色背景 #0d1117。顶部标题 "ConfigureAwait(false)：别回去了", 字号 52px，粗体 #e6edf3，距顶 70px。
左右两个代码窗口并排，各占画布约 42% 宽，背景 #161b22，圆角 16px，字号 28px，间距 48px。
左窗口顶部小标签 "库代码 / 不碰 UI" #58a6ff：
```
var data = await client
    .DownloadAsync(url)
    .ConfigureAwait(false);
// 后半段留在线程池，更快
```
右窗口顶部小标签 "UI 代码 / 要更新界面" #8b949e：
```
var data = await client
    .DownloadAsync(url);
label.Text = data; // 需要回 UI 线程
```
关键字 var/await 用 #ff7b72，方法名 #58a6ff，注释 #8b949e。

--- narration ---
如果后半段根本不碰界面，比如在库里
那"送回 UI 线程"就是多余的开销
这时加上 **ConfigureAwait(false)**
告诉它：别捕获上下文，就地在线程池恢复
更快，也能避开后面要讲的死锁
但如果后半段要更新界面，就 **不能** 加
经验法则：库代码默认加，应用 UI 代码不加


>>> 两个必知细节：async void 与异常 #B11
@enter: fade-up
@exit: fade
@visual: image(./assets/B11.png)

--- visual ---
深色背景 #0d1117。顶部标题 "两个必知细节"，字号 54px，粗体 #e6edf3，距顶 60px。
中央上下两个代码窗口，各占画布 72% 宽，背景 #161b22，圆角 16px，字号 27px，间距 32px。
上窗口顶部小标签 "返回类型" #ff7b72：
```
async void DoWork() {        // ✗ 没人能 await，异常掀翻进程
    await Task.Delay(1000);
}
async Task DoWorkOk() {      // ✓ 几乎总是用 Task
    await Task.Delay(1000);
}
```
下窗口顶部小标签 "异常处理" #58a6ff：
```
try {
    var data = await DownloadAsync();
}
catch (HttpRequestException e) {
    Log(e); // 异常存进 Task，await 时原样重抛
}
```
✗ 行红色 #ff7b72 高亮，✓ 行绿色标记。关键字 async/await/try/catch/var 用 #ff7b72，类型 #58a6ff，注释 #8b949e。

--- narration ---
顺手记住两个实用细节
第一，返回类型几乎永远该用 **Task**
唯一例外 async void 是个陷阱
它没法被 await，里面的异常没人接得住，会直接掀翻进程
所以 **只有事件处理器** 才用 async void
第二，异步里的异常，照常用 **try-catch** 就行
异常会先存进 Task，等你 await 时在那一行原样重抛
所以它能精准落进你的 catch，前提是你真的去 await 它


>>> 并发：WhenAll 与 WhenAny #B12
@enter: fade-up
@exit: fade
@visual: image(./assets/B12.png)

--- visual ---
深色背景 #0d1117。顶部标题 "让多件事同时等：WhenAll", 字号 54px，粗体 #e6edf3，距顶 60px。
中央代码窗口占画布 72% 宽，背景 #161b22，圆角 16px，字号 28px：
```
// ✗ 串行：一个等完再等下一个，共 3 秒
var a = await GetAsync(1);
var b = await GetAsync(2);
var c = await GetAsync(3);

// ✓ 并发：三个一起飞，只等最慢的，约 1 秒
var all = await Task.WhenAll(
    GetAsync(1), GetAsync(2), GetAsync(3));
```
错误段标 ✗ 红色，正确段标 ✓ 绿色。关键字用 #ff7b72，方法名 #58a6ff，注释 #8b949e。

--- narration ---
注意一个常见的浪费
连续 await 三个任务，是 **串行** 的
第一个等完，才发起第二个，时间累加
如果它们彼此独立，应该让它们 **同时** 跑
先把任务都启动，拿到三个 Task
再用 **Task.WhenAll** 一次性等它们全部完成
这样总耗时只取决于最慢的那个
还有 **WhenAny**，谁先完成就先处理谁


>>> 死锁：别用 .Result 和 .Wait() #B13
@enter: fade-up
@exit: fade
@visual: image(./assets/B13.png)

--- visual ---
深色背景 #0d1117。顶部标题 "经典死锁：.Result 同步等异步"，字号 50px，粗体，红色 #ff7b72，距顶 60px。
左侧代码窗口占画布 50% 宽，背景 #161b22，圆角 16px，字号 28px：
```
// UI 线程上
var data = DownloadAsync().Result; // ✗ 死锁
```
右侧是一张简洁的循环等待示意（占画布 38%）：
两个节点 "UI 线程" 与 "await 后半段" 用两条红色箭头首尾相接成一个环，
中间一个红色锁图标，标 "互相等待，永久卡死"，字号 30px。

--- narration ---
有个坑，也是面试常考
在 UI 线程上用 **.Result** 或 **.Wait()** 去同步等一个异步任务
你会得到一个 **死锁**
为什么
.Result 把 UI 线程 **阻塞** 在这里
而异步任务的后半段，默认要 **送回 UI 线程** 才能恢复
可 UI 线程正被你卡着，永远腾不出来
两边互相等，谁也动不了
解法：要么一路 await 到底，要么加 ConfigureAwait(false)


>>> 取消：CancellationToken #B14
@enter: fade-up
@exit: fade
@visual: image(./assets/B14.png)

--- visual ---
深色背景 #0d1117。顶部标题 "随时喊停：CancellationToken", 字号 52px，粗体 #e6edf3，距顶 70px。
中央代码窗口占画布 72% 宽，背景 #161b22，圆角 16px，字号 28px：
```
async Task RunAsync(CancellationToken token) {
    var data = await DownloadAsync(token);
    token.ThrowIfCancellationRequested();
    Process(data);
}

// 调用方
var cts = new CancellationTokenSource();
cts.CancelAfter(5000);          // 5 秒后自动取消
await RunAsync(cts.Token);
```
关键字 async/await/var/new 用 #ff7b72，类型 #58a6ff，注释 #8b949e。

--- narration ---
异步操作常常需要能 **中途取消**
比如用户点了取消，或者超时了
C# 的标准做法是传一个 **CancellationToken**
把它一路往下传给每个异步调用
在合适的地方检查它，被取消就抛出取消异常
调用方用 **CancellationTokenSource** 来发号施令
甚至能设定几秒后自动取消
这套模式贯穿整个 .NET 异步生态，务必习惯它


>>> 放眼世界：三种并发模型 #B15
@enter: fade-up
@exit: fade
@visual: image(./assets/B15.png)

--- visual ---
深色背景 #0d1117。顶部标题 "并发，其实只有几种底层模型", 字号 52px，粗体 #e6edf3，距顶 50px。
中央三张卡片横向排列，各占画布约 28% 宽，间距 40px，高约 380px，圆角 16px，背景 #161b22，内边距 28px。
每卡顶部一个大图标 + 标题 36px，下方两行说明 27px #8b949e：
卡①「多线程」🧵：抢占式，OS 调度，代表 C# Task 线程池
卡②「事件循环」🔁：单线程，任务排队，代表 JS / Python asyncio
卡③「协程 / 绿色线程」🟢：用户态调度，代表 Go goroutine
标题用 accent 色 #58a6ff，图标用辉光。

--- narration ---
C# 的原理我们讲透了，现在跳出 C#，横向看世界
你会发现一件有意思的事
JS、Python、Rust 的 async/await 语法几乎一样，底层却差别巨大
先建立一个框架
表面五花八门，底层并发其实就几种模型
第一种 **多线程**：靠操作系统抢占式调度，C# 的 Task 池就是
第二种 **事件循环**：单线程，任务排队轮流跑，JS 和 Python 走这条
第三种 **协程 / 绿色线程**：在用户态自己调度，Go 是代表
async/await 这套语法，主要服务前两种


>>> JS 单线程事件循环 #B16
@enter: fade-up
@exit: fade
@visual: image(./assets/B16.png)

--- visual ---
一张扁平矢量概念插画。画面中央是一个旋转木马 / 环形传送带，
只有 **一个** 高亮的蓝色 #58a6ff 工人（代表 JS 单线程）站在中心，
传送带上的任务卡片排着队，工人一次只拿一张处理完再拿下一张。
旁边有一个 "任务队列" 的等待区，新任务（定时器、网络回包）从外部不断加入队列尾部排队。
整体传达"单线程、靠队列轮转、永不并行"。深色科技背景 #0d1117，扁平现代矢量风格。

--- narration ---
先看 JavaScript，它和 C# 最大的不同在这
JS 是 **单线程** 的
它只有一个工人，没有线程池
那它怎么"同时"做很多事
靠的是 **事件循环**
异步操作完成后，回调被丢进一个 **任务队列** 排队
主线程处理完手头的，再从队列里取下一个
所以 JS 的异步，**从来不是真并行**，只是快速轮转


>>> JS：看，和 C# 几乎一样 #B17
@enter: fade-up
@exit: fade
@visual: image(./assets/B17.png)

--- visual ---
深色背景 #0d1117。顶部标题 "看，和 C# 几乎一样", 字号 54px，粗体 #e6edf3，距顶 50px。
左右两个代码窗口并排，各占画布约 44% 宽，间距 40px，背景 #161b22，圆角 16px，字号 27px。
左窗口顶标签 "JavaScript" #f1e05a：
```
async function load() {
  try {
    const data = await fetch(url);
    return await data.json();
  } catch (e) { log(e); }
}
```
右窗口顶标签 "C#" #178600：
```
async Task<Json> Load() {
    try {
        var data = await Fetch(url);
        return await data.Json();
    } catch (Exception e) { Log(e); }
}
```
两窗口中间一个大大的约等号 "≈" accent 色 #58a6ff，字号 64px。关键字 #ff7b72，方法 #58a6ff，字符串 #a5d6ff。

--- narration ---
JS 里"未来的值"叫 **Promise**，正好对应 C# 的 Task
早期用 .then 链式回调，回调一多就成了"回调地狱"
于是 JS 也引入了 async/await，作为 Promise 的语法糖
看这两段代码，左边 JS，右边 C#
async、await、try-catch，**几乎逐字对应**
它已经成了跨语言的通用异步语法
但请别被表象骗了，**底层完全是两回事**


>>> 同样的 await，底层天差地别 #B18
@enter: fade-up
@exit: fade
@visual: image(./assets/B18.png)

--- visual ---
深色背景 #0d1117。顶部标题 "同样的 await，底下天差地别", 字号 50px，粗体 #e6edf3，距顶 50px。
中央一张两列对比表，占画布 86% 宽，行高 56px，字号 28px。
表头："维度" / "C#" / "JavaScript"，表头条 accent 风格。
行（左 #8b949e，C# 列 #e6edf3，JS 列 #e6edf3）：
线程模型      | 多线程 + 线程池 | 单线程事件循环
await 后半段  | 可能在别的线程  | 永远同一个线程
真并行计算    | 可以 Task.Run  | 不行（要靠 Worker）
数据竞争      | 需要加锁        | 几乎不用担心
分隔线 #30363d。C# 的"多线程"和 JS 的"单线程"分别用对比色微调强调。

--- narration ---
最关键的区别就在线程模型
C# 是 **多线程**，await 之后可能落到 **另一个线程**
所以 C# 程序员要操心 **数据竞争**、要加锁
而 JS 是 **单线程**，await 之后 **永远是同一个线程**
好处是几乎不用担心数据竞争
代价是没法做真正的并行计算，算密集任务得另开 Worker
同一行 await，背后的世界观完全不同


>>> Python：asyncio 与 GIL #B19
@enter: fade-up
@exit: fade
@visual: image(./assets/B19.png)

--- visual ---
一张扁平矢量概念插画。画面中央是 Python 的事件循环（一个环形传送带），
和 JS 一样只有一个工人在轮转处理任务。但画面上方悬着一把醒目的大锁，
标注感暗示它叫 "GIL 全局解释器锁"，它像一道闸门，规定"同一时刻只有一个线程能执行 Python 字节码"。
锁下方几个线程工人排队，只有一个能通过闸门，其余在等。
深色科技背景 #0d1117，扁平现代矢量风格，锁用红色 #ff7b72 提示，传送带蓝色 #58a6ff。

--- narration ---
Python 的 **asyncio** 也是同一套
async def 定义协程，await 等待，语法依旧眼熟
但你必须显式地 **asyncio.run** 启动一个事件循环
而且 Python 有个绕不开的角色：**GIL**，全局解释器锁
它规定：同一时刻，只有一个线程能执行 Python 字节码
所以即使你开多线程，CPU 密集计算 **也快不起来**
asyncio 因此和 JS 一样，非常适合 IO 密集
异步 ≠ 并行，这一点 Python 体现得最明显


>>> Rust：Future + 执行器 #B20
@enter: fade-up
@exit: fade
@visual: image(./assets/B20.png)

--- visual ---
深色背景 #0d1117。顶部标题 "Rust：async 不自带运行时", 字号 50px，粗体 #e6edf3，距顶 50px。
中央代码窗口占画布 72% 宽，背景 #161b22，圆角 16px，字号 27px：
```
async fn download() -> String {
    let data = fetch(url).await;   // await 是后缀
    parse(data)
}

#[tokio::main]                     // 需要自己选执行器
async fn main() {
    let result = download().await;
}
```
关键字 async/fn/let/await 用 #ff7b72，类型 String #58a6ff，宏 #[tokio::main] #d2a8ff，注释 #8b949e。
右侧小标注框 30px："async fn 只是返回一个 Future，需要 executor 来推动" accent 色边框。

--- narration ---
Rust 也有 async/await，但哲学很不一样
注意它的 await 是 **后缀**，写在点后面
更关键的是
Rust 的 async 函数 **只返回一个 Future**，本身不会跑
Future 是惰性的，必须有一个 **执行器** 来推动它
而且标准库 **不自带** 执行器，你得自己选，比如 tokio
这是 Rust 的"零成本抽象"：要什么自己装，不为没用的东西买单


>>> Go：另一条路 goroutine #B21
@enter: fade-up
@exit: fade
@visual: image(./assets/B21.png)

--- visual ---
深色背景 #0d1117。顶部标题 "Go：根本没有 async/await", 字号 52px，粗体 #e6edf3，距顶 50px。
中央代码窗口占画布 72% 宽，背景 #161b22，圆角 16px，字号 28px：
```
func download(ch chan string) {
    data := fetch(url)      // 看起来是同步阻塞写法
    ch <- parse(data)       // 结果通过 channel 传回
}

go download(ch)             // go 关键字：开一个 goroutine
result := <-ch              // 从 channel 取结果
```
关键字 func/go/chan 用 #ff7b72，方法 #58a6ff，channel 操作符 <- 用 accent 色 #58a6ff，注释 #8b949e。
右侧小标注框 30px："goroutine = 极轻量绿色线程，运行时自动调度" accent 色边框。

--- narration ---
Go 干脆放弃了 async/await
它的代码看起来全是 **同步阻塞** 的写法
你用 **go** 关键字，就能开一个 **goroutine**
goroutine 是极轻量的"绿色线程"
开几十万个都没压力，由 Go 运行时自动调度
goroutine 之间用 **channel** 通信传结果
没有函数染色，没有 await 满天飞
这是和 async/await 完全不同的并发美学


>>> 五种语言，一张总表 #B22
@enter: fade-up
@exit: fade
@visual: image(./assets/B22.png)

--- visual ---
深色背景 #0d1117。顶部标题 "五种语言，一张总表", 字号 52px，粗体 #e6edf3，距顶 40px。
中央一张五行对比表，占画布 92% 宽，行高约 52px，字号 25px。
表头四列："语言" / "底层模型" / "语法" / "运行时"，表头条 accent 风格。
行（语言列加粗 #e6edf3，其余 #8b949e，亮点用 #58a6ff）：
C#         | 多线程 + 线程池   | async/await | 自带，捕获同步上下文
JavaScript | 单线程事件循环    | async/await | 自带，靠微任务队列
Python     | 单线程 + GIL      | async/await | 需 asyncio.run 启动
Rust       | 多线程 + 执行器   | async/.await| 不自带，需选 tokio
Go         | 绿色线程 goroutine| go + channel| 自带运行时调度
分隔线 #30363d，C#/JS/Python 的 "async/await" 用统一 accent 色凸显其语法一致。

--- narration ---
把五种语言放进一张表
你能一眼看清异同
语法上，C#、JS、Python、Rust 都有 await，**高度统一**
底层却各走各路
C# 多线程，JS 和 Python 单线程，Rust 要自己选执行器
Go 完全另立门户，用 goroutine 加 channel
学会读这张表，你换任何语言都能快速上手它的异步


>>> 共同的本质：续体 #B23
@enter: fade-up
@exit: fade
@visual: image(./assets/B23.png)

--- visual ---
一张扁平矢量概念插画。画面中央是一段被剪刀剪断的发光代码丝带，
断口处贴着一张"书签 / 存档"标签（蓝色 #58a6ff），暗示"在 await 处把后续保存为一个续体"。
丝带的后半截被卷成一个小卷轴待命，等条件满足后再被接回继续展开。
四周环绕 C#、JS、Python、Rust 的小图标，都用同一根光带连到这个"剪断—保存—续接"的核心装置，
传达"不同语言，同一个本质：把 await 之后的代码打包成续体"。深色科技背景 #0d1117，扁平现代矢量风格。

--- narration ---
撕开语法的外衣，它们共享同一个本质
在 await 这个点，把 **之后要执行的代码** 打包保存起来
这个被保存的"后续"，学名叫 **续体**，英文 continuation
事件一完成，运行时就把这个续体重新接上、继续执行
不管是 C# 的状态机、JS 的微任务，还是 Rust 的 Future
做的都是同一件事：**剪断、保存、续接**
理解了续体，你就抓住了所有异步语言的共同灵魂


>>> 上集小结 #B24
@enter: fade-up
@exit: fade
@visual: image(./assets/B24.png)

--- visual ---
深色背景 #0d1117。顶部居中标题 "上集 · 记住这几点"，字号 58px，粗体 #e6edf3，距顶 60px。
下方五行要点，纵向排列，占画布 82% 宽，每行左侧一个 accent 色 #58a6ff 圆点，字号 33px，依次淡入（间隔 0.4s）：
• async ≠ 多线程，await 是"暂停并交还线程"
• 编译器把 async 方法改写成一台状态机
• 默认把后半段送回原来的同步上下文；别用 .Result，会死锁
• 各语言语法统一、底层各异：多线程 / 事件循环 / 绿色线程
• 共同的本质，是把"后续"打包成续体
底部一行小字 "下集：async/await 在 Unity 实战", 字号 28px，颜色 #8b949e。

--- narration ---
上集到这里，复习一下
**async 不是多线程**，await 是暂停并交还线程
编译器把你的方法改写成一台 **状态机**
默认会把后半段送回原来的 **同步上下文**，别用 .Result，会死锁
跳出 C#，各语言语法统一、底层各异
而它们共同的本质，是把"后续"打包成 **续体**
下集，我们进入真实战场 **Unity**
看 async 在游戏里怎么落地，又有哪些专属的坑
