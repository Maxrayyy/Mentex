import asyncio
import json
import threading
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from backend.agent.graph import create_graph
from backend.agent.state import StudioState
from backend.db import db

app = FastAPI(title="Mentex API")

# CORS — 允许 React 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph = None

# 运行中的任务 {task_id: {"events": [...], "status": "running"|"done"|"error"}}
_running_tasks: dict = {}

# SSE 队列：每个运行中的任务对应一个 asyncio.Queue
_task_queues: dict[str, asyncio.Queue] = {}


def get_graph():
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


class TaskRequest(BaseModel):
    task: str


def _push_event_safe(task_id: str, event: dict):
    """从后台线程安全地向 asyncio.Queue 推送事件"""
    if task_id in _task_queues:
        q = _task_queues[task_id]
        try:
            # 获取当前运行的事件循环（主线程）
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(q.put_nowait, event)
        except RuntimeError:
            # 万一事件循环不可用，跳过推送
            pass


def _run_agent(task_id: str, task_text: str):
    """后台线程：用 graph.stream() 逐个节点执行，即时产出事件"""
    graph = get_graph()

    initial_state: StudioState = {
        "task": task_text,
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

    try:
        # stream_mode="values": 每个 chunk 是当前完整 state
        # 每个节点完成后 yield 一次，state["events"] 累积了新事件
        all_events = []
        final_state = initial_state
        for chunk in graph.stream(initial_state, stream_mode="values"):
            final_state = chunk

            # 取增量事件（chunk["events"] 是累积的，必须 copy 避免引用复用）
            current_events = list(chunk.get("events", []))
            new_events = current_events[len(all_events):]
            all_events = current_events

            if new_events:
                # 写入共享 dict（保留兼容旧轮询端点）
                _running_tasks[task_id]["events"].extend(new_events)
                # 推送到 SSE 队列
                for evt in new_events:
                    _push_event_safe(task_id, evt)

        # 存储到数据库
        db.save_task(
            task=task_text,
            plan=final_state.get("plan", {}),
            final_output=final_state.get("final_output", ""),
            events=all_events,
        )

        final_output = final_state.get("final_output", "")
        _running_tasks[task_id]["status"] = "done"
        _running_tasks[task_id]["final_output"] = final_output

        # 发送完成事件到 SSE 队列
        _push_event_safe(task_id, {
            "event": "done",
            "timestamp": "",
            "node": "system",
            "instance": "",
            "content": "任务完成",
            "final_output": final_output,
        })

    except Exception as e:
        _running_tasks[task_id]["status"] = "error"
        _running_tasks[task_id]["error"] = str(e)

        # 发送错误事件到 SSE 队列
        _push_event_safe(task_id, {
            "event": "error",
            "timestamp": "",
            "node": "system",
            "instance": "",
            "content": str(e),
        })


async def _event_generator(task_id: str):
    """SSE 事件生成器：从 Queue 取事件并 yield"""
    # 创建队列
    queue: asyncio.Queue = asyncio.Queue()
    _task_queues[task_id] = queue

    # 如果任务已经在运行，先推送已有的事件
    task = _running_tasks.get(task_id)
    if task:
        for evt in task.get("events", []):
            yield {
                "event": evt.get("event", "message"),
                "data": json.dumps(evt, ensure_ascii=False),
            }
        # 如果任务已完成
        if task["status"] == "done":
            yield {
                "event": "done",
                "data": json.dumps({
                    "event": "done",
                    "final_output": task.get("final_output", ""),
                }, ensure_ascii=False),
            }
            _task_queues.pop(task_id, None)
            return
        elif task["status"] == "error":
            yield {
                "event": "error",
                "data": json.dumps({
                    "event": "error",
                    "content": task.get("error", "未知错误"),
                }, ensure_ascii=False),
            }
            _task_queues.pop(task_id, None)
            return

    try:
        while True:
            # 等待新事件，超时 5 秒发一次心跳
            try:
                event = await asyncio.wait_for(queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                # 发送心跳保持连接
                yield {
                    "event": "heartbeat",
                    "data": "{}",
                }
                continue

            event_type = event.get("event", "message")

            if event_type == "done":
                yield {
                    "event": "done",
                    "data": json.dumps(event, ensure_ascii=False),
                }
                break
            elif event_type == "error":
                yield {
                    "event": "error",
                    "data": json.dumps(event, ensure_ascii=False),
                }
                break
            else:
                yield {
                    "event": event_type,
                    "data": json.dumps(event, ensure_ascii=False),
                }

    except asyncio.CancelledError:
        # 客户端断开连接
        pass
    finally:
        _task_queues.pop(task_id, None)


@app.post("/task")
async def run_task(req: TaskRequest):
    """提交任务，立即返回 task_id，后台逐节点执行"""
    import uuid
    task_id = str(uuid.uuid4())[:8]

    _running_tasks[task_id] = {
        "status": "running",
        "events": [],
        "final_output": "",
    }

    thread = threading.Thread(
        target=_run_agent,
        args=(task_id, req.task),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@app.get("/task/{task_id}/stream")
async def stream_events(task_id: str, request: Request):
    """SSE 流式端点：实时推送 Agent 事件"""
    # 检查任务是否存在
    task = _running_tasks.get(task_id)
    if not task:
        # 查数据库中的历史任务
        db_task = db.get_task(task_id)
        if db_task:
            # 已完成的任务：只发送历史事件然后关闭
            async def history_generator():
                for evt in db_task.get("events", []):
                    yield {
                        "event": evt.get("event", "message"),
                        "data": json.dumps(evt, ensure_ascii=False),
                    }
                yield {
                    "event": "done",
                    "data": json.dumps({"event": "done", "final_output": db_task.get("final_output", "")}, ensure_ascii=False),
                }
            return EventSourceResponse(history_generator())
        return JSONResponse({"error": "task not found"}, status_code=404)

    return EventSourceResponse(_event_generator(task_id))


@app.get("/task/{task_id}/events")
async def get_events(task_id: str, after: int = 0):
    """只返回索引 after 之后的新事件（增量拉取，保留兼容旧轮询前端）"""
    task = _running_tasks.get(task_id)

    if not task:
        # 可能已完成并清除内存，查数据库
        db_task = db.get_task(task_id)
        if db_task:
            return {
                "status": "done",
                "events": db_task["events"][after:],
                "final_output": db_task["final_output"],
                "total": len(db_task["events"]),
            }
        return {"status": "not_found", "events": [], "total": 0}

    events = task.get("events", [])
    result = {
        "status": task["status"],
        "events": events[after:],    # 只返回新增的
        "total": len(events),
    }

    if task["status"] == "done":
        result["final_output"] = task.get("final_output", "")
    elif task["status"] == "error":
        result["error"] = task.get("error", "")

    return result


@app.get("/history")
async def get_history(limit: int = 20):
    return db.list_history(limit)


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        return {"error": "task not found"}
    return task
