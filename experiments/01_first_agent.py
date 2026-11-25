"""实验 1：不调用真实模型，跑通一次完整的工具调用循环。

这个模拟模型只用于观察 Agent 的工作方式，不代表真正的智能。
"""

from smolagents import ChatMessage, ChatMessageToolCall, MessageRole, Model, ToolCallingAgent, tool
from smolagents.models import ChatMessageToolCallFunction


# 这是我们的“个人笔记”。下周会换成真正的本地文件和检索工具。
NOTES = {
    "agent": "Agent 是一个让模型根据任务和观察结果，自主决定下一步行动的系统。",
    "工具": "工具是 Agent 可以调用的预定义函数，例如查询笔记或读取文件。",
}


SEARCH_CALL_COUNT = 0


@tool
def search_notes(keyword: str) -> str:
    """Search the local study notes and return matching content with its source.

    Args:
        keyword: A Chinese keyword to search for, such as 'Agent' or '工具'.
    """
    global SEARCH_CALL_COUNT
    SEARCH_CALL_COUNT += 1

    # .casefold() 让英文关键词匹配不区分大小写。
    normalized_keyword = keyword.casefold()
    matches = [
        f"来源：{title}.md\n内容：{content}"
        for title, content in NOTES.items()
        if normalized_keyword in f"{title}\n{content}".casefold()
    ]
    return "\n\n".join(matches) if matches else "没有找到相关笔记。"


class ScriptedTeachingModel(Model):
    """按固定脚本回答的假模型：先查资料，再根据观察结果作答。"""

    def __init__(self):
        super().__init__()
        self.call_count = 0

    def generate(self, messages, tools_to_call_from=None, stop_sequences=None, **kwargs):
        self.call_count += 1

        if self.call_count == 1:
            print("\n[模拟模型] 我需要查询笔记，请求调用 search_notes。")
            return self._tool_call(
                name="search_notes",
                arguments={"keyword": "Agent"},
                call_id="call_search",
            )

        # 第二次调用时，messages 已包含工具返回的观察结果。
        tool_result = str(messages[-1])
        print("\n[模拟模型] 我收到了工具结果：")
        print(tool_result)
        answer = (
            "根据学习笔记，Agent 会让模型结合任务和观察结果，"
            "自主决定下一步行动。来源：agent.md"
        )
        return self._tool_call(
            name="final_answer",
            arguments={"answer": answer},
            call_id="call_final",
        )

    @staticmethod
    def _tool_call(name, arguments, call_id):
        return ChatMessage(
            role=MessageRole.ASSISTANT,
            content=None,
            tool_calls=[
                ChatMessageToolCall(
                    id=call_id,
                    type="function",
                    function=ChatMessageToolCallFunction(
                        name=name,
                        arguments=arguments,
                    ),
                )
            ],
        )


def main():
    model = ScriptedTeachingModel()
    agent = ToolCallingAgent(
        tools=[search_notes],
        model=model,
        max_steps=4,
        verbosity_level=2,
    )

    answer = agent.run("什么是 Agent？请根据笔记回答。")

    print("\n" + "=" * 60)
    print("最终答案：", answer)
    print("模型被调用次数：", model.call_count)
    print("工具实际被调用次数：", SEARCH_CALL_COUNT)
    print("=" * 60)
    print("注意：工具函数由 Agent 框架执行，不是模型自己执行。")


if __name__ == "__main__":
    main()
