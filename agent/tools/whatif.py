# -*- coding: utf-8 -*-
"""
What-if 情景模拟工具
移植自衡练 SportHealthAgent（ArkTS）rules/WhatIfSimulator.ets：
  - 7700 kcal ≈ 1kg 体脂经验公式，推算 4/8 周体重变化与累计负荷
"""

KCAL_PER_KG = 7700       # 每公斤体脂约对应热量（kcal/kg，经验值）
LOSS_RATE_WARN = -1.0    # 减脂安全速率下限（kg/周）


def what_if_simulate(current_weight_kg: float, weekly_sessions: int,
                     avg_session_load: float, daily_kcal_delta: int) -> dict:
    """模拟未来趋势。

    :param current_weight_kg: 当前体重（kg）
    :param weekly_sessions: 假设的每周训练次数
    :param avg_session_load: 当前单次平均负荷（0–100，由历史统计得出）
    :param daily_kcal_delta: 假设的每日热量增减（kcal；负 = 缺口）
    """
    daily_delta_kg = daily_kcal_delta / KCAL_PER_KG
    weight4 = round(current_weight_kg + daily_delta_kg * 28, 1)
    weight8 = round(current_weight_kg + daily_delta_kg * 56, 1)
    weekly_load = weekly_sessions * avg_session_load
    load4 = int(round(weekly_load * 4))
    load8 = int(round(weekly_load * 8))

    weekly_rate = daily_delta_kg * 7
    if weekly_rate < LOSS_RATE_WARN:
        note = (f"减重速率 {round(weekly_rate, 2)}kg/周 过快，"
                "建议缩小热量缺口，避免肌肉流失")
    elif daily_kcal_delta < 0:
        note = f"每日缺口 {-daily_kcal_delta} kcal：4 周约 {weight4}kg，8 周约 {weight8}kg"
    elif daily_kcal_delta > 0:
        note = (f"每日盈余 {daily_kcal_delta} kcal：4 周约 {weight4}kg，"
                f"8 周约 {weight8}kg（增肌期建议盈余 ≤ 300 kcal）")
    else:
        note = "热量维持现状：体重预计基本不变"

    return {
        "weight_4_week_kg": weight4,
        "weight_8_week_kg": weight8,
        "load_4_week": load4,
        "load_8_week": load8,
        "note": note,
    }
