#include <glad/gl.h>
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {

const char* kVertSrc = R"(#version 330 core
void main() {
    vec2 p = vec2(-1.0 + float((gl_VertexID & 1) << 2), -1.0 + float((gl_VertexID & 2) << 1));
    gl_Position = vec4(p, 0.0, 1.0);
}
)";

const char* kFragHeader = R"(#version 330 core
#define HW_PERFORMANCE 1
uniform vec3 iResolution;
uniform float iTime;
uniform int iFrame;
uniform vec4 iMouse;
uniform sampler2D iChannel0;
)";

const char* kFragFooter = R"(
layout(location = 0) out vec4 outColor;
void main() {
    mainImage(outColor, gl_FragCoord.xy);
}
)";

std::string readFile(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return {};
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

// Loads a raw texture file: first 8 bytes are two little-endian int32 (w, h),
// followed by w*h*3 RGB24 bytes. Returns texture id (0 on failure).
GLuint loadRawTexture(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) {
        std::fprintf(stderr, "Could not open texture: %s\n", path.c_str());
        return 0;
    }
    int32_t w = 0, h = 0;
    f.read(reinterpret_cast<char*>(&w), 4);
    f.read(reinterpret_cast<char*>(&h), 4);
    if (w <= 0 || h <= 0 || w > 16384 || h > 16384) {
        std::fprintf(stderr, "Bad texture dims in %s: %dx%d\n", path.c_str(), w, h);
        return 0;
    }
    std::vector<unsigned char> data(static_cast<size_t>(w) * h * 3);
    f.read(reinterpret_cast<char*>(data.data()), static_cast<std::streamsize>(data.size()));
    if (!f) {
        std::fprintf(stderr, "Texture %s truncated\n", path.c_str());
        return 0;
    }

    GLuint tex = 0;
    glGenTextures(1, &tex);
    glBindTexture(GL_TEXTURE_2D, tex);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    // Shadertoy uploads textures flipped so v=0 is bottom; flip rows here.
    std::vector<unsigned char> flipped(data.size());
    const size_t rowBytes = static_cast<size_t>(w) * 3;
    for (int y = 0; y < h; ++y) {
        std::copy(data.begin() + static_cast<long>((h - 1 - y) * rowBytes),
                  data.begin() + static_cast<long>((h - 1 - y) * rowBytes + rowBytes),
                  flipped.begin() + static_cast<long>(y * rowBytes));
    }
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, flipped.data());
    glGenerateMipmap(GL_TEXTURE_2D);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    std::fprintf(stderr, "Loaded texture %s (%dx%d)\n", path.c_str(), w, h);
    return tex;
}

GLuint compileShader(GLenum type, const char* src) {
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, nullptr);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char buf[4096];
        GLsizei len = 0;
        glGetShaderInfoLog(s, sizeof(buf), &len, buf);
        std::fprintf(stderr, "Shader compile failed:\n%s\n", buf);
        glDeleteShader(s);
        return 0;
    }
    return s;
}

GLuint linkProgram(GLuint vs, GLuint fs) {
    GLuint p = glCreateProgram();
    glAttachShader(p, vs);
    glAttachShader(p, fs);
    glLinkProgram(p);
    GLint ok = 0;
    glGetProgramiv(p, GL_LINK_STATUS, &ok);
    if (!ok) {
        char buf[4096];
        GLsizei len = 0;
        glGetProgramInfoLog(p, sizeof(buf), &len, buf);
        std::fprintf(stderr, "Program link failed:\n%s\n", buf);
        glDeleteProgram(p);
        return 0;
    }
    return p;
}

struct MouseState {
    double x = 0.0;
    double y = 0.0;
    bool left = false;
    double clickX = 0.0;
    double clickY = 0.0;
};

void cursorCallback(GLFWwindow* w, double x, double y) {
    auto* m = static_cast<MouseState*>(glfwGetWindowUserPointer(w));
    m->x = x;
    m->y = y;
}

void mouseButtonCallback(GLFWwindow* w, int button, int action, int) {
    if (button != GLFW_MOUSE_BUTTON_LEFT) return;
    auto* m = static_cast<MouseState*>(glfwGetWindowUserPointer(w));
    if (action == GLFW_PRESS) {
        m->left = true;
        m->clickX = m->x;
        m->clickY = m->y;
    } else if (action == GLFW_RELEASE) {
        m->left = false;
    }
}

}  // namespace

