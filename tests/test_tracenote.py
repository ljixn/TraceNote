"""tracenote 包的单元测试：切块、入库、检索，不调用模型、不花钱。"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.loader import Chunk, chunk_markdown, load_notes, split_by_headings, split_long_text
from tracenote.store import NotesStore
from tracenote.agent import build_agent

NOTES_DIR = ROOT / "data" / "notes"


@pytest.fixture
def store(tmp_path):
    chunks = load_notes(NOTES_DIR)
    with NotesStore(tmp_path / "test.db") as s:
        s.rebuild(chunks)
        yield s


class TestSplitByHeadings:
    def test_no_headings_returns_whole_file(self):
        assert split_by_headings(["正文一行", "正文两行"]) == [(0, 1, "")]

    def test_headings_split_sections(self):
        lines = ["# 标题一", "内容A", "## 小节", "内容B"]
        sections = split_by_headings(lines)
        assert len(sections) == 2
        assert sections[0] == (0, 1, "标题一")
        assert sections[1] == (2, 3, "小节")

    def test_content_before_first_heading(self):
        lines = ["引言", "# 标题", "内容"]
        sections = split_by_headings(lines)
        assert sections[0] == (0, 0, "")
        assert sections[1] == (1, 2, "标题")


class TestSplitLongText:
    def test_short_text_unchanged(self):
        assert split_long_text("短文本", 100) == ["短文本"]

    def test_long_text_split_by_paragraph(self):
        paras = ["A" * 300, "B" * 300]
        text = "\n\n".join(paras)
        parts = split_long_text(text, 400)
        assert len(parts) == 2

    def test_oversize_paragraph_hard_split(self):
        parts = split_long_text("X" * 1500, 600)
        assert len(parts) == 3
        assert all(len(p) <= 600 for p in parts)


class TestChunkMarkdown:
    def test_chunks_have_source_and_lines(self):
        chunks = chunk_markdown(NOTES_DIR / "agent.md", NOTES_DIR)
        assert len(chunks) >= 4
        assert all(c.source == "agent.md" for c in chunks)
        assert all(c.start_line >= 1 for c in chunks)
        titles = {c.title for c in chunks}
        assert "什么是 Agent" in titles

    def test_load_notes_all_files(self):
        chunks = load_notes(NOTES_DIR)
        sources = {c.source for c in chunks}
        assert {"agent.md", "learning.md", "retrieval.md"} == sources


class TestNotesStore:
    def test_rebuild_and_count(self, store):
        assert store.count() == len(load_notes(NOTES_DIR))

    def test_search_chinese_english_mix(self, store):
        results = store.search("Agent 是什么")
        assert len(results) > 0
        assert any("agent.md" in r.source for r in results)

    def test_search_short_query_falls_back_to_like(self, store):
        results = store.search("切块")  # 2 字查询：trigram 不可用，走 LIKE 兜底
        assert len(results) > 0
        assert any("切块" in r.text for r in results)

    def test_search_rank_ordering(self, store):
        results = store.search("为什么需要切块")
        assert len(results) > 0
        ranks = [r.rank for r in results]
        assert ranks == sorted(ranks)  # BM25 负值：数值越小越相关，升序排列

    def test_search_no_result_returns_empty(self, store):
        assert store.search("巴黎铁塔的高度") == []

    def test_search_result_fields(self, store):
        results = store.search("BM25")
        assert results
        r = results[0]
        assert r.source == "retrieval.md"
        assert r.title == "FTS5 与 BM25"
        assert isinstance(r.start_line, int)
        assert "FTS5" in r.text or "BM25" in r.text


class TestAgentInstructions:
    """拒答规则测试：不调用模型，只验证 instructions 被正确设置。"""

    def test_instructions_contains_refusal_rule(self):
        # build_agent 会读 .env，但 instructions 是静态字符串，不依赖网络
        try:
            agent = build_agent()
        except KeyError:
            pytest.skip("SILICONFLOW_API_KEY 未配置，跳过 Agent 构建测试")
        assert "无法回答" in agent.instructions
        assert "search_notes" in agent.instructions
        assert "来源" in agent.instructions
