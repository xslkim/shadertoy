// =============================================================================
//  VK_EXT_descriptor_heap —— 教学参考(本扩展的真实 API 形态)
//
//  这个文件【不参与实际渲染】,它的作用是用真实的 SDK 类型和函数签名,把新扩展
//  的完整工作流走一遍,并与 main.cpp 里用的 descriptor_buffer 做对照。
//  所有结构体/枚举都来自 vulkan_core.h(spec v1),因此本文件能编译通过;
//  当本机驱动尚未暴露该扩展时,运行时优雅打印形态说明而不调用未启用的函数。
//
//  心智模型(和 D3D12 / Shader Model 6.6 的 ResourceDescriptorHeap[] 一致):
//    一整块 GPU 内存 = "堆"。所有资源的描述符按尺寸紧密排布其中。
//    shader 不再"绑定描述符集",而是拿一个【整数索引】直接到堆里取资源。
// =============================================================================
#include "vk_demo.h"
#include <cstring>

static void printConcept() {
    std::printf("\n------------------- VK_EXT_descriptor_heap 教学参考 -------------------\n");
    std::printf("传统模型: DescriptorPool -> 分配 DescriptorSet -> vkUpdateDescriptorSets\n");
    std::printf("          -> vkCmdBindDescriptorSets  (每种资源组合都要一套 set/layout)\n");
    std::printf("descriptor_buffer (本 demo 实际用的): 把描述符当数据写进一个 buffer,\n");
    std::printf("          用 vkGetDescriptorEXT 填充, vkCmdBindDescriptorBuffersEXT 绑定。\n");
    std::printf("descriptor_heap (新): 更进一步 —— 一块全局【堆】+ 一张【映射表】,\n");
    std::printf("          shader 里的 set/binding 通过 push 来的整数索引直接定位到堆中资源。\n");
}

