"""实验 5：验证拒答规则生效（不启动网页，只跑两个问题）。

- 问题 1：笔记里有答案 → 应该带来源回答
- 问题 2：笔记里没答案 → 应该说"不知道"而不是瞎编
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.agent import build_agent
from tracenote.store import NotesStore

DB_PATH = ROOT / "data" / "notes.db"

with NotesStore(DB_PATH) as store:
    print(f"知识库块数：{store.count()}")

agent = build_agent()

questions = [
    "什么是 Agent？请根据笔记回答。",
    "法国的首都是哪里？请根据笔记回答。",  # 笔记里没有
]

for q in questions:
    print("\n" + "=" * 60)
    print("问题：", q)
    answer = agent.run(q)
    print("回答：", answer)
