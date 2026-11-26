"""第二周第 1 阶段验证：导入切块 + FTS5 检索，不调用模型、不花钱。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.loader import load_notes
from tracenote.store import NotesStore

NOTES_DIR = ROOT / "data" / "notes"
DB_PATH = ROOT / "data" / "notes.db"

chunks = load_notes(NOTES_DIR)
print(f"导入 {len(chunks)} 个块：")
for c in chunks:
    print("  ", c)

with NotesStore(DB_PATH) as store:
    n = store.rebuild(chunks)
    print(f"\n入库 {n} 块 → {DB_PATH}")

    for query in ["Agent 是什么", "为什么需要切块", "BM25", "巴黎"]:
        results = store.search(query)
        print(f"\n查询「{query}」→ {len(results)} 条结果")
        for r in results:
            print(f"  - {r.source}:{r.start_line} [{r.title}] rank={r.rank:.2f}")
            print(f"    {r.text[:60]}...")
