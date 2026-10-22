# -*- coding: utf-8 -*-
"""
工具层单元测试（pytest）
覆盖：负荷估算公式、三档边界、互补映射、疲劳加权、1RM 双公式、
饮食规划校验、What-if、Skill 读取与写入沙箱（权限隔离）。
运行：python -m pytest tests/ -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import training, diet, strength, whatif, skills
from agent.tools.registry import TOOL_SPECS, dispatch


# ---------- LangChain 工具封装层（path-a 分支，供 LangGraph 后端） ----------
def test_lc_tools_wrapped():
    from agent.tools.lc_tools import TOOLS
    assert len(TOOLS) == len(TOOL_SPECS)  # 两种后端工具数量一致（10 个）
    names = {t.name for t in TOOLS}
    assert {"evaluate_training", "write_weekly_report", "read_skill"} <= names


def test_lc_tool_invoke():
    from agent.tools.lc_tools import estimate_one_rep_max as lc_1rm
    import json as _json
    out = _json.loads(lc_1rm.invoke({"weight_kg": 80, "reps": 5}))
    assert out["average_kg"] > 0


# ---------- 负荷估算公式 ----------
def test_load_formula_basic():
    # 60min × factor=1（心率 200 → (200-60)/140=1）→ 60
    assert training.estimate_training_load(60, 200) == 60
    # 心率 60 → factor 下限 0.1 → 30min × 0.1 = 3
    assert training.estimate_training_load(30, 60) == 3


def test_load_formula_clamped():
    assert training.estimate_training_load(300, 200) == 100   # 上限 100
    assert training.estimate_training_load(0, 150) == 0       # 时长 0


# ---------- 训练评估三档（边界 50 / 80）----------
def test_evaluate_three_tiers():
    # 负荷 = 时长 × min(1, max(0.1, (心率-60)/140))，预期值均按公式推算
    high = training.evaluate_training("力量", 90, 200, 800)   # 90×1.0=90 → 超标
    assert high["load_status"] == "超标" and high["suggested_recovery_hours"] == 36
    normal = training.evaluate_training("跑步", 90, 150, 400)  # 90×0.643≈58 → 正常
    assert normal["load_status"] == "正常" and normal["suggested_recovery_hours"] == 18
    low = training.evaluate_training("步行", 30, 90, 100)      # 30×0.214≈6 → 偏低
    assert low["load_status"] == "偏低" and low["suggested_recovery_hours"] == 8
    # 边界值
    assert training.evaluate_training("跑步", 5, 0, 0, training_load=80)["load_status"] == "超标"
    assert training.evaluate_training("跑步", 5, 0, 0, training_load=79)["load_status"] == "正常"
    assert training.evaluate_training("跑步", 5, 0, 0, training_load=50)["load_status"] == "正常"
    assert training.evaluate_training("跑步", 5, 0, 0, training_load=49)["load_status"] == "偏低"


# ---------- 互补训练映射 ----------
def test_next_workout_mapping():
    assert training.plan_next_workout("跑步", 60)["workout_type"] == "力量/核心"
    assert training.plan_next_workout("力量", 60)["workout_type"] == "有氧慢跑 + 全身拉伸"
    assert training.plan_next_workout("HIIT", 60)["workout_type"] == "主动恢复"
    assert training.plan_next_workout("瑜伽", 30)["workout_type"] == "力量/有氧"
    assert training.plan_next_workout("未知类型", 30)["workout_type"] == "交替上下肢"
    # 负荷超标优先级最高
    assert training.plan_next_workout("力量", 90)["workout_type"] == "主动恢复（拉伸/散步）"


# ---------- 疲劳模型 ----------
def test_fatigue_weighted():
    # 7 天每天 50 → 加权 50×(7+6+5+4+3+2+1)=1400 → /14 = 100
    assert training.compute_fatigue([50] * 7)["fatigue_index"] == 100
    # 全 0 → 低
    r = training.compute_fatigue([0] * 7)
    assert r["fatigue_index"] == 0 and r["fatigue_level"] == "低"
    # 中档：每天 20 → 20×28/14 = 40 → 中
    r = training.compute_fatigue([20] * 7)
    assert r["fatigue_index"] == 40 and r["fatigue_level"] == "中" and r["recovery_factor"] == 1.2
    # 高档：≥70
    r = training.compute_fatigue([100, 100, 100, 0, 0, 0, 0])
    assert r["fatigue_index"] >= 70 and r["recovery_factor"] == 1.5


# ---------- 1RM 双公式 ----------
def test_one_rep_max():
    r = strength.estimate_one_rep_max(100, 1)
    assert r["average_kg"] == 100
    r = strength.estimate_one_rep_max(100, 5)
    assert abs(r["epley_kg"] - 116.7) < 0.1          # 100×(1+5/30)
    assert abs(r["brzycki_kg"] - 112.5) < 0.1        # 100×36/32
    assert strength.estimate_one_rep_max(0, 5)["average_kg"] == 0
    assert "error" in strength.estimate_one_rep_max(100, 0)


def test_effective_sets_rir_track():
    sets = [
        {"weight_kg": 80, "reps": 8, "rpe": 8},     # 有效
        {"weight_kg": 60, "reps": 12, "rpe": 5},    # 无效（RPE<7）
        {"weight_kg": 40, "reps": 15, "rir": 2},    # 有效（10-2=8 ≥ 7）
        {"weight_kg": 30, "reps": 15, "rir": 5},    # 无效（10-5=5）
    ]
    r = strength.effective_sets(sets)
    assert r["effective_sets"] == 2
    assert r["effective_volume_kg"] == 80 * 8 + 40 * 15


# ---------- 饮食规划 ----------
def test_diet_mifflin():
    r = diet.plan_daily_diet("男", 70, 175, 25, "增肌")
    assert r["bmr_kcal"] == int(round(10 * 70 + 6.25 * 175 - 5 * 25 + 5))  # 1724
    assert r["target_kcal_training_day"] == r["tdee_kcal"] + 300
    assert "disclaimer" in r and "非医疗诊断" in r["disclaimer"]
    # 减脂修正 −500
    r2 = diet.plan_daily_diet("女", 55, 162, 22, "减脂")
    assert r2["target_kcal_training_day"] == r2["tdee_kcal"] - 500
    # 非训练日碳水下调 50g
    assert r["carb_g_rest_day"] == max(0, r["carb_g_training_day"] - 50)


def test_diet_validation():
    assert "error" in diet.plan_daily_diet("X", 70, 175, 25, "增肌")
    assert "error" in diet.plan_daily_diet("男", 70, 175, 25, "变瘦")
    assert "error" in diet.plan_daily_diet("男", 70, 175, 25, "增肌", activity_level="超人")


def test_recovery_meal_overload():
    r = diet.recovery_meal_plan(500, 85)
    assert r["supplement_kcal"] == 300                # 500 × 0.6
    r2 = diet.recovery_meal_plan(500, 50)
    assert r2["supplement_kcal"] == 500


# ---------- What-if ----------
def test_what_if():
    r = whatif.what_if_simulate(70, 4, 50, -500)
    assert abs(r["weight_4_week_kg"] - round(70 - 500 / 7700 * 28, 1)) < 0.01
    assert r["load_4_week"] == 4 * 50 * 4
    assert "缺口" in r["note"]
    # 减重过快告警：每日 -1500 kcal → 约 -1.36kg/周 < -1.0
    r2 = whatif.what_if_simulate(70, 4, 50, -1500)
    assert "过快" in r2["note"]


# ---------- Skill 与写入沙箱 ----------
def test_read_skill():
    r = skills.read_skill("weekly-report")
    assert "content" in r and "周训练报告" in r["content"]
    assert "error" in skills.read_skill("hack-skill")


def test_write_sandbox(tmp_path, monkeypatch):
    # 危险文件名被清洗：不得逃逸 output/
    r = skills.write_weekly_report("..\\..\\evil.md", "# t")
    assert ".." not in os.path.relpath(r["path"], skills.OUTPUT_DIR)
    assert os.path.isfile(r["path"])
    os.remove(r["path"])
    # 空内容拒绝写入
    assert "error" in skills.write_weekly_report("x.md", "   ")


# ---------- 注册表 ----------
def test_registry_dispatch():
    r = dispatch("estimate_one_rep_max", '{"weight_kg": 100, "reps": 5}')
    assert r["average_kg"] > 0
    assert "error" in dispatch("no_such_tool", "{}")
    assert "error" in dispatch("estimate_one_rep_max", "not-json")
    assert len(TOOL_SPECS) >= 8
