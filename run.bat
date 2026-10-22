@echo off
chcp 65001 >nul
title 衡练 AI 助手
cd /d "%~dp0"

if not exist .venv (
    echo [首次运行] 创建虚拟环境并安装依赖...
    python -m venv .venv
    call .venv\Scripts\pip install -r requirements.txt
)

if not exist .env (
    echo [警告] 未找到 .env，请先复制 .env.example 为 .env 并填入 DASHSCOPE_API_KEY
)

echo 启动衡练 AI 助手...
call .venv\Scripts\streamlit run app.py
