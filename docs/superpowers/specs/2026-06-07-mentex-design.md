# Mentex — 多 Agent 创意工作室 · 设计规格

> 最后更新：2026-06-08（反映 Phase 1 实际实现）

## 1. 产品定义

Mentex 是一个多 Agent 协作的创意工作室。用户给一个任意任务，Planner Agent 自动分析并动态组建 Agent 团队，各角色协作完成。用户通过 Web UI 实时观看整个协作过程。

**核心体验**：你像老板一样下达任务，然后看你的 AI 团队开工。

**边界**：不依赖任何网页抓取，所有内容由 LLM 知识生成。

---

## 2. 用户故事

1. 用户在 Web UI 输入：*"分析 2026 年 AI Agent 的发展趋势，写一篇深度文章"*
2. Planner 判断 → 需要 2 个 Researcher 并行检索 + Synthesizer 融合 + Writer 撰写 + Critic 审查
3. 用户在右侧执行区实时看到每个 Agent 的工作过程（逐角色出现，0.5s 刷新）
4. Critic 打完分后，如果低于 7 分自动触发 Reviser 修改（最多 2 轮）
5. 最终产出展示在底部，用户可下载 Markdown
6. 左侧历史栏可回顾之前的所有任务

---

## 3. Agent 架构

### 3.1 角色池（8 个角色，按需启用）

| 角色 | 职责 | 触发条件 |
|------|------|----------|
| 🧠 Planner | 分析任务、制定计划、指派角色 | 每次都先启动 |
| 🔍 Researcher | 检索 LLM 知识、整理研究笔记 | 需要事实/背景 |
| 🔗 Synthesizer | 融合多人产出，去重整理 | 多个 Researcher 并行 |
| ✍️ Writer | 撰写正文（文章/报告/方案等） | 需要文字产出 |
| 📊 Analyst | 结构化分析（SWOT/利弊/数字量化） | 复杂分析任务 |
| 🎨 Designer | 创意构思、方案框架设计 | 需要创意/方案 |
| 👁️ Critic | 评分 + 提出修改建议 | 每次产出后 |
| 🔧 Reviser | 根据建议逐条修改 | Critic 判定需修改 |

### 3.2 Planner 决策规则

```
简单任务（"写一首诗"）→ [Writer] → Critic（2 个角色）
复杂分析（"AI 行业趋势"）→ [Researcher, Researcher, Synthesizer, Writer] → Critic
创意创作（"设计产品"）→ [Researcher, Designer, Writer] → Critic
争议话题（"核能利弊"）→ [Researcher×2（正反方）, Synthesizer, Writer] → Critic
```

### 3.3 执行流（LangGraph 状态图）

```
START → Planner → Worker（循环 pipeline）→ Critic
                                              ↓       ↓
                                            pass    revise
                                              ↓       ↓
                                            END    Reviser → Critic（最多 2 轮）
```

### 3.4 LangGraph State

```python
class StudioState(TypedDict):
    task: str                    # 用户原始任务
    messages: Annotated[list, add_messages]  # 对话历史
    plan: dict                   # Planner 的执行计划 {task_type, pipeline, roles, ...}
    worker_outputs: dict         # {角色名: 产出文本}
    draft: str                   # 当前草稿
    critique: dict               # Critic 审查结果 {score, verdict, suggestions, ...}
    final_output: str            # 最终产出
    iteration: int               # Critic-Reviser 循环计数
    pipeline_index: int          # 当前 pipeline 执行位置
    events: list[dict]           # 事件流 [{event, timestamp, node, content}, ...]
```

### 3.5 Critic-Reviser 质量循环

```
Writer 产出 → Critic 审查
                ├── score >= 7 AND verdict = "pass" → final_output = draft → END
                └── score < 7 OR verdict = "revise" → Reviser → Critic
                                                            ├── pass → END
                                                            └── revise AND iteration < 2
                                                                  → Reviser → Critic → 强制 END
```

---

## 4. UI 设计

### 4.1 技术选型: React（Phase 2 重构）

| 维度 | 选型理由 |
|------|----------|
| 实时更新 | EventSource + SSE 实时推送 |
| 布局灵活 | 三栏 Flex 布局（历史 \| 内容 \| 工作流） |
| 组件化 | React 组件树 + Context 状态管理 |
| 样式 | Tailwind CSS v4 深色/浅色主题 |

> **Phase 1 (已废弃)**: Streamlit + 增量轮询。SSE 会阻塞 Streamlit 单线程渲染，改用 React 后可原生消费 EventSource。

### 4.2 布局

