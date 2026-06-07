# 🧠 Mentex — 多 Agent 创意工作室

把你的任务交给 AI 团队，看他们实时协作完成。

## 这是什么

Mentex 是一个多 Agent 协作系统。你像老板一样下达任务，Planner Agent 自动分析并组建团队（Researcher、Writer、Designer、Analyst 等），各角色按 pipeline 顺序协作，Critic 负责质量把关。整个协作过程通过 Web UI 实时可见。

**核心特点**：
- 动态组队：Planner 根据任务类型自动决定需要哪些角色
- 流式可见：每个 Agent 的工作过程实时推送，逐角色出现
- 质量循环：Critic 评分 + Reviser 修改，最多 2 轮自动优化
- 零外部依赖：所有内容由 LLM 知识生成，不爬网页

## 架构概览

```
用户（Streamlit UI）
    │  POST /task
    ▼
FastAPI 后端 ──→ 后台线程启动 LangGraph Agent
    │                │
    │                ├── Planner → Worker → Worker → Critic → (Reviser)
    │                │   每个节点完成后即时推送事件到共享存储
    │                │
    │  GET /task/{id}/events?after=N  (增量轮询，0.5s 间隔)
    ▼
Streamlit 前端 ←── 拉取新事件 → 逐角色渲染
```

### 流式执行机制

后端使用 `graph.stream(stream_mode="values")` 而非 `graph.invoke()`。每完成一个节点（Planner / Worker / Critic），LangGraph 立即 yield 当前状态。

前端采用 **增量轮询**：`GET /task/{id}/events?after=N` 只返回第 N 条之后的新事件。配合 `st.rerun()` 实现每 0.5 秒刷新 UI，Agent 工作过程自然逐角色呈现。

> **为什么是轮询而不是 SSE？** Streamlit 的单线程模型会阻塞 SSE 消费循环，导致 UI 冻结。增量轮询 + `st.rerun()` 是 Streamlit 下最稳定的流式方案。

## 快速开始

### 1. 环境准备

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 2. 配置 Provider

`.env` 中通过 `LLM_PROVIDER` 一键切换：

| 值 | Provider | 模型 |
|----|----------|------|
| `agnes` | Agnes AI（默认，免费） | `agnes-2.0-flash` |
| `deepseek` | DeepSeek（备用） | `deepseek-v4-flash` |

### 3. 启动

```bash
# 终端 1：后端
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# 终端 2：前端
streamlit run frontend/app.py
```

浏览器打开 **http://localhost:8501**

### 4. 使用

在左侧输入任意任务，点击「开始执行」。例如：

- `写一首关于秋天的五言诗`
- `分析 2026 年 AI Agent 的发展趋势，写一篇深度文章`
- `设计一个面向大学生的笔记 App`
- `分析核能发电的利弊`
- `用 SWOT 方法分析特斯拉的竞争地位`

## Agent 角色

| 角色 | 职责 | 触发条件 |
|------|------|----------|
| 🧠 Planner | 分析任务、制定 pipeline | 每次都启动 |
| 🔍 Researcher | 检索 LLM 知识 | 需要背景信息 |
| 🔗 Synthesizer | 融合多人产出 | 多个 Researcher 并行 |
| ✍️ Writer | 撰写正文 | 需要文字产出 |
| 📊 Analyst | 结构化分析 (SWOT) | 复杂分析 |
| 🎨 Designer | 创意构思 | 设计方案 |
| 👁️ Critic | 质量审查 + 评分 | 每次产出后 |
| 🔧 Reviser | 根据建议修改 | Critic 判定需改 |

### Pipeline 示例

```
简单创作 → [Writer] → [Critic]
深度分析 → [Researcher, Researcher, Synthesizer, Writer] → [Critic]
争议话题 → [Researcher×2(正反方), Synthesizer, Writer] → [Critic]
```

Critic 评分低于 7 分时，自动触发 Reviser 修改后重新审查（最多 2 轮）。

## 项目结构

```
Mentex/
├── backend/
│   ├── config.py              # 双 Provider 切换
│   ├── llm.py                 # chat() + chat_stream()
│   ├── api.py                 # FastAPI（POST /task, GET /task/{id}/events）
│   ├── db.py                  # SQLite 历史记录
│   └── agent/
│       ├── state.py           # StudioState（工作台）
│       ├── prompts.py         # 8 个角色的 Prompt
│       ├── nodes.py           # planner / worker / critic / reviser
│       └── graph.py           # LangGraph 状态图
├── frontend/
│   └── app.py                 # Streamlit Web UI（增量轮询）
├── tests/
│   ├── test_config.py         # Provider 切换测试
│   ├── test_nodes.py          # 各节点测试
│   ├── test_graph.py          # 端到端流程测试
│   ├── test_db.py             # 数据库测试
│   └── test_api.py            # API 测试
└── docs/
    └── superpowers/
        ├── specs/2026-06-07-mentex-design.md
        └── plans/2026-06-07-mentex-phase1.md
```

## 测试

```bash
python -m pytest tests/ -v
# 16 tests, 全部通过
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/task` | 提交任务，返回 `task_id`，后台执行 |
| GET | `/task/{id}/events?after=N` | 获取第 N 条之后的新事件（增量轮询） |
| GET | `/task/{id}` | 任务完整详情 |
| GET | `/history` | 历史任务列表 |

## 技术栈

| 层 | 选型 |
|----|------|
| Agent 编排 | LangGraph（`stream()` 流式执行） |
| LLM | Agnes AI / DeepSeek 双 Provider |
| 后端 | FastAPI + 后台线程 |
| 前端 | Streamlit（增量轮询 + `st.rerun()`） |
| 存储 | SQLite |

## License

MIT
