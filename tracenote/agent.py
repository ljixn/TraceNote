"""TraceNote Agent 工具与构建逻辑。

- 工具层：search_notes 查 SQLite FTS5 本地知识库；
- 运行层：run_with_trace() 包装 Agent，存运行档案 + 友好报错。
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from smolagents import OpenAIServerModel, Tool, ToolCallingAgent

from .errors import to_friendly_message
from .loader import load_notes
from .store import NotesStore
from .tracer import RunTrace, extract_token_usage, extract_tool_calls, new_trace, save_trace

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NOTES_DIR = ROOT / "data" / "notes"
DEFAULT_DB_PATH = ROOT / "data" / "notes.db"


class NotesSearchTool(Tool):
    """搜索本地笔记知识库的工具。

    为什么写成类而不是 @tool 函数：检索条数 top_k 需要在构造时配置，
    这样才能做 A/B 对比（同一批题，查 1 条 vs 查 3 条）。
    """

    name = "search_notes"
    description = (
        "Search the personal knowledge base of Markdown notes and return matching passages with their sources. "
        "Use this tool for any question about Agent concepts, RAG, retrieval, study methods, "
        "or any knowledge that might exist in the notes. Always search before answering. "
        "If the tool returns no results, say you don't know instead of guessing."
    )
    inputs = {
        "query": {
            "type": "string",
            "description": "A search query in Chinese or English, e.g. 'Agent 是什么', '为什么需要切块', 'BM25'.",
        }
    }
    output_type = "string"

    def __init__(self, db_path: Path = DEFAULT_DB_PATH, top_k: int = 3):
        super().__init__()
        self.db_path = db_path
        self.top_k = top_k

    def forward(self, query: str) -> str:
        with NotesStore(self.db_path) as store:
            results = store.search(query, limit=self.top_k)

        if not results:
            return "知识库中没有找到相关内容。请如实告知用户：根据现有笔记无法回答。"

        parts = []
        for r in results:
            parts.append(f"来源：{r.source}（第 {r.start_line} 行起，标题：{r.title}）\n{r.text}")
        return "\n\n---\n\n".join(parts)


# 默认工具实例：网页界面和其他调用方使用 top_k=3
search_notes = NotesSearchTool()


def rebuild_index(notes_dir: Path = DEFAULT_NOTES_DIR, db_path: Path = DEFAULT_DB_PATH) -> int:
    """重建知识库索引：导入 notes_dir 下所有 .md 并写入 db_path。返回块数。"""
    chunks = load_notes(notes_dir)
    with NotesStore(db_path) as store:
        return store.rebuild(chunks)


def build_agent(model_id: str | None = None, top_k: int = 3) -> ToolCallingAgent:
    """构建 Agent。

    Args:
        model_id: 覆盖 .env 里的模型名。
        top_k: 每次检索返回几条笔记。评测时用来做 A/B 对比。
    """
    model = OpenAIServerModel(
        model_id=model_id or os.environ.get("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V4.1-Flash"),
        api_base=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        api_key=os.environ["SILICONFLOW_API_KEY"],
        temperature=0.2,
        # 硅基流动不支持 tool_choice="required"（smolagents 默认），返回空 choices。
        tool_choice="auto",
    )
    tool_instance = search_notes if top_k == 3 else NotesSearchTool(top_k=top_k)
    return ToolCallingAgent(
        tools=[tool_instance],
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


def run_with_trace(question: str, agent: ToolCallingAgent | None = None, reset: bool = True) -> tuple[str, RunTrace]:
    """运行一次问答：返回答案 + 运行档案，出错时给出友好提示而不是报错堆栈。

    这是网页界面和实验脚本统一使用的入口。
    档案自动保存到 runs/ 目录（该目录不进 Git）。

    Args:
        question: 用户问题。
        agent: 复用的 Agent 实例；不传则新建一个。
        reset: True 清空 Agent 记忆开始新对话；False 接着上轮对话。
    """
    trace = new_trace(question)
    agent = agent or build_agent()
    start = time.monotonic()

    try:
        trace.answer = agent.run(question, reset=reset)
    except Exception as e:
        trace.error = to_friendly_message(e)
        trace.answer = trace.error
    finally:
        trace.duration_seconds = time.monotonic() - start
        trace.steps = len(getattr(agent.memory, "steps", []))
        trace.tool_calls = extract_tool_calls(agent)
        trace.input_tokens, trace.output_tokens = extract_token_usage(agent)
        save_trace(trace)

    return trace.answer, trace
