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

    # 模拟 LLM 返回的 JSON（planner_node 用 chat() 调用）

    # mock chat() 函数本身（planner_node 直接 import 了 chat）
    with patch("backend.agent.nodes.chat", return_value=f"```json\n{plan_json}\n```"):

        # 构造初始 state（只有 task 有值）
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

        # 验证：plan 被正确解析
        assert result["plan"]["task_type"] == "article"
        assert len(result["plan"]["pipeline"]) == 3      # Writer + 自动追加 Critic
        assert "Researcher" in result["plan"]["pipeline"]
        assert "Critic" in result["plan"]["pipeline"]    # Planner 自动追加
        # 验证：发行了事件（前端能看到）
        assert len(result["events"]) >= 2
