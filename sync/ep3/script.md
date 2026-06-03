>>> 开场：同一个关键字，不同的世界 #B01
@enter: fade
@exit: fade
@visual: image(./assets/B01.png)

--- visual ---
一张扁平矢量插画。画面中央漂浮着一个巨大的、发光的蓝色 #58a6ff "await" 符号，
从它向四周辐射出几条光带，分别连向五个风格化的语言图标牌：C#、JavaScript、Python、Rust、Go，
每个图标牌的底座机制画得略有不同（有的下面是单条传送带，有的是多线程齿轮，有的是协程循环），
暗示"同一个关键字，底层却是不同的世界"。深色科技背景 #0d1117，扁平现代矢量风格，强对比，蓝色辉光。

--- narration ---
前两集我们吃透了 C# 的 async/await
这一集跳出 C#，横向看世界
你会发现一件有意思的事
**JS、Python、Rust** 的 async/await，语法几乎一模一样
但它们底层的运行机制，差别巨大
而 **Go** 干脆走了另一条路
看完这一集，你对异步会有一个更立体的认识


>>> 三种并发模型 #B02
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部标题 "并发，其实只有几种底层模型", 字号 52px，粗体 #e6edf3，距顶 50px。
中央三张卡片横向排列，各占画布约 28% 宽，间距 40px，高约 380px，圆角 16px，背景 #161b22，内边距 28px。
每卡顶部一个大图标 + 标题 36px，下方两行说明 27px #8b949e：
卡①「多线程」🧵：抢占式，OS 调度，代表 C# Task 线程池
卡②「事件循环」🔁：单线程，任务排队，代表 JS / Python asyncio
卡③「协程 / 绿色线程」🟢：用户态调度，代表 Go goroutine
标题用 accent 色 #58a6ff，图标用辉光。

--- narration ---
先建立一个框架
表面五花八门，底层并发其实就几种模型
第一种，**多线程**：靠操作系统抢占式调度，C# 的 Task 池就是
第二种，**事件循环**：单线程，任务排队轮流跑，JS 和 Python 走这条
第三种，**协程 / 绿色线程**：在用户态自己调度，Go 是代表
async/await 这套语法，主要服务前两种
带着这个框架，我们逐个看


>>> JS 单线程事件循环 #B03
@enter: fade-up
@exit: fade
@visual: image(./assets/B03.png)

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


>>> JS：Promise #B04
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部标题 "JS 的 Promise ≈ C# 的 Task", 字号 52px，粗体 #e6edf3，距顶 50px。
中央代码窗口占画布 74% 宽，背景 #161b22，圆角 16px，字号 28px：
```
function downloadData() {
  return fetch(url)                 // 返回 Promise
    .then(res => res.json())        // 链式回调
    .catch(err => console.log(err));
}
```
关键字 function/return 用 #ff7b72，方法 fetch/then/catch #58a6ff，字符串/url #a5d6ff，注释 #8b949e。
代码右侧一个小标注框 30px：「Promise = 未来的值，对应 C# 的 Task」accent 色边框。

--- narration ---
JS 里"未来的值"叫 **Promise**
它就对应 C# 的 Task
早期大家用 **.then** 链式回调来串联异步
fetch 返回一个 Promise，then 处理结果，catch 处理错误
能用，但回调一多就嵌套成"回调地狱"
于是 JS 也引入了 async/await，作为 Promise 的语法糖


>>> JS：async/await #B05
@enter: fade-up
@exit: fade
@visual: animation

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
看这两段代码，左边 JS，右边 C#
async、await、try-catch，**几乎逐字对应**
这就是 async/await 的魅力
它已经成了跨语言的通用异步语法
所以你学会了 C# 这套，迁到 JS 几乎零成本
但请别被表象骗了，**底层完全是两回事**


>>> 关键区别：线程模型 #B06
@enter: fade-up
@exit: fade
@visual: animation

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
代价是没法用它做真正的并行计算，要算密集任务得另开 Worker
同一行 await，背后的世界观完全不同


>>> await 的语义差异 #B07
@enter: fade-up
@exit: fade
@visual: image(./assets/B07.png)

--- visual ---
一张扁平矢量概念插画，左右对比两个"恢复调度"机制。
左半：C#，画一个发光的 "SynchronizationContext" 传送门，把 await 后半段送回某个指定的线程讲台，
旁边有线程池的多个工人，强调"可配置回到哪"。
右半：JS，画一个单一工人面前有两条排队通道，标注感暗示一条是 "微任务队列 microtask"、
一条是 "宏任务队列 macrotask"，await 后半段总是插进优先级更高的微任务队列等这一轮跑完立即执行。
两边用一条竖直分割线分开。深色科技背景 #0d1117，扁平现代矢量风格，蓝色 #58a6ff 辉光。

