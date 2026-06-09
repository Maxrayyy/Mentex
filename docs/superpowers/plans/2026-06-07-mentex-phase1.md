# Mentex Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建多 Agent 创意工作室 MVP——用户输入任务，Planner 动态组队，Agent 团队协作产出内容，通过 Streamlit Web UI 实时观看全过程。

**Architecture:** FastAPI 后端托管 LangGraph Agent，使用 `graph.stream(stream_mode="values")` 逐节点流式执行。后台线程将事件写入共享 dict，前端通过 `GET /task/{id}/events?after=N` 增量轮询（0.5s 间隔）+ `st.rerun()` 实现逐角色实时渲染。Agnes AI 作为默认 LLM，DeepSeek 作为备用，`.env` 一行切换。

**Tech Stack:** Python 3.10+, LangGraph, FastAPI, Streamlit, Agnes AI / DeepSeek (openai SDK), SQLite

---

## 文件结构

```
Mentex/
├── backend/
│   ├── __init__.py
│   ├── config.py              # Settings dataclass，读 .env
│   ├── llm.py                 # DeepSeek API 封装（chat + chat_stream）
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py           # StudioState TypedDict
│   │   ├── prompts.py         # 8 个角色的 System Prompt
│   │   ├── nodes.py           # planner / worker / critic / reviser 节点
│   │   └── graph.py           # StateGraph 组装 + 条件路由
│   ├── db.py                  # SQLite 存取任务记录
│   └── api.py                 # FastAPI app，SSE 端点
├── frontend/
│   └── app.py                 # Streamlit UI
├── tests/
│   ├── test_config.py
│   ├── test_nodes.py
│   ├── test_graph.py
│   ├── test_db.py
│   └── test_api.py
├── docs/superpowers/
│   ├── specs/2026-06-07-Mentex-design.md
│   └── plans/2026-06-07-Mentex-phase1.md
├── .env.example
├── requirements.txt
└── README.md
```

---

### Task 1: 项目初始化

**Files:**
- Create: `Mentex/.env.example`
- Create: `Mentex/requirements.txt`
- Create: `Mentex/backend/__init__.py`
- Create: `Mentex/backend/agent/__init__.py`
- Create: `Mentex/tests/__init__.py`
- Create: `Mentex/README.md`

- [ ] **Step 1: 创建 .env.example**

```bash
# DeepSeek API（兼容 OpenAI SDK）
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

# 服务端口
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_PORT=8501
```

- [ ] **Step 2: 创建 requirements.txt**

```
langgraph>=0.2.0
langchain-core>=0.3.0
openai>=1.50.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sse-starlette>=2.0.0
streamlit>=1.40.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.28.0
```

- [ ] **Step 3: 安装依赖 + 创建空文件**

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
pip install -r requirements.txt

touch backend/__init__.py
touch backend/agent/__init__.py
touch tests/__init__.py
```

- [ ] **Step 4: 创建 README.md**

```markdown
# 🧠 Mentex — 多 Agent 创意工作室

把你的任务交给 AI 团队，看他们实时协作完成。

## 快速开始

```bash
source ../.venv/bin/activate
cp .env.example .env    # 编辑 .env 填入 DeepSeek API Key

# 终端 1：启动后端
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000

# 终端 2：启动前端
streamlit run frontend/app.py
```

浏览器打开 http://localhost:8501
```

- [ ] **Step 5: 验证**

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
python -c "import langgraph; import fastapi; import streamlit; print('OK')"
```

---

### Task 2: Config + LLM 客户端

**Files:**
- Create: `Mentex/backend/config.py`
- Create: `Mentex/backend/llm.py`
- Create: `Mentex/tests/test_config.py`

- [ ] **Step 1: 写 Config 测试**

```python
# tests/test_config.py
import os
from backend.config import Settings

def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    
    settings = Settings()
    assert settings.deepseek_api_key == "sk-test"
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"

def test_settings_defaults(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    
    settings = Settings()
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.streamlit_port == 8501
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
python -m pytest tests/test_config.py -v
# Expected: FAIL (ModuleNotFoundError)
```

- [ ] **Step 3: 实现 config.py**

```python
# backend/config.py
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    deepseek_api_key: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", "")
    )
    deepseek_base_url: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    )
    deepseek_model: str = field(
        default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    )
    api_host: str = field(
        default_factory=lambda: os.getenv("API_HOST", "0.0.0.0")
    )
    api_port: int = field(
        default_factory=lambda: int(os.getenv("API_PORT", "8000"))
    )
    streamlit_port: int = field(
        default_factory=lambda: int(os.getenv("STREAMLIT_PORT", "8501"))
    )


settings = Settings()
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_config.py -v
# Expected: 2 PASSED
```

- [ ] **Step 5: 实现 llm.py**

```python
# backend/llm.py
from openai import OpenAI
from backend.config import settings

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """同步调用 LLM，返回完整文本"""
    client = get_client()
    response = client.chat.completions.create(
        model=model or settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def chat_stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """流式调用 LLM，yield 文本片段"""
    client = get_client()
    stream = client.chat.completions.create(
        model=model or settings.deepseek_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

- [ ] **Step 6: 验证 LLM 客户端（需要配置 .env 后运行）**

```bash
python -c "
from backend.llm import chat
r = chat([{'role': 'user', 'content': '说一个字：好'}])
print(r)
"
# Expected: 好
```

---

### Task 3: State 定义

**Files:**
- Create: `Mentex/backend/agent/state.py`

- [ ] **Step 1: 实现 state.py**

```python
# backend/agent/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class StudioState(TypedDict):
    """多 Agent 协作工作流的状态"""
    # 输入
    task: str

    # 对话历史（自动追加）
    messages: Annotated[list, add_messages]

    # Planner 产出
    plan: dict  # {task_type, plan_summary, roles, pipeline}

    # 各 Worker 的产出 {role_instance: content}
    worker_outputs: dict

    # 当前草稿（Writer/Analyst/Designer 的产出）
    draft: str

    # Critic 审查结果 {score, strengths, weaknesses, suggestions, verdict}
    critique: dict

    # 最终产出
    final_output: str

    # Critic-Reviser 循环计数
    iteration: int

    # 当前 pipeline 执行位置
    pipeline_index: int

    # 事件流（供 SSE 消费）
    events: list[dict]
