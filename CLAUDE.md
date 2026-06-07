# Mentex — CLAUDE.md

## 运行环境

- Python 虚拟环境: `/home/max-rayyy/ai-workspace/.venv`
- 所有命令需先激活: `source /home/max-rayyy/ai-workspace/.venv/bin/activate`
- Python 版本: 3.10+
- 工作目录: `/home/max-rayyy/ai-workspace/Mentex`

## 项目信息

- 名称: Mentex — 多 Agent 创意工作室
- 目标: 学习 LangGraph + 多 Agent 协作，构建可实时观看 Agent 团队协作过程的创意工作室
- 技术栈: LangGraph, FastAPI, Streamlit, Agnes AI / DeepSeek, SQLite

## 开发流程: SDD (Specification-Driven Development)

本项目采用规格驱动开发，核心原则：

1. **文档即真相** — `docs/superpowers/specs/` 中的设计规格 + `docs/superpowers/plans/` 中的实现计划是唯一真相来源
2. **代码与文档同步** — 技术决策变更时，需同步更新相关文档
3. **无上下文时先读文档** — 每次新会话开始，若无上下文，先读取 `docs/superpowers/` 下的规格和计划
4. **任务完成标记** — 每完成一个 Task，在实现计划中将对应步骤标记为 `[x]`

## 文档结构

```
docs/superpowers/
├── specs/
│   └── 2026-06-07-mentex-design.md     # 设计规格（产品定义/架构/数据模型）
└── plans/
    └── 2026-06-07-mentex-phase1.md      # Phase 1 实现计划（12 个 Task）
```

## 当前进度

- **Phase 1: MVP ✅ 完成**
  - [x] Task 1: 项目初始化与环境配置
  - [x] Task 2: Config + LLM 客户端
  - [x] Task 3: State 定义
  - [x] Task 4: Prompts（8 个角色）
  - [x] Task 5: Planner 节点
  - [x] Task 6: Worker 节点
  - [x] Task 7: Critic + Reviser 节点
  - [x] Task 8: Graph 组装
  - [x] Task 9: Database (SQLite)
  - [x] Task 10: FastAPI + 增量轮询
  - [x] Task 11: Streamlit UI
  - [x] Task 12: 集成验证

## 已做出的技术决策

| 决策 | 说明 | 原因 |
|------|------|------|
| LLM 提供商 | **Agnes AI**（默认）+ DeepSeek（备用） | Agnes 免费、支持 Function Calling；一键切换 |
| 对话模型 | **agnes-2.0-flash** / deepseek-v4-flash | 256K 上下文，65.5K 输出 |
| Agent 编排 | **LangGraph** | 状态图天然适配多角色路由 + `stream()` 流式执行 |
| 流式执行 | **graph.stream(stream_mode="values")** | 每节点完成后即时 yield，逐角色推送事件 |
| 前端 | **Streamlit** | Python only，增量轮询 + `st.rerun()` 避免 UI 冻结 |
| 前端流式 | **增量轮询**（GET /task/{id}/events?after=N，0.5s） | SSE 会阻塞 Streamlit 单线程，轮询更稳定 |
| 零外部数据 | **纯 LLM 知识** | 避免反爬问题 |
| 质量保证 | **Critic-Reviser 循环**（最多 2 轮） | 自动化审核 + 修改，评分 ≥7 通过 |

## 流式执行架构

```
用户提交任务
    │
    ▼
FastAPI POST /task → 返回 task_id
    │
    ▼
后台线程: graph.stream(stream_mode="values")
    │
    ├── Planner 完成 → 2 个事件写入共享 dict
    ├── Worker 完成  → 2 个事件写入共享 dict
    ├── Critic 完成  → 2 个事件写入共享 dict
    └── 状态: done
    │
    ▼
前端: GET /task/{id}/events?after=N (每 0.5s)
    │
    └── 只返回新增事件 → st.rerun() → 逐角色渲染
```

⚠️ 关键 bug 教训：`list(chunk.get("events", []))` 必须 copy，因为 LangGraph 复用同一个 list 引用，直接赋值 `all_events = current` 会导致 `current[len(all_events):]` 永远为空。

## Git 操作规范

- 远程仓库: `https://github.com/Maxrayyy/Mentex.git`
- `git push` 等待超过 **15 秒** → 停止等待，提示用户手动执行

## 提交规范

- 提交信息用中文
- 使用约定式提交格式: `feat:` / `fix:` / `chore:` / `docs:` / `refactor:`
- **不要在 commit message 中加 `Co-Authored-By` 或其他署名**

## 项目结构

```
Mentex/
├── backend/
│   ├── config.py              # 双 Provider 切换（LLM_PROVIDER=agnes/deepseek）
│   ├── llm.py                 # chat() + chat_stream()
│   ├── api.py                 # FastAPI (POST /task, GET /task/{id}/events?after=N)
│   ├── db.py                  # SQLite 历史记录
│   └── agent/
│       ├── state.py           # StudioState TypedDict
│       ├── prompts.py         # 8 个角色的 System Prompt
│       ├── nodes.py           # planner / worker / critic / reviser
│       └── graph.py           # LangGraph StateGraph
├── frontend/
│   └── app.py                 # Streamlit UI（增量轮询 + st.rerun()）
├── tests/
│   ├── test_config.py         # Provider 切换测试 (3)
│   ├── test_nodes.py          # 节点测试 (6)
│   ├── test_graph.py          # 端到端测试 (2)
│   ├── test_db.py             # 数据库测试 (3)
│   └── test_api.py            # API 测试 (2)
├── docs/superpowers/
│   ├── specs/2026-06-07-mentex-design.md
│   └── plans/2026-06-07-mentex-phase1.md
├── .env.example
├── .gitignore
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## API 配置

- LLM Provider 切换: `.env` 中 `LLM_PROVIDER=agnes` 或 `deepseek`
  - Agnes: `AGENS_API_KEY` + `AGENS_BASE_URL` + `AGENS_MODEL=agnes-2.0-flash`
  - DeepSeek: `DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL` + `DEEPSEEK_MODEL=deepseek-v4-flash`
- 兼容 OpenAI SDK，无需改代码

## 启动命令

```bash
# 后端
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# 前端
streamlit run frontend/app.py --server.port 8501 --server.headless true

# 测试
python -m pytest tests/ -v
```
