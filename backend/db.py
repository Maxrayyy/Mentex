import sqlite3
import json
import uuid
from datetime import datetime, timezone


class Database:
    def __init__(self, db_path: str = "mentex.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 让查询结果可以用列名访问
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                plan TEXT,
                final_output TEXT,
                events TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_task(
        self,
        task: str,
        plan: dict,
        final_output: str,
        events: list[dict],
    ) -> str:
        """保存一次任务执行记录，返回任务 ID"""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            """INSERT INTO tasks (id, task, plan, final_output, events, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                task,
                json.dumps(plan, ensure_ascii=False),
                final_output,
                json.dumps(events, ensure_ascii=False),
                now,
            ),
        )
        self.conn.commit()
        return task_id

    def get_task(self, task_id: str) -> dict | None:
        """获取单个任务的完整详情"""
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "task": row["task"],
            "plan": json.loads(row["plan"]) if row["plan"] else {},
            "final_output": row["final_output"],
            "events": json.loads(row["events"]) if row["events"] else [],
            "created_at": row["created_at"],
        }

    def list_history(self, limit: int = 20) -> list[dict]:
        """获取最近的任务列表（最新在前）"""
        rows = self.conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "task": row["task"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


# 全局单例，其他模块直接 import
db = Database()
