"""检查 default_llm_client 返回什么"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generator.llm_client import default_llm_client, DeepSeekChatClient

client = default_llm_client()
print(f"client 类型: {type(client).__name__}")
print(f"client 标识: {id(client)}")

if hasattr(client, "_api_key"):
    key = client._api_key
    print(f"api_key: {key[:8]}...{key[-4:]}" if key else "api_key: (空)")
if hasattr(client, "_api_root"):
    print(f"api_root: {client._api_root}")
if hasattr(client, "_model"):
    print(f"model: {client._model}")

# 直接看 os.getenv
from dotenv import load_dotenv
load_dotenv()
print(f"env DEEPSEEK_API_KEY: {os.getenv('DEEPSEEK_API_KEY', '')[-4:]}")

# 检查 DeepSeekChatClient().configured
c = DeepSeekChatClient()
print(f"DeepSeekChatClient().configured: {c.configured}")
