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
from PIL import Image, ImageDraw

load_dotenv()

from agent.backend import get_backend, get_model_name, has_api_key
from agent.tools.registry import TOOL_SPECS

st.set_page_config(page_title="衡练 AI 助手", page_icon="💪",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------- 会话状态初始化（纯对话历史，system 由后端注入） ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "events_history" not in st.session_state:
    st.session_state.events_history = []   # 每轮的工具执行事件
if "hl_dark" not in st.session_state:
    st.session_state.hl_dark = False

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

# /* finesse · register=product(AI-console) · A=暖珊瑚橙(#FF5A2C)+纸感浅底 · B=800/600
#  * C=宽屏仪表盘(头部+KPI行+对话/洞察双栏) · D=点击按压回弹+悬浮抬升 · E=现代运动控制台
#  * 增强：首屏一次入场动效 / 深色模式 / 重做对话框(用户珊瑚气泡·助手卡片)
#  * SOUL=6 SPECTACLE=6 DENSITY=6 */


def make_user_avatar() -> Image.Image:
    """生成用户头像（珊瑚渐变圆 + 白色人形剪影），用于对话气泡左侧的 <img> 区分。"""
    s = 64
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, s - 2, s - 2], fill=(255, 90, 44, 255))
    d.ellipse([6, 6, s - 6, s - 6], fill=(255, 122, 77, 255))
    d.ellipse([26, 19, 38, 31], fill=(255, 255, 255, 255))          # 头
    d.pieslice([20, 33, 44, 63], 180, 360, fill=(255, 255, 255, 255))  # 肩
    return img


USER_AVATAR = make_user_avatar()

