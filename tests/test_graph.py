import json
from unittest.mock import patch


# LLM 调用计数器（模拟不同阶段返回不同内容）
_call_count = 0


def _mock_chat_response(*responses):
    """工厂函数：返回一个 side_effect 函数，按顺序返回不同响应"""
    global _call_count
    _call_count = 0

    ordered_responses = list(responses)

    def side_effect(*args, **kwargs):
        global _call_count
        resp = ordered_responses[_call_count % len(ordered_responses)]
        _call_count += 1
        return resp

    return side_effect


def test_graph_simple_task_end_to_end():
    """端到端：简单任务 → Planner → Writer → Critic(pass) → 产出"""
    from backend.agent.graph import create_graph

    # 1️⃣ Planner 返回的计划
    plan_json = json.dumps({
        "task_type": "creative",
        "plan_summary": "写一首诗",
        "roles": [{"name": "Writer", "count": 1, "focus": "写一首诗"}],
        "pipeline": ["Writer"],
        "expected_output": "诗歌"
    })

    # 2️⃣ Critic 返回的评审
    critique_json = json.dumps({
        "score": 9.0,
        "strengths": ["优美", "有意境"],
        "weaknesses": [],
        "suggestions": [],
        "verdict": "pass"
    })

    # 按调用顺序 mock 返回：Planner → Writer → Critic
    with patch("backend.agent.nodes.chat",
               side_effect=_mock_chat_response(
                   f"```json\n{plan_json}\n```",       # 第 0 次: Planner
                   "床前明月光，疑是地上霜...",            # 第 1 次: Writer
                   f"```json\n{critique_json}\n```",   # 第 2 次: Critic
               )):
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

    # 验证完整流程
    assert result["plan"]["task_type"] == "creative"
    assert "Writer" in result["worker_outputs"]
    assert result["critique"]["verdict"] == "pass"
    assert result["final_output"] == result["draft"]
    assert len(result["events"]) >= 6  # Planner start/done + Writer start/done + Critic start/done


def test_graph_with_revision():
    """端到端：低分 → Critic(revise) → Reviser → Critic(pass) → 产出"""
    from backend.agent.graph import create_graph

    plan_json = json.dumps({
        "task_type": "creative",
        "plan_summary": "写文章",
        "roles": [{"name": "Writer", "count": 1, "focus": "写文章"}],
        "pipeline": ["Writer"],
        "expected_output": "文章"
    })

    critique_bad = json.dumps({
        "score": 4.0,
        "strengths": ["选题可以"],
        "weaknesses": ["内容太短", "缺少细节"],
        "suggestions": ["扩展内容", "增加例子"],
        "verdict": "revise"
    })

    critique_good = json.dumps({
        "score": 8.0,
        "strengths": ["内容充实", "例子好"],
        "weaknesses": [],
        "suggestions": [],
        "verdict": "pass"
    })

    with patch("backend.agent.nodes.chat",
               side_effect=_mock_chat_response(
                   f"```json\n{plan_json}\n```",         # Planner
                   "只有两句话的草草草稿。",                 # Writer
                   f"```json\n{critique_bad}\n```",      # Critic 第 1 轮
                   "修改后的长文章，内容丰富了好多。",        # Reviser
                   f"```json\n{critique_good}\n```",     # Critic 第 2 轮（通过）
               )):
        graph = create_graph()
        result = graph.invoke({
            "task": "写一篇文章",
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

    assert result["critique"]["verdict"] == "pass"
    assert result["iteration"] == 2  # 经历了两轮审查
    assert result["final_output"] != ""
    assert "内容" in result["final_output"]
