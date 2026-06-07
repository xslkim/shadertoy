// =============================================================================
//  VK_EXT_descriptor_heap 教学 demo —— 可运行的"双路径"程序
//
//  画面:shadertoy 风格的 SDF raymarching,在多个"场景"之间连续 morph。
//  机制:所有场景参数放进一个【描述符数组 / 堆】,CPU 每帧只 push 一个索引,
//        shader 按索引从堆里取资源。这就是 bindless / descriptor heap 的核心。
//
//  本可执行文件用 VK_EXT_descriptor_buffer 实现真实渲染(你的 GPU 当前支持它);
//  descriptor_heap 的等价 API 在 descriptor_heap_reference.cpp 中并排展示,
//  并在启动时打印它在本机的支持状态。两者心智模型几乎一致。
// =============================================================================
#include "vk_demo.h"
#include <windows.h>
#include <vector>
#include <string>
#include <chrono>
#include <cstring>
#include <cmath>

// ----------------------------- 配置 -----------------------------
static const uint32_t kSceneCount = 6;      // 堆里放 6 个场景
static const wchar_t*  kWndClass   = L"VkDescHeapDemo";
static uint32_t kWidth  = 1280;
static uint32_t kHeight = 720;

// 与 shader 中的 push_constant 完全对应
struct PushConstants {
    float    iResolution[2];
    float    iTime;
    uint32_t sceneA;
    uint32_t sceneB;
    float    blend;
    uint32_t sceneCount;
};

// 与 shader 中 SceneParams (std140) 对应,大小 64 字节
struct SceneParams {
    float palA[4];
    float palB[4];
    float bg[4];
    float cfg[4];   // x=shape y=scale z=spin w=glow
};

// ----------------------------- 全局状态 -----------------------------
struct App {
    HWND hwnd = nullptr;
    bool running = true;
    bool resized = false;

    VkInstance instance = VK_NULL_HANDLE;
    VkSurfaceKHR surface = VK_NULL_HANDLE;
    VkPhysicalDevice phys = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    uint32_t queueFamily = 0;
    VkQueue queue = VK_NULL_HANDLE;

    VkSwapchainKHR swapchain = VK_NULL_HANDLE;
    VkFormat swapFormat = VK_FORMAT_B8G8R8A8_UNORM;
    VkExtent2D swapExtent{};
    std::vector<VkImage> swapImages;
    std::vector<VkImageView> swapViews;
    std::vector<VkFramebuffer> framebuffers;
    VkRenderPass renderPass = VK_NULL_HANDLE;

    VkDescriptorSetLayout setLayout = VK_NULL_HANDLE;
    VkPipelineLayout pipeLayout = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;

    // 场景数据(被描述符指向的真实资源)
    VkBuffer sceneBuf = VK_NULL_HANDLE;
    VkDeviceMemory sceneMem = VK_NULL_HANDLE;
    VkDeviceAddress sceneAddr = 0;
    VkDeviceSize sceneStride = 0;

    // 描述符缓冲(= 堆)
    VkBuffer descBuf = VK_NULL_HANDLE;
    VkDeviceMemory descMem = VK_NULL_HANDLE;
    VkDeviceAddress descAddr = 0;
    VkDeviceSize layoutSize = 0;
    VkDeviceSize bindingOffset = 0;
    VkDeviceSize uboDescSize = 0;

    // 每帧资源
    VkCommandPool cmdPool = VK_NULL_HANDLE;
    VkCommandBuffer cmd = VK_NULL_HANDLE;
    VkSemaphore semAcquire = VK_NULL_HANDLE;
    VkSemaphore semRender = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;

    VkPhysicalDeviceDescriptorBufferPropertiesEXT dbProps{};

    // descriptor_buffer 扩展函数指针(需 vkGetDeviceProcAddr 加载)
    PFN_vkGetDescriptorSetLayoutSizeEXT          pGetLayoutSize = nullptr;
    PFN_vkGetDescriptorSetLayoutBindingOffsetEXT pGetBindingOffset = nullptr;
    PFN_vkGetDescriptorEXT                       pGetDescriptor = nullptr;
    PFN_vkCmdBindDescriptorBuffersEXT            pCmdBindDescBuffers = nullptr;
    PFN_vkCmdSetDescriptorBufferOffsetsEXT       pCmdSetDescOffsets = nullptr;
};
static App g;

// ----------------------------- 工具 -----------------------------
static std::vector<char> readFile(const std::string& path) {
    FILE* f = nullptr;
    fopen_s(&f, path.c_str(), "rb");
    if (!f) { std::fprintf(stderr, "无法打开 %s\n", path.c_str()); std::abort(); }
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    std::vector<char> buf(n);
    fread(buf.data(), 1, n, f); fclose(f);
    return buf;
}

static uint32_t findMemoryType(uint32_t typeBits, VkMemoryPropertyFlags props) {
    VkPhysicalDeviceMemoryProperties mp;
    vkGetPhysicalDeviceMemoryProperties(g.phys, &mp);
    for (uint32_t i = 0; i < mp.memoryTypeCount; ++i)
        if ((typeBits & (1u << i)) && (mp.memoryTypes[i].propertyFlags & props) == props)
            return i;
    std::fprintf(stderr, "找不到合适内存类型\n"); std::abort();
}

