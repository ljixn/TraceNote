"""TraceNote Agent 工具与构建逻辑。

第二周核心变化：search_notes 从"硬编码 3 条笔记"升级为
"SQLite FTS5 检索本地知识库"。Agent 其余部分不动——这就是
工具与编排解耦的价值。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from smolagents import OpenAIServerModel, ToolCallingAgent, tool

from .loader import load_notes
from .store import NotesStore

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NOTES_DIR = ROOT / "data" / "notes"
DEFAULT_DB_PATH = ROOT / "data" / "notes.db"


@tool
def search_notes(query: str) -> str:
    """Search the personal knowledge base of Markdown notes and return matching passages with their sources.

    Use this tool for any question about Agent concepts, RAG, retrieval, study methods,
    or any knowledge that might exist in the notes. Always search before answering.
    If the tool returns no results, say you don't know instead of guessing.

    Args:
        query: A search query in Chinese or English, e.g. 'Agent 是什么', '为什么需要切块', 'BM25'.
    """
    with NotesStore(DEFAULT_DB_PATH) as store:
        results = store.search(query, limit=3)

    if not results:
        return "知识库中没有找到相关内容。请如实告知用户：根据现有笔记无法回答。"

    parts = []
    for r in results:
        parts.append(f"来源：{r.source}（第 {r.start_line} 行起，标题：{r.title}）\n{r.text}")
    return "\n\n---\n\n".join(parts)


def rebuild_index(notes_dir: Path = DEFAULT_NOTES_DIR, db_path: Path = DEFAULT_DB_PATH) -> int:
    """重建知识库索引：导入 notes_dir 下所有 .md 并写入 db_path。返回块数。"""
    chunks = load_notes(notes_dir)
    with NotesStore(db_path) as store:
        return store.rebuild(chunks)


def build_agent(model_id: str | None = None) -> ToolCallingAgent:
    model = OpenAIServerModel(
        model_id=model_id or os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash"),
        api_base=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        api_key=os.environ["SILICONFLOW_API_KEY"],
        temperature=0.2,
        # 硅基流动不支持 tool_choice="required"（smolagents 默认），返回空 choices。
        tool_choice="auto",
    )
    return ToolCallingAgent(
        tools=[search_notes],
        model=model,
        max_steps=5,
        verbosity_level=2,
        # 拒答规则：写进系统提示，让模型在笔记查不到时老实说"不知道"，不瞎编。
        instructions=(
            "你是 TraceNote，一个基于个人笔记的知识问答助手。\n"
            "回答规则：\n"
            "1. 回答任何知识性问题时，必须先调用 search_notes 查笔记。\n"
            "2. 回答中必须标明信息来源（文件名和标题），没有来源的内容不要说。\n"
            "3. 如果 search_notes 返回【没有找到相关内容】，必须明确告诉用户"
            "【根据现有笔记无法回答这个问题】，不要根据你自己的知识猜测。\n"
            "4. 回答用中文，结构清晰，可以用分点和加粗。"
        ),
    )