```
┌──────────┬──────────────────────┬─────────────────────┐
│  侧边栏   │  中间（内容生成）      │  右侧（工作流）       │
│  w-64    │  flex-1              │  w-96               │
│          │                      │                     │
│  Logo    │  WelcomeScreen /     │  Pipeline 可视化     │
│          │  StreamingOutput /   │  🧠 Planner   ✅ 💰  │
│  历史记录 │  FinalResult         │  🔍 Researcher ✅ 💰  │
│  • 任务1  │  (Markdown 渲染)     │  ✍️ Writer    ⏳    │
│  • 任务2  │                      │  👁️ Critic    ⏸️    │
│  • 任务3  │                      │                     │
│          │ ┌──────────────────┐ │                     │
│          │ │💬 输入任务 [发送] │ │                     │
│          │ └──────────────────┘ │                     │
└──────────┴──────────────────────┴─────────────────────┘
```

---

## 5. 数据流（实际实现）

### 5.1 流式执行架构

```
用户提交任务（Streamlit）
    │
    ▼
POST /task → 返回 task_id → 后台线程启动 graph.stream()
    │                              │
    │                              ├── Planner 完成 → 2 个事件写入共享 dict
    │                              ├── Worker 完成  → 2 个事件写入共享 dict
    │                              └── Critic 完成  → 2 个事件写入共享 dict
    │
    ▼
前端: GET /task/{id}/events?after=N（每 0.5s，只取新增事件）
    │
    └── 新事件渲染到 expander → st.rerun() → 再次轮询
```

> **设计决策**：SSE 会阻塞 Streamlit 的单线程渲染循环。改用增量轮询后，每次 `st.rerun()` 只做一次 HTTP 请求，渲染完立即返回控制权给 Streamlit。

### 5.2 关键实现细节

- **LangGraph 流式**：`graph.stream(stream_mode="values")` 每完成一个节点 yield 一次完整 state
- **增量事件**：`list(chunk.get("events", []))` **必须 copy**（LangGraph 复用 list 引用，直接赋值会导致 delta 永远为空）
- **增量返回**：`GET /task/{id}/events?after=N` 返回 `events[N:]` + `total` + `status`
- **状态存储**：`_running_tasks[task_id]` 内存 dict，完成后写入 SQLite

### 5.3 事件格式

```json
{
  "event": "agent_start | agent_done | final",
  "timestamp": "2026-06-07T15:30:00+00:00",
  "node": "planner | researcher | writer | critic | reviser",
  "instance": "",
  "content": "人类可读的状态文本"
}
```

### 5.4 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/task` | 提交任务，返回 `{"task_id": "xxx"}`，后台执行 |
| GET | `/task/{id}/events?after=N` | 增量事件：`{"status", "events[N:]", "total", "final_output"}` |
| GET | `/task/{id}` | 任务完整详情（含所有事件和产出） |
| GET | `/history` | 历史任务列表 |

---

## 6. 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| Agent 编排 | LangGraph | `stream(stream_mode="values")` 逐节点流式执行 |
| LLM | Agnes AI（默认）/ DeepSeek（备用） | `.env` 中 `LLM_PROVIDER` 一键切换 |
| Web 框架 | FastAPI | 后台线程 + 内存共享 dict |
| 前端 | Streamlit | 增量轮询 + `st.rerun()` |
| 流式方案 | 增量轮询（非 SSE） | Streamlit 单线程模型下更稳定 |
| 存储 | SQLite | 任务历史持久化 |
| Python | 3.10+ | - |
| 包管理 | pip + venv | 共享 workspace venv |

---

## 7. 项目目录结构

```
Mentex/
├── backend/
│   ├── config.py              # 双 Provider 切换（LLM_PROVIDER=agnes/deepseek）
│   ├── llm.py                 # chat() + chat_stream()
│   ├── api.py                 # FastAPI（后台线程 + 增量轮询端点）
│   ├── db.py                  # SQLite 任务历史
│   └── agent/
│       ├── state.py           # StudioState TypedDict
│       ├── prompts.py         # 8 个角色的 System Prompt
│       ├── nodes.py           # planner / worker / critic / reviser
│       └── graph.py           # LangGraph StateGraph
├── frontend/
│   └── app.py                 # Streamlit UI（增量轮询 + st.rerun()）
├── tests/
│   ├── test_config.py         # Provider 切换测试 (3)
│   ├── test_nodes.py          # 节点逻辑测试 (6)
│   ├── test_graph.py          # 端到端流程测试 (2)
│   ├── test_db.py             # 数据库测试 (3)
│   └── test_api.py            # API 测试 (2)
├── docs/superpowers/
│   ├── specs/2026-06-07-mentex-design.md   # 本文件
│   └── plans/2026-06-07-mentex-phase1.md   # 实现计划
├── .env.example
├── .gitignore
├── requirements.txt
├── CLAUDE.md
└── README.md
```

---

## 8. 关键约束

- **零外部数据**：不爬网页，不调用外部 API（除 LLM）
- **纯 LLM 知识**：所有内容来自 LLM 自身训练数据
- **单用户**：本地运行，不考虑多租户
- **中文优先**：所有 Prompt 和 UI 用中文
- **最多 2 轮修改**：Critic-Reviser 循环防止无限消耗 token