# ---------------- 基础主题（浅色 + 全部组件样式） ----------------
BASE_CSS = """
<style>
:root {
  --hl-ink: #211c19;
  --hl-ink-soft: #8d8175;
  --hl-accent: #ff5a2c;
  --hl-accent-deep: #e23c10;
  --hl-accent-soft: #fff1ea;
  --hl-accent-glow: rgba(255, 90, 44, 0.18);
  --hl-surface-a: #fffdfb;
  --hl-surface-b: #f7f2ec;
  --hl-panel: #faf6f1;
  --hl-card: #ffffff;
  --hl-line: rgba(33, 28, 25, 0.09);
  --hl-ok: #16a34a;
  --hl-ok-soft: #e7f6ec;
  --hl-fail: #dc2626;
  --hl-fail-soft: #fdeaea;
  --hl-radius: 16px;
  --hl-shadow-sm: 0 1px 3px rgba(33, 28, 25, 0.06), 0 1px 2px rgba(33, 28, 25, 0.04);
  --hl-shadow-md: 0 6px 22px rgba(33, 28, 25, 0.08);
  --hl-shadow-accent: 0 8px 26px rgba(255, 90, 44, 0.18);
}

/* 应用底色：暖白渐变 + 顶部珊瑚光晕，白卡片"浮"起来 */
.stApp {
  background:
    radial-gradient(1200px 480px at 50% -12%, var(--hl-accent-soft) 0%, rgba(255, 241, 234, 0) 60%),
    linear-gradient(180deg, #fffdfb 0%, #f8f3ed 55%, #f5efe7 100%);
  color: var(--hl-ink);
}

/* ---------- 头部横幅 ---------- */
.hl-hero {
  position: relative;
  display: flex; align-items: center; gap: 18px;
  background: linear-gradient(135deg, #ffffff 50%, #fff4ee 100%);
  border: 1px solid rgba(255, 90, 44, 0.16);
  border-left: 5px solid var(--hl-accent);
  border-radius: 20px;
  padding: 22px 26px;
  margin: 16px 0 18px;
  box-shadow: var(--hl-shadow-accent);
  overflow: hidden;
  animation: hl-fade-up .5s ease both;
}
.hl-hero::after {
  content: ""; position: absolute; right: -40px; top: -40px;
  width: 170px; height: 170px; border-radius: 50%;
  background: radial-gradient(circle, var(--hl-accent-glow), transparent 70%);
}
.hl-hero-icon {
  width: 58px; height: 58px; border-radius: 16px; flex: none;
  background: linear-gradient(135deg, #ff7a4d 0%, #ff5a2c 55%, #e23c10 100%);
  box-shadow: var(--hl-shadow-accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 30px; position: relative; z-index: 1;
}
.hl-hero-title {
  font-size: 24px; font-weight: 800; letter-spacing: -0.02em;
  background: linear-gradient(90deg, #211c19, #e23c10);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hl-hero-sub { font-size: 13.5px; color: var(--hl-ink-soft); margin-top: 5px; }
.hl-hero-meta {
  margin-left: auto; flex: none; text-align: right;
  font-size: 12.5px; color: var(--hl-ink-soft); line-height: 1.9;
  padding-left: 18px; border-left: 1px dashed rgba(255, 90, 44, 0.3);
  position: relative; z-index: 1;
}
.hl-hero-meta b { color: var(--hl-accent-deep); }
@media (max-width: 640px) { .hl-hero-meta { display: none; } }

/* ---------- KPI 卡片行 ---------- */
.hl-kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 4px 0 18px; }
@media (max-width: 900px) { .hl-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.hl-kpi {
  position: relative; overflow: hidden;
  background: var(--hl-card);
  border: 1px solid var(--hl-line);
  border-radius: 16px;
  padding: 16px 18px 16px 22px;
  box-shadow: var(--hl-shadow-sm);
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
  animation: hl-fade-up .45s ease both;
}
.hl-kpi::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: linear-gradient(180deg, #ff7a4d, #ff5a2c);
  transition: width .18s ease;
}
.hl-kpi:hover { transform: translateY(-3px); box-shadow: var(--hl-shadow-accent); border-color: rgba(255, 90, 44, 0.3); }
.hl-kpi:hover::before { width: 6px; }
.hl-kpi:active { transform: translateY(-1px) scale(0.985); }
.hl-kpi-label { font-size: 12.5px; color: var(--hl-ink-soft); font-weight: 600; }
.hl-kpi-value { font-size: 22px; font-weight: 800; margin-top: 6px; letter-spacing: -0.01em; }
.hl-kpi-value.accent { color: var(--hl-accent-deep); }

/* ---------- 演示话术胶囊按钮 ---------- */
.hl-demo-label { font-size: 13px; color: var(--hl-ink-soft); margin: 2px 0 10px; font-weight: 600; }
.hl-demo-label::before {
  content: ""; display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; background: var(--hl-accent);
  margin-right: 8px; vertical-align: 1px;
  box-shadow: 0 0 0 4px var(--hl-accent-soft);
}
.stButton > button {
  border: 1px solid var(--hl-line) !important;
  border-radius: 12px !important;
  background: var(--hl-card) !important;
  color: var(--hl-ink) !important;
  font-size: 13px !important; font-weight: 600 !important;
  transition: transform .14s ease, border-color .16s ease, box-shadow .16s ease, color .16s ease !important;
  box-shadow: var(--hl-shadow-sm);
}
.stButton > button:hover {
  border-color: var(--hl-accent) !important;
  color: var(--hl-accent-deep) !important;
  box-shadow: var(--hl-shadow-accent) !important;
  transform: translateY(-2px) !important;
}
.stButton > button:active {
  transform: scale(0.95) !important;
  box-shadow: inset 0 2px 7px rgba(33, 28, 25, 0.16) !important;
}

/* ---------- 对话框重做：用户(右·珊瑚气泡) / 助手(左·卡片) ---------- */
[data-testid="stChatMessage"] {
  display: flex; align-items: flex-start; gap: 10px;
  margin: 0 0 14px; max-width: 92%; padding: 0;
  background: transparent; border: none; box-shadow: none;
}
[data-testid="stChatMessage"]:not(:has([data-testid="stChatMessageAvatar"] img)) { margin-right: auto; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) {
  flex-direction: row-reverse; margin-left: auto;
}
[data-testid="stChatMessage"] .stChatMessageContent {
  width: fit-content; max-width: min(100%, 560px);
  background: var(--hl-card);
  border: 1px solid var(--hl-line);
  border-radius: 16px;
  padding: 10px 14px;
  box-shadow: var(--hl-shadow-sm);
  transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stChatMessage"]:hover .stChatMessageContent { transform: translateY(-1px); box-shadow: var(--hl-shadow-md); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent {
  background: linear-gradient(135deg, #ff7a4d 0%, #ff5a2c 60%, #e23c10 100%);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #fff; box-shadow: var(--hl-shadow-accent);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent * { color: #fff !important; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent code,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent pre {
  background: rgba(255, 255, 255, 0.18) !important; color: #fff !important;
}
[data-testid="stChatMessageAvatar"] { flex: none; display: flex; align-items: center; }
[data-testid="stChatMessageAvatar"] img { border-radius: 50%; border: 2px solid #fff; box-shadow: var(--hl-shadow-sm); }
[data-testid="stChatMessageAvatar"] { font-size: 22px; }

/* ---------- 执行过程面板 ---------- */
[data-testid="stExpander"] {
  border: 1px solid rgba(255, 90, 44, 0.22) !important;
  border-radius: 14px !important;
  background: linear-gradient(180deg, #fff7f2, #fdf2ec);
  overflow: hidden; box-shadow: var(--hl-shadow-sm);
  transition: box-shadow .2s ease, border-color .2s ease;
}
[data-testid="stExpander"]:hover { box-shadow: var(--hl-shadow-accent); border-color: rgba(255, 90, 44, 0.35) !important; }
[data-testid="stExpander"] details { border: none !important; }
[data-testid="stExpander"] summary { font-size: 14px; font-weight: 700; cursor: pointer; }
[data-testid="stExpander"] summary strong { color: var(--hl-accent-deep); }
.hl-step {
  position: relative; display: flex; align-items: center; gap: 12px;
  padding: 9px 14px; margin: 8px 0;
  background: var(--hl-card); border: 1px solid var(--hl-line);
  border-radius: 12px; font-size: 13.5px; box-shadow: var(--hl-shadow-sm);
  animation: hl-fade-up .3s ease both;
  transition: transform .15s ease, box-shadow .15s ease;
}
.hl-step:hover { transform: translateX(3px); box-shadow: var(--hl-shadow-md); }
.hl-step-idx {
  flex: none; width: 24px; height: 24px; border-radius: 50%;
  background: linear-gradient(135deg, #ff7a4d, #ff5a2c); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 800; box-shadow: 0 2px 6px rgba(255, 90, 44, 0.35);
}
.hl-step-name { font-weight: 700; font-family: ui-monospace, Consolas, monospace; }
.hl-step-args { color: var(--hl-ink-soft); font-size: 12.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.hl-badge { flex: none; font-size: 11.5px; font-weight: 800; padding: 3px 10px; border-radius: 999px; }
.hl-badge.ok { background: var(--hl-ok-soft); color: var(--hl-ok); }
.hl-badge.fail { background: var(--hl-fail-soft); color: var(--hl-fail); }
.hl-badge.on { background: var(--hl-ok-soft); color: var(--hl-ok); }
.hl-badge.off { background: var(--hl-fail-soft); color: var(--hl-fail); }

[data-testid="stCodeBlock"], [data-testid="stJson"] { border-radius: 12px !important; border: 1px solid var(--hl-line) !important; font-size: 12.5px !important; }

/* ---------- 侧边栏 ---------- */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #faf6f1 0%, #f4efe8 100%);
  border-right: 1px solid var(--hl-line);
}
section[data-testid="stSidebar"] .stSubheader { color: var(--hl-accent-deep); font-size: 14px !important; letter-spacing: 0.02em; font-weight: 700 !important; }
section[data-testid="stSidebar"] hr { margin: 12px 0; border-color: var(--hl-line); }
.hl-status { background: var(--hl-card); border: 1px solid var(--hl-line); border-radius: 14px; padding: 6px 14px; margin: 6px 0 12px; box-shadow: var(--hl-shadow-sm); }
.hl-status-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; font-size: 13.5px; border-bottom: 1px dashed var(--hl-line); }
.hl-status-row:last-child { border-bottom: none; }
.hl-status-row > span:first-child { color: var(--hl-ink-soft); }
.hl-status-row code { background: var(--hl-panel); border-radius: 6px; padding: 2px 8px; font-size: 12.5px; color: var(--hl-accent-deep); }
.hl-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.hl-chip { font-family: ui-monospace, Consolas, monospace; font-size: 11.5px; background: var(--hl-card); border: 1px solid var(--hl-line); border-radius: 999px; padding: 4px 11px; color: var(--hl-ink); transition: all 0.15s ease; }
.hl-chip:hover { border-color: var(--hl-accent); color: var(--hl-accent-deep); background: var(--hl-accent-soft); }

/* ---------- 右侧实时洞察面板（sticky + 列表可滚动） ---------- */
.hl-panel-sticky {
  position: sticky; top: 4.5rem;
  max-height: calc(100vh - 6rem); overflow-y: auto;
  padding-right: 4px;
}
.hl-insight {
  background: var(--hl-card); border: 1px solid var(--hl-line);
  border-radius: 16px; padding: 16px 18px; box-shadow: var(--hl-shadow-sm);
  animation: hl-fade-up .5s ease both;
}
.hl-insight h4 { font-size: 14px; color: var(--hl-accent-deep); margin: 0 0 10px; }
.hl-act-list { max-height: 40vh; overflow-y: auto; margin-top: 4px; }
.hl-act { display: flex; align-items: center; gap: 10px; padding: 8px 10px; margin: 6px 0; background: var(--hl-panel); border-radius: 10px; font-size: 13px; transition: transform .15s ease, background .15s ease; }
.hl-act:hover { transform: translateX(3px); background: var(--hl-accent-soft); }
.hl-act-ico { flex: none; width: 26px; height: 26px; border-radius: 8px; background: var(--hl-accent-soft); display: flex; align-items: center; justify-content: center; font-size: 14px; }
.hl-live-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--hl-ok); margin-right: 6px; vertical-align: 0; box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.5); animation: hl-pulse 2s infinite; }

/* ---------- 空状态欢迎卡 ---------- */
.hl-welcome { background: var(--hl-card); border: 1px dashed rgba(33, 28, 25, 0.18); border-radius: 16px; padding: 26px 30px; text-align: center; color: var(--hl-ink-soft); font-size: 14px; margin-top: 8px; box-shadow: var(--hl-shadow-sm); }
.hl-welcome b { color: var(--hl-ink); }

/* ---------- 动效关键帧 ---------- */
@keyframes hl-fade-up { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes hl-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.5); }
  70%  { box-shadow: 0 0 0 8px rgba(22, 163, 74, 0); }
  100% { box-shadow: 0 0 0 0 rgba(22, 163, 74, 0); }
}

@media (prefers-reduced-motion: reduce) {
  .stButton > button, .hl-step, .hl-chip, .hl-kpi, .hl-act, .hl-insight, .hl-hero,
  [data-testid="stChatMessage"] { transition: none !important; animation: none !important; }
}
</style>
"""

