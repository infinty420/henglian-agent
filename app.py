# -*- coding: utf-8 -*-
"""
衡练 AI 助手 · Streamlit 界面（课堂 demo_1 Web 界面能力延伸）

启动：streamlit run app.py
功能：多轮对话、工具调用过程可视化（执行过程面板）、会话保存/加载（JSON 落盘）。
"""
import json
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent.backend import get_backend, get_model_name, has_api_key
from agent.tools.registry import TOOL_SPECS

st.set_page_config(page_title="衡练 AI 助手", page_icon="💪", layout="centered")

# ---------------- 会话状态初始化（纯对话历史，system 由后端注入） ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "events_history" not in st.session_state:
    st.session_state.events_history = []   # 每轮的工具执行事件

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)


def render_events(events: list, key_prefix: str):
    """执行过程面板：可视化每一轮工具调用（课程要求可当场展示工具被调用）。"""
    if not events:
        return
    with st.expander(f"⚙️ 执行过程（本轮 {sum(1 for e in events if e['type'] == 'tool_call')} 次工具调用）",
                     expanded=True):
        for i, ev in enumerate(events):
            if ev["type"] == "tool_call":
                st.markdown(f"**→ 调用工具** `{ev['name']}`")
                st.code(ev["args"], language="json")
            else:
                icon = "✅" if ev["ok"] else "❌"
                st.markdown(f"{icon} **{ev['name']} 返回**")
                st.json(ev["result"])
                # 图片生成工具：直接在对话中内嵌展示
                path = (ev.get("result") or {}).get("local_path")
                if path and os.path.isfile(path):
                    st.image(path, caption=path)


# ---------------- 侧边栏 ----------------
with st.sidebar:
    st.title("💪 衡练 AI 助手")
    st.caption("自然语言驱动的运动健康 Agent · 课程期末项目")

    st.divider()
    st.subheader("当前配置")
    has_key = has_api_key()
    runner, backend_name = get_backend()
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    st.markdown(f"""
    - 模型：`{get_model_name()}`（OpenAI 兼容接口）
    - 端点：`{base_url.split('//')[1].split('/')[0]}`
    - Agent 后端：**{backend_name}**（`AGENT_BACKEND` 可切换 langgraph / custom）
    - 密钥：{'✅ 已配置' if has_key else '❌ 未配置（见 .env.example）'}
    """)
    if not has_key:
        st.error("请先复制 `.env.example` 为 `.env` 并填入 API Key，然后重启应用。")

    st.divider()
    st.subheader("已注册工具（%d 个）" % len(TOOL_SPECS))
    for spec in TOOL_SPECS:
        st.markdown(f"- `{spec['function']['name']}`")

    st.divider()
    st.subheader("会话管理")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 保存会话", use_container_width=True):
            fname = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(os.path.join(SESSIONS_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)
            st.success(f"已保存 {fname}")
    with c2:
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.events_history = []
            st.rerun()

    saved = sorted(f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json"))
    if saved:
        picked = st.selectbox("加载历史会话", ["（不加载）"] + list(reversed(saved)))
        if picked != "（不加载）" and st.button("📂 加载所选会话"):
            with open(os.path.join(SESSIONS_DIR, picked), "r", encoding="utf-8") as f:
                st.session_state.messages = json.load(f)
            st.session_state.events_history = []
            st.rerun()

# ---------------- 主对话区 ----------------
st.title("衡练 · 你的运动健康 Agent 💪")
st.caption("描述你的训练、身体状态或饮食目标，我会调用工具计算后给出建议。试试："
           "「我今天跑了 40 分钟，平均心率 150，帮我评估一下并安排明天的训练」")

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").markdown(msg["content"] or "")

for evs in st.session_state.events_history:
    render_events(evs, f"hist")

if prompt := st.chat_input("输入消息，回车发送…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    if not has_key:
        st.chat_message("assistant").error(
            "未配置 API 密钥：请复制 .env.example 为 .env，填入 DASHSCOPE_API_KEY 后重启。")
    else:
        try:
            with st.chat_message("assistant"):
                with st.spinner(f"思考中（{backend_name}）…"):
                    answer, events, updated = runner(st.session_state.messages)
                st.session_state.messages = updated
                st.session_state.events_history.append(events)
                st.markdown(answer)
                render_events(events, "current")
        except Exception as e:
            st.chat_message("assistant").error(
                f"调用失败：{type(e).__name__}: {e}\n\n请检查 .env 中的密钥与网络后重试。")
