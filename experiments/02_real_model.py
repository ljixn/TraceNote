"""实验 2：接入真实模型（硅基流动 OpenAI 兼容接口），观察模型自主决定是否调用工具。

密钥从项目根目录 .env 读取，.env 已被 Git 忽略，不会提交。
"""

import os

from dotenv import load_dotenv
from smolagents import OpenAIServerModel, ToolCallingAgent, tool

load_dotenv()

API_KEY = os.environ["SILICONFLOW_API_KEY"]
BASE_URL = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL_ID = os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash")


# 第一周的硬编码笔记，下周换成真正的本地文件检索。
NOTES = {
    "agent": "Agent 是一个让模型根据任务和观察结果，自主决定下一步行动的系统。",
    "工具": "工具是 Agent 可以调用的预定义函数，例如查询笔记或读取文件。",
    "max_steps": "最大执行步数用于防止模型陷入无限循环，是 Agent 的安全上限。",
}


@tool
def search_notes(keyword: str) -> str:
    """Search the local study notes and return matching content with its source.

    Use this tool for any question about Agent concepts, notes, or study material.
    Always search before answering from memory.

    Args:
        keyword: A Chinese or English keyword to search for, such as 'Agent', '工具' or 'max_steps'.
    """
    normalized_keyword = keyword.casefold()
    matches = [
        f"来源：{title}.md\n内容：{content}"
        for title, content in NOTES.items()
        if normalized_keyword in f"{title}\n{content}".casefold()
    ]
    return "\n\n".join(matches) if matches else "没有找到相关笔记。"


def build_agent(model_id: str = MODEL_ID) -> ToolCallingAgent:
    model = OpenAIServerModel(
        model_id=model_id,
        api_base=BASE_URL,
        api_key=API_KEY,
        temperature=0.2,
        # 硅基流动不支持 tool_choice="required"（smolagents 默认值），会返回空 choices。
        # auto 模式下模型同样会自主决定是否调用工具，实测可用。
        tool_choice="auto",
    )
    return ToolCallingAgent(
        tools=[search_notes],
        model=model,
        max_steps=5,
        verbosity_level=2,
    )


def main():
    agent = build_agent()

    questions = [
        "根据笔记，什么是 Agent？",
        "法国的首都是哪里？",  # 答案不在笔记里：观察模型是否还去调用工具
    ]

    for question in questions:
        print("\n" + "#" * 60)
        print("问题：", question)
        print("#" * 60)
        answer = agent.run(question)
        print("\n>>> 最终答案：", answer)


if __name__ == "__main__":
    main()