# 非首屏：关闭入场动效（仅保留 hover/按压过渡），避免每次发消息重播
INTRO_OFF = """
<style>
.hl-hero, .hl-kpi, .hl-insight, [data-testid="stChatMessage"], .hl-step, .hl-act { animation: none !important; }
</style>
"""

# 深色模式：仅在开启时注入，覆盖 :root 变量与关键背景
DARK_CSS = """
<style>
:root {
  --hl-ink: #f2ece6;
  --hl-ink-soft: #b8ad9f;
  --hl-accent: #ff6b3d;
  --hl-accent-deep: #ff7a4d;
  --hl-accent-soft: rgba(255, 107, 61, 0.18);
  --hl-accent-glow: rgba(255, 107, 61, 0.22);
  --hl-surface-a: #14110f;
  --hl-surface-b: #1b1714;
  --hl-panel: #211c19;
  --hl-card: #211b18;
  --hl-line: rgba(255, 255, 255, 0.10);
  --hl-ok: #34d27e;
  --hl-ok-soft: rgba(52, 210, 126, 0.16);
  --hl-fail: #ff6b6b;
  --hl-fail-soft: rgba(255, 107, 107, 0.16);
  --hl-shadow-sm: 0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --hl-shadow-md: 0 6px 22px rgba(0,0,0,0.45);
  --hl-shadow-accent: 0 8px 26px rgba(255, 107, 61, 0.28);
}
.stApp {
  background:
    radial-gradient(1200px 480px at 50% -12%, rgba(255,107,61,0.16) 0%, rgba(255,107,61,0) 60%),
    linear-gradient(180deg, #14110f 0%, #181311 55%, #1b1613 100%) !important;
  color: var(--hl-ink);
  --text-color: var(--hl-ink);
  --body-text-color: var(--hl-ink);
}
.hl-hero { background: linear-gradient(135deg, #221b18 50%, #2a201c 100%) !important; }
.hl-kpi, .hl-insight, .hl-status, .hl-welcome, .hl-step, .hl-act { background: var(--hl-card) !important; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a1512 0%, #15110e 100%) !important; border-right: 1px solid var(--hl-line) !important; }
[data-testid="stExpander"] { background: linear-gradient(180deg, #241d1a, #1f1916) !important; border-color: rgba(255,107,61,0.3) !important; }
[data-testid="stCodeBlock"], [data-testid="stJson"] { background: #2a2320 !important; color: var(--hl-ink) !important; border: 1px solid var(--hl-line) !important; }
[data-testid="stChatInput"], [data-testid="stChatInput"] textarea { background: var(--hl-card) !important; color: var(--hl-ink) !important; }
[data-testid="stChatInput"] { border-color: var(--hl-line) !important; }
.hl-step-args { color: var(--hl-ink-soft) !important; }
/* —— 核心修复：Streamlit 浅色主题默认深字，整页文字翻浅避免压底 —— */
.stApp p, .stApp li, .stApp span, .stApp label, .stApp a,
.stApp .stMarkdown, .stApp .stText, .stApp .stCaption,
.stApp [data-testid="stChatMessageContent"],
.stApp [data-testid="stChatMessageContent"] p,
.stApp [data-testid="stChatMessageContent"] li,
.stApp [data-testid="stChatMessageContent"] span,
.stApp [data-testid="stExpander"] summary,
.stApp section[data-testid="stSidebar"] .stMarkdown {
  color: var(--hl-ink) !important;
}
/* 强调色保护：防止被上面的规则抹成普通色 */
.hl-kpi-value.accent { color: var(--hl-accent-deep) !important; }
.hl-step-idx { color: #fff !important; }
.hl-badge.ok, .hl-badge.on { color: var(--hl-ok) !important; }
.hl-badge.fail, .hl-badge.off { color: var(--hl-fail) !important; }
.hl-status-row code { color: var(--hl-accent-deep) !important; }
.stApp section[data-testid="stSidebar"] .stSubheader { color: var(--hl-accent-deep) !important; }
.hl-chip { color: var(--hl-ink) !important; }
.hl-chip:hover { color: var(--hl-accent-deep) !important; background: var(--hl-accent-soft) !important; }
/* 用户气泡：白字锁定（放在最后，优先级最高） */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatar"] img) .stChatMessageContent * { color: #fff !important; }
</style>
"""


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


