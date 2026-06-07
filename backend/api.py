import json
import threading
from fastapi import FastAPI
from pydantic import BaseModel
from backend.agent.graph import create_graph
from backend.agent.state import StudioState
from backend.db import db

app = FastAPI(title="Mentex API")

_graph = None

# 运行中的任务 {task_id: {"status": "running"|"done", "result": {...}}}
_running_tasks: dict = {}


def get_graph():
    global _graph
    if _graph is None:
        _graph = create_graph()
    return _graph


class TaskRequest(BaseModel):
    task: str


def _run_agent(task_id: str, task_text: str):
    """后台线程中执行 Agent"""
    try:
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

        result = graph.invoke(initial_state)

        # 存储到数据库
        db.save_task(
            task=task_text,
            plan=result.get("plan", {}),
            final_output=result.get("final_output", ""),
            events=result.get("events", []),
        )

        _running_tasks[task_id] = {
            "status": "done",
            "result": result,
        }
    except Exception as e:
        _running_tasks[task_id] = {
            "status": "error",
            "error": str(e),
        }


@app.post("/task")
async def run_task(req: TaskRequest):
    """提交任务，立即返回 task_id，后台执行"""
    import uuid
    task_id = str(uuid.uuid4())[:8]

    _running_tasks[task_id] = {"status": "running", "result": None}

    thread = threading.Thread(
        target=_run_agent,
        args=(task_id, req.task),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id}


@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str):
    """轮询任务状态（前端每秒调用）"""
    task = _running_tasks.get(task_id)
    if not task:
        # 可能已经完成并从内存中清除了，查数据库
        db_task = db.get_task(task_id)
        if db_task:
            return {
                "status": "done",
                "events": db_task["events"],
                "final_output": db_task["final_output"],
            }
        return {"status": "not_found"}

    if task["status"] == "done":
        result = task["result"]
        return {
            "status": "done",
            "events": result.get("events", []),
            "final_output": result.get("final_output", ""),
        }
    elif task["status"] == "error":
        return {"status": "error", "error": task.get("error", "")}

    return {"status": "running", "events": []}


@app.get("/history")
async def get_history(limit: int = 20):
    """获取历史任务列表"""
    return db.list_history(limit)


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    """获取单个任务完整详情"""
    task = db.get_task(task_id)
    if not task:
        return {"error": "task not found"}
    return task
