"""Small SQLite database: escalated tickets, message log (for stats) and customer feedback."""
import contextlib
import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional

_ready = set()  # database files whose tables we have already created


def _path() -> str:
    return os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "support.db"))


@contextlib.contextmanager
def connect():
    path = _path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        if path not in _ready:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    escalated INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    query TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    category TEXT
                );
                """
            )
            _ready.add(path)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_message(reply: Dict) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO messages (created_at, category, sentiment, escalated) VALUES (?, ?, ?, ?)",
            (_now(), reply["category"], reply["sentiment"], int(reply["escalated"])),
        )


def create_ticket(ticket: str, query: str, category: str, sentiment: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO tickets (ticket, created_at, query, category, sentiment) VALUES (?, ?, ?, ?, ?)",
            (ticket, _now(), query, category, sentiment),
        )


def add_feedback(rating: str, category: Optional[str]) -> None:
    with connect() as c:
        c.execute("INSERT INTO feedback (created_at, rating, category) VALUES (?, ?, ?)", (_now(), rating, category))


def list_tickets(status: str = "open") -> List[Dict]:
    with connect() as c:
        if status == "all":
            rows = c.execute("SELECT * FROM tickets ORDER BY id DESC LIMIT 200").fetchall()
        else:
            rows = c.execute("SELECT * FROM tickets WHERE status = ? ORDER BY id DESC LIMIT 200", (status,)).fetchall()
    return [dict(r) for r in rows]


def resolve_ticket(ticket: str) -> bool:
    with connect() as c:
        cur = c.execute("UPDATE tickets SET status = 'resolved' WHERE ticket = ?", (ticket,))
        return cur.rowcount > 0


def stats() -> Dict:
    with connect() as c:
        messages = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        escalated = c.execute("SELECT COUNT(*) FROM messages WHERE escalated = 1").fetchone()[0]
        open_tickets = c.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'").fetchone()[0]
        by_category = {"Technical": 0, "Billing": 0, "General": 0}
        for r in c.execute("SELECT category, COUNT(*) AS n FROM messages GROUP BY category"):
            by_category[r["category"]] = r["n"]
        feedback = {"up": 0, "down": 0}
        for r in c.execute("SELECT rating, COUNT(*) AS n FROM feedback GROUP BY rating"):
            feedback[r["rating"]] = r["n"]
    return {
        "messages": messages,
        "escalated": escalated,
        "open_tickets": open_tickets,
        "by_category": by_category,
        "feedback": feedback,
    }
