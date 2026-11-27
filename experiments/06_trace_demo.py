"""实验 6：真实模型 + 运行记录（黑匣子）。

跑两个问题，每次问答后打印运行详情，并展示保存的 JSON 档案。
档案保存在 runs/ 目录（不进 Git）。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.agent import build_agent, run_with_trace

agent = build_agent()

questions = [
    "根据笔记，FTS5 和 BM25 是什么关系？",
    "法国的首都在哪里？",
]

for question in questions:
    print("\n" + "=" * 60)
    print("问题：", question)
    answer, trace = run_with_trace(question, agent=agent)
    print("\n回答：", answer[:300])
    print("\n" + trace.summary_text())

runs_dir = ROOT / "runs"
saved = sorted(runs_dir.glob("*.json"))
print(f"\n\n已保存 {len(saved)} 份运行档案到 {runs_dir}")
print("最新一份：", saved[-1].name if saved else "无")
