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

st.set_page_config(page_title="衡练 AI 助手", page_icon="💪",
                   layout="centered", initial_sidebar_state="expanded")

# ---------------- 会话状态初始化（纯对话历史，system 由后端注入） ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "events_history" not in st.session_state:
    st.session_state.events_history = []   # 每轮的工具执行事件

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# ---------------- 演示话术（现场一键触发，替代现场打字） ----------------
DEMO_PROMPTS = [
    "我今天练了90分钟力量，平均心率125，消耗500千卡，帮我评估一下并安排明天的训练",
    "帮我规划明天一天的饮食：我75公斤、175cm、25岁，目标是增肌",
    "我现在75公斤，如果每周练4次、每天少吃500千卡，8周后体重大概多少？",
    "帮我画一张标准的杠铃深蹲动作示意图",
]

# /* finesse · register=product(AI-console) · A=暖中性+活力橙(#E8542F) · B=700/400
#  * C=居中对话+侧栏控制台 · D=feedback-only(微过渡) · E=纸感浅色 · SOUL=5 SPECTACLE=2 DENSITY=6 */
THEME_CSS = """
<style>
:root {
  --hl-ink: #2b2724;
  --hl-ink-soft: #776d64;
  --hl-accent: #e8542f;
  --hl-accent-deep: #c93f1d;
  --hl-accent-soft: #fdece4;
  --hl-surface: #faf8f5;
  --hl-panel: #f3eee7;
  --hl-card: #ffffff;
  --hl-line: rgba(43, 39, 36, 0.09);
  --hl-ok: #2e7d4f;
  --hl-ok-soft: #e3f1e8;
  --hl-fail: #b3361f;
  --hl-fail-soft: #fbe7e2;
}

/* 应用底色：暖纸感，非纯白 */
.stApp {
  background: linear-gradient(180deg, #faf8f5 0%, #f5f0e9 100%);
  color: var(--hl-ink);
}

/* ---------- 头部横幅 ---------- */
.hl-hero {
  display: flex; align-items: center; gap: 18px;
  background: var(--hl-card);
  border: 1px solid var(--hl-line);
  border-left: 4px solid var(--hl-accent);
  border-radius: 14px;
  padding: 18px 22px;
  margin: 14px 0 18px;
  box-shadow: 0 2px 12px rgba(43, 39, 36, 0.06);
}
.hl-hero-icon {
  width: 52px; height: 52px; border-radius: 12px; flex: none;
  background: var(--hl-accent-soft);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
}
.hl-hero-title { font-size: 22px; font-weight: 700; letter-spacing: -0.01em; }
.hl-hero-sub { font-size: 13px; color: var(--hl-ink-soft); margin-top: 3px; }
.hl-hero-meta {
  margin-left: auto; flex: none; text-align: right;
  font-size: 12.5px; color: var(--hl-ink-soft); line-height: 1.75;
}
.hl-hero-meta b { color: var(--hl-ink); }
@media (max-width: 640px) { .hl-hero-meta { display: none; } }

/* ---------- 演示话术胶囊按钮 ---------- */
.hl-demo-label { font-size: 13px; color: var(--hl-ink-soft); margin: 2px 0 8px; }
.stButton > button {
  border: 1px solid var(--hl-line) !important;
  border-radius: 10px !important;
  background: var(--hl-card) !important;
  color: var(--hl-ink) !important;
  font-size: 13px !important;
  transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
  box-shadow: 0 1px 3px rgba(43, 39, 36, 0.05);
}
.stButton > button:hover {
  border-color: var(--hl-accent) !important;
  box-shadow: 0 3px 10px rgba(232, 84, 47, 0.14) !important;
  transform: translateY(-1px);
}

/* ---------- 聊天气泡 ---------- */
[data-testid="stChatMessage"] {
  border: 1px solid var(--hl-line);
  border-radius: 14px;
  background: var(--hl-card);
  box-shadow: 0 1px 4px rgba(43, 39, 36, 0.04);
  padding: 10px 16px !important;
}

/* ---------- 执行过程面板 ---------- */
[data-testid="stExpander"] {
  border: 1px solid var(--hl-line) !important;
  border-radius: 12px !important;
  background: var(--hl-panel);
  overflow: hidden;
}
[data-testid="stExpander"] details { border: none !important; }
[data-testid="stExpander"] summary { font-size: 14px; }
.hl-step {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 12px; margin: 6px 0;
  background: var(--hl-card);
  border: 1px solid var(--hl-line);
  border-radius: 10px;
  font-size: 13.5px;
}
.hl-step-idx {
  flex: none; width: 22px; height: 22px; border-radius: 50%;
  background: var(--hl-accent); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
}
.hl-step-name { font-weight: 600; font-family: ui-monospace, Consolas, monospace; }
.hl-step-args {
  color: var(--hl-ink-soft); font-size: 12.5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  min-width: 0;
}
.hl-badge {
  flex: none; font-size: 11.5px; font-weight: 700;
  padding: 2px 9px; border-radius: 999px;
}
.hl-badge.ok { background: var(--hl-ok-soft); color: var(--hl-ok); }
.hl-badge.fail { background: var(--hl-fail-soft); color: var(--hl-fail); }
.hl-badge.on { background: var(--hl-ok-soft); color: var(--hl-ok); }
.hl-badge.off { background: var(--hl-fail-soft); color: var(--hl-fail); }

/* 代码块 / JSON 视图与暖色系协调 */
[data-testid="stCodeBlock"], [data-testid="stJson"] {
  border-radius: 10px !important;
  border: 1px solid var(--hl-line) !important;
  font-size: 12.5px !important;
}

/* ---------- 侧边栏：控制台化 ---------- */
section[data-testid="stSidebar"] {
  background: var(--hl-panel);
  border-right: 1px solid var(--hl-line);
}
section[data-testid="stSidebar"] hr { margin: 10px 0; }
.hl-status {
  background: var(--hl-card);
  border: 1px solid var(--hl-line);
  border-radius: 12px;
  padding: 4px 14px; margin: 6px 0 12px;
}
.hl-status-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 7px 0; font-size: 13.5px;
  border-bottom: 1px dashed var(--hl-line);
}
.hl-status-row:last-child { border-bottom: none; }
.hl-status-row > span:first-child { color: var(--hl-ink-soft); }
.hl-status-row code {
  background: var(--hl-panel); border-radius: 6px; padding: 1px 7px;
  font-size: 12.5px; color: var(--hl-accent-deep);
}
.hl-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.hl-chip {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 11.5px;
  background: var(--hl-card);
  border: 1px solid var(--hl-line);
  border-radius: 999px;
  padding: 3px 10px;
  color: var(--hl-ink);
}
.hl-chip:hover { border-color: var(--hl-accent); color: var(--hl-accent-deep); }

/* ---------- 空状态欢迎卡 ---------- */
.hl-welcome {
  background: var(--hl-card);
  border: 1px dashed rgba(43, 39, 36, 0.16);
  border-radius: 14px;
  padding: 22px 26px;
  text-align: center;
  color: var(--hl-ink-soft);
  font-size: 14px;
  margin-top: 8px;
}
.hl-welcome b { color: var(--hl-ink); }

@media (prefers-reduced-motion: reduce) {
  .stButton > button { transition: none; }
}
</style>
"""
st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_events(events: list, key_prefix: str):
    """执行过程面板：可视化每一轮工具调用（课程要求可当场展示工具被调用）。"""
    if not events:
        return
    n_calls = sum(1 for e in events if e["type"] == "tool_call")
    with st.expander(f"⚙️ 执行过程 · 本轮 {n_calls} 次工具调用", expanded=True):
        step_no = 0
        for ev in events:
            if ev["type"] == "tool_call":
                step_no += 1
                args_line = " ".join(ev["args"].split())[:72]
                st.markdown(
                    f'<div class="hl-step"><span class="hl-step-idx">{step_no}</span>'
                    f'<span class="hl-step-name">🛠 {ev["name"]}</span>'
                    f'<span class="hl-step-args">{args_line}</span></div>',
                    unsafe_allow_html=True)
                st.code(ev["args"], language="json")
            else:
                badge = '<span class="hl-badge ok">成功</span>' if ev["ok"] \
                    else '<span class="hl-badge fail">失败</span>'
                st.markdown(
                    f'<div class="hl-step">{badge}'
                    f'<span class="hl-step-name">{ev["name"]}</span></div>',
                    unsafe_allow_html=True)
                st.json(ev["result"])
                # 图片生成工具：直接在对话中内嵌展示
                path = (ev.get("result") or {}).get("local_path")
                if path and os.path.isfile(path):
                    st.image(path, caption=path)