```

---

### Task 4: Prompts

**Files:**
- Create: `Mentex/backend/agent/prompts.py`

- [ ] **Step 1: 实现 prompts.py**

```python
# backend/agent/prompts.py

PLANNER_PROMPT = """你是一个创意工作室的策划总监。用户给你一个任务，你需要分析并制定执行计划。

## 可选角色
- Researcher: 从 LLM 知识库检索背景信息，整理研究笔记
- Synthesizer: 融合多个 Researcher 的产出，去重整理
- Writer: 撰写正文（文章/报告/方案）
- Analyst: 结构化分析（SWOT/利弊/量化）
- Designer: 创意构思、方案框架设计
- Critic: 质量审查、评分、提修改建议（自动追加在最后）
- Reviser: 根据 Critic 建议修改草稿（自动追加在最后）

## 决策规则
- 简单创作（"写一首诗"）→ [Writer]
- 需要背景知识（"分析AI趋势"）→ [Researcher, Researcher, Synthesizer, Writer]
- 创意设计（"设计产品"）→ [Researcher, Designer, Writer]
- 争议话题（"核能利弊"）→ [Researcher, Researcher, Synthesizer, Writer]
- 复杂分析（"SWOT分析"）→ [Researcher, Analyst, Writer]

⚠️ Critic 和 Reviser 会自动追加到 pipeline 末尾，你不需要写进去。
⚠️ 能用 2 个角色完成的，不要用 5 个。简单任务尽量少用角色。

## 输出格式（严格 JSON）
```json
{
  "task_type": "article | analysis | creative | decision | mixed",
  "plan_summary": "一句话执行计划",
  "roles": [
    {"name": "Researcher", "count": 1, "focus": "研究方向"},
    {"name": "Writer", "count": 1, "focus": "撰写方向"}
  ],
  "pipeline": ["Researcher", "Writer"],
  "expected_output": "文章 | 报告 | 方案 | 分析 | 创意"
}
```
"""

WORKER_BASE_PROMPT = """你是 Mentex 创意工作室的 {role_name}。

{role_description}

## 当前任务
用户原始任务：{task}

## 已有信息
{context}

## 你的任务
{role_focus}

请直接输出你的工作成果，不要模拟其他人。如果是 Researcher，输出结构化笔记。如果是 Writer，输出完整正文。"""

ROLE_DESCRIPTIONS = {
    "Researcher": """你是一个资深研究员。从你的知识库中检索与任务相关的信息。
输出结构化的研究笔记：
- 关键事实和数据
- 不同观点和视角
- 重要概念解释
不确定的信息标注「待验证」。
不要编造信息。""",

    "Synthesizer": """你是一个信息整合专家。收到多份研究报告后：
1. 找出共同点和分歧点
2. 去掉重复内容
3. 按逻辑顺序整理
4. 标注信息置信度（高/中/低）
输出一份整合后的知识简报。""",

    "Writer": """你是一个专业撰稿人。根据整合好的资料撰写完整正文。
要求：
- 有清晰的结构（引言 → 正文 → 结论）
- 引用资料时保留置信度标注
- 语言风格根据任务类型自适应
- 使用 Markdown 格式
直接输出完整正文，不要写"这是草稿"之类的开头。""",

    "Designer": """你是一个创意设计师。产出内容：
- 创意概念和核心理念
- 方案结构或框架
- 具体的设计描述
- 可行性评估
不需要写代码。输出完整方案。""",

    "Analyst": """你是一个数据分析师。对已有材料进行结构化分析：
- 问题拆解
- 量化分析（有数据用数据，无则合理估算并标注）
- SWOT 矩阵或利弊对比
- 可执行的建议
使用 Markdown 表格和列表。""",
}

CRITIC_PROMPT = """你是一个严苛的审稿人。对以下草稿进行审查。

## 草稿
{draft}

## 用户原始需求
{task}

## 审查标准
1. 是否完整覆盖用户需求
2. 逻辑是否清晰、结构是否合理
3. 内容是否准确、有无明显错误
4. 语言表达是否流畅
5. 是否有改进空间

## 输出格式（严格 JSON）
```json
{{
  "score": 8.5,
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["问题1", "问题2"],
  "suggestions": ["具体修改建议1", "具体修改建议2"],
  "verdict": "pass"
}}
```

verdict 规则：
- "pass": 分数 >= 7，只需微调或无需修改
- "revise": 分数 < 7，必须修改
"""

REVISER_PROMPT = """你是一个修改专家。根据审稿意见修改草稿。

## 原始草稿
{draft}

## 审稿意见
评分：{score}/10
优点：{strengths}
问题：{weaknesses}
修改建议：{suggestions}

## 修改要求
1. 逐条处理修改建议
2. 保留优点
3. 每处修改用注释标注：<!-- 修改：原 xxx → 改为 yyy -->
4. 输出完整修改后的正文，不要只输出修改部分
"""
```

---

### Task 5: Planner 节点

**Files:**
- Create: `Mentex/backend/agent/nodes.py`（Planner 部分）
- Create: `Mentex/tests/test_nodes.py`（Planner 测试）

- [ ] **Step 1: 写 Planner 测试**

```python
# tests/test_nodes.py
import json
from unittest.mock import patch, MagicMock
from backend.agent.state import StudioState
from backend.agent.nodes import planner_node


