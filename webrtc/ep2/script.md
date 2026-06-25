>>> 下集开场 · 数据怎么上路 #B01
@enter: zoom-in
@exit: fade
@visual: image

--- visual ---
概念艺术图，深色背景，一个层层嵌套的发光数据包，像俄罗斯套娃/同心盒，
最里层是媒体载荷，外面一层层包裹：RTP、SRTP 加密层、UDP、IP，每层用不同冷色调发光边框区分。
电影质感，无文字。

--- narration ---
上集我们搞懂了 WebRTC 怎么压低延迟、怎么编码压缩
这是下集，接着回答后两个问题
编码好的数据，到底**怎么封装成包**
市面上那些远程遥控方案，**和它比谁更强**
WebRTC 里跑着好几种完全不同的包
我们先一层一层拆开看


>>> 协议全景栈 #B02
@enter: fade
@exit: fade
@visual: image(./assets/B02.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B02.png）
WebRTC 协议栈全景：底层 UDP/IP；其上三条路——
①媒体：RTP/SRTP；②数据：SCTP over DTLS（DataChannel）；③DTLS 握手负责密钥；
ICE/STUN/TURN 负责连通；信令(SDP)在带外。一图看清谁走谁。

--- narration ---
先看全景，所有东西最终都跑在 **UDP** 上
往上分三条路
音视频走 **RTP**，再用 **SRTP** 加密
应用数据走 **DataChannel**，底下是 SCTP 套在 DTLS 里
而 **DTLS** 握手，负责给大家发密钥
连接怎么建起来，靠 **ICE、STUN、TURN**
至于交换信息的**信令**，是走带外的，不归 WebRTC 管
记住这张图，下面逐个拆


>>> RTP 包头逐字段 #B03
@enter: fade-up
@exit: fade
@visual: image(./assets/B03.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B03.png）
RTP 固定头 12 字节逐字段比特拆解：V(2) P(1) X(1) CC(4) M(1) PT(7) 序列号(16)
时间戳(32) SSRC(32)，下面接可选 CSRC 和头部扩展（transport-wide cc seq 等）。
用按位宽度成比例的比特格子展示。

--- narration ---
先看最常见的 RTP 头，固定 **12 个字节**
开头是版本号、填充位、扩展位、CSRC 计数
然后是 **M 标记位**，常用来标记一帧的最后一个包
**PT 负载类型**七位，对应刚才协商的编码
接着 **序列号** 16 位，丢包检测全靠它
**时间戳** 32 位，决定这帧何时播
最后 **SSRC** 32 位，是这路流的唯一身份证
后面还能挂头部扩展，比如带上拥塞控制要用的全局序号


>>> 视频载荷怎么打包 #B04
@enter: fade
@exit: fade
@visual: image(./assets/B04.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B04.png）
H.264 over RTP 三种打包模式：①单 NAL——一个 NAL 刚好一个包；
②STAP-A 聚合——多个小 NAL（如 SPS+PPS）塞进一个包；
③FU-A 分片——一个大 NAL（如 IDR 关键帧）拆到多个包，带 S/E 起止标记。
配 MTU≈1200 字节限制说明。

--- narration ---
一个 NAL 单元，可能比一个网络包还大，怎么办？
RTP 有三种打包模式
小的 NAL，比如 SPS 加 PPS，用 **STAP-A** 聚合，几个塞进一个包
正常大小，**单 NAL** 模式，一个包装一个
而大的，比如几十 KB 的 IDR 关键帧
就得 **FU-A 分片**，切到很多个包里，每片标好是开头还是结尾
接收端再按序列号拼回来
所以一个关键帧丢一片，整帧就废了，这才要请求重传或新关键帧


>>> RTCP：质量反馈回路 #B05
@enter: fade
@exit: fade
@visual: image(./assets/B05.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B05.png）
RTCP 报文家族：SR 发送报告 / RR 接收报告（丢包率、抖动、往返时延）/
反馈包 NACK、PLI、FIR、REMB、transport-cc。说明 RTCP 与 RTP 配对，占用约 5% 带宽，是前面拥塞控制和抗丢包的"控制信道"。

--- narration ---
RTP 只管发媒体，那质量谁来盯？是 **RTCP**
它和 RTP 配对，专门走控制信息
**SR 和 RR** 互相通报：丢了多少、抖动多大、往返多久
上集讲的那些反馈，全靠它
**NACK** 要重传、**PLI** 要关键帧、**REMB 和 transport-cc** 报带宽
可以说，上集里实时性的那套自适应
就是 RTCP 这条反馈回路在背后撑着


>>> 加密：SRTP 与 DTLS #B06
@enter: fade
@exit: fade
@visual: image(./assets/B06.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B06.png）
加密流程图：先用 DTLS 在 UDP 上握手交换密钥（DTLS-SRTP），
之后媒体不直接走 DTLS，而是用导出的密钥做 SRTP，加密+认证 RTP 载荷。
强调 WebRTC 强制加密，没有明文媒体。

--- narration ---
WebRTC 有条铁律，**没有明文，全程加密**
具体分工很巧妙
先用 **DTLS** 在 UDP 上握一次手，安全地交换密钥
但媒体不直接塞进 DTLS
而是用握手导出的密钥，去做 **SRTP**
SRTP 专门给 RTP 包加密和防篡改，开销小、对实时友好
握手归 DTLS，加密归 SRTP，各司其职


>>> DataChannel：传任意数据 #B07
@enter: fade
@exit: fade
@visual: image(./assets/B07.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B07.png）
DataChannel 协议叠层：应用数据 → SCTP → DTLS → UDP；
SCTP 提供可配置可靠性：完全可靠/有序（像 TCP）、限定重传次数或时限（部分可靠）、完全不可靠（像 UDP）。
用途：文件传输、游戏状态、遥控指令、聊天。

--- narration ---
除了音视频，WebRTC 还能传任意数据，靠 **DataChannel**
它底下是 **SCTP**，套在 DTLS 里，再走 UDP
SCTP 最妙的是**可靠性可配**
你要像 TCP 一样完全可靠、有序，行
你要像 UDP 一样丢了不管、只图快，也行
还能折中，最多重传几次、或只在几毫秒内有效
所以远程遥控的**键鼠指令**，常走这条不可靠但极快的通道


>>> 连接怎么建：ICE 穿透 #B08
@enter: fade
@exit: fade
@visual: image(./assets/B08.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B08.png）
ICE/NAT 穿透流程：双方先经信令服务器交换 SDP（offer/answer）；
各自收集候选地址——host 本地、srflx 经 STUN 反射拿公网映射、relay 经 TURN 中转；
连通性检查后选最优路径，能直连就直连，不行才走 TURN 中转。

--- narration ---
最后一个封装问题，两台在不同家庭网络后面的电脑，怎么找到对方？
难点在 **NAT**，大家都没有公网地址
流程是这样
先通过**信令服务器**交换一份 **SDP**，里面写明编码能力和地址候选
每一端都去收集候选
本地地址、经 **STUN** 问到的公网映射地址、还有 **TURN** 中转地址
然后互相试探，挑一条能通的最优路
能**直连**就直连，延迟最低
实在穿不过去，才退而走 **TURN** 中转


>>> 第四幕 · 方案对比 #B09
@enter: zoom-in
@exit: fade
@visual: image

--- visual ---
概念艺术图，深色背景，多块发光的远程桌面屏幕呈扇形排开，
每块屏幕用细蓝光带连回中央一台主控设备，象征各种远程遥控方案在比拼。
电影质感，冷色调，无文字。

--- narration ---
理解了 WebRTC，再回头看市面上的远程遥控
你会发现，它们本质上都是同一件事
**采集屏幕、编码、低延迟传输、再把键鼠指令传回去**
区别只在每一步的取舍


>>> 遥控的本质拆解 #B10
@enter: fade
@exit: fade
@visual: image(./assets/B10.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B10.png）
远程遥控通用管线：被控端 抓屏→硬件编码(H.264/HEVC/AV1)→低延迟传输→
主控端 解码渲染；反向 键鼠/手柄指令 走可靠/低延迟控制通道回传。标注每家差异都落在"编码器、传输协议、中转策略"三处。

--- narration ---
所有遥控方案，都是这条管线
被控端抓屏、硬件编码、压成码流发出去
主控端解码、显示
再把你的键鼠操作，从一条控制通道送回去
各家的差异，无非落在三个地方
**用什么编码器、用什么传输协议、要不要中转服务器**
而 WebRTC，就是这条管线的**通用基准线**
它为了浏览器即开即用、为了适配任意公网，处处留足余量
接下来你会看到，专用方案怎么在这三处做减法
用**牺牲通用性**，换回那几十毫秒延迟


>>> RustDesk / 自建 #B11
@enter: fade-up
@exit: fade
@visual: image(./assets/B11.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B11.png）
RustDesk 方案卡：开源、Rust 编写；编码 VP8/VP9/AV1/H264（含硬编）；
自研传输协议，支持直连 + 自建中继(hbbs/hbbr)；最大卖点 可完全私有化自托管。定位：开源可控、个人/企业自部署。

--- narration ---
先看 **RustDesk**，开源、Rust 写的
编码上 VP9、AV1、H.264 都能用，尽量走硬件
传输是自研协议，能直连也能走中继
它的打洞加中继，其实就是**复刻了 ICE 那套**思路
能直连时，延迟和 WebRTC 一个量级，几十毫秒
一旦穿不过去走中继，被服务器绕一圈，延迟就上去了
但它真正的卖点不是延迟，是**完全自托管**
中转服务器自己搭，数据不经过别人
适合在意隐私、想私有化部署的个人和团队


>>> Parsec / Moonlight #B12
@enter: fade
@exit: fade
@visual: image(./assets/B12.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B12.png）
游戏串流卡：Parsec(闭源) + Moonlight(开源, 配 Sunshine/NVIDIA)；
NVENC 硬件 H.264/HEVC/AV1，自研 UDP 传输，支持 4:4:4 与高帧率；极致追求"动作到画面"低延迟。定位：游戏/创作串流。

--- narration ---
要极致低延迟，看 **Parsec** 和 **Moonlight**
它们为游戏串流而生，甚至能比 WebRTC 还快
为什么？因为两端都是**原生客户端**，没有浏览器的包袱
第一，把抖动缓冲压到极限，甚至只缓**一帧**
WebRTC 为通用网络留的那点余量，它们全砍了
第二，画面本就在 GPU 里，**渲染完直接送编码**
省掉了普通抓屏那段回读，还用上 NVENC 低延迟预设
第三，局域网或专线带宽稳，敢上高码率和 **4:4:4**
于是在局域网里，延迟能压到一帧，十几毫秒
代价是它挑硬件、挑网络，通用性远不如 WebRTC


>>> TeamViewer / 向日葵 #B13
@enter: fade
@exit: fade
@visual: image(./assets/B13.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B13.png）
商业通用远控卡：TeamViewer / 向日葵；自研私有协议，跨平台兼容广；
中转服务器优先，确保任何防火墙/NAT 都能连上；权衡是延迟一般、画质一般。定位：企业运维、远程支持，稳为先。

--- narration ---
再看 **TeamViewer** 和**向日葵**
它们走的是另一条路，**兼容和稳定优先**
私有协议、跨平台，几乎什么设备都连得上
而且**中转优先**，宁可绕一圈走服务器，也要保证连得通
绕这一圈本身就多出几十毫秒，网差时还可能退回 TCP
所以延迟和画质都只能算一般
但对企业远程运维、帮长辈修电脑，稳定连上才是刚需


>>> 云游戏 / 云手机 #B14
@enter: fade
@exit: fade
@visual: image(./assets/B14.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B14.png）
云游戏/云手机卡：GeForce NOW、Xbox Cloud、各类云手机；
运行在云端 GPU，画面串到本地；部分用 WebRTC，部分用私有 UDP 协议。
关注点：边缘机房就近、硬件编码、超低延迟与高并发。定位：算力在云、终端只显示。

--- narration ---
最后是**云游戏和云手机**
游戏直接跑在云端的 GPU 上，画面串到你的设备
和 Parsec 一样，画面**渲染完直接编码**，管线极短
有的方案干脆就用 **WebRTC**，浏览器打开即玩
有的用更可控的私有 UDP 协议
它们最大的瓶颈不在管线，而在**你到机房的物理距离**
所以才拼命建**就近的边缘机房**，把这段往返压下来
本质还是那条管线，只是把算力整个搬到了云端


>>> 横向大对比 #B15
@enter: fade
@exit: fade
@visual: image(./assets/B15.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B15.png）
五行横向对比表：WebRTC、RustDesk、Parsec/Moonlight、TeamViewer/向日葵、云游戏；
列：典型编码、传输协议、延迟、画质、是否开源/自托管、最佳场景。用 good/mid/bad 颜色标注。

--- narration ---
把它们摆到一张表上，顺手标上延迟量级
通用实时通信，WebRTC 浏览器原生、生态最广，百毫秒级
极致低延迟串流，Parsec、Moonlight 称王，局域网十几毫秒
开源可自托管，选 RustDesk
要兼容稳定、随处能连，TeamViewer 和向日葵
而把算力搬上云，那就是云游戏
你会发现一条规律
越**专用**、越能攥住两端和网络，延迟就压得越低
越**通用**、越要适配所有人，就越得留余量
WebRTC 选了后者，输掉一点极限延迟
赢回来的，是整个互联网随处能用


>>> 收尾 · 一句话总结 #B16
@enter: fade-up
@exit: fade
@visual: image(./assets/B16.png)

--- visual ---
（此描述仅作文档参考，实际使用 ./assets/B16.png）
收尾总结卡：大字"WebRTC 为什么这么快"，下方三行凝练答案：
①宁丢不等的 UDP+RTP 与全程自适应 ②高效硬件编解码只传变化 ③层层封装的包各司其职。
底部一行小字"实时，是无数取舍堆出来的"。

--- narration ---
回到最开始那个问题，WebRTC 为什么这么快
答案其实是三句话
第一，它选了**宁丢不等**的 UDP，并且全程自适应延迟
第二，它用**高效的编解码**，只传变化、压到极限
第三，它把每种数据**层层封装**，各走各的最优通道
所谓实时，从来不是某个黑科技
而是无数个取舍，一点一点堆出来的
这个系列就到这，我们下个主题见
