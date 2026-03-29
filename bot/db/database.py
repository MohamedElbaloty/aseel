"""
Local SQLite database for storing check-in records.
Used as primary storage and backup when Sheets is unavailable.
"""
import sqlite3
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "checkins.db")


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    """Create tables if not exist."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_telegram_id TEXT NOT NULL,
                employee_name TEXT,
                client_name TEXT,
                account_number TEXT,
                product TEXT,
                visit_reason TEXT,
                meeting_type TEXT,
                account_manager_present INTEGER,
                admin_manager_present INTEGER,
                meeting_datetime TEXT,
                meeting_objective TEXT,
                next_visit_date TEXT,
                notes TEXT,
                follow_up_actions TEXT,
                raw_message TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                synced_to_sheet INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()
    logger.info("Database initialized.")


def save_checkin(data: dict, employee_id: str, employee_name: str, raw_message: str) -> int:
    """Save a check-in record. Returns the new record ID."""
    initialize_db()
    actions = data.get("follow_up_actions") or []
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO checkins (
                employee_telegram_id, employee_name, client_name, account_number,
                product, visit_reason, meeting_type, account_manager_present,
                admin_manager_present, meeting_datetime, meeting_objective,
                next_visit_date, notes, follow_up_actions, raw_message
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                employee_id,
                employee_name,
                data.get("client_name"),
                data.get("account_number"),
                data.get("product"),
                data.get("visit_reason"),
                data.get("meeting_type"),
                1 if data.get("account_manager_present") is True else (0 if data.get("account_manager_present") is False else None),
                1 if data.get("admin_manager_present") is True else (0 if data.get("admin_manager_present") is False else None),
                data.get("meeting_datetime"),
                data.get("meeting_objective"),
                data.get("next_visit_date"),
                data.get("notes"),
                json.dumps(actions, ensure_ascii=False),
                raw_message,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_employee_history(employee_id: str, limit: int = 5) -> list:
    """Get recent check-ins for an employee."""
    initialize_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM checkins
            WHERE employee_telegram_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (employee_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_checkins(limit: int = 200) -> list:
    """Get all check-ins (for dashboard)."""
    initialize_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM checkins ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(row) for row in rows]


def mark_synced(record_id: int):
    """Mark a record as synced to Google Sheets."""
    with get_connection() as conn:
        conn.execute("UPDATE checkins SET synced_to_sheet=1 WHERE id=?", (record_id,))
        conn.commit()
