"""
Blender MCP Socket Client
=========================
直接连接 BlenderMCP addon 的 socket server (localhost:9876)，
等价于 MCP 协议但更可控（能拿到结构化 JSON 返回）。

用法:
    python blender_client.py ping
    python blender_client.py scene
    python blender_client.py exec-code "import bpy; bpy.ops.mesh.primitive_cube_add()"
    python blender_client.py exec script.py
    python blender_client.py screenshot output.png [max_size]
    python blender_client.py object Cube
    python blender_client.py polyhaven-status
    python blender_client.py raw <command_type> [params_json]

环境变量:
    BLENDER_HOST (默认 localhost)
    BLENDER_PORT (默认 9876)
"""
import sys
import os
import json
import socket
import time
from pathlib import Path

DEFAULT_HOST = os.getenv("BLENDER_HOST", "localhost")
DEFAULT_PORT = int(os.getenv("BLENDER_PORT", "9876"))
TIMEOUT = 180.0  # 与 addon 端一致


def connect(host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=10.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((host, port))
    return sock


def receive_full_response(sock, buffer_size=65536):
    """分块接收直到完整 JSON。复用 blender-mcp server.py 的逻辑。"""
    chunks = []
    sock.settimeout(TIMEOUT)
    while True:
        try:
            chunk = sock.recv(buffer_size)
            if not chunk:
                if not chunks:
                    raise ConnectionError("连接在收到数据前关闭")
                break
            chunks.append(chunk)
            # 尝试解析，成功则返回
            data = b"".join(chunks)
            try:
                json.loads(data.decode("utf-8"))
                return data
            except json.JSONDecodeError:
                continue
        except socket.timeout:
            if chunks:
                data = b"".join(chunks)
                try:
                    json.loads(data.decode("utf-8"))
                    return data
                except json.JSONDecodeError:
                    raise TimeoutError(f"超时且数据不完整，已收 {len(data)} 字节")
            raise TimeoutError("超时，未收到任何数据")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            raise ConnectionError(f"连接错误: {e}")


def send_command(command_type, params=None, host=DEFAULT_HOST, port=DEFAULT_PORT):
    """发送命令到 Blender addon，返回结果 dict。"""
    command = {"type": command_type, "params": params or {}}
    sock = connect(host, port)
    try:
        sock.sendall(json.dumps(command).encode("utf-8"))
        response_data = receive_full_response(sock)
        response = json.loads(response_data.decode("utf-8"))
        if response.get("status") == "error":
            raise RuntimeError(f"Blender 错误: {response.get('message', '未知错误')}")
        return response.get("result", {})
    finally:
        try:
            sock.close()
        except Exception:
            pass


def cmd_ping():
    """测试连接 + 返回场景基本信息。"""
    try:
        result = send_command("get_polyhaven_status")
        print(json.dumps({"connected": True, "polyhaven_status": result}, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"connected": False, "error": str(e)}, ensure_ascii=False, indent=2))
        return 1


def cmd_scene():
    """获取场景信息。"""
    result = send_command("get_scene_info")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_object(name):
    """获取指定对象信息。"""
    result = send_command("get_object_info", {"name": name})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_exec_code(code):
    """执行 Python 代码字符串。"""
    result = send_command("execute_code", {"code": code})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_exec_file(filepath):
    """执行 .py 文件里的代码。"""
    path = Path(filepath)
    if not path.exists():
        print(f"错误: 文件不存在 {filepath}", file=sys.stderr)
        return 1
    code = path.read_text(encoding="utf-8")
    return cmd_exec_code(code)


def cmd_screenshot(output_path, max_size=1000):
    """截图保存到文件。"""
    # 用临时文件让 Blender 写入，再复制到目标
    result = send_command("get_viewport_screenshot", {
        "max_size": int(max_size),
        "filepath": output_path,
        "format": "png"
    })
    if "error" in result:
        print(f"截图失败: {result['error']}", file=sys.stderr)
        return 1
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print(json.dumps({
            "success": True,
            "path": output_path,
            "size_bytes": size,
            "result": result
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"截图命令返回但文件未生成: {result}", file=sys.stderr)
    return 1


def cmd_raw(command_type, params_json=None):
    """发送任意命令。"""
    params = json.loads(params_json) if params_json else {}
    result = send_command(command_type, params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        if cmd == "ping":
            return cmd_ping()
        elif cmd == "scene":
            return cmd_scene()
        elif cmd == "object":
            if not args:
                print("用法: object <name>", file=sys.stderr)
                return 1
            return cmd_object(args[0])
        elif cmd == "exec-code":
            if not args:
                print("用法: exec-code <code_string>", file=sys.stderr)
                return 1
            return cmd_exec_code(args[0])
        elif cmd == "exec":
            if not args:
                print("用法: exec <script.py>", file=sys.stderr)
                return 1
            return cmd_exec_file(args[0])
        elif cmd == "screenshot":
            if not args:
                print("用法: screenshot <output.png> [max_size]", file=sys.stderr)
                return 1
            output = args[0]
            max_size = int(args[1]) if len(args) > 1 else 1000
            return cmd_screenshot(output, max_size)
        elif cmd == "polyhaven-status":
            return cmd_raw("get_polyhaven_status")
        elif cmd == "hyper3d-status":
            return cmd_raw("get_hyper3d_status")
        elif cmd == "raw":
            if not args:
                print("用法: raw <command_type> [params_json]", file=sys.stderr)
                return 1
            return cmd_raw(args[0], args[1] if len(args) > 1 else None)
        else:
            print(f"未知命令: {cmd}", file=sys.stderr)
            print(__doc__)
            return 1
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