# ---------------- 侧边栏 ----------------
with st.sidebar:
    st.markdown(
        '<div style="font-size:20px;font-weight:700;padding:4px 0 0">💪 衡练 AI 助手</div>'
        '<div style="font-size:12.5px;color:var(--hl-ink-soft);padding-bottom:4px">'
        '自然语言驱动的运动健康 Agent · 课程期末项目</div>',
        unsafe_allow_html=True)

    st.divider()
    st.subheader("当前配置")
    has_key = has_api_key()
    runner, backend_name = get_backend()
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    st.markdown(
        '<div class="hl-status">'
        f'<div class="hl-status-row"><span>模型</span><code>{get_model_name()}</code></div>'
        f'<div class="hl-status-row"><span>端点</span><code>{base_url.split("//")[1].split("/")[0]}</code></div>'
        f'<div class="hl-status-row"><span>Agent 后端</span>'
        f'<b>{backend_name}</b></div>'
        '<div class="hl-status-row"><span>API 密钥</span>'
        + ('<span class="hl-badge on">已配置</span>' if has_key else '<span class="hl-badge off">未配置</span>')
        + '</div></div>',
        unsafe_allow_html=True)
    st.caption("`AGENT_BACKEND` 可切换 langgraph / custom 双后端")
    if not has_key:
        st.error("请先复制 `.env.example` 为 `.env` 并填入 API Key，然后重启应用。")

    st.divider()
    st.subheader("已注册工具（%d 个）" % len(TOOL_SPECS))
    st.markdown(
        '<div class="hl-chips">' + "".join(
            f'<span class="hl-chip">{spec["function"]["name"]}</span>' for spec in TOOL_SPECS)
        + '</div>', unsafe_allow_html=True)

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
# 头部横幅（替代默认 title + caption）
st.markdown(
    '<div class="hl-hero">'
    '<div class="hl-hero-icon">💪</div>'
    '<div><div class="hl-hero-title">衡练 · 你的运动健康 Agent</div>'
    '<div class="hl-hero-sub">描述训练、身体状态或饮食目标 → Agent 调用本地工具计算后给出建议</div></div>'
    f'<div class="hl-hero-meta"><b>{len(TOOL_SPECS)}</b> 个工具<br>'
    f'后端 <b>{backend_name}</b><br>模型 <b>{get_model_name()}</b></div>'
    '</div>', unsafe_allow_html=True)