def render_turn_images(events: list):
    """本轮若生成了图片，直接在对话中展示本地图片（不再依赖会过期的外链）。"""
    seen = set()
    for ev in (events or []):
        if ev.get("type") == "tool_call":
            continue
        res = ev.get("result") or {}
        path = res.get("local_path")
        if path and os.path.isfile(path) and path not in seen:
            seen.add(path)
            st.image(path, caption=os.path.basename(path), width="stretch")


# ---------------- 侧边栏 ----------------
with st.sidebar:
    st.markdown(
        '<div style="font-size:20px;font-weight:700;padding:4px 0 0">💪 衡练 AI 助手</div>'
        '<div style="font-size:12.5px;color:var(--hl-ink-soft);padding-bottom:4px">'
        '自然语言驱动的运动健康 Agent · 课程期末项目</div>',
        unsafe_allow_html=True)

    st.divider()
    # 深色模式开关
    dark = st.toggle("🌙 深色模式", value=st.session_state.hl_dark)
    st.session_state.hl_dark = dark

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
        + '</div>',
        unsafe_allow_html=True)

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

# ---------------- 主题注入（首屏动效 + 深色模式，均按会话状态条件注入） ----------------
play_intro = "hl_intro_played" not in st.session_state
css = BASE_CSS
if not play_intro:
    css += INTRO_OFF
