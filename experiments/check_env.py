"""检查 .env 配置格式，不打印密钥本体。"""

import os

from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("SILICONFLOW_API_KEY", "")
base = os.environ.get("SILICONFLOW_BASE_URL", "")
model = os.environ.get("SILICONFLOW_MODEL", "")

print("Key present:", bool(key) and key.startswith("sk-"), "| length:", len(key))
print("Key has surrounding quotes:", key != key.strip() or key[:1] in {'"', "'"})
print("Base URL:", base)
print("Model ID:", model)
