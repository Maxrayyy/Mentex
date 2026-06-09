from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class StudioState(TypedDict):
    """多 Agent 协作工作流的状态"""

    # 用户原始任务
    task: str

    # 对话历史（LangGraph 自动追加）
    messages: Annotated[list, add_messages]

    # Planner 产出 {task_type, plan_summary, roles, pipeline, expected_output}
    plan: dict

    # 各 Worker 的产出 {role_instance: content}
    worker_outputs: dict

    # 当前草稿（Writer / Analyst / Designer 的产出）
    draft: str

    # Critic 审查结果 {score, strengths, weaknesses, suggestions, verdict}
    critique: dict

    # 最终产出
    final_output: str

    # Critic-Reviser 循环计数
    iteration: int

    # 当前 pipeline 执行位置
    pipeline_index: int

    # 累计 token 用量
    total_tokens: int

    # 事件流（供 SSE 消费）
    events: list[dict]
