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


def test_worker_node_runs_researcher():
    """Worker 节点：根据 pipeline 当前位置，以 Researcher 角色执行"""
    from backend.agent.nodes import worker_node

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
        "pipeline_index": 0,    # ← 当前在 pipeline 第 0 步 = Researcher
        "events": [],
    }

    # Mock：LLM 返回一段研究笔记
    with patch("backend.agent.nodes.chat", return_value="AI发展趋势研究笔记：..."):
        result = worker_node(state)

    # 验证：pipeline 前进了一步
    assert result["pipeline_index"] == 1
    # 验证：Researcher 的产出被存下来了
    assert "Researcher" in result["worker_outputs"]
    assert result["worker_outputs"]["Researcher"] == "AI发展趋势研究笔记：..."
    # 验证：事件被记录
    assert len(result["events"]) >= 2


def test_worker_skips_critic():
    """Worker 遇到 Critic 或 Reviser 时直接跳过（不由 worker_node 处理）"""
    from backend.agent.nodes import worker_node

    state: StudioState = {
        "task": "测试",
        "messages": [],
        "plan": {
            "pipeline": ["Writer", "Critic"],
            "plan_summary": "test",
            "roles": [],
            "expected_output": "test"
        },
        "worker_outputs": {},
        "draft": "",
        "critique": {},
        "final_output": "",
        "iteration": 0,
        "pipeline_index": 1,    # ← 当前指向 Critic
        "events": [],
    }

    result = worker_node(state)

    # Critic 不由 worker_node 处理 → 只移动 index 到下一步
    assert result["pipeline_index"] == 2
