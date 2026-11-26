"""实验 4：真实模型 + 本地知识库（SQLite FTS5）的完整 Agent。

先确保索引存在（不存在则重建），再让模型自主检索本地笔记回答问题。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.agent import build_agent, rebuild_index
from tracenote.store import NotesStore

DB_PATH = ROOT / "data" / "notes.db"

with NotesStore(DB_PATH) as store:
    count = store.count()
print(f"当前索引块数：{count}")
if count == 0:
    n = rebuild_index()
    print(f"索引为空，已重建：{n} 块")

agent = build_agent()

questions = [
    "根据我的笔记，Agent 和普通的 RAG 有什么区别？",
    "我的笔记里提到遇到问题该怎么学习？",
]

for question in questions:
    print("\n" + "#" * 60)
    print("问题：", question)
    print("#" * 60)
    answer = agent.run(question)
    print("\n>>> 最终答案：", answer)
