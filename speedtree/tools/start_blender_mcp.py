"""
Blender 启动脚本：自动启用 BlenderMCP addon 并启动 socket server。
用法: blender --python tools\start_blender_mcp.py
(必须用 GUI 模式，不能加 --background)
"""
import bpy
import sys
import os


def start_mcp_server():
    """延迟启动 MCP server，确保 Blender 完全加载。"""
    try:
        # 把 addons 目录加到 sys.path，确保能 import
        addon_dir = os.path.join(bpy.utils.resource_path('USER'), 'scripts', 'addons')
        if addon_dir not in sys.path:
            sys.path.insert(0, addon_dir)

        # 尝试启用 addon（在 preferences 里注册）
        prefs = bpy.context.preferences
        if "blender_mcp" not in prefs.addons:
            try:
                prefs.addons.new(module="blender_mcp")
                prefs.save()
            except Exception as e:
                print(f"[MCP-AUTO] addon enable warning: {e}")

        # 直接 import 并实例化 server（绕过 operator context 限制）
        from blender_mcp import BlenderMCPServer
        server = getattr(bpy.types, 'blendermcp_server', None)
        if server is None:
            bpy.types.blendermcp_server = BlenderMCPServer(port=9876)
            server = bpy.types.blendermcp_server
        if not server.running:
            server.start()
            print("[MCP-AUTO] ✓ BlenderMCP server started on localhost:9876")
        else:
            print("[MCP-AUTO] ✓ Server already running")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[MCP-AUTO] ✗ Failed to start: {e}")
    return None  # 不重复执行


# 延迟 2 秒执行，等 Blender 完全启动
bpy.app.timers.register(start_mcp_server, first_interval=2.0)
print("[MCP-AUTO] Startup script registered, will start server in 2s...")
