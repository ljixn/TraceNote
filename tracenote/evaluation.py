"""评测模块：用固定题库量化 Agent 的表现。

为什么需要评测：
- "感觉效果不错"不是证据。同样的题目跑两遍，你才知道改动到底有没有用。
- 自动打分能用同一把尺子比较不同配置（比如检索 1 条 vs 3 条）。

打分规则全部是**确定性规则**（关键词匹配），不用再调一次模型当裁判——
这样既省钱又可复现，同样的答案永远得同样的分。

三类题目：
- answerable   笔记里有完整答案 → 期望：答对 + 带来源引用
- unanswerable 笔记里完全没有   → 期望：明确拒答，不许瞎编
- partial      笔记里只有一部分 → 期望：观察到"用通用知识补充"的倾向（不判对错，只统计）
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .agent import build_agent, run_with_trace
from .tracer import RunTrace

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "evaluation" / "results"

# 拒答用语：命中任一即视为"明确拒答"
REFUSAL_MARKERS = ("无法回答", "没有找到", "不知道", "未找到", "无法确定", "没有相关")

# 引用标记：.md 文件名，或"来源"字样
CITATION_PATTERN = re.compile(r"\.md|来源[:：]")


@dataclass
class EvalCase:
    """一道评测题。"""

    case_id: str
    question: str
    category: str  # answerable / unanswerable / partial
    expected_keywords: tuple[str, ...] = ()  # 答对时答案里应该出现的词
    note: str = ""  # 这道题想测什么


@dataclass
class CaseResult:
    """一道题的结果。"""

    case_id: str
    question: str
    category: str
    answer: str
    passed: bool  # 是否达到该类别的预期
    has_citation: bool  # 答案里有没有来源引用
    refused: bool  # 是否明确拒答
    steps: int
    input_tokens: int
    output_tokens: int
    duration_seconds: float

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class EvalReport:
    """一轮评测的汇总报告。"""

    config_name: str  # 如 "top_k=1" 或 "top_k=3"
    top_k: int
    results: list[CaseResult] = field(default_factory=list)
    started_at: str = ""

    def by_category(self, category: str) -> list[CaseResult]:
        return [r for r in self.results if r.category == category]

    @property
    def accuracy(self) -> float:
        """总体通过率。"""
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    @property
    def refusal_accuracy(self) -> float:
        """不可答题目中，正确拒答的比例（防幻觉核心指标）。"""
        cases = self.by_category("unanswerable")
        if not cases:
            return 0.0
        return sum(1 for r in cases if r.refused) / len(cases)

    @property
    def hallucination_rate(self) -> float:
        """不可答题目中，瞎编答案的比例（越低越好）。"""
        cases = self.by_category("unanswerable")
        if not cases:
            return 0.0
        return sum(1 for r in cases if not r.refused) / len(cases)

    @property
    def citation_rate(self) -> float:
        """可答题目中，带来源引用的比例。"""
        cases = self.by_category("answerable")
        if not cases:
            return 0.0
        return sum(1 for r in cases if r.has_citation) / len(cases)

    @property
    def avg_tokens(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.total_tokens for r in self.results) / len(self.results)

    @property
    def avg_duration(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.duration_seconds for r in self.results) / len(self.results)

    @property
    def avg_steps(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.steps for r in self.results) / len(self.results)

    def summary(self) -> dict:
        return {
            "config": self.config_name,
            "top_k": self.top_k,
            "total_cases": len(self.results),
            "accuracy": round(self.accuracy, 3),
            "refusal_accuracy": round(self.refusal_accuracy, 3),
            "hallucination_rate": round(self.hallucination_rate, 3),
            "citation_rate": round(self.citation_rate, 3),
            "avg_tokens": round(self.avg_tokens, 1),
            "avg_duration_seconds": round(self.avg_duration, 1),
            "avg_steps": round(self.avg_steps, 2),
        }


def score_case(case: EvalCase, trace: RunTrace, answer: str) -> CaseResult:
    """给一道题的答案打分（确定性规则，不用模型当裁判）。"""
    refused = any(marker in answer for marker in REFUSAL_MARKERS)
    has_citation = bool(CITATION_PATTERN.search(answer))

    if case.category == "unanswerable":
        # 不可答：只有明确拒答才算通过；瞎编则失败
        passed = refused
    elif case.category == "answerable":
        # 可答：必须带引用，且包含预期关键词
        keyword_hit = any(kw in answer for kw in case.expected_keywords) if case.expected_keywords else True
        passed = has_citation and keyword_hit and not refused
    else:  # partial：不判对错，只记录行为
        passed = has_citation

    return CaseResult(
        case_id=case.case_id,
        question=case.question,
        category=case.category,
        answer=answer,
        passed=passed,
        has_citation=has_citation,
        refused=refused,
        steps=trace.steps,
        input_tokens=trace.input_tokens,
        output_tokens=trace.output_tokens,
        duration_seconds=trace.duration_seconds,
    )


def run_evaluation(
    cases: list[EvalCase],
    config_name: str,
    top_k: int = 3,
    model_id: str | None = None,
    verbose: bool = True,
) -> EvalReport:
    """跑一轮评测：同一批题，同一个 Agent 配置。

    Args:
        cases: 题库。
        config_name: 这轮配置的名字，如 "top_k=1"。
        top_k: 每次检索返回几条笔记。
        model_id: 覆盖默认模型。
        verbose: 是否打印每题进度。
    """
    from datetime import datetime

    agent = build_agent(model_id=model_id, top_k=top_k)
    report = EvalReport(
        config_name=config_name,
        top_k=top_k,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )

    for i, case in enumerate(cases, 1):
        if verbose:
            print(f"  [{i}/{len(cases)}] {case.case_id} ({case.category}) ... ", end="", flush=True)

        answer, trace = run_with_trace(case.question, agent=agent, reset=True)
        result = score_case(case, trace, answer)
        report.results.append(result)

        if verbose:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} | {result.steps}步 {result.total_tokens}tok {result.duration_seconds:.1f}s")

        # 避免请求过于密集触发限流
        time.sleep(0.5)

    return report


def save_report(report: EvalReport, results_dir: Path = RESULTS_DIR) -> tuple[Path, Path]:
    """保存评测报告：一份明细 JSON + 一份汇总 JSON。返回两个路径。"""
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = report.started_at.replace(":", "").replace("-", "")
    safe_name = report.config_name.replace("=", "_").replace(" ", "")

    detail_path = results_dir / f"{stamp}_{safe_name}_detail.json"
    detail = {
        "config": report.config_name,
        "top_k": report.top_k,
        "started_at": report.started_at,
        "cases": [asdict(r) for r in report.results],
    }
    detail_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_path = results_dir / f"{stamp}_{safe_name}_summary.json"
    summary_path.write_text(
        json.dumps(report.summary(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return detail_path, summary_path
