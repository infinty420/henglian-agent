# -*- coding: utf-8 -*-
"""
衡练 MCP 服务器（路径 A 加分项：1 个 MCP 服务器，不少于 2 个工具）

基于官方 MCP Python SDK（FastMCP），通过 stdio 传输对外暴露 5 个运动健康
业务工具。任意支持 MCP 的客户端（Claude Desktop / Open WebUI / 自研客户端）
均可即插即用；本仓库附带最小客户端演示 mcp_client_demo.py。

运行：python mcp_server.py          # stdio 模式，由客户端拉起，一般不直接交互
演示：python mcp_client_demo.py     # 一键验证服务器与工具调用
"""
import json

# MCP Python SDK 2.x：FastMCP 已更名为 MCPServer（1.x 时代为 mcp.server.fastmcp.FastMCP）
from mcp.server.mcpserver import MCPServer

from agent.tools import training, diet, strength, whatif

mcp = MCPServer(
    name="henglian-sport-health",
    instructions="衡练运动健康工具集：训练评估、疲劳模型、饮食规划、1RM 估算、What-if 模拟。",
)


@mcp.tool()
def evaluate_training(sport_type: str, duration_min: float,
                      avg_heart_rate: float = 0, calories: float = 0) -> str:
    """评估一次训练：按时长与平均心率估算训练负荷（0-100），给出三档评估（超标/正常/偏低）与建议恢复时长。"""
    return json.dumps(training.evaluate_training(sport_type, duration_min,
                                                 avg_heart_rate, calories),
                      ensure_ascii=False)


@mcp.tool()
def compute_fatigue(loads_recent_first: list) -> str:
    """按最近 7 天每日总负荷计算疲劳指数（0-100，越近权重越高）与恢复系数。下标 0=今天，无训练的天填 0。"""
    return json.dumps(training.compute_fatigue(loads_recent_first), ensure_ascii=False)


@mcp.tool()
def plan_daily_diet(gender: str, weight_kg: float, height_cm: float, age: int,
                    goal: str, activity_level: str = "中度活动",
                    is_training_day: bool = True) -> str:
    """按 Mifflin-St Jeor 公式计算每日热量目标、双碳水方案、蛋白质与饮水目标（增肌/减脂/维持）。"""
    return json.dumps(diet.plan_daily_diet(gender, weight_kg, height_cm, age,
                                           goal, activity_level, is_training_day),
                      ensure_ascii=False)


@mcp.tool()
def estimate_one_rep_max(weight_kg: float, reps: int) -> str:
    """用 Epley 与 Brzycki 双公式估算单次极限重量 1RM（kg）。"""
    return json.dumps(strength.estimate_one_rep_max(weight_kg, reps), ensure_ascii=False)


@mcp.tool()
def what_if_simulate(current_weight_kg: float, weekly_sessions: int,
                     avg_session_load: float, daily_kcal_delta: int) -> str:
    """What-if 情景模拟：假设每周训练次数与每日热量增减，推算 4/8 周后的体重与累计训练负荷。"""
    return json.dumps(whatif.what_if_simulate(current_weight_kg, weekly_sessions,
                                              avg_session_load, daily_kcal_delta),
                      ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()  # stdio 传输
