# -*- coding: utf-8 -*-
"""
力量科学工具
移植自衡练 SportHealthAgent（ArkTS）rules/StrengthCalculator.ets：
  - Epley / Brzycki 双公式交叉估算 1RM（单次极限重量）
"""

EFFECTIVE_RPE_MIN = 7  # RPE ≥ 7 视为接近力竭的工作组


def estimate_one_rep_max(weight_kg: float, reps: int) -> dict:
    """双公式估算 1RM。

    - Epley：重量 × (1 + 次数/30)
    - Brzycki：重量 × 36/(37 − 次数)（次数 ≥ 37 时退化为 Epley）
    - 次数为 1 时直接取重量本身；非法输入返回全 0 并说明原因。
    """
    if weight_kg is None or reps is None or weight_kg <= 0 or reps <= 0:
        return {"error": "weight_kg 与 reps 必须为正数",
                "epley_kg": 0, "brzycki_kg": 0, "average_kg": 0}
    if reps == 1:
        return {"epley_kg": weight_kg, "brzycki_kg": weight_kg,
                "average_kg": weight_kg,
                "note": "次数为 1，1RM 即该重量本身。"}
    epley = round(weight_kg * (1 + reps / 30), 1)
    brzycki = epley if reps >= 37 else round(weight_kg * 36 / (37 - reps), 1)
    average = round((epley + brzycki) / 2, 1)
    return {
        "epley_kg": epley,
        "brzycki_kg": brzycki,
        "average_kg": average,
        "note": f"Epley {epley}kg / Brzycki {brzycki}kg，推荐采用均值 {average}kg；"
                "正式冲极限请在保护下进行。",
    }


def effective_sets(sets: list) -> dict:
    """统计有效组数与有效容量（RPE/RIR 双轨，有效强度 ≥ 7）。

    :param sets: 组列表，每组 {"weight_kg": .., "reps": .., "rpe": .., "rir": ..}
                 rir 填写时有效强度 = 10 − RIR，否则取 RPE。
    """
    count, volume = 0, 0
    for s in sets:
        rir, rpe = s.get("rir"), s.get("rpe")
        if rir is not None and rir >= 0:
            effective = 10 - rir
        else:
            effective = rpe or 0
        if effective >= EFFECTIVE_RPE_MIN and s.get("reps", 0) > 0:
            count += 1
            volume += s["reps"] * s.get("weight_kg", 0)
    return {
        "effective_sets": count,
        "effective_volume_kg": int(round(volume)),
        "standard": f"有效强度（RPE 或 10−RIR）≥ {EFFECTIVE_RPE_MIN} 的组计入",
    }