# 演示话术（一键发送，现场演示用）
st.markdown('<div class="hl-demo-label">🎬 演示话术 · 点击直接发送</div>', unsafe_allow_html=True)
demo_cols = st.columns(len(DEMO_PROMPTS))
demo_clicked = None
for i, (col, p) in enumerate(zip(demo_cols, DEMO_PROMPTS)):
    with col:
        if st.button(f"{'①②③④'[i]} {p[:9]}…", key=f"demo_{i}", use_container_width=True):
            demo_clicked = p

# 空状态欢迎卡
if not st.session_state.messages:
    st.markdown(
        '<div class="hl-welcome">还没有对话。<br>'
        '点击上方任一<b>演示话术</b>，或在底部输入框用自然语言描述你的训练——'
        '「⚙️ 执行过程」面板会展示 Agent 实际调用了哪些工具。</div>',
        unsafe_allow_html=True)

# 渲染历史消息与各轮执行过程
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").markdown(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").markdown(msg["content"] or "")

for evs in st.session_state.events_history:
    render_events(evs, "hist")


def handle_prompt(prompt: str):
    """统一处理：聊天输入与演示话术按钮共用同一执行路径。"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(prompt)

    if not has_key:
        st.chat_message("assistant").error(
            "未配置 API 密钥：请复制 .env.example 为 .env，填入 DASHSCOPE_API_KEY 后重启。")
        return
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


if prompt := st.chat_input("输入消息，回车发送…"):
    handle_prompt(prompt)
elif demo_clicked:
    handle_prompt(demo_clicked)
