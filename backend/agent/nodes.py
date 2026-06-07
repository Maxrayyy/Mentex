import json
import re
from datetime import datetime, timezone
from backend.agent.state import StudioState
from backend.agent.prompts import PLANNER_PROMPT, WORKER_BASE_PROMPT, ROLE_DESCRIPTIONS
from backend.llm import get_client, chat
from backend.config import settings


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 格式字符串"""
    return datetime.now(timezone.utc).isoformat()


def _emit(state: StudioState, event: str, node: str, content: str, instance: str = ""):
    """向事件流追加一条事件（前端用 SSE 消费）"""
    state["events"].append({
        "event": event,
        "timestamp": _now_iso(),
        "node": node,
        "instance": instance,
        "content": content,
    })


def _parse_json_from_response(text: str) -> dict:
    """从 LLM 的回复中提取 JSON（处理 ```json ... ``` 代码块）"""
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
    """Planner 节点：分析用户任务 → 输出执行计划（角色 + pipeline）"""
    # 1️⃣ 发事件：告诉前端 "Planner 开始了"
    _emit(state, "agent_start", "planner", "开始分析任务...")

    # 2️⃣ 构造发给 LLM 的消息
    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": state["task"]},
    ]

    # 3️⃣ 调用 LLM，获取计划
    response = chat(messages, temperature=0.3)  # 低温度 = 更稳定
    plan = _parse_json_from_response(response)

    # 4️⃣ 自动追加 Critic 到 pipeline 末尾（保证每次都有质量审查）
    if "Critic" not in plan.get("pipeline", []):
        plan["pipeline"].append("Critic")

    # 5️⃣ 发事件：告诉前端结果
    _emit(state, "agent_done", "planner",
          f"计划制定完成：{plan.get('plan_summary', '')}，"
          f"pipeline: {' → '.join(plan.get('pipeline', []))}")

    # 6️⃣ 返回要更新的 state 字段
    return {
        "plan": plan,
        "pipeline_index": 0,
        "iteration": 0,
        "worker_outputs": {},
        "draft": "",
        "critique": {},
        "events": state.get("events", []),
    }


def _build_worker_context(state: StudioState) -> str:
    """把之前所有 Worker 的产出拼成一段上下文，供当前 Worker 参考"""
    if not state["worker_outputs"]:
        return "（这是 pipeline 的第一步，没有前人的产出可以参考）"

    parts = []
    for role_name, output in state["worker_outputs"].items():
        # 截断过长内容，避免超过 LLM 上下文窗口
        truncated = output[:2000] + "..." if len(output) > 2000 else output
        parts.append(f"### {role_name} 的产出：\n{truncated}")
    return "\n\n".join(parts)


def worker_node(state: StudioState) -> dict:
    """通用 Worker 节点：读 pipeline 当前位置 → 以对应角色调用 LLM → 存产出 → 前进"""

    pipeline = state["plan"]["pipeline"]
    idx = state["pipeline_index"]
    current_step = pipeline[idx]

    # 1️⃣ 如果当前步骤是 Critic 或 Reviser，跳过（由专门的节点处理）
    if current_step in ("Critic", "Reviser"):
        return {"pipeline_index": idx + 1}

    role_name = current_step

    # 2️⃣ 从计划里找到这个角色的详细信息（focus 字段等）
    role_info = next(
        (r for r in state["plan"]["roles"] if r["name"] == role_name),
        {"name": role_name, "focus": "完成你的专业工作"}
    )

    _emit(state, "agent_start", role_name.lower(),
          f"开始工作：{role_info['focus']}")

    # 3️⃣ 构造 Prompt：用模板填入角色描述 + 任务 + 前人产出（上下文）
    system_prompt = WORKER_BASE_PROMPT.format(
        role_name=role_name,
        role_description=ROLE_DESCRIPTIONS.get(
            role_name, ROLE_DESCRIPTIONS["Writer"]
        ),
        task=state["task"],
        context=_build_worker_context(state),
        role_focus=role_info.get("focus", "完成你的专业工作"),
    )

    # 4️⃣ 调用 LLM
    response = chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请开始你的工作，直接输出结果。"},
    ])

    # 5️⃣ 存产出
    new_outputs = dict(state["worker_outputs"])
    output_key = role_name
    # 处理同名角色多次出现的情况（如两个 Researcher → Researcher_1）
    if output_key in new_outputs:
        i = 1
        while f"{role_name}_{i}" in new_outputs:
            i += 1
        output_key = f"{role_name}_{i}"
    new_outputs[output_key] = response

    # 6️⃣ 对于产出型角色（Writer/Analyst/Designer），同时更新 draft
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


def critic_node(state: StudioState) -> dict:
    """Critic 节点：审查草稿质量 → 输出评分 + pass/revise 判定"""
    _emit(state, "agent_start", "critic", "开始审查草稿...")

    from backend.agent.prompts import CRITIC_PROMPT

    # 1️⃣ 把草稿和原始需求填进 Critic Prompt
    prompt = CRITIC_PROMPT.format(
        draft=state["draft"],
        task=state["task"],
    )

    # 2️⃣ 调 LLM，要求返回严格 JSON
    response = chat([
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请审查以上草稿并输出 JSON。"},
    ], temperature=0.2)  # 低温度，评审要稳定

    critique = _parse_json_from_response(response)

    # 3️⃣ 发事件：告诉前端审查结果
    _emit(state, "agent_done", "critic",
          f"评分: {critique['score']}/10, "
          f"判定: {'✅ 通过' if critique['verdict'] == 'pass' else '⚠️ 需要修改'}")

    result = {
        "critique": critique,
        "iteration": state.get("iteration", 0) + 1,
        "events": state.get("events", []),
    }

    # 4️⃣ 通过 → 直接设 final_output；需要改 → 留给 Reviser
    if critique["verdict"] == "pass":
        result["final_output"] = state["draft"]

    return result


def reviser_node(state: StudioState) -> dict:
    """Reviser 节点：根据 Critic 的建议逐条修改草稿"""
    _emit(state, "agent_start", "reviser", "根据审稿意见修改中...")

    from backend.agent.prompts import REVISER_PROMPT

    critique = state["critique"]

    # 1️⃣ 把原始草稿 + Critic 的所有意见填进 Reviser Prompt
    prompt = REVISER_PROMPT.format(
        draft=state["draft"],
        score=critique.get("score", "?"),
        strengths=", ".join(critique.get("strengths", [])),
        weaknesses=", ".join(critique.get("weaknesses", [])),
        suggestions="\n".join(
            f"- {s}" for s in critique.get("suggestions", [])
        ),
    )

    # 2️⃣ 调 LLM 修改
    revised = chat([
        {"role": "system", "content": prompt},
        {"role": "user", "content": "请输出修改后的完整草稿。"},
    ])

    _emit(state, "agent_done", "reviser", "修改完成")

    return {
        "draft": revised,
        "events": state.get("events", []),
    }
