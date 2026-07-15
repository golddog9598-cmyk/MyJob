"""User resume persistence isolated from all recruitment-platform data."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Optional


class ResumeStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS master_resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT '主简历',
                content TEXT NOT NULL DEFAULT '',
                source_format TEXT NOT NULL DEFAULT 'structured-v2',
                source_filename TEXT NOT NULL DEFAULT '',
                source_mime TEXT NOT NULL DEFAULT '',
                structured_json TEXT NOT NULL DEFAULT '{}',
                template_id TEXT NOT NULL DEFAULT 'ats_classic',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._db.commit()

    @staticmethod
    def _payload(row) -> Optional[dict]:
        if not row:
            return None
        value = dict(row)
        try:
            value["structured"] = json.loads(value.pop("structured_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            value["structured"] = {}
            value.pop("structured_json", None)
        return value

    def get(self, user_id: int) -> Optional[dict]:
        with self._lock:
            row = self._db.execute(
                "SELECT * FROM master_resumes WHERE user_id=?", (int(user_id),)
            ).fetchone()
            return self._payload(row)

    def save(
        self,
        user_id: int,
        *,
        content: str,
        name: str = "主简历",
        source_format: str = "structured-v2",
        source_filename: str = "",
        source_mime: str = "",
        structured: Optional[dict] = None,
        template_id: str = "ats_classic",
    ) -> dict:
        with self._lock:
            self._db.execute(
                """
                INSERT INTO master_resumes(
                    user_id,name,content,source_format,source_filename,source_mime,structured_json,template_id
                ) VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name=excluded.name,
                    content=excluded.content,
                    source_format=excluded.source_format,
                    source_filename=excluded.source_filename,
                    source_mime=excluded.source_mime,
                    structured_json=excluded.structured_json,
                    template_id=excluded.template_id,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    int(user_id),
                    str(name or "主简历").strip() or "主简历",
                    str(content or ""),
                    str(source_format or "structured-v2"),
                    str(source_filename or ""),
                    str(source_mime or ""),
                    json.dumps(structured or {}, ensure_ascii=False),
                    str(template_id or "ats_classic"),
                ),
            )
            self._db.commit()
            result = self.get(int(user_id))
            if not result:
                raise RuntimeError("简历保存失败")
            return result

    def set_template(self, user_id: int, template_id: str) -> Optional[dict]:
        with self._lock:
            cursor = self._db.execute(
                "UPDATE master_resumes SET template_id=?,updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (str(template_id), int(user_id)),
            )
            self._db.commit()
            return self.get(int(user_id)) if cursor.rowcount else None
