cmake_minimum_required(VERSION 3.20)
project(vk_descriptor_heap_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- 定位 Vulkan SDK ----
# 优先用环境变量 VULKAN_SDK;否则回退到本机安装路径。
if(DEFINED ENV{VULKAN_SDK})
    set(VK_SDK "$ENV{VULKAN_SDK}")
else()
    set(VK_SDK "C:/VulkanSDK/1.4.350.0")
endif()
message(STATUS "Using Vulkan SDK: ${VK_SDK}")

find_program(GLSLC glslc HINTS "${VK_SDK}/Bin" REQUIRED)

# ---- 编译 GLSL -> SPIR-V ----
set(SHADER_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/shaders")
set(SHADER_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/shaders")
file(MAKE_DIRECTORY "${SHADER_OUT_DIR}")

set(SHADERS fullscreen.vert sdf_bindless.frag)
set(SPV_FILES "")
foreach(S ${SHADERS})
    set(IN  "${SHADER_SRC_DIR}/${S}")
    set(OUT "${SHADER_OUT_DIR}/${S}.spv")
    add_custom_command(
        OUTPUT "${OUT}"
        COMMAND "${GLSLC}" --target-env=vulkan1.3 -O "${IN}" -o "${OUT}"
        DEPENDS "${IN}"
        COMMENT "glslc: ${S} -> ${S}.spv"
        VERBATIM)
    list(APPEND SPV_FILES "${OUT}")
endforeach()
add_custom_target(shaders ALL DEPENDS ${SPV_FILES})

# ---- 可执行文件 ----
add_executable(vk_demo
    src/main.cpp
    src/descriptor_heap_reference.cpp)
add_dependencies(vk_demo shaders)

target_include_directories(vk_demo PRIVATE "${VK_SDK}/Include")
target_link_directories(vk_demo PRIVATE "${VK_SDK}/Lib")
target_link_libraries(vk_demo PRIVATE vulkan-1)

# 让程序知道 .spv 在哪里(指向 build/shaders)
target_compile_definitions(vk_demo PRIVATE
    SHADER_DIR="${SHADER_OUT_DIR}"
    NOMINMAX
    WIN32_LEAN_AND_MEAN
    VK_USE_PLATFORM_WIN32_KHR
    UNICODE _UNICODE)

if(MSVC)
    # /utf-8 让 MSVC 按 UTF-8 解析源文件(含中文注释),否则会按 GBK 误读导致编译错误
    target_compile_options(vk_demo PRIVATE /W3 /permissive- /utf-8)
endif()
