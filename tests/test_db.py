import pytest
from backend.db import Database


@pytest.fixture
def db():
    """每个测试用内存数据库，互不干扰"""
    d = Database(":memory:")
    yield d


def test_save_and_get_task(db):
    """保存任务 → 读出来 → 内容一致"""
    task_id = db.save_task(
        task="测试任务：写一首诗",
        plan={"pipeline": ["Writer"]},
        final_output="床前明月光...",
        events=[{"event": "final", "content": "done"}],
    )
    assert task_id is not None

    task = db.get_task(task_id)
    assert task is not None
    assert task["task"] == "测试任务：写一首诗"
    assert task["final_output"] == "床前明月光..."
    assert task["plan"] == {"pipeline": ["Writer"]}


def test_list_history_returns_latest_first(db):
    """历史列表按时间倒序，最新的在前"""
    db.save_task("任务1", {}, "产出1", [])
    db.save_task("任务2", {}, "产出2", [])
    db.save_task("任务3", {}, "产出3", [])

    history = db.list_history(limit=2)
    assert len(history) == 2
    assert history[0]["task"] == "任务3"  # 最新
    assert history[1]["task"] == "任务2"


def test_get_nonexistent_task(db):
    """查询不存在的任务 → None"""
    task = db.get_task("nonexistent")
    assert task is None
