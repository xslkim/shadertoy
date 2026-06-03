>>> 开场：卡住的程序 #B01
@enter: fade
@exit: fade
@visual: image

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
这一集，我们从根上解决这个问题


>>> 标题卡 #B02
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
全屏深色背景 #0d1117，垂直居中布局，内容占画布约 80% 宽度。
[0s] 顶部小标签 "C# 异步编程 · 第一集"，字号 26px，颜色 #58a6ff，字母间距加宽，淡入。
[0.4s] 主标题 "async / await 的本质"，字号 112px，粗体，白色 #e6edf3，居中，伴随 32px 上移淡入。
[1.1s] 主标题下方 36px 处副标题 "它不是多线程，而是一台状态机"，字号 40px，颜色 #8b949e。
[1.6s] 主标题正下方 16px 处出现 4px 粗、accent 色 #58a6ff 横线，宽度等于主标题宽度，从左向右扫入。

--- narration ---
这是异步编程系列的第一集
我们先把最核心的两个关键字讲透
**async 和 await** 到底做了什么
讲完你会发现，它和你以为的完全不一样


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
@visual: image

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
@visual: animation

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


>>> Task：一个"未来的值" #B06
@enter: fade-up
@exit: fade
@visual: animation

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


>>> await 到底做了什么 #B07
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117，这是一张横向时序图，内容占画布 90%。
顶部标题 "await：把一个方法切成两半"，字号 52px，粗体 #e6edf3。
中央一条水平时间轴从左到右，时间轴上方画方法执行的色块：
[0s] 蓝色块 "前半段：发起请求"，标注 "在调用线程上同步执行"，字号 30px。
[1.5s] 时间轴出现一个明显的断点（虚线缺口），上方标 "await —— 暂停，return 出去"，accent 色 #58a6ff，字号 32px。
[2s] 断点下方一条向下的箭头指向 "线程被交还，去服务别的工作"，颜色 #8b949e。
[3.5s] 时间轴右段出现绿色块 "后半段：拿到结果，继续 Parse"，标注 "等结果到了，从断点处恢复"，字号 30px。

--- narration ---
await 真正神奇的地方在这里
它把一个方法从中间 **切成两半**
await 之前的代码，正常同步执行
执行到 await，如果结果还没好
方法就在这里 **暂停**，并且 return 出去
注意，是 return，不是阻塞
线程被交还，可以去服务别的工作
等结果到了，方法再 **从断点处恢复**，跑后半段


>>> 编译器的魔法：状态机 #B08
@enter: fade-up
@exit: fade
@visual: image

--- visual ---
一张扁平矢量概念插画。主体是一卷电影胶片或一条带有多个存档点的游戏关卡轨道，
轨道上有几个清晰的发光 "存档点 / checkpoint" 节点，用蓝色 #58a6ff 标记。
一个小机器人角色站在某个存档点上，旁边有一个发光的状态指示牌显示着箭头循环，
暗示"可以暂停、保存进度、之后从同一点恢复"。整体传达"可暂停可恢复的进度机"的概念。
深色科技背景 #0d1117，扁平现代矢量风格，蓝色辉光点缀。

--- narration ---
那方法怎么记住自己停在哪、跑到一半的变量又存在哪
答案是：**编译器** 帮你做了
你写的每个 async 方法
编译器都会偷偷改写成一台 **状态机**
每个 await 就是一个存档点
局部变量被搬进状态机的字段，妥善保存
暂停时存档，恢复时读档，从同一个点继续


>>> 状态机长什么样 #B09
@enter: fade-up
@exit: fade
@visual: animation

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


>>> await 之后，回到哪个线程 #B10
@enter: fade-up
@exit: fade
@visual: image

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


>>> ConfigureAwait(false) #B11
@enter: fade-up
@exit: fade
@visual: animation

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
否则你会在错误的线程上碰 UI，直接报错
经验法则：库代码默认加，应用 UI 代码不加


