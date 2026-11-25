"""直接调用硅基流动接口，查看原始返回结构，定位 choices 为空的原因。"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

key = os.environ["SILICONFLOW_API_KEY"]
base = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
model_id = os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash")

payload = {
    "model": model_id,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用一句话回答：法国的首都是哪里？"},
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "search_notes",
                "description": "Search the local study notes.",
                "parameters": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
            },
        }
    ],
    "tool_choice": "auto",
    "max_tokens": 512,
}

resp = requests.post(f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=60)
print("HTTP status:", resp.status_code)
print("Raw response:", resp.text[:2000])
