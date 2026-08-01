"""
视觉评审工具（可迁移到任意项目）
================================
把渲染出的 PNG 发给在线视觉大模型，拿回自然语言评审。
默认走字节火山方舟 **Responses API**（doubao-seed-2.0-lite），
OpenAI Responses 兼容，可换任意支持 input_image 的模型。

用法:
    python vision_judge.py <image.png> [--prompt "自定义问句"]
    python vision_judge.py <image.png> --preset tree|grass|flower|scene
    python vision_judge.py <image.png> --image-url "https://.../x.png"   # 直接用公网 URL
    python vision_judge.py <image.png> --config ./vision_config.json --model doubao-seed-2-0-lite-260428

配置解析优先级（从高到低）:
    --config <json>   >   环境变量 VISION_API_KEY / VISION_BASE_URL / VISION_MODEL   >   同目录 vision_config.json

迁移到其他项目:
    复制本文件 + 一个 vision_config.json 即可，无需 pip 依赖（只用标准库 urllib）。
    vision_config.json 示例（方舟 Responses API）:
        {
          "api_key": "<方舟控制台的 UUID 风格 key>",
          "base_url": "https://ark.cn-beijing.volces.com/api/v3",
          "model": "doubao-seed-2-0-lite-260428"
        }
"""
import argparse
import base64
import io
import json
import os
import sys
import urllib.request

try:
    from PIL import Image
except ImportError:
    Image = None

DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision_config.json")

PRESETS = {
    "tree": "这是程序化生成的一棵松树的渲染图。请像技术美术一样评审：1) 树冠密度够不够茂密 2) 针叶的朝向是否符合真实松树(下垂/向外) 3) 树干材质是否像真实树皮 4) 整体轮廓是否像一棵真松树。给出 0-10 分并列出 2-4 条具体改进建议。",
    "grass": "这是程序化生成的草的渲染图。请评审：1) 草叶是否都立着朝上(没有躺倒/朝向错误) 2) 草丛密度 3) 颜色是否自然 4) 整体是否像真实草地。给出 0-10 分并列出具体改进建议。",
    "flower": "这是程序化生成的一朵花的渲染图。请评审：1) 花瓣的形状和数量是否像真花 2) 花朵是否清晰可见、朝向是否自然 3) 花茎和叶子是否自然 4) 整体观感。给出 0-10 分并列出具体改进建议。",
    "scene": "这是一张植被场景渲染图。请评审整体观感是否像真实自然植被场景，指出最明显的 3 个不真实之处，并给改进建议。",
}


def load_config(config_path):
    cfg = {"api_key": "", "base_url": "", "model": "doubao-seed-2-0-lite-260428"}
    if config_path and os.path.exists(config_path):
        cfg.update(json.load(open(config_path, encoding="utf-8")))
    elif os.path.exists(DEFAULT_CONFIG):
        cfg.update(json.load(open(DEFAULT_CONFIG, encoding="utf-8")))
    for env_key, cfg_key in (("VISION_API_KEY", "api_key"),
                             ("VISION_BASE_URL", "base_url"),
                             ("VISION_MODEL", "model")):
        if os.environ.get(env_key):
            cfg[cfg_key] = os.environ[env_key]
    return cfg


def image_to_data_uri(path, max_side=1024):
    """本地图片 -> data URI。超过 max_side 先等比缩小，控制请求体大小。"""
    mime = "image/png"
    if Image is not None:
        img = Image.open(path)
        img = img.convert("RGB")
        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)
        buf = io.BytesIO()
        if os.path.splitext(path)[1].lower() in (".jpg", ".jpeg"):
            img.save(buf, format="JPEG", quality=88)
            mime = "image/jpeg"
        else:
            img.save(buf, format="PNG")
        data = buf.getvalue()
    else:
        data = open(path, "rb").read()
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def call_vision(cfg, image_url, prompt):
    base_url = cfg["base_url"].rstrip("/")
    url = base_url + "/responses"
    payload = {
        "model": cfg["model"],
        "input": [{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": image_url},
                {"type": "input_text", "text": prompt},
            ],
        }],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode())
    # Responses API: output[] 里 type=message 的 content[] 里 type=output_text
    texts = []
    for item in body.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    texts.append(c.get("text", ""))
    if texts:
        return "\n".join(texts)
    return json.dumps(body, ensure_ascii=False)[:2000]


def main():
    ap = argparse.ArgumentParser(description="植被渲染视觉评审（火山方舟 Responses API）")
    ap.add_argument("image", nargs="?", help="本地图片路径（用 --image-url 可传公网 URL）")
    ap.add_argument("--image-url", help="直接使用图片公网 URL（跳过本地 base64）")
    ap.add_argument("--prompt", help="自定义评审问句")
    ap.add_argument("--preset", choices=PRESETS.keys(), help="预设评审场景")
    ap.add_argument("--config", default=None, help="vision_config.json 路径")
    ap.add_argument("--model", help="覆盖模型名")
    ap.add_argument("--base-url", help="覆盖 base_url（不含 /responses）")
    ap.add_argument("--api-key", help="覆盖 api_key")
    args = ap.parse_args()

    if not args.image and not args.image_url:
        print("需要提供本地图片路径或 --image-url", file=sys.stderr)
        return 1

    cfg = load_config(args.config)
    if args.api_key:
        cfg["api_key"] = args.api_key
    if args.base_url:
        cfg["base_url"] = args.base_url
    if args.model:
        cfg["model"] = args.model

    if not cfg["api_key"] or not cfg["base_url"]:
        print("缺少 api_key / base_url。请在 vision_config.json 或环境变量设置。", file=sys.stderr)
        return 1

    image_url = args.image_url or image_to_data_uri(args.image)
    prompt = args.prompt or PRESETS.get(args.preset, PRESETS["scene"])
    print(f"[vision] model={cfg['model']} url={cfg['base_url']}/responses")
    try:
        result = call_vision(cfg, image_url, prompt)
        print(result)
        return 0
    except Exception as e:
        print(f"[vision] 调用失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