if st.session_state.hl_dark:
    css += DARK_CSS
st.markdown(css, unsafe_allow_html=True)

# ---------------- 主区：头部横幅 + KPI 行 + 双栏仪表盘 ----------------
st.markdown(
    '<div class="hl-hero">'
    '<div class="hl-hero-icon">💪</div>'
    '<div><div class="hl-hero-title">衡练 · 你的运动健康 Agent</div>'
    '<div class="hl-hero-sub">描述训练、身体状态或饮食目标 → Agent 调用本地工具计算后给出建议</div></div>'
    f'<div class="hl-hero-meta"><b>{len(TOOL_SPECS)}</b> 个工具<br>'
    f'后端 <b>{backend_name}</b><br>模型 <b>{get_model_name()}</b></div>'
    '</div>',
    unsafe_allow_html=True)

# KPI 卡片行
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="hl-kpi"><div class="hl-kpi-label">已注册工具</div>'
                f'<div class="hl-kpi-value accent">{len(TOOL_SPECS)}</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="hl-kpi"><div class="hl-kpi-label">Agent 后端</div>'
                f'<div class="hl-kpi-value" style="font-size:18px">{backend_name}</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="hl-kpi"><div class="hl-kpi-label">当前模型</div>'
                f'<div class="hl-kpi-value" style="font-size:15px">{get_model_name()}</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="hl-kpi"><div class="hl-kpi-label">对话轮次</div>'
                f'<div class="hl-kpi-value accent">{len(st.session_state.messages) // 2}</div></div>', unsafe_allow_html=True)

