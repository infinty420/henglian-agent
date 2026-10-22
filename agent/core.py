# -*- coding: utf-8 -*-
"""
衡练 AI 助手 · Agent 核心

自研的 Tool Calling 执行循环（课堂 demo_2 工具调用机制的扩展）：
    用户消息 → LLM → 返回 tool_calls → dispatch 执行本地工具 → 结果回传 LLM
    → 循环直到 LLM 给出最终中文回答（最多 8 轮，防失控）

模型接入采用 OpenAI 兼容接口（课堂 demo_2/3 能力）：
默认阿里百炼 DashScope 兼容模式，也可通过环境变量切换到
Ollama / ModelScope 等任意 OpenAI 兼容端点。
"""
import json
import os

from openai import OpenAI

from agent.tools.registry import TOOL_SPECS, dispatch

MAX_TOOL_ROUNDS = 8

SYSTEM_PROMPT = """你是「衡练」，一名运动健康助手，服务规律训练的健身爱好者与运动入门者。

# 工作方式
1. 用户描述训练、身体状态或饮食需求时，**必须调用工具**获取计算结果，再基于结果回答；禁止凭空编造数值。
2. 一次自然语言请求可能需要多个工具（例如"评估我这次训练并安排明天的训练"→ evaluate_training + plan_next_workout + recovery_meal_plan），按需组合调用。
3. 工具返回 error 时，如实向用户解释原因并请其补充信息，不要重试超过 2 次。
4. 用户信息不全时，先给出基于合理默认值的建议，并说明你做了哪些假设。

# 周报技能
用户要求"周报 / 本周训练总结 / 训练报告"时：先调用 read_skill(skill_name="weekly-report")
读取技能规范，按其中步骤与模板生成报告；调用 write_weekly_report 写入前，
**必须先把报告全文展示给用户并获得明确同意**（这是唯一写文件操作，需用户确认）。

# 安全与合规
1. 所有饮食与营养建议都必须附带免责声明：「以上为日常营养参考，非医疗诊断；如有基础疾病请遵医嘱。」
2. 涉及伤病疼痛的问题：只建议休息/就医，不给诊断。
3. 你只能写项目 output/ 目录，不得声称能操作其他位置。
4. 回答用简体中文，数值带单位，重要结论先说结果再说依据。
"""


def get_client() -> OpenAI:
    """创建 OpenAI 兼容客户端。密钥从环境变量读取，绝不硬编码。"""
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未配置 API 密钥。请复制 .env.example 为 .env 并填入 DASHSCOPE_API_KEY。"
        )
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    return OpenAI(api_key=api_key, base_url=base_url)


def get_model_name() -> str:
    return os.getenv("MODEL_NAME", "qwen-plus")


def run_agent(client: OpenAI, messages: list, model: str = None) -> tuple:
    """执行一轮完整的 Agent 循环。

    :param messages: OpenAI 格式消息列表（含 system，不含本轮结果）
    :return: (最终回答文本, 工具执行事件列表, 更新后的 messages)
             事件：{"type": "tool_call", "name", "args"}
                   {"type": "tool_result", "name", "ok", "result"}
    """
    model = model or get_model_name()
    events = []
    work = list(messages)

    for _ in range(MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(
            model=model,
            messages=work,
            tools=TOOL_SPECS,
            temperature=0.3,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return (msg.content or "（模型未返回内容）"), events, work

        # 记录带 tool_calls 的助手消息，再逐个执行工具并回填结果
        work.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            name = tc.function.name
            args_raw = tc.function.arguments
            try:
                args_show = json.dumps(json.loads(args_raw), ensure_ascii=False) if args_raw else "{}"
            except json.JSONDecodeError:
                args_show = args_raw
            events.append({"type": "tool_call", "name": name, "args": args_show})

            result = dispatch(name, args_raw)
            events.append({
                "type": "tool_result", "name": name,
                "ok": "error" not in result, "result": result,
            })
            work.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # 工具轮次耗尽：强制收尾
    work.append({"role": "user", "content": "（系统提示：请基于以上工具结果直接给出最终回答）"})
    resp = client.chat.completions.create(model=model, messages=work, temperature=0.3)
    return resp.choices[0].message.content, events, work
