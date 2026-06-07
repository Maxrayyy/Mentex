# Mentex — 多 Agent 创意工作室 · 设计规格

> 最后更新：2026-06-07

## 1. 产品定义

Mentex 是一个多 Agent 协作的创意工作室。用户给一个任意任务，Planner Agent 自动分析并动态组建 Agent 团队，各角色协作完成。用户通过 Web UI 实时观看整个协作过程。

**核心体验**：你像老板一样下达任务，然后看你的 AI 团队开工。

**边界**：不依赖任何网页抓取，所有内容由 LLM 知识生成。

---

## 2. 用户故事

1. 用户在 Web UI 输入：*"分析 2026 年 AI Agent 的发展趋势，写一篇深度文章"*
2. Planner 判断 → 需要 2 个 Researcher 并行检索 + Synthesizer 融合 + Writer 撰写 + Critic 审查
3. 用户在右侧执行区实时看到每个 Agent 的工作过程（流式文字 + 结构化数据）
4. Critic 打完分后，如果低于 7 分自动触发 Reviser 修改
5. 最终产出展示在底部，用户可复制/保存
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
简单任务（"写一首诗"）→ Writer → Critic（2 个角色）
复杂分析（"AI 行业趋势"）→ Researcher×2 → Synthesizer → Writer → Critic
创意创作（"设计产品"）→ Researcher → Designer → Writer → Critic
争议话题（"核能利弊"）→ Researcher×2（正反方）→ Synthesizer → Writer → Critic
```

### 3.3 执行流（LangGraph 状态图）

```
START → Planner → Worker Router → [并行 Workers] → Synthesizer
                                          ↓
                                Writer / Analyst / Designer
                                          ↓
                                      Critic
                                      ↓    ↓
                                    pass  revise
                                      ↓    ↓
                                   FINAL  Reviser → Critic（最多 2 轮）
```

### 3.4 LangGraph State

```python
class StudioState(TypedDict):
    task: str                    # 用户原始任务
    messages: list               # 对话历史
    plan: dict                   # Planner 的执行计划
    worker_outputs: dict         # {角色名_instance: 产出}
    synthesis: str               # Synthesizer 融合结果
    draft: str                   # 当前草稿
    critique: dict               # Critic 审查结果
    final_output: str            # 最终产出
    iteration: int               # Critic-Reviser 循环次数
```

### 3.5 Critic-Reviser 质量循环

```
Writer 产出 → Critic 审查
                ├── score >= 7 AND verdict = "pass" → FINAL
                └── score < 7 OR verdict = "revise" → Reviser
                                                        ↓
                                                    Critic 再审查
                                                        ├── pass → FINAL
                                                        └── revise AND iteration < 2
                                                              ↓
                                                          Reviser → Critic → FINAL
```

---

## 4. UI 设计

### 4.1 技术选型：Streamlit

| 维度 | 选型理由 |
|------|----------|
| 实时渲染 | `st.write_stream` 原生支持 |
| 开发速度 | Python only，无需前端上下文切换 |
| 组件 | expander 天然适合展示 Agent 过程 |

### 4.2 布局

```
┌──────────────────────────────────────────────┐
│  🧠 Mentex — 多 Agent 创意工作室            │
├────────────────┬─────────────────────────────┤
│  侧边栏（输入）  │  主区域（执行）               │
│                │                             │
│  任务描述框     │  🧠 Planner（expander）       │
│  [执行] 按钮    │  🔍 Researcher-A/B（expander）│
│  ─────────     │  🔗 Synthesizer（expander）  │
│  历史任务列表   │  ✍️ Writer（expander）       │
│                │  👁️ Critic（expander）       │
│                │  🔧 Reviser（expander）      │
│                │  ─────────────              │
│                │  最终产出（markdown 渲染）     │
│                │  [复制] [保存]                │
└────────────────┴─────────────────────────────┘
```

---

## 5. 数据流

```
用户输入（Streamlit）
  → POST /task（FastAPI）
    → LangGraph Agent 执行
      → 每个节点 yield SSE event
        → Streamlit 消费 SSE → 渲染到对应 expander
          → 最终产出存储 SQLite
```

### 5.1 SSE 事件格式

```json
{
  "event": "agent_start | agent_output | agent_done | final",
  "timestamp": "iso",
  "node": "planner | researcher | synthesizer | writer | critic | reviser | ...",
  "instance": "A",
  "content": "流式文本或结构化 JSON"
}
```

### 5.2 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/task` | 提交任务，返回 SSE 事件流 |
| GET | `/history` | 历史任务列表 |
| GET | `/task/{id}` | 任务详情回放 |

---

## 6. 技术栈

| 层 | 选型 | 版本 |
|----|------|------|
| Agent 编排 | LangGraph | latest |
| LLM | DeepSeek API（deepseek-v4-flash） | - |
| Web 框架 | FastAPI | latest |
| 前端 | Streamlit | latest |
| 流式协议 | SSE (Server-Sent Events) | - |
| 存储 | SQLite | - |
| Python | 3.10+ | - |
| 包管理 | pip + venv | - |

---

## 7. 项目目录结构

```
Mentex/
├── backend/
│   ├── api.py              # FastAPI + SSE 端点
│   ├── agent/
│   │   ├── graph.py         # LangGraph StateGraph
│   │   ├── nodes.py         # 所有节点实现
│   │   ├── prompts.py       # 角色 System Prompt
│   │   └── state.py         # StudioState
│   ├── db.py                # SQLite 操作
│   └── config.py            # 环境变量配置
├── frontend/
│   └── app.py               # Streamlit UI
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-06-07-Mentex-design.md  # 本文件
├── requirements.txt
└── README.md
```

---

## 8. 关键约束

- **零外部依赖**：不爬网页，不调用外部 API（除 DeepSeek LLM）
- **纯 LLM 知识**：所有"检索"来自 LLM 自身训练数据
- **单用户**：本地运行，不考虑多租户
- **中文优先**：所有 Prompt 和 UI 用中文
