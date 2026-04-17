"""
DeepSeek API 客户端
"""
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL, API_TIMEOUT, MAX_RETRIES

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API 调用封装"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.model = model or DEEPSEEK_MODEL
        self.timeout = API_TIMEOUT
        
    def _make_request(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """发送API请求"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(
                    f"{self.api_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES})")
                if attempt == MAX_RETRIES - 1:
                    raise
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
                
    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """对话生成"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self._make_request(messages, temperature)
    
    def chat_with_history(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """带历史记录的对话"""
        return self._make_request(messages, temperature)
    
    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """生成JSON格式响应"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = self._make_request(messages, temperature=0.3)
        return self._parse_json_response(response)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        response = response.strip()
        
        # 尝试提取代码块中的JSON
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
        if json_match:
            response = json_match.group(1)
        else:
            # 尝试直接解析
            json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
            if json_match:
                response = json_match.group(1)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}\n响应内容: {response[:500]}")
            raise ValueError(f"无法解析JSON响应: {e}")
