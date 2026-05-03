"""检查 DeepSeek API 连通性"""
import httpx
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY", "")
base_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com")

print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
print(f"Base URL: {base_url}")

# 测试连通性
try:
    r = httpx.get("https://api.deepseek.com", timeout=10)
    print(f"DeepSeek 首页: {r.status_code}")
except Exception as e:
    print(f"DeepSeek 首页访问失败: {e}")

# 测试 /models
try:
    r = httpx.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10
    )
    print(f"/models: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        ids = [m.get("id") for m in data.get("data", [])]
        print(f"可用模型: {ids[:5]}")
    else:
        print(f"错误: {r.text[:200]}")
except Exception as e:
    print(f"/models 失败: {e}")

# 测试简单对话
try:
    r = httpx.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "说个你好"}],
            "max_tokens": 50,
        },
        timeout=30
    )
    print(f"简单对话: {r.status_code}")
    if r.status_code == 200:
        result = r.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"回复: {content[:200]}")
    else:
        print(f"错误: {r.text[:300]}")
except Exception as e:
    print(f"对话失败: {e}")
