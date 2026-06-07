#version 450
// 全屏三角形:用 gl_VertexIndex 直接生成 3 个顶点,无需顶点缓冲。
// 这是 shadertoy 风格 demo 的标准做法 —— 一个三角形盖满整个屏幕。

layout(location = 0) out vec2 vUV;

void main()
{
    // 0 -> (-1,-1), 1 -> (3,-1), 2 -> (-1,3)  覆盖整个 NDC
    vec2 p = vec2((gl_VertexIndex << 1) & 2, gl_VertexIndex & 2);
    vUV = p;                       // 0..2 的 UV,frag 里会用到
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
