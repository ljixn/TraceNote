import importlib.util
from pathlib import Path


EXPERIMENT = Path(__file__).parents[1] / "experiments" / "01_first_agent.py"
SPEC = importlib.util.spec_from_file_location("first_agent", EXPERIMENT)
first_agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(first_agent)


def test_search_notes_finds_agent():
    result = first_agent.search_notes("agent")

    assert "Agent 是一个" in result
    assert "agent.md" in result


def test_search_notes_handles_missing_content():
    assert first_agent.search_notes("不存在的笔记") == "没有找到相关笔记。"


def test_agent_completes_tool_call_loop():
    model = first_agent.ScriptedTeachingModel()
    agent = first_agent.ToolCallingAgent(
        tools=[first_agent.search_notes],
        model=model,
        max_steps=4,
        verbosity_level=0,
    )

    answer = agent.run("什么是 Agent？请根据笔记回答。")

    assert "自主决定下一步行动" in answer
    assert model.call_count == 2
    assert first_agent.SEARCH_CALL_COUNT >= 1
