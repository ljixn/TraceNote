# TraceNote

一个用于学习与实践的个人知识库 Agent 项目，基于 smolagents 构建。

目标：让 Agent 按需检索个人笔记，给出带引用的回答，并记录可检查的执行轨迹。

## 当前状态

第五周完成：评测体系（12 道固定题库 + A/B 对比 + 真实数据报告）。

- `tracenote/loader.py`：Markdown 导入与切块（按标题分节，单块 ≤600 字符）
- `tracenote/store.py`：SQLite FTS5 存储 + BM25 检索（含中英混合/短查询的降级策略）
- `tracenote/agent.py`：NotesSearchTool（top_k 可配置）+ Agent 构建 + run_with_trace
- `tracenote/tracer.py`：运行记录（每次问答存 JSON 档案到 runs/）
- `tracenote/errors.py`：友好报错（技术错误翻译成人话）
- `tracenote/evaluation.py`：评测框架（题库、规则打分、指标汇总）
- `evaluation/cases.py`：12 道固定题库
- `evaluation/REPORT.md`：评测报告（含真实数据）
- `tracenote/ui.py`：Gradio 网页界面
- 46 个单元测试通过

## 评测结果（真实数据）

| 配置 | 通过率 | 拒答准确率 | 幻觉率 | 引用率 | 平均 token | 平均耗时 |
|---|---|---|---|---|---|---|
| top_k=1 | 83.3% | 100% | 0% | 83.3% | 7853 | 8.2 秒 |
| **top_k=3** | **91.7%** | 100% | 0% | **100%** | **6636** | **6.7 秒** |

详见 [evaluation/REPORT.md](evaluation/REPORT.md)。核心结论：
- 幻觉率 0%——笔记里没有的内容，模型会明确拒答而不是瞎编；
- 查 3 条反而比查 1 条省 16% token——信息不足会导致模型反复重试；
- 瓶颈在检索层而非模型层——长查询在 trigram 分词下容易失配。

## 架构

```text
data/notes/*.md ──loader 切块──▶ notes.db (FTS5 索引) ──store 检索──▶ search_notes 工具
                                                                         │
用户提问 ────────────── ToolCallingAgent（smolagents）◀──────────────────┘
              │  拒答规则：笔记查不到 → 说"不知道"，不瞎编
              │  引用：回答标明来源文件+标题+行号
              │  运行记录：每次问答存 JSON 档案（runs/，不进 Git）
              │  友好报错：出错显示人话，不甩报错堆栈
              ▼
         Gradio 网页界面（http://127.0.0.1:7860）
```

## 开发环境

- Windows
- Python 3.12
- smolagents 1.26.0（只使用 `ToolCallingAgent`，不执行模型生成的任意代码）
- SQLite FTS5（Python 自带，零额外依赖）

## 快速开始

```powershell
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 重建知识库索引（data/notes/ 下放你的 .md 笔记）
python -X utf8 -c "from tracenote.agent import rebuild_index; print(rebuild_index(), '块已入库')"

# 启动网页界面（浏览器打开 http://127.0.0.1:7860）
python -X utf8 -m tracenote.ui

# 命令行跑一次带运行记录的问答（会生成 runs/*.json）
python -X utf8 -c "from tracenote.agent import run_with_trace; a, t = run_with_trace('什么是 Agent？'); print(a); print(t.summary_text())"

# 运行测试
python -X utf8 -m pytest -q

# 跑评测（两轮 A/B 对比，会真实调用模型）
python -X utf8 -m evaluation.run_eval
```

## 真实模型接入要点

硅基流动接口不支持 smolagents 默认的 `tool_choice="required"`，需在构造模型时传
`tool_choice="auto"`（详见 `tracenote/agent.py` 注释）。

## 安全约定

- `.env` 用于本地保存模型配置，已被 Git 忽略。
- 不把 API Key 写进代码、README 或聊天记录。
- `data/`（笔记与数据库）默认被 Git 忽略，可按需自行提交示例笔记。
- 暂时不使用 `CodeAgent` 或本地任意 Python 代码执行功能。

## 开源基础

本项目使用 [smolagents](https://github.com/huggingface/smolagents)（Apache-2.0）作为 Agent 框架，应用功能与项目代码独立开发。
