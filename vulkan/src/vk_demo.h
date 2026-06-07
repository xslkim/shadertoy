// 共享声明:供 main.cpp 与 descriptor_heap_reference.cpp 使用。
#pragma once
#include <vulkan/vulkan.h>
#include <cstdio>
#include <cstdlib>

// 简单的错误检查宏
#define VK_CHECK(x)                                                       \
    do {                                                                  \
        VkResult err__ = (x);                                            \
        if (err__ != VK_SUCCESS) {                                       \
            std::fprintf(stderr, "[VK_CHECK] %s 返回 %d (行 %d)\n",      \
                         #x, (int)err__, __LINE__);                      \
            std::abort();                                                 \
        }                                                                 \
    } while (0)

// descriptor_heap 教学参考:在 main 里调用,演示新扩展的 API 形态。
// supported = 设备是否真的暴露 VK_EXT_descriptor_heap。
void run_descriptor_heap_reference(VkInstance instance,
                                   VkPhysicalDevice phys,
                                   bool supported);
