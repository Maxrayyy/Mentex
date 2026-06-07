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
    """惰性初始化 Graph（只构建一次）"""
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


class TaskRequest(BaseModel):
    task: str


@app.post("/task")
async def run_task(req: TaskRequest):
    """执行 Agent 任务，返回 SSE 事件流"""

    graph = get_graph()

    # 初始 state
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
        # LangGraph 是同步的，在线程池中执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, graph.invoke, initial_state)

        events = result.get("events", [])

        # 逐条推送事件
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)  # 模拟流式延迟

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
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
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
