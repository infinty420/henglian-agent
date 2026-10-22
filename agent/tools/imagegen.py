# -*- coding: utf-8 -*-
"""
文生图工具（第 11 个业务工具）

调用百炼 DashScope 异步文生图 API（默认 wan2.2-t2i-flash，速度快、有免费额度）：
  ① 提交任务（X-DashScope-Async: enable）→ ② 轮询任务状态 → ③ 下载图片
到项目 output/images/ 目录（延续权限隔离约定：Agent 只能写 output/）。

纯标准库实现（urllib），无需新增依赖。密钥复用 .env 的 DASHSCOPE_API_KEY。
"""
import json
import os
import re
import time
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_IMAGES_DIR = os.path.join(BASE_DIR, "output", "images")

CREATE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

POLL_INTERVAL_S = 2
POLL_MAX_TIMES = 30          # 最多等 60 秒
DEFAULT_MODEL = "wan2.2-t2i-flash"


def get_api_key() -> str:
    return os.getenv("DASHSCOPE_API_KEY", "")


def _safe_filename(filename: str) -> str:
    name = os.path.basename((filename or "").strip())
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    if not name:
        name = f"示意图_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        name += ".png"
    return name


def generate_image(prompt: str, filename: str = "") -> dict:
    """提交文生图任务并等待完成，把图片下载到 output/images/。

    :param prompt: 中文画面描述（建议具体：动作、场景、风格）
    :param filename: 保存文件名（可省略，自动按时间命名）
    """
    key = get_api_key()
    if not key:
        return {"error": "未配置 DASHSCOPE_API_KEY（.env），无法生成图片。"}
    if not prompt or not prompt.strip():
        return {"error": "图片描述 prompt 不能为空。"}

    model = os.getenv("IMAGE_MODEL", DEFAULT_MODEL)

    # ① 提交异步任务
    body = json.dumps({
        "model": model,
        "input": {"prompt": prompt.strip()},
        "parameters": {"size": "1024*1024", "n": 1},
    }).encode("utf-8")
    req = urllib.request.Request(CREATE_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        if e.code in (401, 403):
            return {"error": f"鉴权失败（HTTP {e.code}）：请检查 .env 中的 DASHSCOPE_API_KEY。详情：{detail}"}
        return {"error": f"提交任务失败（HTTP {e.code}）：{detail}"}
    except Exception as e:
        return {"error": f"网络请求失败：{type(e).__name__}: {e}"}

    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        return {"error": f"任务提交异常，响应：{json.dumps(data, ensure_ascii=False)[:300]}"}

    # ② 轮询任务状态
    for _ in range(POLL_MAX_TIMES):
        time.sleep(POLL_INTERVAL_S)
        req = urllib.request.Request(TASK_URL.format(task_id=task_id), headers={
            "Authorization": f"Bearer {key}",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                task = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": f"查询任务状态失败：{type(e).__name__}: {e}"}
        status = (task.get("output") or {}).get("task_status")
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            code = (task.get("output") or {}).get("code", "")
            msg = (task.get("output") or {}).get("message", "")
            hint = "（常见原因：提示词触发内容安全审核，请换一个描述）" if "IPInfringement" in code or "sensitive" in msg.lower() else ""
            return {"error": f"图片生成失败（{status}）{hint}：{code} {msg}"}
    else:
        return {"error": f"生成超时（>{POLL_MAX_TIMES * POLL_INTERVAL_S}s），任务 {task_id} 仍在进行，请稍后重试。"}

    # ③ 下载图片到 output/images/
    results = (task.get("output") or {}).get("results") or []
    if not results or not results[0].get("url"):
        return {"error": f"任务成功但未返回图片地址：{json.dumps(task, ensure_ascii=False)[:300]}"}
    url = results[0]["url"]
    os.makedirs(OUTPUT_IMAGES_DIR, exist_ok=True)
    safe_name = _safe_filename(filename)
    local_path = os.path.join(OUTPUT_IMAGES_DIR, safe_name)
    try:
        urllib.request.urlretrieve(url, local_path)
    except Exception as e:
        return {"error": f"图片下载失败：{type(e).__name__}: {e}；原图地址：{url}"}

    size_kb = round(os.path.getsize(local_path) / 1024, 1)
    return {
        "written": True,
        "local_path": local_path,
        "url": url,
        "file": safe_name,
        "size_kb": size_kb,
        "model": model,
        "message": f"图片已生成并保存到 output/images/{safe_name}（{size_kb} KB）。",
    }
