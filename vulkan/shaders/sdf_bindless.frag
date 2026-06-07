#version 450
#extension GL_EXT_nonuniform_qualifier : require
// =============================================================================
//  SDF bindless 片元着色器
//
//  教学核心:屏幕上看到的所有"场景"参数都不来自单独绑定的 uniform,而是放在
//  一个【描述符数组】(本 demo 用 VK_EXT_descriptor_buffer 实现 / 在 descriptor_heap
//  里则是一整块 heap)里。CPU 每帧只 push 两个【索引】sceneA / sceneB,
//  shader 用这两个索引从数组里取出对应的场景参数,并按 blend 在两者之间做
//  SDF 形状 + 调色板的连续 morph。
//
//  "一个 heap,海量资源,按索引访问" —— 这就是 bindless / descriptor heap 的精髓。
// =============================================================================

layout(location = 0) in  vec2 vUV;
layout(location = 0) out vec4 oColor;

// 每个场景的参数块。整个数组就是"堆"里的资源集合。
struct SceneParams {
    vec4 palA;   // 主色
    vec4 palB;   // 强调色
    vec4 bg;     // 背景色
    vec4 cfg;    // x=形状(0球 1立方 2圆环 3八面体) y=缩放 z=自转速度 w=辉光
};

// set=0, binding=0:场景参数描述符【数组】。
// 数组大小必须等于 C++ 端 layout 的 descriptorCount(kSceneCount = 6)。
layout(set = 0, binding = 0) uniform SceneBlock {
    SceneParams s;
} scenes[6];

layout(push_constant) uniform Push {
    vec2  iResolution;
    float iTime;
    uint  sceneA;     // 当前场景索引(CPU 每帧推送 —— 这就是"按索引访问堆")
    uint  sceneB;     // 下一个场景索引,用于平滑过渡
    float blend;      // A->B 的过渡权重 0..1
    uint  sceneCount;
} pc;

// ---------- SDF 基本图元 ----------
float sdSphere(vec3 p, float r)            { return length(p) - r; }
float sdBox(vec3 p, vec3 b)               { vec3 q = abs(p) - b; return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0); }
float sdTorus(vec3 p, vec2 t)             { vec2 q = vec2(length(p.xz)-t.x, p.y); return length(q)-t.y; }
float sdOcta(vec3 p, float s)             { p = abs(p); return (p.x+p.y+p.z-s)*0.57735027; }

mat2 rot(float a){ float c=cos(a), s=sin(a); return mat2(c,-s,s,c); }

// 取出某个场景的有向距离(已含自转)
float sceneSDF(uint idx, vec3 p)
{
    SceneParams sp = scenes[nonuniformEXT(idx)].s;
    float t = pc.iTime * sp.cfg.z;
    p.xz = rot(t) * p.xz;
    p.xy = rot(t * 0.7) * p.xy;
    float sc = sp.cfg.y;
    int   shape = int(sp.cfg.x + 0.5);
    if (shape == 0) return sdSphere(p, 0.9 * sc);
    if (shape == 1) return sdBox(p, vec3(0.7 * sc));
    if (shape == 2) return sdTorus(p, vec2(0.8 * sc, 0.32 * sc));
    return sdOcta(p, 1.1 * sc);
}

// 在 A、B 两个场景之间做 SDF 形状 morph
float mapDist(vec3 p, out float glow)
{
    float da = sceneSDF(pc.sceneA, p);
    float db = sceneSDF(pc.sceneB, p);
    float ga = scenes[nonuniformEXT(pc.sceneA)].s.cfg.w;
    float gb = scenes[nonuniformEXT(pc.sceneB)].s.cfg.w;
    glow = mix(ga, gb, pc.blend);
    return mix(da, db, pc.blend);
}

vec3 calcNormal(vec3 p)
{
    float g;
    vec2 e = vec2(0.0015, 0.0);
    return normalize(vec3(
        mapDist(p+e.xyy,g) - mapDist(p-e.xyy,g),
        mapDist(p+e.yxy,g) - mapDist(p-e.yxy,g),
        mapDist(p+e.yyx,g) - mapDist(p-e.yyx,g)));
}

void main()
{
    // vUV 在可见区为 0..1;转成以画面中心为原点、按高度归一化的坐标
    vec2 uv  = (vUV - 0.5) * pc.iResolution / pc.iResolution.y;
    // 取两个场景调色板,按 blend 混合
    SceneParams A = scenes[nonuniformEXT(pc.sceneA)].s;
    SceneParams B = scenes[nonuniformEXT(pc.sceneB)].s;
    vec3 palA = mix(A.palA.rgb, B.palA.rgb, pc.blend);
    vec3 palB = mix(A.palB.rgb, B.palB.rgb, pc.blend);
    vec3 bg   = mix(A.bg.rgb,   B.bg.rgb,   pc.blend);

    // 相机
    vec3 ro = vec3(0.0, 0.0, 3.2);
    vec3 rd = normalize(vec3(uv, -1.6));

    float glow = 0.0;
    float t = 0.0;
    float glowAccum = 0.0;
    bool  hit = false;
    for (int i = 0; i < 96; ++i) {
        vec3 p = ro + rd * t;
        float g;
        float d = mapDist(p, g);
        glowAccum += g * 0.015 / (1.0 + d * d * 8.0);  // 体积辉光
        if (d < 0.001) { hit = true; glow = g; break; }
        t += d;
        if (t > 8.0) break;
    }

    vec3 col = bg;
    if (hit) {
        vec3 p = ro + rd * t;
        vec3 n = calcNormal(p);
        vec3 l = normalize(vec3(0.8, 0.9, 0.6));
        float dif = clamp(dot(n, l), 0.0, 1.0);
        float fre = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.0);
        col = mix(palA, palB, dif);
        col += palB * fre * 1.2;
        col *= 0.4 + 0.6 * dif;
    }
    col += palB * glowAccum * 2.0;          // 辉光叠加
    col = pow(col, vec3(0.4545));           // gamma
    oColor = vec4(col, 1.0);
}
