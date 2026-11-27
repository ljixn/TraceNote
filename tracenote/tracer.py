"""运行记录（Trace）模块：每次问答存一份"黑匣子档案"。

解决的问题：以前 Agent 答错了，你只能看到最终答案，没法回看中间过程——
它查了几次笔记？用了什么关键词？哪一步开始走歪的？花了多少 token？

现在每次问答存一份 JSON 档案到 runs/ 目录，包含：
- 用户问题、最终答案
- 每一步：模型调了什么工具、传了什么参数、工具返回了什么
- token 用量和耗时

runs/ 目录已被 .gitignore 排除，里面可能有你的提问内容，不会提交到 GitHub。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNS_DIR = ROOT / "runs"


@dataclass
class ToolCallRecord:
    """一次工具调用的记录。"""

    tool_name: str  # 调了什么工具，如 search_notes
    arguments: dict  # 传了什么参数，如 {"query": "Agent 是什么"}


@dataclass
class RunTrace:
    """一次完整问答的档案。"""

    run_id: str
    question: str
    answer: str = ""
    error: str = ""  # 友好报错信息；为空表示没出错
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    steps: int = 0  # Agent 走了几步
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0.0
    started_at: str = ""

    def summary_text(self) -> str:
        """生成给用户看的"本次运行详情"文本。"""
        if self.error:
            return f"**运行状态：出错**\n\n{self.error}"

        lines = ["**本次运行详情**\n"]
        lines.append(f"- 步骤数：{self.steps}")
        lines.append(f"- 耗时：{self.duration_seconds:.1f} 秒")
        if self.input_tokens or self.output_tokens:
            total = self.input_tokens + self.output_tokens
            lines.append(f"- token 用量：输入 {self.input_tokens} + 输出 {self.output_tokens} = {total}")
        if self.tool_calls:
            lines.append("- 工具调用：")
            for i, call in enumerate(self.tool_calls, 1):
                args = ", ".join(f"{k}={v}" for k, v in call.arguments.items())
                lines.append(f"  {i}. `{call.tool_name}({args})`")
        else:
            lines.append("- 工具调用：无（模型直接回答）")
        return "\n".join(lines)


def new_trace(question: str) -> RunTrace:
    """创建一次新的运行记录。"""
    return RunTrace(
        run_id=datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6],
        question=question,
        started_at=datetime.now().isoformat(timespec="seconds"),
    )


def extract_tool_calls(agent: Any) -> list[ToolCallRecord]:
    """从 smolagents 的 memory.steps 里提取所有工具调用。"""
    records: list[ToolCallRecord] = []
    for step in agent.memory.steps:
        for call in getattr(step, "tool_calls", None) or []:
            records.append(
                ToolCallRecord(
                    tool_name=call.name,
                    arguments=call.arguments if isinstance(call.arguments, dict) else {"raw": str(call.arguments)},
                )
            )
    return records


def extract_token_usage(agent: Any) -> tuple[int, int]:
    """从 memory.steps 累计 token 用量，返回 (输入, 输出)。不可用则返回 (0, 0)。"""
    input_tokens = 0
    output_tokens = 0
    for step in agent.memory.steps:
        usage = getattr(step, "token_usage", None)
        if usage is None:
            continue
        input_tokens += getattr(usage, "input_tokens", 0) or 0
        output_tokens += getattr(usage, "output_tokens", 0) or 0
    return input_tokens, output_tokens


def save_trace(trace: RunTrace, runs_dir: Path = DEFAULT_RUNS_DIR) -> Path:
    """把运行档案存成 JSON 文件，返回文件路径。"""
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{trace.run_id}.json"
    data = asdict(trace)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
