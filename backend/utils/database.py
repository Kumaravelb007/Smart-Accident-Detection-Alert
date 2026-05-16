"""
Database Utilities
Handles storing and retrieving historical detection data.
"""

import logging
import sqlite3

from config import BASE_DIR

logger = logging.getLogger(__name__)

DB_PATH = BASE_DIR / "detections.db"


def _safe_add_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    """Initialize the SQLite database and apply lightweight schema migrations."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_email TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    accident_detected BOOLEAN NOT NULL,
                    confidence REAL NOT NULL,
                    message TEXT,
                    vehicle_count INTEGER,
                    frame_url TEXT,
                    ai_report TEXT
                )
                """
            )

            # Schema migration for richer analytics fields.
            _safe_add_column(cursor, "detections", "severity", "TEXT DEFAULT 'Minor'")
            _safe_add_column(cursor, "detections", "detection_strategy", "TEXT DEFAULT ''")
            _safe_add_column(cursor, "detections", "traffic_density", "TEXT DEFAULT 'Low'")
            _safe_add_column(cursor, "detections", "average_speed_kmh", "REAL DEFAULT 0")
            _safe_add_column(cursor, "detections", "anomaly_score", "REAL DEFAULT 0")
            _safe_add_column(cursor, "detections", "congestion_detected", "BOOLEAN DEFAULT 0")

            conn.commit()
    except Exception as exc:
        logger.error("Failed to initialize database: %s", exc)


def save_detection(
    user_email: str,
    timestamp: str,
    accident_detected: bool,
    confidence: float,
    message: str,
    vehicle_count: int,
    frame_url: str,
    ai_report: str,
    severity: str = "Minor",
    detection_strategy: str = "",
    traffic_density: str = "Low",
    average_speed_kmh: float = 0.0,
    anomaly_score: float = 0.0,
    congestion_detected: bool = False,
) -> None:
    """Save a detection result to the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO detections (
                    user_email,
                    timestamp,
                    accident_detected,
                    confidence,
                    message,
                    vehicle_count,
                    frame_url,
                    ai_report,
                    severity,
                    detection_strategy,
                    traffic_density,
                    average_speed_kmh,
                    anomaly_score,
                    congestion_detected
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_email,
                    timestamp,
                    accident_detected,
                    confidence,
                    message,
                    vehicle_count,
                    frame_url or "",
                    ai_report or "",
                    severity,
                    detection_strategy,
                    traffic_density,
                    average_speed_kmh,
                    anomaly_score,
                    int(bool(congestion_detected)),
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.error("Failed to save detection: %s", exc)


def get_user_history(user_email: str, limit: int = 120) -> list:
    """Retrieve detections for a specific user."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM detections
                WHERE user_email = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_email, max(1, int(limit))),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("Failed to retrieve history: %s", exc)
        return []


# Initialize on import
init_db()
