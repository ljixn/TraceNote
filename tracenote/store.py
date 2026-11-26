"""SQLite FTS5 笔记存储与全文检索。

为什么用 FTS5 而不是 Python 的 `keyword in text`？
- 第一周的字符串包含匹配：只能命中"完全包含该子串"的文本，逐块遍历，块多了就慢；
- FTS5：建倒排索引，按词快速定位到块，还有 BM25 相关度排序——最相关的排在前面。
- SQLite 自带 FTS5，零新依赖，数据就是一个文件，符合"本地优先"。

注意：FTS5 默认分词器对中文不友好（按空白分词）。trigram 分词器
支持子串级匹配，对中英文混排都能工作，是第一版的务实选择。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .loader import Chunk

SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    source,
    title,
    text,
    start_line UNINDEXED,
    tokenize='trigram'
);
"""


@dataclass
class SearchResult:
    """一条检索结果：内容 + 来源，供 Agent 引用。"""

    source: str
    title: str
    start_line: int
    text: str
    rank: float  # BM25 相关度（越小越相关）

    def __repr__(self) -> str:
        preview = self.text[:40].replace("\n", " ")
        return f"SearchResult({self.source}:{self.start_line} [{self.title}] {preview}...)"


class NotesStore:
    """笔记的 SQLite FTS5 存储。"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.execute(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "NotesStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def rebuild(self, chunks: list[Chunk]) -> int:
        """清空并用给定块重建索引，返回入库块数。"""
        self.conn.execute("DELETE FROM notes_fts")
        self.conn.executemany(
            "INSERT INTO notes_fts (source, title, text, start_line) VALUES (?, ?, ?, ?)",
            [(c.source, c.title, c.text, c.start_line) for c in chunks],
        )
        self.conn.commit()
        return len(chunks)

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM notes_fts").fetchone()
        return int(row[0])

    def search(self, query: str, limit: int = 3) -> list[SearchResult]:
        """按 BM25 相关度检索，返回前 limit 条结果。

        策略：
        1. 整串精确匹配（trigram 要求全部三字组命中）；
        2. 无结果时按空白拆词，逐词 OR 匹配——中英混合查询（如"Agent 是什么"）
           整串会因中文部分不命中而落空，拆词后每个词独立贡献召回；
        3. 仍无结果且查询较短（<3 字符，trigram 无三字组可用）时，
           回退到 LIKE 子串匹配兜底。
        """
        for match_expr in self._match_expressions(query):
            sql = (
                "SELECT source, title, start_line, text, rank "
                "FROM notes_fts WHERE notes_fts MATCH ? "
                "ORDER BY rank LIMIT ?"
            )
            rows = self.conn.execute(sql, (match_expr, limit)).fetchall()
            if rows:
                return self._to_results(rows)
        return self._fallback_like(query, limit)

    def _fallback_like(self, query: str, limit: int) -> list[SearchResult]:
        """短查询的 LIKE 兜底；无命中返回空列表。无 rank，用 0.0 占位。"""
        if not query.strip():
            return []
        pattern = f"%{query.strip()}%"
        sql = (
            "SELECT source, title, start_line, text FROM notes_fts "
            "WHERE text LIKE ? OR title LIKE ? LIMIT ?"
        )
        rows = self.conn.execute(sql, (pattern, pattern, limit)).fetchall()
        return [
            SearchResult(source=r[0], title=r[1], start_line=r[2], text=r[3], rank=0.0)
            for r in rows
        ]

    @staticmethod
    def _to_results(rows: list[tuple]) -> list[SearchResult]:
        return [
            SearchResult(source=r[0], title=r[1], start_line=r[2], text=r[3], rank=r[4])
            for r in rows
        ]

    @staticmethod
    def _match_expressions(query: str) -> list[str]:
        escaped = query.replace('"', " ").strip()
        if not escaped:
            return []
        candidates = [f'"{escaped}"']
        words = [w for w in escaped.split() if w]
        if len(words) > 1:
            candidates.append(" OR ".join(f'"{w}"' for w in words))
        return candidates
