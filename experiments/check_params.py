"""逐个测试 smolagents 会附加的请求参数，定位空 choices 的原因。"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

key = os.environ["SILICONFLOW_API_KEY"]
base = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
model_id = os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash")

MESSAGES = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "根据笔记，什么是 Agent？"},
]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search the local study notes and return matching content.",
            "parameters": {
                "type": "object",
                "properties": {"keyword": {"type": "string", "description": "Keyword to search."}},
                "required": ["keyword"],
            },
        },
    }
]


def probe(label, extra):
    payload = {
        "model": model_id,
        "messages": MESSAGES,
        "tools": TOOLS,
        "max_tokens": 1024,
    }
    payload.update(extra)
    try:
        resp = requests.post(
            f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=60
        )
        body = resp.json()
        choices = body.get("choices", [])
        content = choices[0]["message"].get("content") if choices else None
        tool_calls = choices[0]["message"].get("tool_calls") if choices else None
        print(f"[{label}] status={resp.status_code} choices={len(choices)}")
        print(f"    content: {str(content)[:120]}")
        print(f"    tool_calls: {str(tool_calls)[:200]}")
        if not choices:
            print("    raw body:", resp.text[:500])
    except Exception as e:
        print(f"[{label}] FAILED: {type(e).__name__}: {e}")


probe("A: auto（基准）", {"tool_choice": "auto"})
probe("B: required", {"tool_choice": "required"})
probe("C: auto + stop", {"tool_choice": "auto", "stop": ["Observation:", "Calling tools:"]})
probe("D: required + stop", {"tool_choice": "required", "stop": ["Observation:", "Calling tools:"]})
