# Mentex — CLAUDE.md

## 运行环境

- Python 虚拟环境: `/home/max-rayyy/ai-workspace/.venv`
- 所有命令需先激活: `source /home/max-rayyy/ai-workspace/.venv/bin/activate`
- Python 版本: 3.10+
- 工作目录: `/home/max-rayyy/ai-workspace/Mentex`

## 项目信息

- 名称: Mentex — 多 Agent 创意工作室
- 目标: 学习 LangGraph + 多 Agent 协作，构建可实时观看 Agent 团队协作过程的创意工作室
- 技术栈: LangGraph, FastAPI, React (Vite + TypeScript + Tailwind CSS v4), Agnes AI / DeepSeek, SQLite

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
  - [x] Task 10: FastAPI + SSE
  - [x] Task 11: React 前端（替代原 Streamlit）
  - [x] Task 12: 集成验证

- **Phase 2: 完善 ✅ 完成**
  - [x] 轮询 → SSE 实时推送
  - [x] 三栏布局（历史 | 内容 | 工作流）
  - [x] 白色主题 + Fira Code/Sans 字体
  - [x] Token 调用量显示（后台 + 前端）
  - [x] SSE 稳定性修复（event: error → task_error）
  - [x] LLM 超时 + Agent 执行日志

## 已做出的技术决策

| 决策 | 说明 | 原因 |
|------|------|------|
| LLM 提供商 | **Agnes AI**（默认）+ DeepSeek（备用） | Agnes 免费、支持 Function Calling；一键切换 |
| 对话模型 | **agnes-2.0-flash** / deepseek-v4-flash | 256K 上下文，65.5K 输出 |
| Agent 编排 | **LangGraph** | 状态图天然适配多角色路由 + `stream()` 流式执行 |
| 流式执行 | **graph.stream(stream_mode="values")** | 每节点完成后即时 yield，逐角色推送事件 |
| 后端流式 | **SSE (asyncio.Queue + sse-starlette)** | 实时推送，替代 Phase 1 的增量轮询 |
| 前端 | **React (Vite + TS + Tailwind CSS v4)** | 替代 Streamlit，支持 SSE 消费、三栏布局 |
| 前端流式 | **EventSource API** | 原生 SSE 消费，自动重连 |
| 零外部数据 | **纯 LLM 知识** | 避免反爬问题 |
| 质量保证 | **Critic-Reviser 循环**（最多 2 轮） | 自动化审核 + 修改，评分 ≥7 通过 |

## 流式执行架构

```
用户提交任务（React）
    │
    ▼
FastAPI POST /task → 返回 task_id
    │
    ▼
后台线程: graph.stream(stream_mode="values")
    │
    ├── Planner 完成 → 2 个事件 push 到 asyncio.Queue
    ├── Worker 完成  → 2 个事件 push 到 asyncio.Queue
    ├── Critic 完成  → 2 个事件 push 到 asyncio.Queue
    └── 状态: done → done 事件 → 写入 SQLite
    │
    ▼
前端: EventSource → GET /task/{id}/stream (SSE)
    │
    └── agent_start / agent_done / heartbeat / done / task_error
        → 右侧工作流实时更新 + 中间产出流式展示
```

⚠️ 关键 bug 教训：
- `list(chunk.get("events", []))` 必须 copy，因为 LangGraph 复用同一个 list 引用
- SSE `event: error` 会被浏览器当作传输错误关闭连接，改用 `event: task_error`
- Vite 代理会缓冲 SSE 流，SSE 必须直连 `http://localhost:8000`
- CORS 中 `127.0.0.1` ≠ `localhost`（不同源），两个地址都要加入白名单
- Python 3.10+ 后台线程调用 `asyncio.get_event_loop()` 会抛 RuntimeError（不再自动返回主线程 loop）
  → 解决：启动时用 `asyncio.get_running_loop()` 捕获 `_main_loop`，跨线程用 `_main_loop.call_soon_threadsafe()`

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
│   ├── llm.py                 # chat() 返回 (content, token_usage)
│   ├── api.py                 # FastAPI (POST /task, GET /task/{id}/stream SSE, GET /history)
│   ├── db.py                  # SQLite 历史记录
│   └── agent/
│       ├── state.py           # StudioState TypedDict（含 total_tokens）
│       ├── prompts.py         # 8 个角色的 System Prompt
│       ├── nodes.py           # planner / worker / critic / reviser（含日志 + token）
│       └── graph.py           # LangGraph StateGraph
├── frontend/                  # [DEPRECATED] Streamlit 旧版
│   └── app.py
├── frontend-react/            # React 新版 ⭐
│   ├── src/
│   │   ├── types.ts           # 类型定义 + Agent 元数据
│   │   ├── context/AppContext.tsx  # useReducer 全局状态
│   │   ├── hooks/useTaskStream.ts  # SSE EventSource Hook
│   │   └── components/        # 10 个组件
│   │       ├── Sidebar.tsx         # 左侧：历史记录
│   │       ├── MainContent.tsx     # 中间：内容 + 底部输入栏
│   │       ├── WorkflowPanel.tsx   # 右侧：工作流可视化
│   │       ├── AgentCard.tsx       # Agent 状态卡片（含 token）
│   │       ├── PipelineVisualization.tsx  # Pipeline 流程图
│   │       ├── WelcomeScreen.tsx   # 欢迎页 + 示例任务
│   │       ├── StreamingOutput.tsx # 流式事件展示
│   │       ├── FinalResult.tsx     # 最终产出 + 下载
│   │       ├── HistoryList.tsx     # 历史任务列表
│   │       └── TaskInput.tsx       # 任务输入组件（独立可复用）
│   ├── vite.config.ts
│   └── index.html
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
- OpenAI 客户端超时: 120s

## 启动命令

```bash
# 后端
cd /home/max-rayyy/ai-workspace/Mentex
source /home/max-rayyy/ai-workspace/.venv/bin/activate
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# 前端（新 React 版）
cd /home/max-rayyy/ai-workspace/Mentex/frontend-react
npm run dev
# 浏览器打开 http://localhost:5173

# 测试
python -m pytest tests/ -v
```
