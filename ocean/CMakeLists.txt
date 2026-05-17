cmake_minimum_required(VERSION 3.16)
project(shadertoy_ocean LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(glad STATIC third_party/glad/src/gl.c)
target_include_directories(glad PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/third_party/glad/include")

include(FetchContent)
FetchContent_Declare(
  glfw
  GIT_REPOSITORY https://github.com/glfw/glfw.git
  GIT_TAG 3.4
)
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(glfw)

add_executable(shadertoy src/main.cpp)
target_link_libraries(shadertoy PRIVATE glad glfw)

if(WIN32)
  target_link_libraries(shadertoy PRIVATE opengl32)
elseif(APPLE)
  find_library(OPENGL_FRAMEWORK OpenGL REQUIRED)
  target_link_libraries(shadertoy PRIVATE ${OPENGL_FRAMEWORK})
else()
  find_package(OpenGL REQUIRED)
  target_link_libraries(shadertoy PRIVATE OpenGL::GL)
endif()

target_include_directories(shadertoy PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/third_party/glad/include")

add_custom_command(
  TARGET shadertoy POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_SOURCE_DIR}/shader.glsl"
          "$<TARGET_FILE_DIR:shadertoy>/shader.glsl"
  COMMENT "Copy shader.glsl next to executable"
)
