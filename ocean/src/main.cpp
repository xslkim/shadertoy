#include <glad/gl.h>
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

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
    //   shadertoy --capture <frames> <fps> <width> <height> <outfile>
    bool capture = false;
    int capFrames = 360;
    double capFps = 30.0;
    int capWidth = 1920;
    int capHeight = 1080;
    std::string capOut = "capture.raw";
    if (argc >= 2 && std::string(argv[1]) == "--capture") {
        capture = true;
        if (argc >= 3) capFrames = std::atoi(argv[2]);
        if (argc >= 4) capFps = std::atof(argv[3]);
        if (argc >= 5) capWidth = std::atoi(argv[4]);
        if (argc >= 6) capHeight = std::atoi(argv[5]);
        if (argc >= 7) capOut = argv[6];
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
    GLFWwindow* window = glfwCreateWindow(width, height, "Shadertoy Seascape (Ms2SD1)", nullptr, nullptr);
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

    GLint locRes = glGetUniformLocation(prog, "iResolution");
    GLint locTime = glGetUniformLocation(prog, "iTime");
    GLint locFrame = glGetUniformLocation(prog, "iFrame");
    GLint locMouse = glGetUniformLocation(prog, "iMouse");

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
            float t = static_cast<float>(i / capFps);
            glUseProgram(prog);
            glUniform3f(locRes, static_cast<float>(width), static_cast<float>(height), 1.0f);
            glUniform1f(locTime, t);
            glUniform1i(locFrame, i);
            glUniform4f(locMouse, 0.5f * width, 0.5f * height, 0.0f, 0.0f);
            glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
            glClear(GL_COLOR_BUFFER_BIT);
            glDrawArrays(GL_TRIANGLES, 0, 3);
            glFinish();
            glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, buf.data());
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
            mouse.left ? static_cast<float>(mouse.x) : 0.5f * fw;
        const float my =
            mouse.left ? static_cast<float>(h - 1 - mouse.y) : 0.5f * fh;
        const float mz = static_cast<float>(mouse.clickX);
        const float mw = static_cast<float>(h - 1 - mouse.clickY);

        glUseProgram(prog);
        glUniform3f(locRes, fw, fh, 1.0f);
        glUniform1f(locTime, t);
        glUniform1i(locFrame, frame);
        glUniform4f(locMouse, mx, my, mz, mw);

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
