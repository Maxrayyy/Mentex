# Mentex — CLAUDE.md

## 运行环境

- Python 虚拟环境: `/home/max-rayyy/ai-workspace/.venv`
- 所有命令需先激活: `source /home/max-rayyy/ai-workspace/.venv/bin/activate`
- Python 版本: 3.10+
- 工作目录: `/home/max-rayyy/ai-workspace/Mentex`

## 项目信息

- 名称: Mentex — 多 Agent 创意工作室
- 目标: 学习 LangGraph + 多 Agent 协作，构建可实时观看 Agent 团队协作过程的创意工作室
- 技术栈: LangGraph, FastAPI, Streamlit, DeepSeek API, SQLite

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

- **Phase 1: MVP** 进行中
  - [x] Task 1: 项目初始化与环境配置
  - [ ] Task 2: Config + LLM 客户端
  - [ ] Task 3: State 定义
  - [ ] Task 4: Prompts（8 个角色）
  - [ ] Task 5: Planner 节点
  - [ ] Task 6: Worker 节点
  - [ ] Task 7: Critic + Reviser 节点
  - [ ] Task 8: Graph 组装
  - [ ] Task 9: Database (SQLite)
  - [ ] Task 10: FastAPI + SSE
  - [ ] Task 11: Streamlit UI
  - [ ] Task 12: 集成验证

## 已做出的技术决策

| 决策 | 说明 | 原因 |
|------|------|------|
| LLM 提供商 | **DeepSeek** | 国内访问快、便宜、兼容 OpenAI SDK |
| 对话模型 | **deepseek-v4-flash** | MindFlow 已验证可用 |
| Agent 编排 | **LangGraph** | 状态图天然适配多角色路由 |
| 前端 | **Streamlit** | Python only，快速出 UI |
| 流式协议 | **SSE** | 比 WebSocket 简单，Streamlit 原生支持 |
| 零外部数据 | **纯 LLM 知识** | 避免反爬问题 |

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
│   ├── config.py              # 全局配置（读 .env）
│   ├── llm.py                 # DeepSeek API 封装
│   ├── agent/
│   │   ├── state.py           # StudioState TypedDict
│   │   ├── prompts.py         # 8 个角色的 System Prompt
│   │   ├── nodes.py           # planner / worker / critic / reviser 节点
│   │   └── graph.py           # LangGraph StateGraph 组装
│   ├── db.py                  # SQLite 存取
│   └── api.py                 # FastAPI + SSE 端点
├── frontend/
│   └── app.py                 # Streamlit UI
├── tests/
│   ├── test_config.py
│   ├── test_nodes.py
│   ├── test_graph.py
│   ├── test_db.py
│   └── test_api.py
├── docs/superpowers/
│   ├── specs/2026-06-07-mentex-design.md
│   └── plans/2026-06-07-mentex-phase1.md
├── .env.example
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## API 配置

- LLM 提供商: DeepSeek (`api.deepseek.com`)
- 模型: `deepseek-v4-flash`
- 兼容 OpenAI SDK，通过 `OPENAI_API_KEY` + `OPENAI_BASE_URL` 配置
