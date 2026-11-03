# -*- coding: utf-8 -*-
"""
衡练 AI 助手 · FastAPI 网页后端（替代 Streamlit，适配无 WebSocket 的托管网关）

启动：uvicorn server:app --host 0.0.0.0 --port 8501
说明：完全复用 agent/ 下的既有能力（11 个业务工具、LangGraph / 自研循环双后端、
      会话与周报产出），仅替换交互层为普通 HTTP，绕开 CloudStudio Gateway 不转发
      WebSocket 的限制。

接口：
  GET  /                 -> 单页前端 HTML
  GET  /api/config       -> 模型 / 后端 / 密钥状态 / 工具列表 / 端点
  POST /api/chat         -> {message, history} -> {reply, events, history}
  GET  /api/sessions     -> 已保存会话文件名列表
  POST /api/sessions     -> {history} 保存，返回 {filename}
  POST /api/session/load -> {filename} -> {history}
  GET  /healthz          -> 健康检查（兼容网关探针）
"""
import os
import json
import base64
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # 必须在导入 agent 之前加载 .env（密钥/模型/后端开关）

from agent.backend import get_backend, get_model_name, has_api_key
from agent.tools.registry import TOOL_SPECS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

OUTPUT_IMAGES_DIR = os.path.join(BASE_DIR, "output", "images")
os.makedirs(OUTPUT_IMAGES_DIR, exist_ok=True)

app = FastAPI(title="衡练 AI 助手")
runner, BACKEND_NAME = get_backend()

with open(os.path.join(BASE_DIR, "templates", "index.html"), encoding="utf-8") as _f:
    INDEX_HTML = _f.read()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/api/config")
def config() -> dict:
    base_url = os.getenv("OPENAI_BASE_URL",
                         "https://dashscope.aliyuncs.com/compatible-mode/v1")
    try:
        endpoint = base_url.split("//")[1].split("/")[0]
    except Exception:
        endpoint = base_url
    return {
        "model": get_model_name(),
        "backend": BACKEND_NAME,
        "has_api_key": has_api_key(),
        "tools": [s["function"]["name"] for s in TOOL_SPECS],
        "endpoint": endpoint,
    }


class ChatReq(BaseModel):
    message: str
    history: list = []


@app.post("/api/chat")
def chat(req: ChatReq):
    if not has_api_key():
        return JSONResponse(
            {"error": "未配置 API 密钥：请复制 .env.example 为 .env，填入 DASHSCOPE_API_KEY 后重启。"},
            status_code=400,
        )
    # history 为当前 user 消息之前的全部消息；runner 会再追加本轮 user + assistant
    history = list(req.history) + [{"role": "user", "content": req.message}]
    try:
        answer, events, updated = runner(history)
        # 把本轮生成的图片以 data-URI 直接内联进响应，前端无需再请求本地文件/接口
        images = _collect_inline_images(events)
        return {"reply": answer, "events": events, "history": updated, "images": images}
    except Exception as e:  # 失败可解释，避免前端白屏
        return JSONResponse(
            {"error": f"调用失败：{type(e).__name__}: {e}"},
            status_code=500,
        )


_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}


def _collect_inline_images(events: list) -> list:
    """扫描工具事件，把本轮生成的本地图片读成 base64 data-URI，供前端直接内联显示。"""
    out, seen = [], set()
    for ev in (events or []):
        if ev.get("type") == "tool_call":
            continue
        res = (ev.get("result") or {})
        path = res.get("local_path")
        if not path or path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        ext = os.path.splitext(path)[1].lower().lstrip(".") or "png"
        mime = _MIME.get(ext, "image/png")
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except Exception:
            continue
        out.append({"name": os.path.basename(path), "mime": mime, "data": b64})
    return out


@app.get("/api/sessions")
def list_sessions() -> dict:
    files = sorted(
        (f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")),
        reverse=True,
    )
    return {"sessions": files}


class SaveReq(BaseModel):
    history: list = []


@app.post("/api/sessions")
def save_session(req: SaveReq) -> dict:
    fname = f"session_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(os.path.join(SESSIONS_DIR, fname), "w", encoding="utf-8") as f:
        json.dump(req.history, f, ensure_ascii=False, indent=2)
    return {"filename": fname}


class LoadReq(BaseModel):
    filename: str


@app.post("/api/session/load")
def load_session(req: LoadReq):
    fname = os.path.basename(req.filename)  # 防路径穿越
    path = os.path.join(SESSIONS_DIR, fname)
    if not os.path.isfile(path):
        return JSONResponse({"error": "会话不存在"}, status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        history = json.load(f)
    return {"history": history}


@app.get("/healthz")
def healthz() -> dict:
    return {"code": 200, "msg": "ok", "data": "alive"}


@app.get("/images/{filename}")
def serve_image(filename: str):
    """提供 output/images/ 下已生成图片的安全访问（仅按文件名读取，禁止路径穿越）。"""
    safe = os.path.basename(filename)
    path = os.path.join(OUTPUT_IMAGES_DIR, safe)
    if not os.path.isfile(path):
        return JSONResponse({"error": "图片不存在"}, status_code=404)
    return FileResponse(path)


if __name__ == "__main__":
    # 直接 `python server.py` 也可启动；部署时由网关注入 PORT 环境变量。
    import uvicorn

    _port = int(os.getenv("PORT", "8501"))
    uvicorn.run(app, host="0.0.0.0", port=_port)
