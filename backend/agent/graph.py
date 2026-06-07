from langgraph.graph import StateGraph, END
from backend.agent.state import StudioState
from backend.agent.nodes import (
    planner_node,
    worker_node,
    critic_node,
    reviser_node,
)


def _should_continue_workers(state: StudioState) -> str:
    """Worker 执行完一步后：继续 Worker 还是去 Critic？"""
    pipeline = state.get("plan", {}).get("pipeline", [])
    idx = state.get("pipeline_index", 0)

    if idx >= len(pipeline):
        # pipeline 结束了，但理论上不应该到这里（Critic 已自动追加）
        return "critic"

    next_step = pipeline[idx]
    if next_step == "Critic":
        return "critic"
    return "worker"


def _after_critic(state: StudioState) -> str:
    """Critic 审查后：通过 → 结束 / 修改 → Reviser / 兜底 → 结束"""
    critique = state.get("critique", {})
    iteration = state.get("iteration", 0)

    if critique.get("verdict") == "pass":
        return "end"

    if critique.get("verdict") == "revise" and iteration < 2:
        return "reviser"

    # 兜底：超过 2 轮也要结束，避免无限循环
    return "end"


def create_graph():
    """构建完整的 Mentex Agent 工作流图"""
    workflow = StateGraph(StudioState)

    # 注册节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("worker", worker_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("reviser", reviser_node)

    # 入口：永远从 Planner 开始
    workflow.set_entry_point("planner")

    # Planner → Worker（开始执行 pipeline）
    workflow.add_edge("planner", "worker")

    # Worker → 条件路由
    workflow.add_conditional_edges(
        "worker",
        _should_continue_workers,
        {
            "worker": "worker",
            "critic": "critic",
        }
    )

    # Critic → 条件路由
    workflow.add_conditional_edges(
        "critic",
        _after_critic,
        {
            "end": END,
            "reviser": "reviser",
        }
    )

    # Reviser → Critic（修改后重新审查）
    workflow.add_edge("reviser", "critic")

    return workflow.compile()
