# -*- coding: utf-8 -*-
"""
路径 A 后端：LangGraph Agent 框架（课程要求项② 开源 Agent 框架）

图结构（经典 ReAct 循环）：
    START → agent(LLM, bind_tools) ──无工具调用──→ END（输出最终回答）
                 │ 有 tool_calls
                 ▼
              tools（ToolNode 执行本地业务工具）──→ 回到 agent

与 agent/core.py 的自研循环共用同一套业务工具（lc_tools 包装）与系统提示词，
通过环境变量 AGENT_BACKEND=langgraph|custom 切换（默认 langgraph）。
"""
import json
import os

from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from agent.core import SYSTEM_PROMPT
from agent.tools.lc_tools import TOOLS

MAX_RECURSION = 30  # agent+tools 交替步数上限，防失控


def get_llm() -> ChatOpenAI:
    """构建 ChatOpenAI（OpenAI 兼容），密钥从环境变量读取，绝不硬编码。"""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未配置 API 密钥。请复制 .env.example 为 .env 并填入 DASHSCOPE_API_KEY。"
        )
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen-plus"),
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
    )


def _build_graph():
    llm = get_llm().bind_tools(TOOLS)

    def call_model(state: MessagesState):
        # 注入系统提示词（放在最前，保持会话历史为纯业务消息）
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + list(state["messages"])
        return {"messages": [llm.invoke(msgs)]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)  # 有工具调用→tools，否则→END
    builder.add_edge("tools", "agent")
    return builder.compile()


def run_agent(messages: list) -> tuple:
    """执行一轮完整的 LangGraph Agent 循环。

    :param messages: OpenAI 格式的纯 dict 消息列表（LangGraph 自动转换）
    :return: (最终回答文本, 工具执行事件列表, 更新后的纯 dict 消息列表)
    """
    app = _build_graph()
    final = app.invoke({"messages": messages}, config={"recursion_limit": MAX_RECURSION})
    msgs = final["messages"]

    # 从执行轨迹中提取工具调用事件（供界面「执行过程」面板展示）
    events = []
    for m in msgs:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                events.append({
                    "type": "tool_call", "name": tc["name"],
                    "args": json.dumps(tc["args"], ensure_ascii=False),
                })
        elif isinstance(m, ToolMessage):
            try:
                result = json.loads(m.content)
                ok = isinstance(result, dict) and "error" not in result
            except (json.JSONDecodeError, TypeError):
                result, ok = {"text": m.content}, True
            events.append({"type": "tool_result", "name": m.name, "ok": ok, "result": result})

    answer = next(
        (m.content for m in reversed(msgs)
         if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None)),
        "（模型未返回内容）",
    )
    # 只把最终回答追加回纯 dict 历史，保证会话可 JSON 落盘
    updated = list(messages) + [{"role": "assistant", "content": answer}]
    return answer, events, updated
