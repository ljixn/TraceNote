"""TraceNote 网页界面。

用 Gradio 搭一个聊天网页：用户输入问题 → Agent 查笔记 → 带引用的回答。
启动后浏览器打开本地地址就能用，也能分享链接给别人。
"""

from __future__ import annotations

import sys
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tracenote.agent import rebuild_index, run_with_trace
from tracenote.store import NotesStore

DB_PATH = ROOT / "data" / "notes.db"


def ensure_index() -> int:
    """确保知识库索引存在且非空，不存在则重建。返回当前块数。"""
    with NotesStore(DB_PATH) as store:
        count = store.count()
    if count == 0:
        count = rebuild_index()
    return count


def chat(question: str, history: list) -> str:
    """处理用户提问：调用 Agent，回答 + 本次运行详情。

    run_with_trace 会自动保存运行档案到 runs/，出错时给出友好提示。
    """
    answer, trace = run_with_trace(question, reset=True)
    return f"{answer}\n\n---\n\n{trace.summary_text()}"


def build_ui() -> gr.Blocks:
    """构建网页界面。"""
    chunk_count = ensure_index()

    with gr.Blocks(title="TraceNote - 个人知识库问答") as ui:
        gr.Markdown(
            f"# TraceNote · 个人知识库问答\n\n"
            f"当前知识库已加载 **{chunk_count} 个笔记片段**。\n\n"
            f"提问后，AI 会自动检索你的笔记，给出**带来源引用**的回答。\n"
            f"如果笔记里没有相关内容，会如实告诉你『不知道』。\n"
            f"每次问答都会保存运行档案到 `runs/` 目录，可回看工具调用过程。"
        )

        gr.ChatInterface(
            fn=chat,
            title="TraceNote",
            description="基于本地 Markdown 笔记的智能问答 Agent",
            examples=[
                "什么是 Agent？",
                "为什么笔记要切块？",
                "FTS5 和普通字符串搜索有什么区别？",
                "法国的首都在哪里？",  # 笔记里没有，测试拒答
            ],
        )

    return ui


if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="127.0.0.1", server_port=7860, share=False)
