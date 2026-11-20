"""SQLite-backed conversation persistence with atomic writes."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MessageStore:
    def __init__(self, url: str):
        prefix = "sqlite:///"
        if not url.startswith(prefix):
            raise ValueError("DATABASE_URL must use sqlite:/// (SQLite only)")
        self.path = url[len(prefix):]
        if not self.path:
            raise ValueError("DATABASE_URL needs a file path")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 20000")
        return connection

    def initialize(self):
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id)")
            conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                system_prompt TEXT NOT NULL
            )""")

    def ready(self) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT 1").fetchone()[0] == 1

    def get_history(self, session_id: str):
        with self.connect() as conn:
            rows = conn.execute("SELECT role, content, metadata FROM messages WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        return [{"role": row["role"], "content": row["content"], **({"metadata": json.loads(row["metadata"])} if row["metadata"] else {})} for row in rows]

    def get_prompt(self, session_id: str):
        with self.connect() as conn:
            row = conn.execute("SELECT system_prompt FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return row["system_prompt"] if row else None

    def save_exchange(self, session_id: str, user_message: str, answer: str, metadata: dict, prompt: str):
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            conn.execute("INSERT INTO sessions(session_id, system_prompt) VALUES(?,?) ON CONFLICT(session_id) DO UPDATE SET system_prompt=excluded.system_prompt", (session_id, prompt))
            conn.executemany("INSERT INTO messages(session_id,role,content,metadata,created_at) VALUES (?,?,?,?,?)", [
                (session_id, "user", user_message, None, now),
                (session_id, "assistant", answer, json.dumps(metadata), now),
            ])
