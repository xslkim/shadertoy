#include <glad/gl.h>
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

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

int main() {
    if (!glfwInit()) {
        std::fprintf(stderr, "glfwInit failed\n");
        return 1;
    }

    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    const int width = 1280;
    const int height = 720;
    GLFWwindow* window = glfwCreateWindow(width, height, "Shadertoy SDF (fragment only)", nullptr, nullptr);
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
