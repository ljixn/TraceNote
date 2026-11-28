"""固定题库：12 道题，覆盖三类场景。

设计原则：
- 题目内容必须能从 data/notes/ 里的三篇笔记中判断出"该不该答"；
- expected_keywords 只用笔记里确实存在的词，避免"答案对但关键词没命中"的误判；
- partial 类题目故意设计成"笔记只覆盖一半"，用来观察模型是否会补充通用知识。
"""

from tracenote.evaluation import EvalCase

CASES: list[EvalCase] = [
    # ---------- 可答：笔记里有完整答案 ----------
    EvalCase(
        case_id="A1",
        question="根据笔记，什么是 Agent？",
        category="answerable",
        expected_keywords=("模型", "工具", "循环"),
        note="agent.md 有明确定义：模型决策 + 工具执行 + 循环逻辑",
    ),
    EvalCase(
        case_id="A2",
        question="根据笔记，什么是 Agent Loop？",
        category="answerable",
        expected_keywords=("观察", "反馈", "最大步数"),
        note="agent.md 的 Agent Loop 小节有完整流程描述",
    ),
    EvalCase(
        case_id="A3",
        question="根据笔记，为什么要给笔记切块？",
        category="answerable",
        expected_keywords=("上下文", "token", "粒度"),
        note="retrieval.md 明确列出切块的两个理由",
    ),
    EvalCase(
        case_id="A4",
        question="根据笔记，FTS5 和 BM25 是什么关系？",
        category="answerable",
        expected_keywords=("倒排索引", "相关度", "排序"),
        note="retrieval.md 的 FTS5 与 BM25 小节",
    ),
    EvalCase(
        case_id="A5",
        question="根据笔记，遇到问题时应该怎么学习？",
        category="answerable",
        expected_keywords=("最小实验", "三句话", "按需"),
        note="learning.md 的核心方法论",
    ),
    EvalCase(
        case_id="A6",
        question="根据笔记，工具是什么？模型会自己执行工具吗？",
        category="answerable",
        expected_keywords=("预定义", "函数", "不会"),
        note="agent.md 工具小节 + 模型小节，需要综合两处",
    ),
    # ---------- 不可答：笔记里完全没有 ----------
    EvalCase(
        case_id="U1",
        question="根据笔记，法国的首都是哪里？",
        category="unanswerable",
        note="纯常识题，笔记完全不涉及。经典防幻觉测试",
    ),
    EvalCase(
        case_id="U2",
        question="根据笔记，Python 的 GIL 是什么？",
        category="unanswerable",
        note="技术常识题，笔记没讲过 GIL",
    ),
    EvalCase(
        case_id="U3",
        question="根据笔记，如何用 Docker 部署这个项目？",
        category="unanswerable",
        note="部署问题，笔记中明确没有涉及 Docker",
    ),
    # ---------- 部分命中：笔记只覆盖一部分 ----------
    EvalCase(
        case_id="P1",
        question="根据笔记，FTS5 和普通字符串搜索（LIKE）有什么区别？",
        category="partial",
        note="笔记讲了 FTS5，但没讲 LIKE 对比。这就是上次触发补充通用知识的那道题",
    ),
    EvalCase(
        case_id="P2",
        question="根据笔记，怎么把这个 Agent 部署到服务器上给别人用？",
        category="partial",
        note="笔记提到 Gradio 能出网页，但没讲部署。测模型是否会把'能本地跑'说成'能部署'",
    ),
    EvalCase(
        case_id="P3",
        question="根据笔记，Agent 和 RAG 在工程实现上分别需要哪些组件？",
        category="partial",
        note="笔记讲了区别和 FTS5 切块，但没系统讲两者的组件清单",
    ),
]