// 创建 host-visible、带 device address 的 buffer
static void createBuffer(VkDeviceSize size, VkBufferUsageFlags usage,
                         VkBuffer& buf, VkDeviceMemory& mem, VkDeviceAddress& addr) {
    VkBufferCreateInfo bi{ VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO };
    bi.size = size;
    bi.usage = usage | VK_BUFFER_USAGE_SHADER_DEVICE_ADDRESS_BIT;
    bi.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    VK_CHECK(vkCreateBuffer(g.device, &bi, nullptr, &buf));

    VkMemoryRequirements mr;
    vkGetBufferMemoryRequirements(g.device, buf, &mr);

    VkMemoryAllocateFlagsInfo fi{ VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_FLAGS_INFO };
    fi.flags = VK_MEMORY_ALLOCATE_DEVICE_ADDRESS_BIT;

    VkMemoryAllocateInfo ai{ VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
    ai.pNext = &fi;
    ai.allocationSize = mr.size;
    ai.memoryTypeIndex = findMemoryType(mr.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    VK_CHECK(vkAllocateMemory(g.device, &ai, nullptr, &mem));
    VK_CHECK(vkBindBufferMemory(g.device, buf, mem, 0));

    VkBufferDeviceAddressInfo dai{ VK_STRUCTURE_TYPE_BUFFER_DEVICE_ADDRESS_INFO };
    dai.buffer = buf;
    addr = vkGetBufferDeviceAddress(g.device, &dai);
}

static VkShaderModule loadShader(const std::string& file) {
    auto code = readFile(std::string(SHADER_DIR) + "/" + file);
    VkShaderModuleCreateInfo ci{ VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO };
    ci.codeSize = code.size();
    ci.pCode = reinterpret_cast<const uint32_t*>(code.data());
    VkShaderModule m;
    VK_CHECK(vkCreateShaderModule(g.device, &ci, nullptr, &m));
    return m;
}

// ----------------------------- Win32 -----------------------------
static LRESULT CALLBACK WndProc(HWND h, UINT msg, WPARAM w, LPARAM l) {
    switch (msg) {
    case WM_CLOSE: case WM_DESTROY: g.running = false; PostQuitMessage(0); return 0;
    case WM_SIZE:
        if (w != SIZE_MINIMIZED) { kWidth = LOWORD(l); kHeight = HIWORD(l); g.resized = true; }
        return 0;
    case WM_KEYDOWN:
        if (w == VK_ESCAPE) { g.running = false; PostQuitMessage(0); }
        return 0;
    }
    return DefWindowProc(h, msg, w, l);
}

static void createWindow() {
    HINSTANCE hi = GetModuleHandle(nullptr);
    WNDCLASSEX wc{ sizeof(wc) };
    wc.style = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hi;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.lpszClassName = kWndClass;
    RegisterClassEx(&wc);

    RECT r{ 0, 0, (LONG)kWidth, (LONG)kHeight };
    AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
    g.hwnd = CreateWindowEx(0, kWndClass,
        L"VK_EXT_descriptor_heap demo  (descriptor_buffer 实现 · ESC 退出)",
        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT,
        r.right - r.left, r.bottom - r.top, nullptr, nullptr, hi, nullptr);
    ShowWindow(g.hwnd, SW_SHOW);
}

// ----------------------------- Vulkan 初始化 -----------------------------
static void createInstance() {
    VkApplicationInfo app{ VK_STRUCTURE_TYPE_APPLICATION_INFO };
    app.pApplicationName = "vk_descriptor_heap_demo";
    app.apiVersion = VK_API_VERSION_1_3;

    const char* exts[] = { VK_KHR_SURFACE_EXTENSION_NAME,
                           VK_KHR_WIN32_SURFACE_EXTENSION_NAME };
    VkInstanceCreateInfo ci{ VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO };
    ci.pApplicationInfo = &app;
    ci.enabledExtensionCount = 2;
    ci.ppEnabledExtensionNames = exts;
    VK_CHECK(vkCreateInstance(&ci, nullptr, &g.instance));

    VkWin32SurfaceCreateInfoKHR si{ VK_STRUCTURE_TYPE_WIN32_SURFACE_CREATE_INFO_KHR };
    si.hinstance = GetModuleHandle(nullptr);
    si.hwnd = g.hwnd;
    VK_CHECK(vkCreateWin32SurfaceKHR(g.instance, &si, nullptr, &g.surface));
}

static bool deviceHasExtension(VkPhysicalDevice p, const char* name) {
    uint32_t n = 0;
    vkEnumerateDeviceExtensionProperties(p, nullptr, &n, nullptr);
    std::vector<VkExtensionProperties> props(n);
    vkEnumerateDeviceExtensionProperties(p, nullptr, &n, props.data());
    for (auto& e : props) if (std::strcmp(e.extensionName, name) == 0) return true;
    return false;
}

static void pickPhysicalDevice(bool& descHeapSupported) {
    uint32_t n = 0;
    vkEnumeratePhysicalDevices(g.instance, &n, nullptr);
    std::vector<VkPhysicalDevice> devs(n);
    vkEnumeratePhysicalDevices(g.instance, &n, devs.data());

    for (auto d : devs) {
        if (!deviceHasExtension(d, VK_EXT_DESCRIPTOR_BUFFER_EXTENSION_NAME)) continue;
        if (!deviceHasExtension(d, VK_KHR_SWAPCHAIN_EXTENSION_NAME)) continue;
        // 找到一个图形+呈现队列
        uint32_t qn = 0;
        vkGetPhysicalDeviceQueueFamilyProperties(d, &qn, nullptr);
        std::vector<VkQueueFamilyProperties> qp(qn);
        vkGetPhysicalDeviceQueueFamilyProperties(d, &qn, qp.data());
        for (uint32_t i = 0; i < qn; ++i) {
            VkBool32 present = VK_FALSE;
            vkGetPhysicalDeviceSurfaceSupportKHR(d, i, g.surface, &present);
            if ((qp[i].queueFlags & VK_QUEUE_GRAPHICS_BIT) && present) {
                g.phys = d; g.queueFamily = i; break;
            }
        }
        if (g.phys) break;
    }
    if (!g.phys) { std::fprintf(stderr, "没有支持 descriptor_buffer 的设备\n"); std::abort(); }

    VkPhysicalDeviceProperties pp;
    vkGetPhysicalDeviceProperties(g.phys, &pp);
    descHeapSupported = deviceHasExtension(g.phys, VK_EXT_DESCRIPTOR_HEAP_EXTENSION_NAME);

    std::printf("==========================================================\n");
    std::printf(" GPU                : %s\n", pp.deviceName);
    std::printf(" VK_EXT_descriptor_buffer : 支持 (本 demo 用它渲染)\n");
    std::printf(" VK_EXT_descriptor_heap   : %s\n",
        descHeapSupported ? "支持!" : "当前驱动【不支持】(用 descriptor_buffer 演示等价机制)");
    std::printf("==========================================================\n");
}

static void createDevice() {
    float prio = 1.0f;
    VkDeviceQueueCreateInfo qi{ VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO };
    qi.queueFamilyIndex = g.queueFamily;
    qi.queueCount = 1;
    qi.pQueuePriorities = &prio;

    // 特性链:descriptor_buffer + bufferDeviceAddress + descriptorIndexing(非一致索引)
    VkPhysicalDeviceDescriptorBufferFeaturesEXT dbFeat{ VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_BUFFER_FEATURES_EXT };
    dbFeat.descriptorBuffer = VK_TRUE;

    VkPhysicalDeviceVulkan12Features v12{ VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES };
    v12.bufferDeviceAddress = VK_TRUE;
    v12.runtimeDescriptorArray = VK_TRUE;
    v12.shaderUniformBufferArrayNonUniformIndexing = VK_TRUE;
    v12.descriptorIndexing = VK_TRUE;
    v12.pNext = &dbFeat;

    VkPhysicalDeviceFeatures2 f2{ VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2 };
    f2.pNext = &v12;

    const char* devExts[] = { VK_KHR_SWAPCHAIN_EXTENSION_NAME,
                              VK_EXT_DESCRIPTOR_BUFFER_EXTENSION_NAME };
    VkDeviceCreateInfo ci{ VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO };
    ci.pNext = &f2;
    ci.queueCreateInfoCount = 1;
    ci.pQueueCreateInfos = &qi;
    ci.enabledExtensionCount = 2;
    ci.ppEnabledExtensionNames = devExts;
    VK_CHECK(vkCreateDevice(g.phys, &ci, nullptr, &g.device));
    vkGetDeviceQueue(g.device, g.queueFamily, 0, &g.queue);

    // 加载扩展函数
    g.pGetLayoutSize     = (PFN_vkGetDescriptorSetLayoutSizeEXT)vkGetDeviceProcAddr(g.device, "vkGetDescriptorSetLayoutSizeEXT");
    g.pGetBindingOffset  = (PFN_vkGetDescriptorSetLayoutBindingOffsetEXT)vkGetDeviceProcAddr(g.device, "vkGetDescriptorSetLayoutBindingOffsetEXT");
    g.pGetDescriptor     = (PFN_vkGetDescriptorEXT)vkGetDeviceProcAddr(g.device, "vkGetDescriptorEXT");
    g.pCmdBindDescBuffers= (PFN_vkCmdBindDescriptorBuffersEXT)vkGetDeviceProcAddr(g.device, "vkCmdBindDescriptorBuffersEXT");
    g.pCmdSetDescOffsets = (PFN_vkCmdSetDescriptorBufferOffsetsEXT)vkGetDeviceProcAddr(g.device, "vkCmdSetDescriptorBufferOffsetsEXT");

    // 取 descriptor_buffer 属性(描述符尺寸/对齐)
    g.dbProps.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DESCRIPTOR_BUFFER_PROPERTIES_EXT;
    VkPhysicalDeviceProperties2 p2{ VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2 };
    p2.pNext = &g.dbProps;
    vkGetPhysicalDeviceProperties2(g.phys, &p2);
    g.uboDescSize = g.dbProps.uniformBufferDescriptorSize;
    std::printf(" uniformBufferDescriptorSize = %zu 字节(单个描述符在堆里占的大小)\n",
                (size_t)g.uboDescSize);
}

static void createSwapchain() {
    VkSurfaceCapabilitiesKHR caps;
    vkGetPhysicalDeviceSurfaceCapabilitiesKHR(g.phys, g.surface, &caps);
    g.swapExtent = caps.currentExtent.width != UINT32_MAX
        ? caps.currentExtent : VkExtent2D{ kWidth, kHeight };
    if (g.swapExtent.width == 0 || g.swapExtent.height == 0) return;

    uint32_t imgCount = caps.minImageCount + 1;
    if (caps.maxImageCount && imgCount > caps.maxImageCount) imgCount = caps.maxImageCount;

    VkSwapchainCreateInfoKHR ci{ VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR };
    ci.surface = g.surface;
    ci.minImageCount = imgCount;
    ci.imageFormat = g.swapFormat;
    ci.imageColorSpace = VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;
    ci.imageExtent = g.swapExtent;
    ci.imageArrayLayers = 1;
    ci.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    ci.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
    ci.preTransform = caps.currentTransform;
    ci.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    ci.presentMode = VK_PRESENT_MODE_FIFO_KHR;
    ci.clipped = VK_TRUE;
    VK_CHECK(vkCreateSwapchainKHR(g.device, &ci, nullptr, &g.swapchain));

    uint32_t n = 0;
    vkGetSwapchainImagesKHR(g.device, g.swapchain, &n, nullptr);
    g.swapImages.resize(n);
    vkGetSwapchainImagesKHR(g.device, g.swapchain, &n, g.swapImages.data());

    g.swapViews.resize(n);
    for (uint32_t i = 0; i < n; ++i) {
        VkImageViewCreateInfo vi{ VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO };
        vi.image = g.swapImages[i];
        vi.viewType = VK_IMAGE_VIEW_TYPE_2D;
        vi.format = g.swapFormat;
        vi.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 };
        VK_CHECK(vkCreateImageView(g.device, &vi, nullptr, &g.swapViews[i]));
    }
}

static void createRenderPass() {
    VkAttachmentDescription color{};
    color.format = g.swapFormat;
    color.samples = VK_SAMPLE_COUNT_1_BIT;
    color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    color.finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;

    VkAttachmentReference ref{ 0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
    VkSubpassDescription sub{};
    sub.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    sub.colorAttachmentCount = 1;
    sub.pColorAttachments = &ref;

    VkSubpassDependency dep{};
    dep.srcSubpass = VK_SUBPASS_EXTERNAL;
    dep.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dep.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dep.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo ci{ VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO };
    ci.attachmentCount = 1; ci.pAttachments = &color;
    ci.subpassCount = 1; ci.pSubpasses = &sub;
    ci.dependencyCount = 1; ci.pDependencies = &dep;
    VK_CHECK(vkCreateRenderPass(g.device, &ci, nullptr, &g.renderPass));
}

static void createFramebuffers() {
    g.framebuffers.resize(g.swapViews.size());
    for (size_t i = 0; i < g.swapViews.size(); ++i) {
        VkFramebufferCreateInfo fi{ VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO };
        fi.renderPass = g.renderPass;
        fi.attachmentCount = 1;
        fi.pAttachments = &g.swapViews[i];
        fi.width = g.swapExtent.width;
        fi.height = g.swapExtent.height;
        fi.layers = 1;
        VK_CHECK(vkCreateFramebuffer(g.device, &fi, nullptr, &g.framebuffers[i]));
    }
}

static void createPipeline() {
    // 描述符集布局:binding 0 = uniform buffer 数组(kSceneCount 个),片元阶段。
    // 关键:带 DESCRIPTOR_BUFFER_BIT —— 这个 layout 走 descriptor_buffer 路径。
    VkDescriptorSetLayoutBinding b{};
    b.binding = 0;
    b.descriptorType = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
    b.descriptorCount = kSceneCount;
    b.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;

    VkDescriptorSetLayoutCreateInfo li{ VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO };
    li.flags = VK_DESCRIPTOR_SET_LAYOUT_CREATE_DESCRIPTOR_BUFFER_BIT_EXT;
    li.bindingCount = 1;
    li.pBindings = &b;
    VK_CHECK(vkCreateDescriptorSetLayout(g.device, &li, nullptr, &g.setLayout));

    VkPushConstantRange pc{};
    pc.stageFlags = VK_SHADER_STAGE_FRAGMENT_BIT;
    pc.offset = 0;
    pc.size = sizeof(PushConstants);

    VkPipelineLayoutCreateInfo pli{ VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO };
    pli.setLayoutCount = 1;
    pli.pSetLayouts = &g.setLayout;
    pli.pushConstantRangeCount = 1;
    pli.pPushConstantRanges = &pc;
    VK_CHECK(vkCreatePipelineLayout(g.device, &pli, nullptr, &g.pipeLayout));

    VkShaderModule vs = loadShader("fullscreen.vert.spv");
    VkShaderModule fs = loadShader("sdf_bindless.frag.spv");
    VkPipelineShaderStageCreateInfo stages[2]{};
    stages[0] = { VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO };
    stages[0].stage = VK_SHADER_STAGE_VERTEX_BIT;
    stages[0].module = vs; stages[0].pName = "main";
    stages[1] = { VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO };
    stages[1].stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    stages[1].module = fs; stages[1].pName = "main";

    VkPipelineVertexInputStateCreateInfo vin{ VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO };
    VkPipelineInputAssemblyStateCreateInfo ia{ VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO };
    ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

    VkPipelineViewportStateCreateInfo vp{ VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO };
    vp.viewportCount = 1; vp.scissorCount = 1;

    VkPipelineRasterizationStateCreateInfo rs{ VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO };
    rs.polygonMode = VK_POLYGON_MODE_FILL;
    rs.cullMode = VK_CULL_MODE_NONE;
    rs.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    rs.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo ms{ VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO };
    ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

    VkPipelineColorBlendAttachmentState cba{};
    cba.colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                         VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
    VkPipelineColorBlendStateCreateInfo cb{ VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO };
    cb.attachmentCount = 1; cb.pAttachments = &cba;

    VkDynamicState dyn[] = { VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR };
    VkPipelineDynamicStateCreateInfo ds{ VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO };
    ds.dynamicStateCount = 2; ds.pDynamicStates = dyn;

    VkGraphicsPipelineCreateInfo gi{ VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO };
    gi.flags = VK_PIPELINE_CREATE_DESCRIPTOR_BUFFER_BIT_EXT;  // 关键:声明用 descriptor buffer
    gi.stageCount = 2; gi.pStages = stages;
    gi.pVertexInputState = &vin;
    gi.pInputAssemblyState = &ia;
    gi.pViewportState = &vp;
    gi.pRasterizationState = &rs;
    gi.pMultisampleState = &ms;
    gi.pColorBlendState = &cb;
    gi.pDynamicState = &ds;
    gi.layout = g.pipeLayout;
    gi.renderPass = g.renderPass;
    VK_CHECK(vkCreateGraphicsPipelines(g.device, VK_NULL_HANDLE, 1, &gi, nullptr, &g.pipeline));

    vkDestroyShaderModule(g.device, vs, nullptr);
    vkDestroyShaderModule(g.device, fs, nullptr);
}

static VkDeviceSize alignUp(VkDeviceSize v, VkDeviceSize a) {
    return a ? ((v + a - 1) / a) * a : v;
}

// 由时间算出"当前要按索引访问哪个场景"(drawFrame 与离屏截图共用)
static PushConstants computePush(float time, uint32_t w, uint32_t h) {
    float cycle = time * 0.35f;
    uint32_t a = (uint32_t)cycle % kSceneCount;
    float blend = cycle - std::floor(cycle);
    blend = blend * blend * (3.0f - 2.0f * blend);   // smoothstep
    PushConstants pc{};
    pc.iResolution[0] = (float)w; pc.iResolution[1] = (float)h;
    pc.iTime = time;
    pc.sceneA = a;
    pc.sceneB = (a + 1) % kSceneCount;
    pc.blend = blend;
    pc.sceneCount = kSceneCount;
    return pc;
}

static void createSceneData() {
    // 6 个场景:不同形状 + 不同调色板
    SceneParams scenes[kSceneCount] = {
        // palA, palB, bg, cfg{shape,scale,spin,glow}
        {{0.95f,0.35f,0.20f,1},{1.0f,0.85f,0.30f,1},{0.05f,0.02f,0.08f,1},{0,1.0f,0.6f,0.6f}},
        {{0.20f,0.65f,0.95f,1},{0.55f,0.95f,1.0f,1},{0.02f,0.05f,0.10f,1},{1,0.9f,0.9f,0.4f}},
        {{0.85f,0.25f,0.75f,1},{0.45f,0.20f,0.95f,1},{0.08f,0.02f,0.10f,1},{2,1.0f,-0.7f,0.7f}},
        {{0.30f,0.95f,0.55f,1},{0.85f,1.0f,0.40f,1},{0.02f,0.08f,0.05f,1},{3,1.1f,0.8f,0.5f}},
        {{1.0f,0.55f,0.15f,1},{1.0f,0.20f,0.35f,1},{0.10f,0.03f,0.02f,1},{0,0.8f,1.2f,0.9f}},
        {{0.55f,0.60f,0.95f,1},{0.95f,0.95f,1.0f,1},{0.06f,0.06f,0.12f,1},{2,0.9f,1.0f,0.6f}},
    };

    VkPhysicalDeviceProperties pp;
    vkGetPhysicalDeviceProperties(g.phys, &pp);
    g.sceneStride = alignUp(sizeof(SceneParams), pp.limits.minUniformBufferOffsetAlignment);

    VkDeviceSize total = g.sceneStride * kSceneCount;
    createBuffer(total, VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, g.sceneBuf, g.sceneMem, g.sceneAddr);

    void* map = nullptr;
    VK_CHECK(vkMapMemory(g.device, g.sceneMem, 0, total, 0, &map));
    for (uint32_t i = 0; i < kSceneCount; ++i)
        std::memcpy((char*)map + i * g.sceneStride, &scenes[i], sizeof(SceneParams));
    vkUnmapMemory(g.device, g.sceneMem);
}

// 把 6 个 uniform buffer 描述符写进"堆"(descriptor buffer)
static void createDescriptorBuffer() {
    g.pGetLayoutSize(g.device, g.setLayout, &g.layoutSize);
    g.pGetBindingOffset(g.device, g.setLayout, 0, &g.bindingOffset);
    g.layoutSize = alignUp(g.layoutSize, g.dbProps.descriptorBufferOffsetAlignment);

    std::printf(" 描述符集布局大小 = %zu 字节,binding0 偏移 = %zu\n",
                (size_t)g.layoutSize, (size_t)g.bindingOffset);

    createBuffer(g.layoutSize,
        VK_BUFFER_USAGE_RESOURCE_DESCRIPTOR_BUFFER_BIT_EXT,
        g.descBuf, g.descMem, g.descAddr);

    char* map = nullptr;
    VK_CHECK(vkMapMemory(g.device, g.descMem, 0, g.layoutSize, 0, (void**)&map));

    // 逐个场景:取得 uniform buffer 描述符,写到 堆基址 + binding偏移 + i*描述符尺寸
    for (uint32_t i = 0; i < kSceneCount; ++i) {
        VkDescriptorAddressInfoEXT addr{ VK_STRUCTURE_TYPE_DESCRIPTOR_ADDRESS_INFO_EXT };
        addr.address = g.sceneAddr + (VkDeviceAddress)i * g.sceneStride;
        addr.range = sizeof(SceneParams);
        addr.format = VK_FORMAT_UNDEFINED;

        VkDescriptorGetInfoEXT gi{ VK_STRUCTURE_TYPE_DESCRIPTOR_GET_INFO_EXT };
        gi.type = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        gi.data.pUniformBuffer = &addr;

        char* dst = map + g.bindingOffset + (VkDeviceSize)i * g.uboDescSize;
        g.pGetDescriptor(g.device, &gi, g.uboDescSize, dst);
    }
    vkUnmapMemory(g.device, g.descMem);
    std::printf(" 已把 %u 个 uniform 描述符写入堆。运行时只 push 索引即可访问。\n", kSceneCount);
}

static void createFrameResources() {
    VkCommandPoolCreateInfo pi{ VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO };
    pi.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    pi.queueFamilyIndex = g.queueFamily;
    VK_CHECK(vkCreateCommandPool(g.device, &pi, nullptr, &g.cmdPool));

    VkCommandBufferAllocateInfo ai{ VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO };
    ai.commandPool = g.cmdPool;
    ai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    ai.commandBufferCount = 1;
    VK_CHECK(vkAllocateCommandBuffers(g.device, &ai, &g.cmd));

    VkSemaphoreCreateInfo si{ VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO };
    VK_CHECK(vkCreateSemaphore(g.device, &si, nullptr, &g.semAcquire));
    VK_CHECK(vkCreateSemaphore(g.device, &si, nullptr, &g.semRender));
    VkFenceCreateInfo fi{ VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
    fi.flags = VK_FENCE_CREATE_SIGNALED_BIT;
    VK_CHECK(vkCreateFence(g.device, &fi, nullptr, &g.fence));
}

static void destroySwapchain() {
    for (auto fb : g.framebuffers) vkDestroyFramebuffer(g.device, fb, nullptr);
    for (auto v : g.swapViews) vkDestroyImageView(g.device, v, nullptr);
    g.framebuffers.clear(); g.swapViews.clear();
    if (g.swapchain) vkDestroySwapchainKHR(g.device, g.swapchain, nullptr);
    g.swapchain = VK_NULL_HANDLE;
}

static void recreateSwapchain() {
    vkDeviceWaitIdle(g.device);
    destroySwapchain();
    createSwapchain();
    if (!g.swapchain) return;
    createFramebuffers();
}

// ----------------------------- 每帧绘制 -----------------------------
static void drawFrame(float time) {
    if (!g.swapchain) { recreateSwapchain(); if (!g.swapchain) return; }

    vkWaitForFences(g.device, 1, &g.fence, VK_TRUE, UINT64_MAX);

    uint32_t idx = 0;
    VkResult acq = vkAcquireNextImageKHR(g.device, g.swapchain, UINT64_MAX,
                                         g.semAcquire, VK_NULL_HANDLE, &idx);
    if (acq == VK_ERROR_OUT_OF_DATE_KHR) { recreateSwapchain(); return; }

    vkResetFences(g.device, 1, &g.fence);
    vkResetCommandBuffer(g.cmd, 0);

    VkCommandBufferBeginInfo bi{ VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkBeginCommandBuffer(g.cmd, &bi);

    VkClearValue clear{}; clear.color = { {0.0f, 0.0f, 0.0f, 1.0f} };
    VkRenderPassBeginInfo rp{ VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO };
    rp.renderPass = g.renderPass;
    rp.framebuffer = g.framebuffers[idx];
    rp.renderArea.extent = g.swapExtent;
    rp.clearValueCount = 1; rp.pClearValues = &clear;
    vkCmdBeginRenderPass(g.cmd, &rp, VK_SUBPASS_CONTENTS_INLINE);

    VkViewport vp{ 0, 0, (float)g.swapExtent.width, (float)g.swapExtent.height, 0, 1 };
    VkRect2D sc{ {0,0}, g.swapExtent };
    vkCmdSetViewport(g.cmd, 0, 1, &vp);
    vkCmdSetScissor(g.cmd, 0, 1, &sc);

    vkCmdBindPipeline(g.cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, g.pipeline);

    // 绑定"堆"(descriptor buffer)并把 offset 设为 0
    VkDescriptorBufferBindingInfoEXT dbb{ VK_STRUCTURE_TYPE_DESCRIPTOR_BUFFER_BINDING_INFO_EXT };
    dbb.address = g.descAddr;
    dbb.usage = VK_BUFFER_USAGE_RESOURCE_DESCRIPTOR_BUFFER_BIT_EXT;
    g.pCmdBindDescBuffers(g.cmd, 1, &dbb);

    uint32_t bufIndex = 0;
    VkDeviceSize setOffset = 0;
    g.pCmdSetDescOffsets(g.cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, g.pipeLayout,
                         0, 1, &bufIndex, &setOffset);

    // 计算当前要"按索引访问"的场景:随时间在 6 个场景间循环 morph
    PushConstants pcv = computePush(time, g.swapExtent.width, g.swapExtent.height);
    vkCmdPushConstants(g.cmd, g.pipeLayout, VK_SHADER_STAGE_FRAGMENT_BIT,
                       0, sizeof(pcv), &pcv);

    vkCmdDraw(g.cmd, 3, 1, 0, 0);   // 全屏三角形
    vkCmdEndRenderPass(g.cmd);
    vkEndCommandBuffer(g.cmd);

    VkPipelineStageFlags wait = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    VkSubmitInfo su{ VK_STRUCTURE_TYPE_SUBMIT_INFO };
    su.waitSemaphoreCount = 1; su.pWaitSemaphores = &g.semAcquire;
    su.pWaitDstStageMask = &wait;
    su.commandBufferCount = 1; su.pCommandBuffers = &g.cmd;
    su.signalSemaphoreCount = 1; su.pSignalSemaphores = &g.semRender;
    VK_CHECK(vkQueueSubmit(g.queue, 1, &su, g.fence));

    VkPresentInfoKHR pr{ VK_STRUCTURE_TYPE_PRESENT_INFO_KHR };
    pr.waitSemaphoreCount = 1; pr.pWaitSemaphores = &g.semRender;
    pr.swapchainCount = 1; pr.pSwapchains = &g.swapchain;
    pr.pImageIndices = &idx;
    VkResult pres = vkQueuePresentKHR(g.queue, &pr);
    if (pres == VK_ERROR_OUT_OF_DATE_KHR || pres == VK_SUBOPTIMAL_KHR || g.resized) {
        g.resized = false; recreateSwapchain();
    }
}

// ----------------------------- 离屏截图(--shot) -----------------------------
// 渲染一帧到离屏 image,拷回 host 内存,写出 32bpp BMP(无需窗口/桌面控制权限)。
static void writeBMP(const char* path, const uint8_t* bgra, uint32_t w, uint32_t h) {
    uint32_t dataSize = w * h * 4;
#pragma pack(push, 1)
    struct { uint16_t bf; uint32_t size; uint16_t r1, r2; uint32_t off; } fh{
        0x4D42, 54 + dataSize, 0, 0, 54 };
    struct { uint32_t size; int32_t w, h; uint16_t planes, bpp; uint32_t comp, img;
             int32_t xr, yr; uint32_t clr, imp; } ih{
        40, (int32_t)w, -(int32_t)h, 1, 32, 0, dataSize, 2835, 2835, 0, 0 };
#pragma pack(pop)
    FILE* f = nullptr; fopen_s(&f, path, "wb");
    if (!f) { std::fprintf(stderr, "无法写入 %s\n", path); return; }
    fwrite(&fh, sizeof(fh), 1, f);
    fwrite(&ih, sizeof(ih), 1, f);
    fwrite(bgra, 1, dataSize, f);
    fclose(f);
}

static void captureScreenshot(const char* path, float time, uint32_t w, uint32_t h) {
    // 离屏 color image,格式与交换链一致 -> 与已有管线/渲染流程兼容
    VkImageCreateInfo ici{ VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO };
    ici.imageType = VK_IMAGE_TYPE_2D;
    ici.format = g.swapFormat;             // B8G8R8A8_UNORM == BMP 的 BGRA 顺序
    ici.extent = { w, h, 1 };
    ici.mipLevels = 1; ici.arrayLayers = 1;
    ici.samples = VK_SAMPLE_COUNT_1_BIT;
    ici.tiling = VK_IMAGE_TILING_OPTIMAL;
    ici.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    VkImage img; VK_CHECK(vkCreateImage(g.device, &ici, nullptr, &img));

    VkMemoryRequirements mr; vkGetImageMemoryRequirements(g.device, img, &mr);
    VkMemoryAllocateInfo mai{ VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
    mai.allocationSize = mr.size;
    mai.memoryTypeIndex = findMemoryType(mr.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    VkDeviceMemory imgMem; VK_CHECK(vkAllocateMemory(g.device, &mai, nullptr, &imgMem));
    VK_CHECK(vkBindImageMemory(g.device, img, imgMem, 0));

    VkImageViewCreateInfo vi{ VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO };
    vi.image = img; vi.viewType = VK_IMAGE_VIEW_TYPE_2D; vi.format = g.swapFormat;
    vi.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 };
    VkImageView view; VK_CHECK(vkCreateImageView(g.device, &vi, nullptr, &view));

    // 离屏渲染通道:finalLayout = TRANSFER_SRC,渲染完直接可拷贝
    VkAttachmentDescription color{};
    color.format = g.swapFormat; color.samples = VK_SAMPLE_COUNT_1_BIT;
    color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR; color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    color.finalLayout = VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
    VkAttachmentReference ref{ 0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
    VkSubpassDescription sub{}; sub.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    sub.colorAttachmentCount = 1; sub.pColorAttachments = &ref;
    VkSubpassDependency dep{};
    dep.srcSubpass = 0; dep.dstSubpass = VK_SUBPASS_EXTERNAL;
    dep.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dep.dstStageMask = VK_PIPELINE_STAGE_TRANSFER_BIT;
    dep.srcAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    dep.dstAccessMask = VK_ACCESS_TRANSFER_READ_BIT;
    VkRenderPassCreateInfo rpi{ VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO };
    rpi.attachmentCount = 1; rpi.pAttachments = &color;
    rpi.subpassCount = 1; rpi.pSubpasses = &sub;
    rpi.dependencyCount = 1; rpi.pDependencies = &dep;
    VkRenderPass rp; VK_CHECK(vkCreateRenderPass(g.device, &rpi, nullptr, &rp));

    VkFramebufferCreateInfo fbi{ VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO };
    fbi.renderPass = rp; fbi.attachmentCount = 1; fbi.pAttachments = &view;
    fbi.width = w; fbi.height = h; fbi.layers = 1;
    VkFramebuffer fb; VK_CHECK(vkCreateFramebuffer(g.device, &fbi, nullptr, &fb));

    // host 可见回读 buffer
    VkBuffer rb; VkDeviceMemory rbMem; VkDeviceAddress rbAddr;
    createBuffer((VkDeviceSize)w * h * 4, VK_BUFFER_USAGE_TRANSFER_DST_BIT, rb, rbMem, rbAddr);

    // 录制:离屏渲染 -> 拷到 buffer
    vkResetCommandBuffer(g.cmd, 0);
    VkCommandBufferBeginInfo bi{ VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    vkBeginCommandBuffer(g.cmd, &bi);

    VkClearValue clear{}; clear.color = { {0,0,0,1} };
    VkRenderPassBeginInfo rb2{ VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO };
    rb2.renderPass = rp; rb2.framebuffer = fb;
    rb2.renderArea.extent = { w, h };
    rb2.clearValueCount = 1; rb2.pClearValues = &clear;
    vkCmdBeginRenderPass(g.cmd, &rb2, VK_SUBPASS_CONTENTS_INLINE);

    VkViewport vp{ 0, 0, (float)w, (float)h, 0, 1 };
    VkRect2D sc{ {0,0}, { w, h } };
    vkCmdSetViewport(g.cmd, 0, 1, &vp);
    vkCmdSetScissor(g.cmd, 0, 1, &sc);
    vkCmdBindPipeline(g.cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, g.pipeline);

    VkDescriptorBufferBindingInfoEXT dbb{ VK_STRUCTURE_TYPE_DESCRIPTOR_BUFFER_BINDING_INFO_EXT };
    dbb.address = g.descAddr;
    dbb.usage = VK_BUFFER_USAGE_RESOURCE_DESCRIPTOR_BUFFER_BIT_EXT;
    g.pCmdBindDescBuffers(g.cmd, 1, &dbb);
    uint32_t bufIndex = 0; VkDeviceSize off = 0;
    g.pCmdSetDescOffsets(g.cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, g.pipeLayout, 0, 1, &bufIndex, &off);

    PushConstants pcv = computePush(time, w, h);
    vkCmdPushConstants(g.cmd, g.pipeLayout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pcv), &pcv);
    vkCmdDraw(g.cmd, 3, 1, 0, 0);
    vkCmdEndRenderPass(g.cmd);

    VkBufferImageCopy region{};
    region.imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 };
    region.imageExtent = { w, h, 1 };
    vkCmdCopyImageToBuffer(g.cmd, img, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, rb, 1, &region);
    vkEndCommandBuffer(g.cmd);

    vkResetFences(g.device, 1, &g.fence);
    VkSubmitInfo su{ VK_STRUCTURE_TYPE_SUBMIT_INFO };
    su.commandBufferCount = 1; su.pCommandBuffers = &g.cmd;
    VK_CHECK(vkQueueSubmit(g.queue, 1, &su, g.fence));
    vkWaitForFences(g.device, 1, &g.fence, VK_TRUE, UINT64_MAX);

    void* map = nullptr;
    VK_CHECK(vkMapMemory(g.device, rbMem, 0, (VkDeviceSize)w * h * 4, 0, &map));
    writeBMP(path, (const uint8_t*)map, w, h);
    vkUnmapMemory(g.device, rbMem);
    std::printf("已写出截图: %s (%ux%u, t=%.2f)\n", path, w, h, time);

    // 清理离屏资源
    vkDestroyBuffer(g.device, rb, nullptr); vkFreeMemory(g.device, rbMem, nullptr);
    vkDestroyFramebuffer(g.device, fb, nullptr);
    vkDestroyRenderPass(g.device, rp, nullptr);
    vkDestroyImageView(g.device, view, nullptr);
    vkDestroyImage(g.device, img, nullptr); vkFreeMemory(g.device, imgMem, nullptr);
}

// ----------------------------- 入口 -----------------------------
int main(int argc, char** argv) {
    SetConsoleOutputCP(CP_UTF8);
    setvbuf(stdout, nullptr, _IONBF, 0);   // 无缓冲,日志即时可见(便于录屏/重定向)
    createWindow();
    createInstance();

    bool descHeapSupported = false;
    pickPhysicalDevice(descHeapSupported);
    createDevice();

    // descriptor_heap 教学参考(打印新扩展 API 形态 / 本机支持状态)
    run_descriptor_heap_reference(g.instance, g.phys, descHeapSupported);

    createSwapchain();
    createRenderPass();
    createFramebuffers();
    createPipeline();
    createSceneData();
    createDescriptorBuffer();
    createFrameResources();

    // --shot 模式:离屏渲染若干帧存成 BMP 后退出(无需窗口可见 / 桌面控制)
    bool shotMode = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--shot") == 0) shotMode = true;
    if (shotMode) {
        std::printf("\n[--shot] 离屏渲染截图中...\n");
        const float times[] = { 1.4f, 2.9f, 4.6f, 6.3f };  // 不同时刻 -> 不同场景/过渡
        char path[260];
        for (int i = 0; i < 4; ++i) {
            std::snprintf(path, sizeof(path), "%s\\..\\..\\video\\shot_%d.bmp", SHADER_DIR, i);
            captureScreenshot(path, times[i], 1280, 720);
        }
        vkDeviceWaitIdle(g.device);
        return 0;
    }

    std::printf("\n开始渲染。窗口里应看到 SDF 形状在 6 个场景间循环 morph。ESC 退出。\n");

    auto start = std::chrono::high_resolution_clock::now();
    MSG msg{};
    while (g.running) {
        while (PeekMessage(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
        if (!g.running) break;
        float t = std::chrono::duration<float>(
            std::chrono::high_resolution_clock::now() - start).count();
        drawFrame(t);
    }

    vkDeviceWaitIdle(g.device);
    // 清理(简洁起见省略部分细粒度销毁,进程退出时由驱动回收)
    destroySwapchain();
    return 0;
}