--- narration ---
再往细里看，连"恢复"的调度都不一样
C# 用 **同步上下文** 决定后半段回哪个线程
还能用 ConfigureAwait 来配置，我们第一集讲过
JS 没有线程概念，它用 **任务队列的优先级**
await 之后的代码，会进入优先级更高的 **微任务队列**
在当前这一轮事件循环结束后、下一个宏任务之前执行
所以两者连"什么时候恢复"的规则都不同


>>> Python：asyncio #B08
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部标题 "Python：又是熟悉的配方", 字号 52px，粗体 #e6edf3，距顶 50px。
中央代码窗口占画布 74% 宽，背景 #161b22，圆角 16px，字号 28px：
```
import asyncio

async def download():
    data = await fetch(url)        # 协程里 await
    return parse(data)

async def main():
    a, b = await asyncio.gather(   # 并发，对应 WhenAll
        download(), download())

asyncio.run(main())                # 启动事件循环
```
关键字 import/async/def/await/return 用 #ff7b72，方法 #58a6ff，字符串 #a5d6ff，注释 #8b949e。

--- narration ---
Python 的 **asyncio** 也是同一套
async def 定义协程，await 等待，语法依旧眼熟
并发用 **asyncio.gather**，正好对应 C# 的 WhenAll
但 Python 有个独特之处
你必须显式地 **asyncio.run** 启动一个事件循环
异步代码才能跑起来
不像 C#，运行时早就帮你把这些铺好了


>>> Python：事件循环 + GIL #B09
@enter: fade-up
@exit: fade
@visual: image(./assets/B09.png)

--- visual ---
一张扁平矢量概念插画。画面中央是 Python 的事件循环（一个环形传送带），
和 JS 一样只有一个工人在轮转处理任务。但画面上方悬着一把醒目的大锁，
标注感暗示它叫 "GIL 全局解释器锁"，它像一道闸门，规定"同一时刻只有一个线程能执行 Python 字节码"。
锁下方几个线程工人排队，只有一个能通过闸门，其余在等。
深色科技背景 #0d1117，扁平现代矢量风格，锁用红色 #ff7b72 提示，传送带蓝色 #58a6ff。

--- narration ---
Python 还有一个绕不开的角色：**GIL**
全局解释器锁
它规定：同一时刻，只有一个线程能执行 Python 字节码
所以即使你开多线程，CPU 密集计算 **也快不起来**
这让 asyncio 的事件循环模型，和 JS 一样
非常适合 IO 密集，比如大量网络请求
但碰到 CPU 密集，得靠多进程绕开 GIL
异步 ≠ 并行，这一点 Python 体现得最明显


>>> Rust：Future + 执行器 #B10
@enter: fade-up
@exit: fade
@visual: animation

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
这是 Rust 的"零成本抽象"哲学：要什么自己装，不为你不用的东西买单


>>> Go：另一条路 goroutine #B11
@enter: fade-up
@exit: fade
@visual: animation

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


>>> 横向大对比 #B12
@enter: fade-up
@exit: fade
@visual: animation

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


>>> 共同的本质：续体 #B13
@enter: fade-up
@exit: fade
@visual: image(./assets/B13.png)

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


>>> 全系列总结 #B14
@enter: fade-up
@exit: fade
@visual: animation

--- visual ---
深色背景 #0d1117。顶部居中标题 "三集回顾 · 你的异步心智模型", 字号 50px，粗体 #e6edf3，距顶 50px。
下方三张横向卡片，各占画布约 30% 宽，间距 36px，高约 320px，圆角 16px，背景 #161b22，内边距 28px。
每卡顶部集数标签 accent 色 #58a6ff 28px + 标题 32px + 两行要点 26px #8b949e：
卡①「第一集 · 原理」async≠多线程 / 状态机 / 同步上下文 / 不要 .Result
卡②「第二集 · Unity」主线程铁律 / UniTask 零 GC / 永远传取消 token
卡③「第三集 · 对比」语法统一、底层各异 / 共同本质是续体
底部一行 30px #e6edf3："会用，更要懂它为什么这么设计"。

--- narration ---
三集到这里就讲完了，我们回顾一下
第一集，**async 不是多线程**，它是编译器生成的状态机
第二集，在 Unity 里守住 **主线程铁律**，用 UniTask，永远传取消 token
第三集，各语言语法统一、底层各异，共同本质是 **续体**
异步编程不难
难的是从"会用"到真正"懂它为什么这么设计"
希望这三集，帮你跨过了这道坎
我们下个系列再见
