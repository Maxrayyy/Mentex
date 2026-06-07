import json
import re
from datetime import datetime, timezone
from backend.agent.state import StudioState
from backend.agent.prompts import PLANNER_PROMPT
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
