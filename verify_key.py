# -*- coding: utf-8 -*-
"""
百炼 API Key 验证脚本（填完 .env 后第一步跑它）

用法：.venv\Scripts\python verify_key.py
成功：打印模型返回的一句问候，说明密钥与网络都通。
失败：打印具体原因与排查建议。
"""
import os

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI


def main():
    key = os.getenv("DASHSCOPE_API_KEY", "")
    if not key or "你的密钥" in key:
        print("❌ 尚未填写密钥：请用记事本打开 .env，把 DASHSCOPE_API_KEY=sk-你的密钥")
        print("   中的「sk-你的密钥」替换为百炼控制台复制的真实 Key，保存后重跑本脚本。")
        return
    print(f"① 已读取密钥：{key[:6]}****{key[-4:]}（.env 文件，不会进 Git）")
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("MODEL_NAME", "qwen-plus")
    print(f"② 端点：{base_url}　模型：{model}")

    client = OpenAI(api_key=key, base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "只回复四个字：密钥验证成功"}],
            max_tokens=16,
        )
        print(f"③ 模型返回：{resp.choices[0].message.content}")
        print("✅ 百炼 Key 验证通过！可以启动应用：.venv\\Scripts\\streamlit run app.py")
    except Exception as e:
        print(f"❌ 调用失败：{type(e).__name__}: {e}")
        print("排查建议：")
        print("  - 401/InvalidApiKey：Key 复制不完整或已删除，去百炼控制台重新创建")
        print("  - 403/AccessDenied：未开通「模型服务」，在百炼控制台首页开通（有免费额度）")
        print("  - 超时/连接错误：检查代理或网络；也可把 OPENAI_BASE_URL 换成 Ollama 等本地端点")


if __name__ == "__main__":
    main()
