# -*- coding: utf-8 -*-
"""
工具注册表：集中定义每个工具的 JSON Schema（供 LLM Tool Calling）
与执行入口（本地函数）。LLM 返回的工具调用经 dispatch 路由到真实函数，
异常被捕获并转为 {"error": ...}，保证失败可解释（课程要求）。
"""
import json
import traceback

from agent.tools import training, diet, strength, whatif, skills, imagegen


def _spec(name: str, desc: str, func, params: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": params,
                "required": required,
            },
        },
        "_func": func,
    }


_NUM = {"type": "number"}
_STR = {"type": "string"}
_BOOL = {"type": "boolean"}

TOOL_SPECS_RAW = [
    _spec(
        "evaluate_training",
        "评估一次训练：按时长与平均心率估算训练负荷（0-100）并给出负荷分档（超标/正常/偏低）"
        "与建议恢复时长。用户描述完一次训练后应调用本工具。",
        training.evaluate_training,
        {
            "sport_type": {"type": "string", "description": "运动类型：力量/跑步/骑行/游泳/HIIT/瑜伽/步行/跳绳/椭圆机/动感单车/爬楼机 等"},
            "duration_min": _NUM | {"description": "训练时长（分钟）"},
            "avg_heart_rate": _NUM | {"description": "平均心率（次/分），负荷估算用"},
            "calories": _NUM | {"description": "本次消耗热量（kcal），可为 0"},
            "training_load": _NUM | {"description": "已知的训练负荷 0-100；用户未提供则不要填，由公式估算"},
        },
        ["sport_type", "duration_min"],
    ),
    _spec(
        "plan_next_workout",
        "根据本次运动类型与训练负荷，规划下一次互补训练（类型/强度/时长/理由）。负荷≥80 时强制主动恢复。",
        training.plan_next_workout,
        {
            "sport_type": _STR,
            "training_load": _NUM | {"description": "本次训练负荷 0-100（可用 evaluate_training 的结果）"},
        },
        ["sport_type", "training_load"],
    ),
    _spec(
        "compute_fatigue",
        "按最近 7 天每日总负荷计算疲劳指数（0-100，加权：越近权重越高）与恢复系数。",
        training.compute_fatigue,
        {
            "loads_recent_first": {
                "type": "array", "items": {"type": "number"},
                "description": "最近 7 天每日总负荷，下标 0=今天、1=昨天…；没有训练的天填 0",
            },
        },
        ["loads_recent_first"],
    ),
    _spec(
        "plan_daily_diet",
        "按 Mifflin-St Jeor 公式计算基础代谢/TDEE，结合目标（增肌/减脂/维持）给出每日热量、"
        "双碳水方案、蛋白质与饮水目标。",
        diet.plan_daily_diet,
        {
            "gender": {"type": "string", "enum": ["男", "女"]},
            "weight_kg": _NUM,
            "height_cm": _NUM,
            "age": {"type": "integer"},
            "goal": {"type": "string", "enum": ["增肌", "减脂", "维持"]},
            "activity_level": {"type": "string", "enum": ["久坐", "轻度活动", "中度活动", "高强度活动", "运动员"]},
            "is_training_day": _BOOL | {"description": "当日是否训练日，默认 true"},
        },
        ["gender", "weight_kg", "height_cm", "age", "goal"],
    ),
    _spec(
        "recovery_meal_plan",
        "计算运动后恢复餐的补充热量与宏量营养素克数（蛋白30%/碳水50%/脂肪20%，负荷超标时热量下调为消耗的60%）。",
        diet.recovery_meal_plan,
        {
            "calories": _NUM | {"description": "本次训练消耗热量（kcal）"},
            "training_load": _NUM | {"description": "本次训练负荷 0-100"},
        },
        ["calories", "training_load"],
    ),
    _spec(
        "estimate_one_rep_max",
        "用 Epley 与 Brzycki 双公式估算单次极限重量 1RM。",
        strength.estimate_one_rep_max,
        {
            "weight_kg": _NUM | {"description": "完成的重量（kg）"},
            "reps": {"type": "integer", "description": "完成的次数"},
        },
        ["weight_kg", "reps"],
    ),
    _spec(
        "effective_sets",
        "统计一组训练数据的有效组数与有效容量（有效强度 RPE 或 10-RIR ≥ 7 计入）。",
        strength.effective_sets,
        {
            "sets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "weight_kg": _NUM, "reps": {"type": "integer"},
                        "rpe": _NUM, "rir": _NUM,
                    },
                },
                "description": "训练组列表，每组含 weight_kg/reps 与 rpe 或 rir（二选一）",
            },
        },
        ["sets"],
    ),
    _spec(
        "what_if_simulate",
        "What-if 情景模拟：假设每周训练次数与每日热量增减，推算 4/8 周后的体重与累计训练负荷。",
        whatif.what_if_simulate,
        {
            "current_weight_kg": _NUM,
            "weekly_sessions": {"type": "integer", "description": "假设的每周训练次数"},
            "avg_session_load": _NUM | {"description": "单次平均负荷 0-100"},
            "daily_kcal_delta": {"type": "integer", "description": "每日热量增减（kcal，负数=缺口）"},
        },
        ["current_weight_kg", "weekly_sessions", "avg_session_load", "daily_kcal_delta"],
    ),
    _spec(
        "generate_image",
        "生成一张运动/训练主题示意图（百炼文生图模型），保存到 output/images/ 并返回本地路径。"
        "用户想要「画一张图 / 示意图 / 生成图片」时调用；prompt 需为具体中文画面描述。",
        imagegen.generate_image,
        {
            "prompt": _STR | {"description": "中文画面描述，尽量具体：动作、姿势、场景、风格"},
            "filename": _STR | {"description": "保存文件名（可省略），如 深蹲示意图.png"},
        },
        ["prompt"],
    ),
    _spec(
        "read_skill",
        "读取指定 Agent Skill 的 SKILL.md（含操作步骤与模板）。用户要求生成周报时，先调用本工具读取 weekly-report 技能。",
        skills.read_skill,
        {"skill_name": {"type": "string", "enum": ["weekly-report"]}},
        ["skill_name"],
    ),
    _spec(
        "write_weekly_report",
        "⚠️写文件操作：把周训练报告 Markdown 写入项目 output/ 目录（唯一可写目录）。"
        "调用前必须先向用户展示报告内容概要并获得明确同意。",
        skills.write_weekly_report,
        {
            "filename": _STR | {"description": "文件名，如 周训练报告_2026-10-26.md"},
            "content": _STR | {"description": "报告完整 Markdown 正文"},
        },
        ["filename", "content"],
    ),
]

# 供 OpenAI SDK 使用的工具描述（剥离 _func 私有键）
TOOL_SPECS = [{k: v for k, v in spec.items() if k != "_func"} for spec in TOOL_SPECS_RAW]

_REGISTRY = {spec["function"]["name"]: spec for spec in TOOL_SPECS_RAW}


def dispatch(name: str, arguments_json: str) -> dict:
    """执行 LLM 发起的工具调用。任何异常都转为可读的 error 字段（失败可解释）。"""
    spec = _REGISTRY.get(name)
    if spec is None:
        return {"error": f"未知工具：{name}（可用：{'、'.join(_REGISTRY)}）"}
    try:
        args = json.loads(arguments_json) if arguments_json else {}
    except json.JSONDecodeError as e:
        return {"error": f"工具参数不是合法 JSON：{e}"}
    try:
        result = spec["_func"](**args)
        return result if isinstance(result, dict) else {"result": result}
    except TypeError as e:
        return {"error": f"工具参数不匹配：{e}"}
    except Exception as e:
        traceback.print_exc()
        return {"error": f"工具执行出错：{type(e).__name__}: {e}"}
