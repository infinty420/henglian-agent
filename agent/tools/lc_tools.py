# -*- coding: utf-8 -*-
"""
业务工具的 LangChain 封装层

把 agent/tools/ 下的纯 Python 业务函数包装为 LangChain Tool 对象，
供 LangGraph Agent 框架（路径 A 要求项②）bind_tools 使用。
工具逻辑与自研 Tool Calling 循环（agent/core.py）完全共用同一份实现，
保证两种后端行为一致，答辩时可比对。
"""
import json

from langchain_core.tools import tool

from agent.tools import training, diet, strength, whatif, skills, imagegen


def _j(result: dict) -> str:
    """工具返回值统一序列化为 JSON 字符串（中文不转义），与自研后端格式一致。"""
    return json.dumps(result, ensure_ascii=False)


@tool
def evaluate_training(sport_type: str, duration_min: float,
                      avg_heart_rate: float = 0, calories: float = 0,
                      training_load: float = None) -> str:
    """评估一次训练：按时长与平均心率估算训练负荷（0-100），给出负荷分档（超标/正常/偏低）与建议恢复时长。用户描述完一次训练后调用。"""
    return _j(training.evaluate_training(sport_type, duration_min, avg_heart_rate,
                                         calories, training_load))


@tool
def plan_next_workout(sport_type: str, training_load: float) -> str:
    """根据本次运动类型与训练负荷规划下一次互补训练（类型/强度/时长/理由）。负荷≥80 强制主动恢复。"""
    return _j(training.plan_next_workout(sport_type, training_load))


@tool
def compute_fatigue(loads_recent_first: list) -> str:
    """按最近 7 天每日总负荷计算疲劳指数（0-100，越近权重越高）与恢复系数。loads_recent_first 下标 0=今天、1=昨天…，无训练的天填 0。"""
    return _j(training.compute_fatigue(loads_recent_first))


@tool
def plan_daily_diet(gender: str, weight_kg: float, height_cm: float, age: int,
                    goal: str, activity_level: str = "中度活动",
                    is_training_day: bool = True) -> str:
    """按 Mifflin-St Jeor 公式计算 BMR/TDEE，结合目标（增肌/减脂/维持）给出每日热量、双碳水方案、蛋白质与饮水目标。"""
    return _j(diet.plan_daily_diet(gender, weight_kg, height_cm, age, goal,
                                   activity_level, is_training_day))


@tool
def recovery_meal_plan(calories: float, training_load: float) -> str:
    """计算运动后恢复餐的补充热量与宏量营养素克数（蛋白30/碳水50/脂肪20，负荷超标时热量下调为消耗的60%）。"""
    return _j(diet.recovery_meal_plan(calories, training_load))


@tool
def estimate_one_rep_max(weight_kg: float, reps: int) -> str:
    """用 Epley 与 Brzycki 双公式估算单次极限重量 1RM（kg）。"""
    return _j(strength.estimate_one_rep_max(weight_kg, reps))


@tool
def effective_sets(sets: list) -> str:
    """统计训练组数据的有效组数与有效容量（有效强度 RPE 或 10-RIR ≥ 7 计入）。sets 每组含 weight_kg/reps 与 rpe 或 rir。"""
    return _j(strength.effective_sets(sets))


@tool
def what_if_simulate(current_weight_kg: float, weekly_sessions: int,
                     avg_session_load: float, daily_kcal_delta: int) -> str:
    """What-if 情景模拟：假设每周训练次数与每日热量增减，推算 4/8 周后的体重与累计训练负荷。"""
    return _j(whatif.what_if_simulate(current_weight_kg, weekly_sessions,
                                      avg_session_load, daily_kcal_delta))


@tool
def generate_image(prompt: str, filename: str = "") -> str:
    """生成一张运动/训练主题示意图（百炼文生图模型），保存到 output/images/ 并返回本地路径。用户想要「画一张图 / 示意图 / 生成图片」时调用；prompt 需为具体中文画面描述。"""
    return _j(imagegen.generate_image(prompt, filename))


@tool
def read_skill(skill_name: str) -> str:
    """读取指定 Agent Skill 的 SKILL.md（含操作步骤与模板）。用户要求生成周报时，先调用本工具读取 weekly-report 技能。"""
    return _j(skills.read_skill(skill_name))


@tool
def write_weekly_report(filename: str, content: str) -> str:
    """⚠️写文件操作：把周训练报告 Markdown 写入项目 output/ 目录（唯一可写目录）。调用前必须先向用户展示报告全文并获得明确同意。"""
    return _j(skills.write_weekly_report(filename, content))


# 供 LangGraph bind_tools 使用的完整工具集（11 个，与自研后端一一对应）
TOOLS = [
    evaluate_training, plan_next_workout, compute_fatigue, plan_daily_diet,
    recovery_meal_plan, estimate_one_rep_max, effective_sets, what_if_simulate,
    generate_image, read_skill, write_weekly_report,
]