int main(int argc, char** argv) {
    // Offline capture mode: render a fixed sequence of frames as raw RGB24
    // to a file (for encoding into a video clip with ffmpeg).
    //   shadertoy --capture <frames> <fps> <width> <height> <outfile> [startSeconds]
    bool capture = false;
    int capFrames = 360;
    double capFps = 30.0;
    int capWidth = 1920;
    int capHeight = 1080;
    std::string capOut = "capture.raw";
    double capStart = 0.0;  // time (seconds) of the first captured frame
    if (argc >= 2 && std::string(argv[1]) == "--capture") {
        capture = true;
        if (argc >= 3) capFrames = std::atoi(argv[2]);
        if (argc >= 4) capFps = std::atof(argv[3]);
        if (argc >= 5) capWidth = std::atoi(argv[4]);
        if (argc >= 6) capHeight = std::atoi(argv[5]);
        if (argc >= 7) capOut = argv[6];
        if (argc >= 8) capStart = std::atof(argv[7]);
    }

    if (!glfwInit()) {
        std::fprintf(stderr, "glfwInit failed\n");
        return 1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    if (capture) glfwWindowHint(GLFW_VISIBLE, GLFW_FALSE);

    const int width = capture ? capWidth : 1280;
    const int height = capture ? capHeight : 720;
    GLFWwindow* window = glfwCreateWindow(width, height, "Shadertoy Heartfelt (ltffzl)", nullptr, nullptr);
    if (!window) {
        std::fprintf(stderr, "glfwCreateWindow failed\n");
        glfwTerminate();
        return 1;
    }

    MouseState mouse;
    glfwSetWindowUserPointer(window, &mouse);
    glfwSetCursorPosCallback(window, cursorCallback);
    glfwSetMouseButtonCallback(window, mouseButtonCallback);

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    if (!gladLoadGL(glfwGetProcAddress)) {
        std::fprintf(stderr, "gladLoadGL failed\n");
        glfwDestroyWindow(window);
        glfwTerminate();
        return 1;
    }

    std::string userFrag = readFile("shader.glsl");
    if (userFrag.empty()) {
        std::fprintf(stderr, "Could not read shader.glsl (place it next to the executable or cwd)\n");
        glfwDestroyWindow(window);
        glfwTerminate();
        return 1;
    }

    std::string fragFull = std::string(kFragHeader) + userFrag + kFragFooter;

    GLuint vs = compileShader(GL_VERTEX_SHADER, kVertSrc);
    GLuint fs = compileShader(GL_FRAGMENT_SHADER, fragFull.c_str());
    if (!vs || !fs) {
        glfwDestroyWindow(window);
        glfwTerminate();
        return 1;
    }

    GLuint prog = linkProgram(vs, fs);
    glDeleteShader(vs);
    glDeleteShader(fs);
    if (!prog) {
        glfwDestroyWindow(window);
        glfwTerminate();
        return 1;
    }

    GLuint bgTex = loadRawTexture("bg.raw");

    GLint locRes = glGetUniformLocation(prog, "iResolution");
    GLint locTime = glGetUniformLocation(prog, "iTime");
    GLint locFrame = glGetUniformLocation(prog, "iFrame");
    GLint locMouse = glGetUniformLocation(prog, "iMouse");
    GLint locCh0 = glGetUniformLocation(prog, "iChannel0");

    GLuint vao = 0;
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);

    // Offline capture: render the sequence and dump raw RGB24 frames, then exit.
    if (capture) {
        std::ofstream out(capOut, std::ios::binary);
        if (!out) {
            std::fprintf(stderr, "Could not open capture output: %s\n", capOut.c_str());
            return 1;
        }
        std::vector<unsigned char> buf(static_cast<size_t>(width) * height * 3);
        glPixelStorei(GL_PACK_ALIGNMENT, 1);
        glViewport(0, 0, width, height);
        for (int i = 0; i < capFrames; ++i) {
            float t = static_cast<float>(capStart + i / capFps);
            glUseProgram(prog);
            glUniform3f(locRes, static_cast<float>(width), static_cast<float>(height), 1.0f);
            glUniform1f(locTime, t);
            glUniform1i(locFrame, i);
            glUniform4f(locMouse, 0.0f, 0.0f, 0.0f, 0.0f);
            if (bgTex) {
                glActiveTexture(GL_TEXTURE0);
                glBindTexture(GL_TEXTURE_2D, bgTex);
                glUniform1i(locCh0, 0);
            }
            glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
            glClear(GL_COLOR_BUFFER_BIT);
            glDrawArrays(GL_TRIANGLES, 0, 3);
            glFinish();
            glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, buf.data());
            // glReadPixels returns rows bottom-to-top; raw video / ffmpeg expect
            // top-to-bottom, so flip vertically before writing.
            const size_t rb = static_cast<size_t>(width) * 3;
            for (int y = 0; y < height / 2; ++y) {
                std::swap_ranges(buf.begin() + static_cast<long>(y * rb),
                                 buf.begin() + static_cast<long>(y * rb + rb),
                                 buf.begin() + static_cast<long>((height - 1 - y) * rb));
            }
            out.write(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(buf.size()));
            if ((i % 30) == 0) {
                std::fprintf(stderr, "capture %d/%d\n", i, capFrames);
            }
        }
        out.close();
        std::fprintf(stderr, "capture done: %d frames -> %s\n", capFrames, capOut.c_str());
        glDeleteVertexArrays(1, &vao);
        glDeleteProgram(prog);
        glfwDestroyWindow(window);
        glfwTerminate();
        return 0;
    }

    int frame = 0;
    double t0 = glfwGetTime();

    while (!glfwWindowShouldClose(window)) {
        int w = 0, h = 0;
        glfwGetFramebufferSize(window, &w, &h);
        glViewport(0, 0, w, h);

        float t = static_cast<float>(glfwGetTime() - t0);

        const float fw = static_cast<float>(w);
        const float fh = static_cast<float>(h);
        const float mx =
            mouse.left ? static_cast<float>(mouse.x) : 0.0f;
        const float my =
            mouse.left ? static_cast<float>(h - 1 - mouse.y) : 0.0f;
        const float mz = static_cast<float>(mouse.clickX);
        const float mw = static_cast<float>(h - 1 - mouse.clickY);

        glUseProgram(prog);
        glUniform3f(locRes, fw, fh, 1.0f);
        glUniform1f(locTime, t);
        glUniform1i(locFrame, frame);
        glUniform4f(locMouse, mx, my, mz, mw);
        if (bgTex) {
            glActiveTexture(GL_TEXTURE0);
            glBindTexture(GL_TEXTURE_2D, bgTex);
            glUniform1i(locCh0, 0);
        }

        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glDrawArrays(GL_TRIANGLES, 0, 3);

        glfwSwapBuffers(window);
        glfwPollEvents();
        ++frame;
    }

    glDeleteVertexArrays(1, &vao);
    glDeleteProgram(prog);
    glfwDestroyWindow(window);
    glfwTerminate();
    return 0;
}
