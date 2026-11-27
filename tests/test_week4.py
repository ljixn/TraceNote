"""第四周功能测试：运行记录、友好报错、运行档案保存。不调用真实模型、不花钱。"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.agent import run_with_trace
from tracenote.errors import TraceNoteError, to_friendly_message
from tracenote.tracer import RunTrace, ToolCallRecord, extract_tool_calls, new_trace, save_trace


class TestTracer:
    def test_new_trace_has_id_and_question(self):
        trace = new_trace("什么是 Agent？")
        assert trace.run_id
        assert trace.question == "什么是 Agent？"
        assert trace.answer == ""
        assert trace.error == ""

    def test_save_and_load_trace(self, tmp_path):
        trace = new_trace("测试问题")
        trace.answer = "测试答案"
        trace.steps = 3
        trace.tool_calls = [ToolCallRecord(tool_name="search_notes", arguments={"query": "Agent"})]

        path = save_trace(trace, tmp_path)
        data = json.loads(path.read_text(encoding="utf-8"))

        assert data["question"] == "测试问题"
        assert data["answer"] == "测试答案"
        assert data["steps"] == 3
        assert data["tool_calls"][0]["tool_name"] == "search_notes"
        assert data["tool_calls"][0]["arguments"] == {"query": "Agent"}

    def test_summary_text_with_tool_calls(self):
        trace = new_trace("什么是 Agent？")
        trace.answer = "答案"
        trace.steps = 2
        trace.duration_seconds = 1.5
        trace.input_tokens = 100
        trace.output_tokens = 50
        trace.tool_calls = [ToolCallRecord(tool_name="search_notes", arguments={"query": "Agent"})]

        summary = trace.summary_text()
        assert "步骤数：2" in summary
        assert "1.5 秒" in summary
        assert "输入 100 + 输出 50 = 150" in summary
        assert "search_notes" in summary

    def test_summary_text_error(self):
        trace = new_trace("问题")
        trace.error = "模型服务响应超时了。"
        summary = trace.summary_text()
        assert "运行状态：出错" in summary
        assert "超时" in summary


class TestExtractToolCalls:
    """用一个假 Agent 结构验证从 memory.steps 提取工具调用。"""

    def test_extracts_calls(self):
        class FakeCall:
            def __init__(self, name, args):
                self.name = name
                self.arguments = args

        class FakeStep:
            def __init__(self, calls):
                self.tool_calls = calls

        class FakeMemory:
            steps = [
                FakeStep([FakeCall("search_notes", {"query": "A"})]),
                FakeStep([FakeCall("search_notes", {"query": "B"}), FakeCall("final_answer", {"answer": "x"})]),
                FakeStep(None),  # 有的步骤没有工具调用
            ]

        class FakeAgent:
            memory = FakeMemory()

        records = extract_tool_calls(FakeAgent())
        assert len(records) == 3
        assert records[0].tool_name == "search_notes"
        assert records[1].arguments == {"query": "B"}
        assert records[2].tool_name == "final_answer"


class TestFriendlyErrors:
    @pytest.mark.parametrize(
        "message, expected_keyword",
        [
            ("401 Unauthorized", "密钥"),
            ("Connection timed out", "超时"),
            ("connection refused", "网络"),
            ("insufficient balance quota", "额度"),
            ("model not exist", "模型名称"),
        ],
    )
    def test_translate(self, message, expected_keyword):
        friendly = to_friendly_message(Exception(message))
        assert expected_keyword in friendly

    def test_unknown_error_fallback(self):
        friendly = to_friendly_message(Exception("weird internal xyz"))
        assert "出了点问题" in friendly

    def test_tracenote_error_carries_message(self):
        err = TraceNoteError("给用户的提示", original=ValueError("底层错误"))
        assert err.user_message == "给用户的提示"
        assert isinstance(err.original, ValueError)


class TestRunWithTrace:
    """验证 run_with_trace 的完整流程：正常回答 + 出错时的友好处理。"""

    def test_success_run(self, tmp_path, monkeypatch):
        """用一个假的 build_agent 代替真实模型，验证记录流程。"""
        import tracenote.agent as agent_module
        import tracenote.tracer as tracer_module

        class FakeAgent:
            def __init__(self):
                self.memory = type("M", (), {"steps": []})()

            def run(self, question, reset=True):
                return "这是假答案"

        monkeypatch.setattr(agent_module, "build_agent", lambda: FakeAgent())
        monkeypatch.setattr(agent_module, "save_trace", lambda t, runs_dir=tracer_module.DEFAULT_RUNS_DIR: save_trace(t, tmp_path))

        answer, trace = run_with_trace("什么是 Agent？")

        assert answer == "这是假答案"
        assert trace.error == ""
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 1

    def test_error_becomes_friendly_message(self, tmp_path, monkeypatch):
        """模拟网络超时，验证用户看到的是友好提示而不是报错堆栈。"""
        import tracenote.agent as agent_module
        import tracenote.tracer as tracer_module

        class FailingAgent:
            def __init__(self):
                self.memory = type("M", (), {"steps": []})()

            def run(self, question, reset=True):
                raise TimeoutError("Connection timed out after 60s")

        monkeypatch.setattr(agent_module, "build_agent", lambda: FailingAgent())
        monkeypatch.setattr(agent_module, "save_trace", lambda t, runs_dir=tracer_module.DEFAULT_RUNS_DIR: save_trace(t, tmp_path))

        answer, trace = run_with_trace("什么是 Agent？")

        assert "超时" in answer
        assert "Traceback" not in answer  # 用户看不到报错堆栈
        assert trace.error
        saved = list(tmp_path.glob("*.json"))
        assert len(saved) == 1  # 出错的运行也被记录下来了
