"""验证 tool_choice=auto 能让硅基流动接口正常返回。"""

import os

from dotenv import load_dotenv
from smolagents import OpenAIServerModel

load_dotenv()

model = OpenAIServerModel(
    model_id=os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash"),
    api_base=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
    api_key=os.environ["SILICONFLOW_API_KEY"],
    temperature=0.2,
    tool_choice="auto",
)

message = model.generate(
    [{"role": "user", "content": "根据笔记，什么是 Agent？请调用工具查询。"}],
    tools_to_call_from=None,
)

print("content:", str(message.content)[:300])
print("tool_calls:", message.tool_calls)
