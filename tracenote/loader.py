"""Markdown 文档导入与切块（chunking）。

为什么需要切块？
- 模型的上下文窗口有限，且按 token 计费：整篇笔记直接塞给模型既贵又容易超限；
- 检索粒度粗：一篇 2000 字的笔记里只有一段与问题相关时，返回整篇会稀释关键信息。
- 切成小段后，检索命中的是"最相关的那一段"，答案的引用也更精确。

切块策略（第一版，够用就好）：
- 优先按二级/三级标题（## / ###）分节，一节一个块；
- 超过 max_chars 的节再按段落边界二分；
- 每个块记录来源文件和行号，供引用溯源。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_CHARS = 600


@dataclass
class Chunk:
    """一个可被检索的笔记片段。"""

    source: str  # 来源文件相对路径，如 "notes/agent.md"
    start_line: int  # 块在原文件中的起始行号（1-based）
    title: str  # 所属标题（无标题时用文件名）
    text: str  # 块内容

    def __repr__(self) -> str:
        preview = self.text[:40].replace("\n", " ")
        return f"Chunk({self.source}:{self.start_line} [{self.title}] {preview}...)"


def split_by_headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """按 Markdown 标题切分，返回 (起始行, 结束行, 标题) 列表（行号为 1-based，含端点）。

    没有任何标题时，整篇作为一个块返回。
    """
    boundaries: list[tuple[int, str]] = []  # (行号, 标题)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and stripped.lstrip("#").startswith(" "):
            if 1 <= len(stripped) - len(stripped.lstrip("#")) <= 3:  # # 到 ### 级标题
                boundaries.append((idx, stripped.lstrip("# ").strip()))

    if not boundaries:
        return [(0, len(lines) - 1, "")]

    sections: list[tuple[int, int, str]] = []
    for i, (start, title) in enumerate(boundings := boundaries):
        end = boundaries[i + 1][0] - 1 if i + 1 < len(boundaries) else len(lines) - 1
        # 标题行本身归入这一节
        sections.append((start, end, title))

    # 标题之前的内容（如果有）归为文件级引言块
    if boundaries[0][0] > 0:
        sections.insert(0, (0, boundaries[0][0] - 1, ""))
    return sections


def split_long_text(text: str, max_chars: int) -> list[str]:
    """把超长文本按段落边界切开；段落本身超长时按 max_chars 硬切。"""
    if len(text) <= max_chars:
        return [text]

    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    parts: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                parts.append(current)
            if len(para) <= max_chars:
                current = para
            else:  # 单段超长，硬切
                for i in range(0, len(para), max_chars):
                    parts.append(para[i : i + max_chars])
                current = ""
    if current:
        parts.append(current)
    return parts


def chunk_markdown(path: Path, base_dir: Path, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """读取单个 Markdown 文件并切块。

    Args:
        path: 文件绝对路径。
        base_dir: 用于计算相对路径的基准目录（通常为 data/）。
        max_chars: 单块最大字符数。
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    source = path.relative_to(base_dir).as_posix()
    file_title = path.stem

    chunks: list[Chunk] = []
    for start, end, heading in split_by_headings(lines):
        section_lines = lines[start : end + 1]
        section_text = "\n".join(section_lines).strip()
        if not section_text:
            continue

        title = heading or file_title
        for piece in split_long_text(section_text, max_chars):
            chunks.append(
                Chunk(
                    source=source,
                    start_line=start + 1,
                    title=title,
                    text=piece,
                )
            )
    return chunks


def load_notes(notes_dir: Path, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """扫描目录下所有 .md 文件并切块返回。"""
    chunks: list[Chunk] = []
    for path in sorted(notes_dir.rglob("*.md")):
        chunks.extend(chunk_markdown(path, notes_dir, max_chars))
    return chunks
