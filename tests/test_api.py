import json
from unittest.mock import patch
import pytest
from httpx import ASGITransport, AsyncClient
from backend.api import app


@pytest.mark.anyio
async def test_history_endpoint():
    """GET /history 返回空列表"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_task_endpoint_returns_sse():
    """POST /task 返回 SSE 事件流，末尾有 final 事件"""
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

    # 按顺序 mock: Planner → Writer → Critic
    call_count = [0]
    responses = [
        f"```json\n{plan_json}\n```",
        "静夜思...",
        f"```json\n{critique_json}\n```",
    ]

    def mock_chat(*args, **kwargs):
        idx = call_count[0] % len(responses)
        call_count[0] += 1
        return responses[idx]

    with patch("backend.agent.nodes.chat", side_effect=mock_chat):
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
                # 最后一个事件必须是 final
                assert events[-1]["event"] == "final"
                # 有 Planner 的事件
                planner_events = [e for e in events if e["node"] == "planner"]
                assert len(planner_events) >= 2  # agent_start + agent_done
