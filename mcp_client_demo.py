# -*- coding: utf-8 -*-
"""
MCP 客户端演示（课堂现场可跑，无需 API Key、无需联网到模型）

流程：以子进程拉起 mcp_server.py（stdio 传输）→ MCP 握手 initialize
→ list_tools 列出服务器工具 → call_tool 实际调用 1RM 估算 → 打印结果。
证明 MCP 服务器真实可用（课程要求项③的 MCP 路径）。

运行：python mcp_client_demo.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server.py"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
)


async def main():
    print("① 拉起 MCP 服务器（stdio）…")
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("② 握手成功，服务器：henglian-sport-health")

            tools = await session.list_tools()
            print(f"③ 服务器暴露 {len(tools.tools)} 个工具：")
            for t in tools.tools:
                print(f"   - {t.name}：{(t.description or '').splitlines()[0]}")

            print("\n④ 调用 estimate_one_rep_max(weight_kg=80, reps=5)…")
            result = await session.call_tool("estimate_one_rep_max",
                                             {"weight_kg": 80, "reps": 5})
            print("   返回：", result.content[0].text)

            print("\n⑤ 调用 evaluate_training(力量, 90min, 心率125)…")
            result = await session.call_tool(
                "evaluate_training",
                {"sport_type": "力量", "duration_min": 90, "avg_heart_rate": 125})
            print("   返回：", result.content[0].text)

            print("\n✅ MCP 服务器验证通过（握手 / 列工具 / 实际调用均正常）")


if __name__ == "__main__":
    asyncio.run(main())
