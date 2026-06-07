import threading
from fastapi import FastAPI
from pydantic import BaseModel
from backend.agent.graph import create_graph
from backend.agent.state import StudioState
from backend.db import db

app = FastAPI(title="Mentex API")

_graph = None

# 运行中的任务 {task_id: {"events": [...], "status": "running"|"done"|"error"}}
_running_tasks: dict = {}


def get_graph():
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


class TaskRequest(BaseModel):
    task: str


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

            # 取增量事件（chunk["events"] 是累积的，需要 copy 避免引用复用）
            current_events = list(chunk.get("events", []))
            new_events = current_events[len(all_events):]
            all_events = current_events

            if new_events:
                _running_tasks[task_id]["events"].extend(new_events)

        # 存储到数据库
        db.save_task(
            task=task_text,
            plan=final_state.get("plan", {}),
            final_output=final_state.get("final_output", ""),
            events=all_events,
        )

        _running_tasks[task_id]["status"] = "done"
        _running_tasks[task_id]["final_output"] = final_state.get("final_output", "")

    except Exception as e:
        _running_tasks[task_id] = {
            "status": "error",
            "error": str(e),
            "events": _running_tasks[task_id].get("events", []),
        }


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


@app.get("/task/{task_id}/events")
async def get_events(task_id: str, after: int = 0):
    """只返回索引 after 之后的新事件（增量拉取）"""
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