def test_planner_parses_valid_json():
    """Planner 正确解析 LLM 返回的 JSON 计划"""
    plan_json = json.dumps({
        "task_type": "article",
        "plan_summary": "写一篇AI趋势分析文章",
        "roles": [
            {"name": "Researcher", "count": 1, "focus": "AI趋势研究"},
            {"name": "Writer", "count": 1, "focus": "撰写文章"}
        ],
        "pipeline": ["Researcher", "Writer"],
        "expected_output": "文章"
    })
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = f"```json\n{plan_json}\n```"
    
    with patch("backend.agent.nodes.get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        
        state: StudioState = {
            "task": "分析AI发展趋势",
            "messages": [],
            "plan": {},
            "worker_outputs": {},
            "draft": "",
            "critique": {},
            "final_output": "",
            "iteration": 0,
            "pipeline_index": 0,
            "events": [],
        }
        
        result = planner_node(state)
        
        assert result["plan"]["task_type"] == "article"
        assert len(result["plan"]["pipeline"]) == 2
        assert "Researcher" in result["plan"]["pipeline"]
        assert len(result["events"]) >= 2  # agent_start + agent_done
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
python -m pytest tests/test_nodes.py::test_planner_parses_valid_json -v
# Expected: FAIL (ImportError)
```

- [ ] **Step 3: 实现 Planner 节点**

```python
# backend/agent/nodes.py
import json
import re
from datetime import datetime, timezone
from backend.agent.state import StudioState
from backend.agent.prompts import PLANNER_PROMPT
from backend.llm import get_client, chat
from backend.config import settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit(state: StudioState, event: str, node: str, content, instance: str = ""):
    """向事件流追加一条事件"""
    state["events"].append({
        "event": event,
        "timestamp": _now_iso(),
        "node": node,
        "instance": instance,
        "content": content,
    })


def _parse_json_from_response(text: str) -> dict:
    """从 LLM 回复中提取 JSON"""
    # 尝试匹配 ```json ... ``` 代码块
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # 尝试直接解析整个文本
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试找 { ... } 块
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"无法从 LLM 回复中提取 JSON: {text[:200]}")


def planner_node(state: StudioState) -> dict:
    """Planner 节点：分析任务 → 输出执行计划"""
    _emit(state, "agent_start", "planner", "开始分析任务...")

    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": state["task"]},
    ]

    response = chat(messages, temperature=0.3)
    plan = _parse_json_from_response(response)

    # 自动追加 Critic pipeline 步骤（Planner 不需要写）
    if "Critic" not in plan["pipeline"]:
        plan["pipeline"].append("Critic")

    _emit(state, "agent_done", "planner",
          f"计划制定完成：{plan['plan_summary']}，"
          f"pipeline: {' → '.join(plan['pipeline'])}")

    return {
        "plan": plan,
        "pipeline_index": 0,
        "iteration": 0,
        "worker_outputs": {},
        "draft": "",
        "critique": {},
        "events": state.get("events", []),
    }
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_nodes.py::test_planner_parses_valid_json -v
# Expected: PASS
```

---

### Task 6: Worker 节点

**Files:**
- Modify: `Mentex/backend/agent/nodes.py`（追加 Worker 节点）
- Modify: `Mentex/tests/test_nodes.py`（追加 Worker 测试）

- [ ] **Step 1: 写 Worker 测试**

```python
# 追加到 tests/test_nodes.py

