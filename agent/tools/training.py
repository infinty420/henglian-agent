# -*- coding: utf-8 -*-
"""
训练评估 / 互补训练规划 / 疲劳模型
移植自衡练 SportHealthAgent（ArkTS）：
  - rules/TrainingEvaluator.ets   负荷三档评估
  - rules/NextWorkoutPlanner.ets  互补训练映射表
  - rules/FatigueModel.ets        7 天负荷加权疲劳指数
  - model/HealthRecord.ets        负荷估算公式
"""

# ---------- 规则参数（与原项目 RuleConfig 默认值一致，可调） ----------
LOAD_HIGH = 80          # 负荷「超标」阈值
LOAD_NORMAL = 50        # 负荷「正常」下限

# 运动类型（中文 → 互补分支）
AEROBIC_ENDURANCE = {"跑步", "骑行", "游泳", "跳绳", "椭圆机", "动感单车", "爬楼机"}


def estimate_training_load(duration_min: float, avg_heart_rate: float) -> int:
    """负荷估算公式（原项目 HealthRecord.ets）：
    负荷 = round(时长 × min(1, max(0.1, (平均心率-60)/140)))，限幅 0–100。
    """
    if duration_min <= 0:
        return 0
    factor = min(1.0, max(0.1, (avg_heart_rate - 60) / 140))
    return int(round(min(100, max(0, duration_min * factor))))


def evaluate_training(sport_type: str, duration_min: float,
                      avg_heart_rate: float = 0, calories: float = 0,
                      training_load: float = None) -> dict:
    """模块①：本次训练评估（负荷三档 + 恢复时长建议）。

    :param sport_type: 运动类型（力量/跑步/骑行/游泳/HIIT/瑜伽/步行/跳绳 等）
    :param duration_min: 训练时长（分钟）
    :param avg_heart_rate: 平均心率（次/分），用于缺失负荷时估算
    :param calories: 消耗热量（kcal），供饮食工具参考
    :param training_load: 训练负荷 0–100；缺省时按公式估算
    """
    load_estimated = training_load is None
    if training_load is None:
        training_load = estimate_training_load(duration_min, avg_heart_rate)

    if training_load >= LOAD_HIGH:
        result = {
            "load": training_load,
            "load_status": "超标",
            "recovery_status": "需充分恢复",
            "suggested_recovery_hours": 36,
            "advice": "本次训练负荷超标，身体处于高疲劳状态。建议 24–48 小时内避免高强度训练，"
                      "优先睡眠与主动恢复（拉伸、散步），并关注静息心率变化。",
        }
    elif training_load >= LOAD_NORMAL:
        result = {
            "load": training_load,
            "load_status": "正常",
            "recovery_status": "常规恢复",
            "suggested_recovery_hours": 18,
            "advice": "本次训练负荷正常。建议 12–24 小时常规恢复，补充水分与营养，"
                      "下一次训练可按计划进行。",
        }
    else:
        result = {
            "load": training_load,
            "load_status": "偏低",
            "recovery_status": "快速恢复",
            "suggested_recovery_hours": 8,
            "advice": "本次训练负荷偏低，身体可快速恢复（<12 小时）。"
                      "若目标是提升体能，可适当提高下次训练的强度或时长。",
        }

    result.update({
        "sport_type": sport_type,
        "duration_min": duration_min,
        "avg_heart_rate": avg_heart_rate,
        "calories": calories,
        "load_estimated_by_formula": load_estimated,
    })
    return result


def plan_next_workout(sport_type: str, training_load: float) -> dict:
    """模块③：下一次互补训练规划（运动互补原则查表推导）。"""
    if training_load >= LOAD_HIGH:
        return {
            "workout_type": "主动恢复（拉伸/散步）",
            "intensity": "低",
            "duration_min": 20,
            "reason": "本次负荷超标，身体需要充分恢复；以低强度主动恢复促进血液循环、"
                      "加速代谢废物清除，避免叠加疲劳。",
        }
    if sport_type == "力量":
        return {
            "workout_type": "有氧慢跑 + 全身拉伸",
            "intensity": "低-中",
            "duration_min": 25,
            "reason": "力量训练以无氧供能与肌纤维微损伤为主，互补低-中强度有氧可促进恢复"
                      "并提升心肺基础，拉伸缓解肌肉紧张。",
        }
    if sport_type in AEROBIC_ENDURANCE:
        return {
            "workout_type": "力量/核心",
            "intensity": "中",
            "duration_min": 30,
            "reason": "本次为有氧耐力训练，互补力量/核心训练可增强肌群支撑与动作经济性，"
                      "降低运动损伤风险。",
        }
    if sport_type == "HIIT":
        return {
            "workout_type": "主动恢复",
            "intensity": "低",
            "duration_min": 20,
            "reason": "高强度间歇对神经与心肺系统刺激大，下一次以低强度主动恢复为主，"
                      "防止过度疲劳累积。",
        }
    if sport_type in ("瑜伽", "拉伸"):
        return {
            "workout_type": "力量/有氧",
            "intensity": "中",
            "duration_min": 30,
            "reason": "瑜伽/拉伸以柔韧与放松为主，互补中等强度力量或有氧训练，"
                      "均衡发展力量与心肺能力。",
        }
    if sport_type == "步行":
        return {
            "workout_type": "力量",
            "intensity": "中",
            "duration_min": 25,
            "reason": "步行强度较低，互补中等强度力量训练可有效提升肌肉量与基础代谢。",
        }
    return {
        "workout_type": "交替上下肢",
        "intensity": "中",
        "duration_min": 30,
        "reason": "本次训练类型较特殊，采用上下肢交替训练，在一侧肌群工作时另一侧恢复，"
                  "实现互补刺激。",
    }


def compute_fatigue(loads_recent_first: list) -> dict:
    """疲劳模型：近 7 天负荷按权重 [7,6,5,4,3,2,1]（越近越大）加权求和，
    以「7 天每天中等负荷 50」为满分基准（350）归一化到 0–100。

    :param loads_recent_first: 最近 7 天每日总负荷列表，下标 0 = 今天（最近一天），
                               下标 1 = 昨天，以此类推；不足 7 天按已有天数计算。
    """
    weighted = 0.0
    for age_days, load in enumerate(loads_recent_first[:7]):
        if load and load > 0:
            weighted += load * (7 - age_days)
    index = min(100, int(round(weighted / 14)))

    if index >= 70:
        level, factor = "高", 1.5
    elif index >= 40:
        level, factor = "中", 1.2
    else:
        level, factor = "低", 1.0
    return {
        "fatigue_index": index,
        "fatigue_level": level,
        "recovery_factor": factor,
        "advice": f"近 7 天疲劳指数 {index}（{level}）。"
                  + ("疲劳偏高，建议安排休息日或主动恢复，训练强度下调。" if index >= 70
                     else "疲劳中等，注意睡眠与营养，恢复时长建议上浮 20%。" if index >= 40
                     else "疲劳较低，可按计划正常训练。"),
    }
