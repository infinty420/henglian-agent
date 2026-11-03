@echo off
chcp 65001 >nul
title 衡练 AI 助手 · 网页版 (HTTP)
cd /d "%~dp0"

if not exist .venv (
    echo [首次运行] 创建虚拟环境并安装依赖...
    python -m venv .venv
    call .venv\Scripts\python.exe -m pip install -r requirements.txt
)

if not exist .env (
    echo [警告] 未找到 .env，请先复制 .env.example 为 .env 并填入 DASHSCOPE_API_KEY
)

echo 启动衡练 AI 助手（网页版）：http://localhost:8501
echo 说明：本版为 FastAPI + 原生网页，普通 HTTP 通信，适合部署到不支持 WebSocket 的托管平台。
call .venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8501
