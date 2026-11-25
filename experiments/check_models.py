"""查询硅基流动可用模型列表，确认实验 2 使用的模型 ID 存在且支持工具调用。"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

key = os.environ["SILICONFLOW_API_KEY"]
base = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")

resp = requests.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
print("HTTP status:", resp.status_code)

if resp.ok:
    data = resp.json().get("data", [])
    print("Total models:", len(data))
    for m in data:
        model_id = m.get("id", "")
        if any(tag in model_id.lower() for tag in ("deepseek", "glm", "qwen")):
            print(" -", model_id)
else:
    print("Response body:", resp.text[:500])
