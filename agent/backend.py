# -*- coding: utf-8 -*-
"""
Agent 后端切换器

AGENT_BACKEND 环境变量（见 .env.example）：
  - langgraph（默认）：LangGraph StateGraph ReAct 循环 —— 路径 A 要求项②
  - custom：自研 Tool Calling 循环（openai SDK 直连）—— 便于讲解原理/对照

两种后端共用同一份系统提示词与同一批业务工具实现，行为一致。
"""
import os


def has_api_key() -> bool:
    return bool(os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY"))


def get_model_name() -> str:
    return os.getenv("MODEL_NAME", "qwen-plus")


def get_backend() -> tuple:
    """返回 (run_agent(messages)->(answer, events, updated), 后端显示名)。"""
    backend = os.getenv("AGENT_BACKEND", "langgraph").strip().lower()
    if backend == "langgraph":
        from agent.graph import run_agent
        return run_agent, "LangGraph（StateGraph · 开源框架）"
    from agent.core import get_client, run_agent as _custom_run
    from agent.core import get_model_name as _gm

    def runner(messages):
        return _custom_run(get_client(), messages)

    return runner, "自研循环（openai SDK 直连）"
