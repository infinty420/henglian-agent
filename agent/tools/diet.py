# -*- coding: utf-8 -*-
"""
饮食规划工具
移植自衡练 SportHealthAgent（ArkTS）rules/DietPlanner.ets：
  - Mifflin-St Jeor 基础代谢率 + TDEE + 目标修正（增肌 +300 / 减脂 −500 / 维持 0）
  - 双碳水周期化（训练日/非训练日）
  - 运动后恢复餐宏量配比（蛋白 30% / 碳水 50% / 脂肪 20%，负荷超标时热量下调 60%）
"""

KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARB = 4
KCAL_PER_G_FAT = 9

DIET_DISCLAIMER = "以上为日常营养参考，非医疗诊断；如有基础疾病请遵医嘱。"

ACTIVITY_FACTORS = {
    "久坐": 1.2,
    "轻度活动": 1.375,
    "中度活动": 1.4,
    "高强度活动": 1.55,
    "运动员": 1.725,
}


def mifflin_bmr(gender: str, weight_kg: float, height_cm: float, age: int) -> int:
    """Mifflin-St Jeor 基础代谢率：10×kg + 6.25×cm − 5×age +（男 5 / 女 −161）"""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return int(round(base + (-161 if gender == "女" else 5)))


def plan_daily_diet(gender: str, weight_kg: float, height_cm: float, age: int,
                    goal: str, activity_level: str = "中度活动",
                    is_training_day: bool = True) -> dict:
    """每日热量与双碳水方案（原项目 DietPlanner.dailyPlan）。

    :param gender: 性别（男/女）
    :param goal: 目标（增肌/减脂/维持）
    :param activity_level: 活动水平（久坐/轻度活动/中度活动/高强度活动/运动员）
    :param is_training_day: 当日是否训练日（影响碳水分配）
    """
    if gender not in ("男", "女"):
        return {"error": "gender 仅支持「男」或「女」"}
    if goal not in ("增肌", "减脂", "维持"):
        return {"error": "goal 仅支持「增肌」「减脂」「维持」"}
    factor = ACTIVITY_FACTORS.get(activity_level)
    if factor is None:
        return {"error": f"activity_level 仅支持：{'/'.join(ACTIVITY_FACTORS)}"}

    bmr = mifflin_bmr(gender, weight_kg, height_cm, age)
    tdee = int(round(bmr * factor))
    adjust = {"增肌": 300, "减脂": -500, "维持": 0}[goal]
    target_kcal = max(1200, tdee + adjust)

    protein_g = int(round(weight_kg * 1.6))                    # 1.6 g/kg
    fat_g = int(round(target_kcal * 0.25 / KCAL_PER_G_FAT))    # 脂肪占 25%
    training_carb_g = max(0, int(round(
        (target_kcal - protein_g * KCAL_PER_G_PROTEIN - fat_g * KCAL_PER_G_FAT) / KCAL_PER_G_CARB)))
    rest_carb_g = max(0, training_carb_g - 50)                 # 非训练日碳水 −50g
    rest_kcal = max(1000, target_kcal - 200)
    water_ml = int(round(weight_kg * 35))

    return {
        "bmr_kcal": bmr,
        "tdee_kcal": tdee,
        "target_kcal_training_day": target_kcal,
        "target_kcal_rest_day": rest_kcal,
        "protein_g_per_day": protein_g,
        "fat_g_per_day": fat_g,
        "carb_g_training_day": training_carb_g,
        "carb_g_rest_day": rest_carb_g,
        "water_target_ml": water_ml,
        "today_is_training_day": is_training_day,
        "today_target_kcal": target_kcal if is_training_day else rest_kcal,
        "today_carb_g": training_carb_g if is_training_day else rest_carb_g,
        "timing_tips": [
            "训练前 1–2 小时：以碳水为主的正餐（约当日碳水的 25%）",
            "训练后 30 分钟内：蛋白质 20–40g + 快吸收碳水，促进恢复",
            "非训练日：碳水下调约 50g，蛋白质保持不变",
            f"全天饮水目标约 {water_ml} ml，训练中每 15–20 分钟补水 150–250 ml",
        ],
        "food_reference": {
            "蛋白质": ["鸡胸肉", "鸡蛋", "希腊酸奶", "豆腐"],
            "碳水": ["燕麦", "糙米", "红薯", "全麦面包"],
            "脂肪": ["牛油果", "坚果", "橄榄油"],
        },
        "disclaimer": DIET_DISCLAIMER,
    }


def recovery_meal_plan(calories: float, training_load: float) -> dict:
    """运动后恢复餐宏量配比（原项目 DietPlanner.plan 模块②）：
    蛋白 30% / 碳水 50% / 脂肪 20%；负荷 ≥ 80 时补充热量下调为消耗的 60%。
    """
    if calories <= 0:
        return {"error": "calories 必须大于 0"}
    overloaded = training_load >= 80
    total_kcal = int(round(calories * (0.6 if overloaded else 1.0)))
    protein_g = int(round(total_kcal * 0.30 / KCAL_PER_G_PROTEIN))
    carb_g = int(round(total_kcal * 0.50 / KCAL_PER_G_CARB))
    fat_g = int(round(total_kcal * 0.20 / KCAL_PER_G_FAT))
    return {
        "supplement_kcal": total_kcal,
        "protein_g": protein_g,
        "carb_g": carb_g,
        "fat_g": fat_g,
        "macro_ratio": "蛋白质 30% / 碳水 50% / 脂肪 20%",
        "note": "本次负荷超标，额外补充热量已下调为消耗的 60%，以清淡易消化为主。"
                if overloaded else "按运动恢复配比补充营养即可。",
        "disclaimer": DIET_DISCLAIMER,
    }