>>> async void 的陷阱 #B12
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部标题 "async void：一个危险的例外"，字号 52px，粗体，红色 #ff7b72，距顶 70px。
中央代码窗口占画布 70% 宽，背景 #161b22，圆角 16px，字号 28px：
```
async void DoWork() {        // ✗ 没人能 await 它
    await Task.Delay(1000);
    throw new Exception();   // ✗ 异常直接崩进程
}

async Task DoWorkOk() {      // ✓ 几乎总是用 Task
    await Task.Delay(1000);
}
```
错误行用红色 #ff7b72 高亮标 ✗，正确行用绿色标 ✓。注释 #8b949e。

--- narration ---
async 方法的返回类型，几乎永远该是 **Task**
唯一例外是 async void，而它是个陷阱
async void 没法被 await，你无法知道它何时完成
更糟的是，里面抛出的异常 **没人接得住**
它会直接掀翻整个进程
那为什么还存在它
因为事件处理器的签名要求是 void
所以记住：**只有事件处理器**才用 async void，其余一律 Task


>>> 异步里的异常 #B13
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部标题 "异常：try-catch 照常能用"，字号 54px，粗体 #e6edf3，距顶 70px。
中央代码窗口占画布 70% 宽，背景 #161b22，圆角 16px，字号 28px：
```
try {
    var data = await DownloadAsync();
}
catch (HttpRequestException e) {
    Log(e); // 异常被存进 Task，await 时重新抛出
}
```
关键字 try/catch/var/await 用 #ff7b72，类型 #58a6ff，注释 #8b949e。
代码下方一条说明条：左 "异常发生 → 存入 Task" → 右 "await 取结果 → 原样抛出"，
用 accent 色箭头连接，字号 30px。

--- narration ---
好消息是，异步里的异常处理几乎没有心智负担
你照样用熟悉的 **try-catch** 包住 await 就行
原理是这样
异步方法里抛出的异常，会先被 **存进那个 Task**
等你 await 这个 Task 取结果时
异常会在 await 这一行 **原样重新抛出**
所以它能精准落进你的 catch 块
唯一要小心的是：你必须真的去 await 它，异常才会浮出来


>>> 并发：WhenAll 与 WhenAny #B14
@enter: fade-up
@exit: fade
@visual: animation

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


>>> 死锁：别用 .Result 和 .Wait() #B15
@enter: fade-up
@exit: fade
@visual: animation

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
最后一个坑，也是面试常考
在 UI 线程上用 **.Result** 或 **.Wait()** 去同步等一个异步任务
你会得到一个 **死锁**
为什么
.Result 把 UI 线程 **阻塞** 在这里
而异步任务的后半段，默认要 **送回 UI 线程** 才能恢复
可 UI 线程正被你卡着，永远腾不出来
两边互相等，谁也动不了
解法：要么一路 await 到底，要么给被等的代码加 ConfigureAwait(false)


>>> 取消：CancellationToken #B16
@enter: fade-up
@exit: fade
@visual: animation

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


>>> 第一集小结 #B17
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部居中标题 "第一集 · 记住这几点"，字号 58px，粗体 #e6edf3，距顶 60px。
下方五行要点，纵向排列，占画布 80% 宽，每行左侧一个 accent 色 #58a6ff 圆点，字号 34px，依次淡入（间隔 0.4s）：
• async ≠ 多线程，await 是"暂停并交还线程"
• 编译器把 async 方法改写成一台状态机
• 默认会把后半段送回原来的同步上下文
• 返回类型用 Task，async void 只留给事件处理器
• 别用 .Result / .Wait()，会死锁；要取消用 Token
底部一行小字 "下一集：async/await 在 Unity 里的应用"，字号 28px，颜色 #8b949e。

--- narration ---
这一集我们把地基打好了，复习一下
**async 不是多线程**，await 是暂停并交还线程
编译器把你的方法改写成一台 **状态机**
默认会把后半段送回原来的 **同步上下文**
返回类型永远用 **Task**，async void 只给事件处理器
绝不用 .Result 或 .Wait 同步等待，那会 **死锁**
下一集，我们看它在 **Unity** 里到底怎么用
那里有主线程、有协程，还有一堆专属的坑
