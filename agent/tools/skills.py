# -*- coding: utf-8 -*-
"""
Skill 加载与产出物写入工具

- read_skill：读取 skills/<name>/SKILL.md（白名单校验），符合 Agent Skills 规范
- write_weekly_report：将周报 Markdown 写入 output/ 目录。
  权限隔离（课程加分项）：文件名做 basename 清洗 + 后缀白名单，
  Agent 只能写本项目 output/ 目录，无法逃逸到其他路径。
"""
import os
import re
from datetime import date

# agent/tools/skills.py → 上溯三层到项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = os.path.join(BASE_DIR, "skills")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

SKILL_WHITELIST = {"weekly-report"}


def read_skill(skill_name: str) -> dict:
    """读取指定 Skill 的 SKILL.md 全文（含模板与步骤说明）。"""
    if skill_name not in SKILL_WHITELIST:
        return {"error": f"未找到 Skill「{skill_name}」，可用：{'、'.join(sorted(SKILL_WHITELIST))}"}
    path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.isfile(path):
        return {"error": f"Skill「{skill_name}」缺少 SKILL.md 文件"}
    with open(path, "r", encoding="utf-8") as f:
        return {"skill_name": skill_name, "content": f.read()}


def _safe_filename(filename: str) -> str:
    """清洗文件名：去路径分隔符与非法字符，强制 .md 后缀。"""
    name = os.path.basename(filename.strip())
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    if not name.endswith(".md"):
        name += ".md"
    return name


def write_weekly_report(filename: str, content: str) -> dict:
    """将周训练报告（Markdown）写入 output/ 目录并返回绝对路径。

    ⚠️ 这是本 Agent 唯一具备「写入文件」能力的工具，且被限制在
    output/ 目录内（权限隔离）。Agent 在调用前必须先向用户确认。
    """
    if not content or not content.strip():
        return {"error": "报告内容为空，拒绝写入。请先生成报告正文。"}
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = _safe_filename(filename)
    if not safe_name or safe_name == ".md":
        safe_name = f"周训练报告_{date.today().isoformat()}.md"
    path = os.path.join(OUTPUT_DIR, safe_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {
        "written": True,
        "path": path,
        "size_chars": len(content),
        "message": f"周报已写入 {path}，用户可在 output/ 目录查看。",
    }
