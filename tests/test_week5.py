"""第五周评测模块的单元测试。不调用真实模型、不花钱。"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.evaluation import (
    CaseResult,
    EvalCase,
    EvalReport,
    score_case,
    save_report,
)
from tracenote.tracer import new_trace


def make_trace(steps=2, input_tokens=100, output_tokens=50, duration=1.5):
    t = new_trace("测试")
    t.steps = steps
    t.input_tokens = input_tokens
    t.output_tokens = output_tokens
    t.duration_seconds = duration
    return t


class TestScoreCase:
    def test_answerable_pass_with_citation_and_keyword(self):
        case = EvalCase(case_id="T1", question="什么是 Agent？", category="answerable", expected_keywords=("模型", "工具"))
        result = score_case(case, make_trace(), "来源：agent.md，Agent 由模型和工具组成。")
        assert result.passed is True
        assert result.has_citation is True

    def test_answerable_fail_without_citation(self):
        case = EvalCase(case_id="T2", question="什么是 Agent？", category="answerable", expected_keywords=("模型",))
        result = score_case(case, make_trace(), "Agent 由模型和工具组成。")
        assert result.passed is False
        assert result.has_citation is False

    def test_answerable_fail_when_refused(self):
        case = EvalCase(case_id="T3", question="什么是 Agent？", category="answerable", expected_keywords=("模型",))
        result = score_case(case, make_trace(), "根据现有笔记无法回答这个问题。来源：无")
        assert result.passed is False
        assert result.refused is True

    def test_unanswerable_pass_when_refused(self):
        case = EvalCase(case_id="T4", question="法国首都？", category="unanswerable")
        result = score_case(case, make_trace(), "根据现有笔记无法回答这个问题。")
        assert result.passed is True
        assert result.refused is True

    def test_unanswerable_fail_when_hallucinated(self):
        case = EvalCase(case_id="T5", question="法国首都？", category="unanswerable")
        result = score_case(case, make_trace(), "法国的首都是巴黎。")
        assert result.passed is False
        assert result.refused is False

    def test_partial_only_requires_citation(self):
        case = EvalCase(case_id="T6", question="混合问题？", category="partial")
        result = score_case(case, make_trace(), "这部分笔记有：来源：a.md")
        assert result.passed is True


class TestEvalReport:
    def _report_with(self, results):
        return EvalReport(config_name="test", top_k=3, results=results)

    def _case_result(self, category, passed, refused, citation, tokens=150):
        return CaseResult(
            case_id="x",
            question="q",
            category=category,
            answer="a",
            passed=passed,
            has_citation=citation,
            refused=refused,
            steps=1,
            input_tokens=100,
            output_tokens=tokens - 100,
            duration_seconds=1.0,
        )

    def test_accuracy(self):
        r = self._report_with(
            [
                self._case_result("answerable", True, False, True),
                self._case_result("answerable", False, False, False),
            ]
        )
        assert r.accuracy == 0.5

    def test_refusal_accuracy_and_hallucination(self):
        r = self._report_with(
            [
                self._case_result("unanswerable", True, True, False),
                self._case_result("unanswerable", False, False, False),
            ]
        )
        assert r.refusal_accuracy == 0.5
        assert r.hallucination_rate == 0.5

    def test_citation_rate_only_counts_answerable(self):
        r = self._report_with(
            [
                self._case_result("answerable", True, False, True),
                self._case_result("unanswerable", True, True, False),  # 拒答题不算进引用率
            ]
        )
        assert r.citation_rate == 1.0

    def test_empty_report_no_crash(self):
        r = self._report_with([])
        assert r.accuracy == 0.0
        assert r.refusal_accuracy == 0.0
        assert r.avg_tokens == 0.0

    def test_summary_dict_keys(self):
        r = self._report_with([self._case_result("answerable", True, False, True)])
        s = r.summary()
        for key in ("config", "top_k", "accuracy", "refusal_accuracy", "hallucination_rate", "citation_rate"):
            assert key in s


class TestSaveReport:
    def test_saves_two_files(self, tmp_path):
        report = EvalReport(config_name="top_k=3", top_k=3, started_at="2026-11-28T10:00:00")
        report.results = [
            CaseResult("c1", "q", "answerable", "a", True, True, False, 1, 10, 5, 1.0)
        ]
        detail_path, summary_path = save_report(report, tmp_path)
        assert detail_path.exists()
        assert summary_path.exists()
        assert "detail" in detail_path.name
        assert "summary" in summary_path.name


class TestSearchToolConfig:
    """验证 top_k 可配置（A/B 对比的基础）。"""

    def test_default_top_k_is_3(self):
        from tracenote.agent import search_notes

        assert search_notes.top_k == 3

    def test_custom_top_k_limits_results(self):
        from tracenote.agent import NotesSearchTool

        tool1 = NotesSearchTool(top_k=1)
        tool3 = NotesSearchTool(top_k=3)
        assert tool1.top_k == 1
        assert tool3.top_k == 3

        hits1 = tool1("Agent").count("来源：")
        hits3 = tool3("Agent").count("来源：")
        assert hits1 == 1
        assert hits3 >= hits1