void run_descriptor_heap_reference(VkInstance instance,
                                   VkPhysicalDevice phys,
                                   bool supported) {
    printConcept();

    // ---- 1. 查询特性与属性(把扩展结构挂到 pNext;不支持时驱动忽略,字段保持 0)----
    VkPhysicalDeviceDescriptorHeapPropertiesEXT props{
        VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_PROPERTIES_EXT };
    VkPhysicalDeviceProperties2 p2{ VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2 };
    p2.pNext = &props;
    vkGetPhysicalDeviceProperties2(phys, &p2);

    VkPhysicalDeviceDescriptorHeapFeaturesEXT feat{
        VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_HEAP_FEATURES_EXT };
    VkPhysicalDeviceFeatures2 f2{ VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2 };
    f2.pNext = &feat;
    vkGetPhysicalDeviceFeatures2(phys, &f2);

    if (!supported) {
        std::printf("\n[状态] 本机驱动尚未暴露 VK_EXT_descriptor_heap。\n");
        std::printf("       下面只打印它【会怎么写】,实际渲染由 descriptor_buffer 完成。\n");
    } else {
        std::printf("\n[状态] 本机支持 descriptor_heap! 关键属性:\n");
        std::printf("   maxResourceHeapSize     = %llu\n", (unsigned long long)props.maxResourceHeapSize);
        std::printf("   imageDescriptorSize     = %llu\n", (unsigned long long)props.imageDescriptorSize);
        std::printf("   bufferDescriptorSize    = %llu\n", (unsigned long long)props.bufferDescriptorSize);
        std::printf("   samplerDescriptorSize   = %llu\n", (unsigned long long)props.samplerDescriptorSize);
        std::printf("   maxPushDataSize         = %llu\n", (unsigned long long)props.maxPushDataSize);
        std::printf("   feature.descriptorHeap  = %u\n", feat.descriptorHeap);
    }

    // ---- 2. descriptor_heap 的完整工作流(真实类型,带注释)----
    //
    //  步骤 A —— 启用设备特性:
    //     VkPhysicalDeviceDescriptorHeapFeaturesEXT f{...};
    //     f.descriptorHeap = VK_TRUE;      // 挂到 vkCreateDevice 的 pNext
    //
    //  步骤 B —— 查描述符尺寸,算出堆要多大:
    //     VkDeviceSize sz = vkGetPhysicalDeviceDescriptorSizeEXT(
    //                           phys, VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE);
    //     // 资源堆容量 = 资源数量 * 对应描述符尺寸,按 resourceHeapAlignment 对齐
    //
    //  步骤 C —— 创建"资源堆"buffer(注意新的 usage 位):
    //     VkBufferCreateInfo bi{...};
    //     bi.usage = VK_BUFFER_USAGE_DESCRIPTOR_HEAP_BIT_EXT       // <- 堆专用
    //              | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT;
    //     // sampler 用单独的 sampler 堆,机制相同。
    //
    //  步骤 D —— 把资源描述符写进堆(host 端直接写内存):
    {
        VkImageDescriptorInfoEXT imgInfo{ VK_STRUCTURE_TYPE_IMAGE_DESCRIPTOR_INFO_EXT };
        imgInfo.layout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        // imgInfo.pView = &someImageViewCreateInfo;   // 直接给 view 的创建信息

        VkResourceDescriptorInfoEXT res{ VK_STRUCTURE_TYPE_RESOURCE_DESCRIPTOR_INFO_EXT };
        res.type = VK_DESCRIPTOR_TYPE_SAMPLED_IMAGE;
        res.data.pImage = &imgInfo;
        (void)res;
        //  VkHostAddressRangeEXT dst{ heapMappedPtr + i*descSize, descSize };
        //  vkWriteResourceDescriptorsEXT(device, 1, &res, &dst);   // 写第 i 个槽位
        //  采样器: vkWriteSamplerDescriptorsEXT(device, n, pSamplerCreateInfos, pDst);
    }
    //
    //  步骤 E —— 描述"shader 的 set/binding 如何映射到堆"(这是 descriptor_heap 的灵魂):
    {
        VkDescriptorSetAndBindingMappingEXT map{
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_AND_BINDING_MAPPING_EXT };
        map.descriptorSet = 0;
        map.firstBinding  = 0;
        map.bindingCount  = 1;
        map.resourceMask  = VK_SPIRV_RESOURCE_TYPE_SAMPLED_IMAGE_BIT_EXT;
        // 核心:索引从哪里来? 这里选"从 push 来的索引访问堆":
        map.source = VK_DESCRIPTOR_MAPPING_SOURCE_HEAP_WITH_PUSH_INDEX_EXT;
        map.sourceData.pushIndex.heapOffset      = 0;
        map.sourceData.pushIndex.pushOffset      = 0;   // push 数据里第 0 字节就是索引
        map.sourceData.pushIndex.heapIndexStride = 1;
        (void)map;

        // VkShaderDescriptorSetAndBindingMappingInfoEXT mi{...};
        // mi.mappingCount = 1; mi.pMappings = &map;
        // -> 挂到 VkShaderCreateInfoEXT / pipeline 的 pNext,告诉驱动如何解释 shader 的资源访问。
    }
    //
    //  步骤 F —— 录制命令:绑定堆 + push 索引,然后正常 draw:
    //     VkBindHeapInfoEXT bh{ VK_STRUCTURE_TYPE_BIND_HEAP_INFO_EXT };
    //     bh.heapRange = { resourceHeapAddr, heapSize };
    //     vkCmdBindResourceHeapEXT(cmd, &bh);          // 绑定整块堆(整帧一次)
    //
    //     uint32_t index = currentScene;               // 我们要访问的堆槽位
    //     VkPushDataInfoEXT pd{ VK_STRUCTURE_TYPE_PUSH_DATA_INFO_EXT };
    //     pd.offset = 0;  pd.data = { &index, sizeof(index) };
    //     vkCmdPushDataEXT(cmd, &pd);                   // 把索引推给 shader
    //     vkCmdDraw(cmd, 3, 1, 0, 0);
    //
    //  对照 main.cpp:descriptor_buffer 用 vkCmdBindDescriptorBuffersEXT +
    //  vkCmdSetDescriptorBufferOffsetsEXT + vkCmdPushConstants 达到几乎一样的效果。
    //  descriptor_heap 把"绑定+偏移"统一成"绑定整块堆 + push 索引",更接近 D3D12,
    //  也更利于一帧内无缝切换海量资源(真正的 bindless)。

    std::printf("(以上工作流见 descriptor_heap_reference.cpp 注释:堆 -> 写描述符 -> 映射 -> push 索引)\n");
    std::printf("----------------------------------------------------------------------\n");
}
