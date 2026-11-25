# TraceNote

一个用于学习与实践的个人知识库 Agent 项目，基于 smolagents 构建。

目标：让 Agent 按需检索个人笔记，给出带引用的回答，并记录可检查的执行轨迹。

## 当前状态

第一周完成：环境搭建、离线模拟实验、真实模型接入（硅基流动 DeepSeek-V4.1-Flash）。

真实模型实验要点：硅基流动接口不支持 smolagents 默认的 `tool_choice="required"`，需在构造模型时传 `tool_choice="auto"`（详见 `experiments/02_real_model.py` 内注释）。

## 开发环境

- Windows
- Python 3.12
- smolagents 1.26.0
- 只使用 `ToolCallingAgent`，暂不执行模型生成的任意代码

## 常用命令

在 `TraceNote` 目录执行：

```powershell
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 以后运行最小 Agent 实验（完成实验脚本后使用）
python experiments\01_first_agent.py

# 运行测试
python -m pytest
```

## 安全约定

- `.env` 用于本地保存模型配置，已被 Git 忽略。
- 不把 API Key 写进代码、README 或聊天记录。
- 不把个人笔记和运行日志默认提交到 Git。
- 暂时不使用 `CodeAgent` 或本地任意 Python 代码执行功能。

## 开源基础

本项目使用 [smolagents](https://github.com/huggingface/smolagents)（Apache-2.0）作为 Agent 框架，应用功能与项目代码将独立开发。