def test_worker_node_calls_correct_role():
    """Worker 节点根据 pipeline 当前位置调用正确的角色"""
    from backend.agent.nodes import worker_node

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "这是研究员的研究笔记"

    state: StudioState = {
        "task": "分析AI发展趋势",
        "messages": [],
        "plan": {
            "task_type": "article",
            "plan_summary": "测试",
            "roles": [
                {"name": "Researcher", "count": 1, "focus": "AI趋势研究"}
            ],
            "pipeline": ["Researcher", "Writer", "Critic"],
            "expected_output": "文章"
        },
        "worker_outputs": {},
        "draft": "",
        "critique": {},
        "final_output": "",
        "iteration": 0,
        "pipeline_index": 0,
        "events": [],
    }

    with patch("backend.agent.nodes.get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = worker_node(state)

    assert result["pipeline_index"] == 1
    assert "Researcher" in result["worker_outputs"]
    assert result["worker_outputs"]["Researcher"] == "这是研究员的研究笔记"
    assert len(result["events"]) >= 2
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_nodes.py::test_worker_node_calls_correct_role -v
# Expected: FAIL (NameError: worker_node not defined)
```

- [ ] **Step 3: 实现 Worker 节点**

```python
# 追加到 backend/agent/nodes.py

def _build_worker_context(state: StudioState) -> str:
    """从已有 worker_outputs 构建上下文"""
    if not state["worker_outputs"]:
        return "（尚无上下文，这是 pipeline 的第一步）"

    parts = []
    for role, output in state["worker_outputs"].items():
        # 截断过长输出
        truncated = output[:2000] + "..." if len(output) > 2000 else output
        parts.append(f"### {role} 的产出：\n{truncated}")
    return "\n\n".join(parts)


def worker_node(state: StudioState) -> dict:
    """通用 Worker 节点：根据 pipeline 当前位置执行对应角色"""
    pipeline = state["plan"]["pipeline"]
    idx = state["pipeline_index"]

    # 找到当前步骤的角色名
    current_step = pipeline[idx]

    # Critic/Reviser 不由 worker_node 处理
    if current_step in ("Critic", "Reviser"):
        return {"pipeline_index": idx + 1}

    role_name = current_step

    # 从 plan["roles"] 中找到对应信息
    role_info = next(
        (r for r in state["plan"]["roles"] if r["name"] == role_name),
        {"name": role_name, "focus": "完成你的专业工作"}
    )

    _emit(state, "agent_start", role_name.lower(),
          f"开始工作：{role_info['focus']}")

    from backend.agent.prompts import WORKER_BASE_PROMPT, ROLE_DESCRIPTIONS

    system_prompt = WORKER_BASE_PROMPT.format(
        role_name=role_name,
        role_description=ROLE_DESCRIPTIONS.get(role_name, ROLE_DESCRIPTIONS["Writer"]),
        task=state["task"],
        context=_build_worker_context(state),
        role_focus=role_info.get("focus", "完成你的专业工作"),
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请开始你的工作，直接输出结果。"},
    ]

    response = chat(messages)

    # 更新 worker_outputs
    new_outputs = dict(state["worker_outputs"])
    output_key = role_name
    if output_key in new_outputs:
        # 同名角色多次出现 → 加后缀
        i = 1
        while f"{role_name}_{i}" in new_outputs:
            i += 1
        output_key = f"{role_name}_{i}"
    new_outputs[output_key] = response

    # 对于产出型角色（Writer/Analyst/Designer），同时设为 draft
    new_draft = state["draft"]
    if role_name in ("Writer", "Analyst", "Designer"):
        new_draft = response

    _emit(state, "agent_done", role_name.lower(), "工作完成")

    return {
        "worker_outputs": new_outputs,
        "draft": new_draft,
        "pipeline_index": idx + 1,
        "events": state.get("events", []),
    }
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_nodes.py::test_worker_node_calls_correct_role -v
# Expected: PASS
```

---

### Task 7: Critic + Reviser 节点

**Files:**
- Modify: `Mentex/backend/agent/nodes.py`（追加 Critic + Reviser）
- Modify: `Mentex/tests/test_nodes.py`（追加测试）

- [ ] **Step 1: 写 Critic 测试**

```python
# 追加到 tests/test_nodes.py

def test_critic_passes_high_quality():
    """高分草稿 → Critic 判定 pass"""
    from backend.agent.nodes import critic_node

    critique_json = json.dumps({
        "score": 8.5,
        "strengths": ["逻辑清晰", "内容充实"],
        "weaknesses": ["结尾略仓促"],
        "suggestions": ["加一个总结段落"],
        "verdict": "pass"
    })

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = f"```json\n{critique_json}\n```"

    state: StudioState = {
        "task": "写一篇AI文章",
        "messages": [],
        "plan": {"pipeline": ["Writer", "Critic"], "plan_summary": "test"},
        "worker_outputs": {"Writer": "一篇关于AI的好文章..."},
        "draft": "一篇关于AI的好文章...",
        "critique": {},
        "final_output": "",
        "iteration": 0,
        "pipeline_index": 1,
        "events": [],
    }

    with patch("backend.agent.nodes.get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = critic_node(state)

    assert result["critique"]["verdict"] == "pass"
    assert result["critique"]["score"] == 8.5
    assert result["final_output"] == state["draft"]


def test_critic_revises_low_quality():
    """低分草稿 → Critic 判定 revise"""
    from backend.agent.nodes import critic_node

    critique_json = json.dumps({
        "score": 5.0,
        "strengths": ["选题不错"],
        "weaknesses": ["逻辑混乱", "缺乏深度"],
        "suggestions": ["重新组织结构", "增加具体案例"],
        "verdict": "revise"
    })

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = f"```json\n{critique_json}\n```"

    state: StudioState = {
        "task": "写一篇AI文章",
        "messages": [],
        "plan": {"pipeline": ["Writer", "Critic"], "plan_summary": "test"},
        "worker_outputs": {"Writer": "草率的内容..."},
        "draft": "草率的内容...",
        "critique": {},
        "final_output": "",
        "iteration": 0,
        "pipeline_index": 1,
        "events": [],
    }

    with patch("backend.agent.nodes.get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_response
        result = critic_node(state)

    assert result["critique"]["verdict"] == "revise"
    assert result["final_output"] == ""
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_nodes.py::test_critic_passes_high_quality -v
# Expected: FAIL
```

- [ ] **Step 3: 实现 Critic + Reviser 节点**

```python
# 追加到 backend/agent/nodes.py

def critic_node(state: StudioState) -> dict:
    """Critic 节点：审查草稿质量，输出评分和建议"""
    _emit(state, "agent_start", "critic", "开始审查草稿...")

    from backend.agent.prompts import CRITIC_PROMPT

    prompt = CRITIC_PROMPT.format(
        draft=state["draft"],
        task=state["task"],
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请审查以上草稿并输出 JSON。"},
    ]

    response = chat(messages, temperature=0.2)
    critique = _parse_json_from_response(response)

    _emit(state, "agent_done", "critic",
          f"评分: {critique['score']}/10, "
          f"判定: {'✅ 通过' if critique['verdict'] == 'pass' else '⚠️ 需要修改'}")

    result = {
        "critique": critique,
        "iteration": state.get("iteration", 0) + 1,
        "events": state.get("events", []),
    }

    # 如果通过，设置 final_output
    if critique["verdict"] == "pass":
        result["final_output"] = state["draft"]

    return result


def reviser_node(state: StudioState) -> dict:
    """Reviser 节点：根据 Critic 建议修改草稿"""
    _emit(state, "agent_start", "reviser", "根据审稿意见修改中...")

    from backend.agent.prompts import REVISER_PROMPT

    critique = state["critique"]
    prompt = REVISER_PROMPT.format(
        draft=state["draft"],
        score=critique.get("score", "?"),
        strengths=", ".join(critique.get("strengths", [])),
        weaknesses=", ".join(critique.get("weaknesses", [])),
        suggestions="\n".join(
            f"- {s}" for s in critique.get("suggestions", [])
        ),
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请输出修改后的完整草稿。"},
    ]

    revised = chat(messages)

    _emit(state, "agent_done", "reviser", "修改完成")

    return {
        "draft": revised,
        "events": state.get("events", []),
    }
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_nodes.py::test_critic_passes_high_quality tests/test_nodes.py::test_critic_revises_low_quality -v
# Expected: 2 PASSED
```

---

### Task 8: Graph 组装

**Files:**
- Create: `Mentex/backend/agent/graph.py`
- Create: `Mentex/tests/test_graph.py`

- [ ] **Step 1: 写 Graph 测试**

```python
# tests/test_graph.py
import json
from unittest.mock import patch, MagicMock
from backend.agent.graph import create_graph


def test_graph_runs_end_to_end():
    """端到端：简单任务，Planner → Writer → Critic(pass)"""
    plan_json = json.dumps({
        "task_type": "creative",
        "plan_summary": "写诗任务",
        "roles": [{"name": "Writer", "count": 1, "focus": "写一首诗"}],
        "pipeline": ["Writer"],
        "expected_output": "诗歌"
    })

    critique_json = json.dumps({
        "score": 9.0,
        "strengths": ["优美"],
        "weaknesses": [],
        "suggestions": [],
        "verdict": "pass"
    })

    # Mock LLM 按调用顺序返回不同内容
    call_responses = [
        f"```json\n{plan_json}\n```",       # Planner
        "明月几时有，把酒问青天...",           # Writer
        f"```json\n{critique_json}\n```",   # Critic
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = lambda **kwargs: _mock_response(
        call_responses
    )

    with patch("backend.agent.nodes.get_client", return_value=mock_client):
        graph = create_graph()
        result = graph.invoke({
            "task": "写一首关于月亮的诗",
            "messages": [],
            "plan": {},
            "worker_outputs": {},
            "draft": "",
            "critique": {},
            "final_output": "",
            "iteration": 0,
            "pipeline_index": 0,
            "events": [],
        })

    assert result["final_output"] != ""
    assert result["plan"]["task_type"] == "creative"
    assert result["critique"]["verdict"] == "pass"


_call_count = 0


def _mock_response(responses: list[str]):
    global _call_count
    resp = responses[_call_count % len(responses)]
    _call_count += 1
    m = MagicMock()
    m.choices = [MagicMock()]
    m.choices[0].message.content = resp
    return m
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_graph.py -v
# Expected: FAIL (ImportError)
```

- [ ] **Step 3: 实现 graph.py**

```python
# backend/agent/graph.py
from langgraph.graph import StateGraph, END
from backend.agent.state import StudioState
from backend.agent.nodes import (
    planner_node,
    worker_node,
    critic_node,
    reviser_node,
)


def _should_continue_workers(state: StudioState) -> str:
    """判断是否还有 Worker 需要执行"""
    pipeline = state["plan"].get("pipeline", [])
    idx = state.get("pipeline_index", 0)

    if idx < len(pipeline):
        step = pipeline[idx]
        if step in ("Critic",):
            return "critic"
        return "worker"

    return "critic"


def _after_critic(state: StudioState) -> str:
    """Critic 后判断：通过 or 修改？"""
    critique = state.get("critique", {})
    iteration = state.get("iteration", 0)

    if critique.get("verdict") == "pass":
        return "end"

    if critique.get("verdict") == "revise" and iteration < 2:
        return "reviser"

    # 兜底：超过 2 轮也要结束
    return "end"


def create_graph() -> StateGraph:
    """构建 Mentex Agent 状态图"""
    workflow = StateGraph(StudioState)

    # 添加节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("worker", worker_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("reviser", reviser_node)

    # 入口
    workflow.set_entry_point("planner")

    # Planner → Worker（开始执行 pipeline）
    workflow.add_edge("planner", "worker")

    # Worker → 条件：继续 Worker 还是去 Critic
    workflow.add_conditional_edges(
        "worker",
        _should_continue_workers,
        {
            "worker": "worker",
            "critic": "critic",
        }
    )

    # Critic → 条件：通过 / 修改 / 结束
    workflow.add_conditional_edges(
        "critic",
        _after_critic,
        {
            "end": END,
            "reviser": "reviser",
        }
    )

    # Reviser → Critic（再次审查）
    workflow.add_edge("reviser", "critic")

    return workflow.compile()
```

- [ ] **Step 4: 运行测试**

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
python -m pytest tests/test_graph.py -v
# Expected: PASS
```

---

### Task 9: Database

**Files:**
- Create: `Mentex/backend/db.py`
- Create: `Mentex/tests/test_db.py`

- [ ] **Step 1: 写 DB 测试**

```python
# tests/test_db.py
import pytest
from backend.db import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d


def test_save_and_get_task(db):
    task_id = db.save_task(
        task="测试任务",
        plan={"pipeline": ["Writer"]},
        final_output="测试产出",
        events=[{"event": "final", "content": "done"}],
    )
    assert task_id is not None

    task = db.get_task(task_id)
    assert task["task"] == "测试任务"
    assert task["final_output"] == "测试产出"


def test_list_history(db):
    db.save_task("任务1", {}, "产出1", [])
    db.save_task("任务2", {}, "产出2", [])
    db.save_task("任务3", {}, "产出3", [])

    history = db.list_history(limit=2)
    assert len(history) == 2
    # 最新的在前
    assert history[0]["task"] == "任务3"


def test_get_nonexistent_task(db):
    task = db.get_task("nonexistent")
    assert task is None
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_db.py -v
# Expected: FAIL (ImportError)
```

- [ ] **Step 3: 实现 db.py**

```python
# backend/db.py
import sqlite3
import json
import uuid
from datetime import datetime, timezone


class Database:
    def __init__(self, db_path: str = "Mentex.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                plan TEXT,
                final_output TEXT,
                events TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_task(
        self,
        task: str,
        plan: dict,
        final_output: str,
        events: list[dict],
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            """INSERT INTO tasks (id, task, plan, final_output, events, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                task,
                json.dumps(plan, ensure_ascii=False),
                final_output,
                json.dumps(events, ensure_ascii=False),
                now,
            ),
        )
        self.conn.commit()
        return task_id

    def get_task(self, task_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "task": row["task"],
            "plan": json.loads(row["plan"]) if row["plan"] else {},
            "final_output": row["final_output"],
            "events": json.loads(row["events"]) if row["events"] else [],
            "created_at": row["created_at"],
        }

    def list_history(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "task": row["task"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


# 全局单例
db = Database()
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_db.py -v
# Expected: 3 PASSED
```

---

### Task 10: FastAPI + SSE

**Files:**
- Create: `Mentex/backend/api.py`
- Create: `Mentex/tests/test_api.py`

- [ ] **Step 1: 写 API 测试**

```python
# tests/test_api.py
import json
import pytest
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient
from backend.api import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_task_endpoint_returns_sse():
    """POST /task 返回 SSE 事件流"""
    plan_json = json.dumps({
        "task_type": "creative",
        "plan_summary": "写诗",
        "roles": [{"name": "Writer", "count": 1, "focus": "写诗"}],
        "pipeline": ["Writer"],
        "expected_output": "诗歌"
    })

    critique_json = json.dumps({
        "score": 9.0,
        "strengths": ["好"],
        "weaknesses": [],
        "suggestions": [],
        "verdict": "pass"
    })

    call_responses = [
        f"```json\n{plan_json}\n```",
        "静夜思...",
        f"```json\n{critique_json}\n```",
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = (
        lambda **kwargs: _make_response(call_responses)
    )

    with patch("backend.agent.nodes.get_client", return_value=mock_client):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST", "/task", json={"task": "写一首诗"}
            ) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]

                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        events.append(json.loads(line[6:]))

                assert len(events) > 0
                # 最后一个事件应该是 final
                assert events[-1]["event"] == "final"

                # 应该有 planner 事件
                planner_events = [e for e in events if e["node"] == "planner"]
                assert len(planner_events) >= 2


@pytest.mark.anyio
async def test_history_endpoint():
    """GET /history 返回历史列表"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def _make_response(responses: list[str]):
    """模拟 LLM 顺序返回"""
    if not hasattr(_make_response, "counter"):
        _make_response.counter = 0
    resp = responses[_make_response.counter % len(responses)]
    _make_response.counter += 1
    m = MagicMock()
    m.choices = [MagicMock()]
    m.choices[0].message.content = resp
    return m
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_api.py -v
# Expected: FAIL (ImportError)
```

- [ ] **Step 3: 实现 api.py**

```python
# backend/api.py
import json
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.agent.graph import create_graph
from backend.agent.state import StudioState
from backend.db import db


app = FastAPI(title="Mentex API")

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


class TaskRequest(BaseModel):
    task: str


@app.post("/task")
async def run_task(req: TaskRequest):
    """执行 Agent 任务，返回 SSE 事件流"""
    queue = asyncio.Queue()
    graph = get_graph()

    initial_state: StudioState = {
        "task": req.task,
        "messages": [],
        "plan": {},
        "worker_outputs": {},
        "draft": "",
        "critique": {},
        "final_output": "",
        "iteration": 0,
        "pipeline_index": 0,
        "events": [],
    }

    async def event_generator():
        # 在后台线程运行 LangGraph（因为它使用同步 API）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, graph.invoke, initial_state)

        # 拉取所有事件
        events = result.get("events", [])

        # 逐个推送事件
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)  # 给前端渲染时间

        # 推送 final 事件
        final_event = {
            "event": "final",
            "timestamp": events[-1]["timestamp"] if events else "",
            "node": "system",
            "instance": "",
            "content": result.get("final_output", ""),
        }
        yield f"data: {json.dumps(final_event, ensure_ascii=False)}\n\n"

        # 存储到数据库
        db.save_task(
            task=req.task,
            plan=result.get("plan", {}),
            final_output=result.get("final_output", ""),
            events=events,
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/history")
async def get_history(limit: int = 20):
    """获取历史任务列表"""
    return db.list_history(limit)


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    """获取单个任务详情"""
    task = db.get_task(task_id)
    if not task:
        return {"error": "task not found"}
    return task
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_api.py -v
# Expected: 2 PASSED
```

---

### Task 11: Streamlit UI

**Files:**
- Create: `Mentex/frontend/app.py`

- [ ] **Step 1: 实现 Streamlit 前端**

```python
# frontend/app.py
import streamlit as st
import requests
import json
import sseclient

st.set_page_config(
    page_title="Mentex — 多 Agent 创意工作室",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Mentex — 多 Agent 创意工作室")
st.caption("像老板一样下达任务，然后看你的 AI 团队开工")

# ── 侧边栏：输入 + 历史 ──
with st.sidebar:
    st.subheader("📝 新任务")
    task = st.text_area(
        "任务描述",
        height=150,
        placeholder="例如：分析 2026 年 AI Agent 的发展趋势，写一篇深度文章\n\n或者简单点：写一首关于秋天的诗",
        key="task_input",
    )

    col1, col2 = st.columns(2)
    with col1:
        run_btn = st.button(
            "🚀 开始执行", type="primary", use_container_width=True
        )
    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            st.rerun()

    st.divider()

    st.subheader("📚 历史任务")
    try:
        resp = requests.get("http://localhost:8000/history", timeout=5)
        if resp.status_code == 200:
            history = resp.json()
            for item in history:
                with st.expander(
                    f"{item['task'][:30]}... — {item['created_at'][:10]}"
                ):
                    st.write(item["task"])
                    if st.button("🔁 重新执行", key=f"rerun_{item['id']}"):
                        st.session_state.task_input = item["task"]
                        st.rerun()
    except requests.ConnectionError:
        st.caption("⚠️ 后端未启动")

# ── 主区域：执行过程 ──
if run_btn and task:
    # 预分配各角色的展示容器
    role_icons = {
        "planner":     "🧠",
        "researcher":  "🔍",
        "synthesizer": "🔗",
        "writer":      "✍️",
        "designer":    "🎨",
        "analyst":     "📊",
        "critic":      "👁️",
        "reviser":     "🔧",
        "system":      "📦",
    }

    # 为每个可能出现的角色创建 expander 占位
    containers = {}
    placeholders = {}

    # 先创建 Planner 和 Critic（一定会出现）
    for role in ["planner", "critic"]:
        icon = role_icons.get(role, "🔹")
        containers[role] = st.expander(f"{icon} {role.title()}", expanded=True)
        placeholders[role] = containers[role].empty()

    final_area = st.empty()

    # 连接 SSE
    try:
        with requests.post(
            "http://localhost:8000/task",
            json={"task": task},
            stream=True,
            timeout=300,
        ) as r:
            if r.status_code != 200:
                st.error(f"后端错误: {r.status_code}")
            else:
                client = sseclient.SSEClient(r)
                agent_outputs = {}  # {node: accumulated_text}

                for sse_event in client.events():
                    data = json.loads(sse_event.data)
                    node = data.get("node", "system")
                    event_type = data.get("event", "")
                    content = data.get("content", "")

                    # 为新出现的角色动态创建 expander
                    if node not in containers:
                        icon = role_icons.get(node, "🔹")
                        containers[node] = st.expander(
                            f"{icon} {node.title()}", expanded=True
                        )
                        placeholders[node] = containers[node].empty()
                        agent_outputs[node] = ""

                    if node not in agent_outputs:
                        agent_outputs[node] = ""

                    if event_type == "agent_start":
                        agent_outputs[node] = f"⏳ {content}\n\n"
                        placeholders[node].markdown(agent_outputs[node])

                    elif event_type == "agent_output":
                        # 流式追加
                        agent_outputs[node] += content
                        placeholders[node].markdown(agent_outputs[node])

                    elif event_type == "agent_done":
                        agent_outputs[node] += f"\n\n✅ {content}"
                        placeholders[node].markdown(agent_outputs[node])

                    elif event_type == "final":
                        if content:
                            final_area.markdown("---")
                            final_area.subheader("📦 最终产出")
                            final_area.markdown(content)

                            # 复制和下载按钮
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.code(content, language="markdown")
                            with col2:
                                st.download_button(
                                    "💾 下载 Markdown",
                                    content,
                                    "output.md",
                                    use_container_width=True,
                                )

                    if event_type == "error":
                        st.error(content)

    except requests.ConnectionError:
        st.error("❌ 无法连接后端，请先启动: python -m uvicorn backend.api:app --port 8000")

elif run_btn and not task:
    st.warning("请在侧边栏输入任务描述")
```

- [ ] **Step 2: 手动验证**

```bash
# 终端 1：启动后端
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：启动前端
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
streamlit run frontend/app.py
```

浏览器打开 http://localhost:8501，输入一个任务测试。

---

### Task 12: 集成验证

**Files:**
- Modify: `Mentex/README.md`（更新）
- Create: `Mentex/.env`（从 .env.example 复制）

- [ ] **Step 1: 运行完整测试套件**

```bash
cd /home/max-rayyy/ai-workspace/Mentex
source ../.venv/bin/activate
python -m pytest tests/ -v
# Expected: ALL PASS (7+ tests)
```

- [ ] **Step 2: 真实 API 集成测试（需要配置 .env）**

```bash
# 先确保 .env 已配置
cp .env.example .env
# 编辑 .env 填入真实的 DEEPSEEK_API_KEY

# 启动后端
python -m uvicorn backend.api:app --port 8000 &

# 用 curl 测试
curl -X POST http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"task": "用100字介绍深度学习"}' \
  --no-buffer

# 应该看到 SSE 事件流
```

- [ ] **Step 3: 更新 README**

README 已在 Task 1 创建，验证内容与最终结构一致。

---

## 自审检查

1. **Spec 覆盖检查**
   - [x] Planner 动态组队 → Task 5
   - [x] 8 个角色池 → Task 4 (prompts) + Task 6 (worker)
   - [x] LangGraph 状态图 → Task 3 (state) + Task 8 (graph)
   - [x] Critic-Reviser 循环 → Task 7
   - [x] SSE 事件流 → Task 10
   - [x] Streamlit UI → Task 11
   - [x] SQLite 存储 → Task 9

2. **占位符检查**
   - [x] 无 TBD、TODO
   - [x] 无 "add appropriate error handling"
   - [x] 所有步骤含具体代码或命令

3. **类型一致性**
   - [x] StudioState 各字段在 nodes.py、graph.py、api.py 中一致
   - [x] Event 格式在 nodes.py、api.py、app.py 中一致
   - [x] DB 接口在 db.py 和 api.py 中一致

---

## Phase 1 实施总结

**完成日期**：2026-06-08  
**实际测试数**：16 tests（3 config + 6 nodes + 2 graph + 3 db + 2 api）  
**Git 仓库**：https://github.com/Maxrayyy/Mentex.git

### 完成情况

| Task | 内容 | 状态 |
|------|------|------|
| 1 | 项目初始化与环境配置 | ✅ 完成 |
| 2 | Config + LLM 客户端 | ✅ 完成 |
| 3 | State 定义 | ✅ 完成 |
| 4 | Prompts（8 个角色） | ✅ 完成 |
| 5 | Planner 节点 | ✅ 完成 |
| 6 | Worker 节点 | ✅ 完成 |
| 7 | Critic + Reviser 节点 | ✅ 完成 |
| 8 | Graph 组装 | ✅ 完成 |
| 9 | Database (SQLite) | ✅ 完成 |
| 10 | FastAPI + 流式端点 | ✅ 完成 |
| 11 | Streamlit UI | ✅ 完成 |
| 12 | 集成验证 + 文档 | ✅ 完成 |

### 与原始计划的主要差异

| 项目 | 原始计划 | 实际实现 | 原因 |
|------|----------|----------|------|
| LLM | DeepSeek only | Agnes AI + DeepSeek 双 Provider | Agnes 免费、支持 Function Calling |
| 流式方案 | SSE (Server-Sent Events) | 增量轮询 (GET /events?after=N) | SSE 阻塞 Streamlit 单线程渲染 |
| 流式执行 | graph.invoke() | graph.stream(stream_mode="values") | 逐节点即时产出事件 |
| 事件引用 | 直接赋值 | `list()` copy | LangGraph 复用 list 引用导致 delta 为空 bug |
| Writer prompt | 允许引用标注 | 禁止 [1][2] 脚注 | agnes-2.0-flash 自动加引用 |

### 踩过的坑

1. **LangGraph list 引用复用**：`all_events = current` 会导致下一次迭代 `len(all_events) == len(current)`（同一对象），delta 永远为空。必须 `list()` copy。
2. **Streamlit + SSE 死锁**：SSE 消费的 for 循环占用主线程，UI 无法渲染。改用 `st.rerun()` 每次只做一次 HTTP 请求。
3. **Streamlit 首次设置**：需要预先创建 `~/.streamlit/credentials.toml` 跳过邮箱输入。
4. **Agnes 模型名**：`LLM_PROVIDER=agnes` 时模型必须是 `agnes-2.0-flash`，不能传 `deepseek-v4-flash`。

---

## Phase 2 实施总结

**完成日期**：2026-06-09
**Git 提交**：3 commits after Phase 1

### Phase 2 任务清单

| Task | 内容 | 状态 |
|------|------|------|
| 2.1 | 后端 SSE 端点（asyncio.Queue + sse-starlette） | ✅ 完成 |
| 2.2 | React 项目脚手架（Vite + TS + Tailwind CSS v4） | ✅ 完成 |
| 2.3 | 类型定义 + Context 状态管理 + useTaskStream Hook | ✅ 完成 |
| 2.4 | 三栏布局组件（Sidebar / MainContent / WorkflowPanel） | ✅ 完成 |
| 2.5 | AgentCard + PipelineVisualization | ✅ 完成 |
| 2.6 | 轮询 → SSE（EventSource 直连后端） | ✅ 完成 |
| 2.7 | 白色主题 + Fira Code/Sans 字体 + Lucide 图标 | ✅ 完成 |
| 2.8 | 输入框移到中间底部 | ✅ 完成 |
| 2.9 | Token 调用量显示（后台日志 + 前端 UI） | ✅ 完成 |
| 2.10 | SSE 稳定性修复（event: error → task_error） | ✅ 完成 |
| 2.11 | LLM 客户端超时 + Agent 执行日志 | ✅ 完成 |
| 2.12 | CORS + Vite 代理（REST 走代理、SSE 直连） | ✅ 完成 |

### 与 Phase 1 的主要差异

| 项目 | Phase 1 | Phase 2 | 原因 |
|------|---------|---------|------|
| 前端 | Streamlit | React (Vite + TS) | SSE 消费、三栏布局、精细样式 |
| 流式方案 | 增量轮询 (0.5s) | SSE EventSource | 真正实时推送 |
| 事件传输 | HTTP GET /events?after=N | GET /stream (SSE) | 服务器主动推送 |
| UI 布局 | 单栏 expander | 三栏（历史\|内容\|工作流） | 更好的信息架构 |
| 主题 | Streamlit 默认 | 浅色主题 + Fira 字体 | 专业设计系统 |
| 图标 | Emoji | Lucide React SVG | UI/UX 规范 |
| Token 追踪 | 无 | 后端日志 + 前端面板 | 成本可见性 |
| LLM 调用 | 无超时 | 120s 超时 | 防止无限挂起 |

### Phase 2 踩过的坑

1. **Vite 代理缓冲 SSE**：Vite 的 http-proxy 会缓冲 SSE 流。解决方案：REST 走 `/api` 代理，SSE 直连 `localhost:8000`（需配置 CORS）。
2. **SSE event: error 坑**：浏览器将 `event: error` 当作传输错误关闭 EventSource。改用 `event: task_error`。
3. **EventSource error handler 混淆**：`addEventListener('error')` 同时捕获传输错误和自定义 SSE error 事件。改用 `es.onerror` 只处理传输层错误。
4. **asyncio.Queue 线程安全**：后台线程通过 `loop.call_soon_threadsafe(q.put_nowait)` 推送事件到主线程的 asyncio.Queue。
5. **LangGraph State 追加字段**：新增 `total_tokens` 字段后需在所有返回 dict 的节点中传递，否则 LangGraph 不会自动保留。

---

## Phase 3 稳定性修复

**完成日期**：2026-06-09
**Git 提交**：
- `44b4bc3` fix: CORS 127.0.0.1白名单 + asyncio event loop跨线程修复
- `c9cdfde` feat: Pipeline 图标化 + UI 布局优化

### 修复清单

| Task | 内容 | 状态 |
|------|------|------|
| 3.1 | CORS origin 补全（127.0.0.1 vs localhost） | ✅ 完成 |
| 3.2 | asyncio.get_event_loop() 跨线程 RuntimeError | ✅ 完成 |
| 3.3 | 前端 SSE Hook 重构（简化 ref、添加错误日志） | ✅ 完成 |
| 3.4 | Pipeline 去掉角色名（仅图标 + 连接线） | ✅ 完成 |
| 3.5 | Planner 消息 pipeline 用 emoji 图标替代文字 | ✅ 完成 |
| 3.6 | AgentCard 紧凑布局 + token 后缀 + 防溢出 | ✅ 完成 |
| 3.7 | FinalResult width→full 占满中间区域 | ✅ 完成 |
| 3.8 | StreamingOutput 支持 `\n` 换行渲染 | ✅ 完成 |

### Phase 3 踩过的坑

1. **CORS origin 127.0.0.1 ≠ localhost**：浏览器将 `127.0.0.1:5173` 和 `localhost:5173` 视为不同源。用户从 `127.0.0.1` 访问前端时，CORS 白名单中只有 `localhost` → SSE 被浏览器拦截。**解决**：同时添加两个地址到 `allow_origins`。

2. **`asyncio.get_event_loop()` 跨线程抛 RuntimeError** ⭐ 关键 bug：后台线程 `_run_agent()` 中调用 `asyncio.get_event_loop()` 时，Python 3.10+ 非主线程不再自动返回主线程 event loop → 抛 `RuntimeError` → 被 `except RuntimeError: pass` 静默吞掉 → 所有 SSE 事件丢失，只剩心跳。**解决**：在 FastAPI `startup` 事件中用 `asyncio.get_running_loop()` 捕获主线程 loop 引用 `_main_loop`，`_push_event_safe()` 改用 `_main_loop.call_soon_threadsafe()`。

3. **前端 EventSource 错误处理不足**：原始代码 `catch { /* ignore parse errors */ }` 静默丢弃所有 JSON 解析错误，导致排查困难。**解决**：添加 `console.error` 输出具体错误信息。