# 双栏：左=对话流，右=实时洞察（sticky）
chat_col, panel_col = st.columns([2.2, 1], gap="large")

with chat_col:
    st.markdown('<div class="hl-demo-label">🎬 演示话术 · 点击直接发送</div>', unsafe_allow_html=True)
    demo_cols = st.columns(len(DEMO_PROMPTS))
    demo_clicked = None
    for i, (col, p) in enumerate(zip(demo_cols, DEMO_PROMPTS)):
        with col:
            if st.button(f"{'①②③④'[i]} {p[:9]}…", key=f"demo_{i}", use_container_width=True):
                demo_clicked = p

    if not st.session_state.messages:
        st.markdown(
            '<div class="hl-welcome">还没有对话。<br>'
            '点击上方任一<b>演示话术</b>，或在底部输入框用自然语言描述你的训练——'
            '「⚙️ 执行过程」面板会展示 Agent 实际调用了哪些工具。</div>',
            unsafe_allow_html=True)

    # 渲染历史消息；每个助手回复后紧跟该轮执行过程
    ev_ptr = 0
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user", avatar=USER_AVATAR):
                if msg.get("error"):
                    st.error(msg["content"])
                else:
                    st.markdown(msg["content"])
        else:  # assistant
            cur_events = st.session_state.events_history[ev_ptr] \
                if ev_ptr < len(st.session_state.events_history) else []
            with st.chat_message("assistant", avatar="💪"):
                if msg.get("error"):
                    st.error(msg["content"])
                else:
                    st.markdown(msg["content"] or "")
                    # 直接展示本轮生成的图片（本地文件，不依赖外链）
                    render_turn_images(cur_events)
            if not msg.get("error") and ev_ptr < len(st.session_state.events_history):
                render_events(st.session_state.events_history[ev_ptr], "hist")
                ev_ptr += 1

with panel_col:
    all_calls = [e["name"] for evs in st.session_state.events_history
                 for e in evs if e["type"] == "tool_call"]
    total_calls = len(all_calls)
    turns = len(st.session_state.messages) // 2
    recent = list(reversed(all_calls))[:5]
    dot = '<span class="hl-live-dot"></span> 已连接' if has_key \
        else '<span style="color:var(--hl-fail);font-weight:700">未配置</span>'
    acts_html = "".join(
        f'<div class="hl-act"><span class="hl-act-ico">⚡</span>'
        f'<span class="hl-step-name">{n}</span></div>' for n in recent) \
        or '<div class="hl-act" style="color:var(--hl-ink-soft)">暂无调用，发条演示话术试试</div>'
    st.markdown('<div class="hl-panel-sticky">', unsafe_allow_html=True)
    st.markdown(
        '<div class="hl-insight">'
        '<h4>📊 实时洞察</h4>'
        f'<div class="hl-status-row"><span>API 状态</span>{dot}</div>'
        f'<div class="hl-status-row"><span>累计工具调用</span><b>{total_calls}</b></div>'
        f'<div class="hl-status-row"><span>对话轮次</span><b>{turns}</b></div>'
        '</div>'
        '<div class="hl-insight" style="margin-top:14px">'
        '<h4>🛠 最近工具调用</h4>'
        '<div class="hl-act-list">'
        f'{acts_html}'
        '</div>'
        '</div>',
        unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def handle_prompt(prompt: str):
    """统一处理：聊天输入与演示话术按钮共用同一执行路径。修改会话状态后整体重渲染。"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    if not has_key:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "未配置 API 密钥：请复制 .env.example 为 .env，填入 DASHSCOPE_API_KEY 后重启。",
            "error": True})
        st.rerun()
        return
    try:
        with st.spinner(f"思考中（{backend_name}）…"):
            answer, events, updated = runner(st.session_state.messages)
        st.session_state.messages = updated
        st.session_state.events_history.append(events)
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"调用失败：{type(e).__name__}: {e}\n\n请检查 .env 中的密钥与网络后重试。",
            "error": True})
    st.rerun()


if prompt := st.chat_input("输入消息，回车发送…"):
    handle_prompt(prompt)
elif demo_clicked:
    handle_prompt(demo_clicked)

# 标记首屏动效已播放（仅当次会话的第一次渲染播放入场动画）
st.session_state.hl_intro_played = True
