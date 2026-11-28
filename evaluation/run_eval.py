"""跑评测：同一批题目分别用 top_k=1 和 top_k=3 跑一遍，对比效果。

用法：
    python -X utf8 -m evaluation.run_eval            # 跑两轮对比
    python -X utf8 -m evaluation.run_eval --topk 3   # 只跑一轮
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evaluation.cases import CASES
from tracenote.evaluation import run_evaluation, save_report


def print_summary(report) -> None:
    s = report.summary()
    print(f"\n{'=' * 60}")
    print(f"配置：{s['config']}（每次检索 {s['top_k']} 条）")
    print(f"{'=' * 60}")
    print(f"  题目总数：{s['total_cases']}")
    print(f"  总体通过率：{s['accuracy']:.1%}")
    print(f"  拒答准确率（不可答题）：{s['refusal_accuracy']:.1%}")
    print(f"  幻觉率（不可答题瞎编）：{s['hallucination_rate']:.1%}")
    print(f"  引用率（可答题带来源）：{s['citation_rate']:.1%}")
    print(f"  平均 token：{s['avg_tokens']:.0f}")
    print(f"  平均耗时：{s['avg_duration_seconds']:.1f} 秒")
    print(f"  平均步数：{s['avg_steps']:.2f}")

    fails = [r for r in report.results if not r.passed]
    if fails:
        print(f"\n  未通过题目（{len(fails)} 道）：")
        for r in fails:
            print(f"    - {r.case_id} [{r.category}] 拒答={r.refused} 引用={r.has_citation}")


def main():
    parser = argparse.ArgumentParser(description="TraceNote 评测")
    parser.add_argument("--topk", type=int, nargs="*", default=[1, 3], help="要对比的检索条数")
    args = parser.parse_args()

    all_reports = []
    for top_k in args.topk:
        print(f"\n{'#' * 60}")
        print(f"# 开始评测：top_k={top_k}，共 {len(CASES)} 道题")
        print(f"{'#' * 60}")
        report = run_evaluation(CASES, config_name=f"top_k={top_k}", top_k=top_k)
        all_reports.append(report)
        print_summary(report)

        detail_path, summary_path = save_report(report)
        print(f"\n  明细：{detail_path.relative_to(ROOT)}")
        print(f"  汇总：{summary_path.relative_to(ROOT)}")

    if len(all_reports) >= 2:
        print(f"\n{'=' * 60}")
        print("对比结果")
        print(f"{'=' * 60}")
        base, other = all_reports[0], all_reports[1]
        print(f"  指标            {base.config_name:<12} {other.config_name:<12} 差异")
        print(f"  总体通过率       {base.accuracy:<12.1%} {other.accuracy:<12.1%} {other.accuracy - base.accuracy:+.1%}")
        print(f"  拒答准确率       {base.refusal_accuracy:<12.1%} {other.refusal_accuracy:<12.1%} {other.refusal_accuracy - base.refusal_accuracy:+.1%}")
        print(f"  引用率           {base.citation_rate:<12.1%} {other.citation_rate:<12.1%} {other.citation_rate - base.citation_rate:+.1%}")
        print(f"  平均 token       {base.avg_tokens:<12.0f} {other.avg_tokens:<12.0f} {other.avg_tokens - base.avg_tokens:+.0f}")
        print(f"  平均耗时(秒)     {base.avg_duration:<12.1f} {other.avg_duration:<12.1f} {other.avg_duration - base.avg_duration:+.1f}")


if __name__ == "__main__":
    main()
