"""
Database — SQLite storage for discovered jobs, with deduplication.
"""

import sqlite3
from datetime import datetime

from config import DB_PATH, logger


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create the jobs table if it doesn't exist."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_found TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            job_type TEXT DEFAULT 'Internship',
            match_score INTEGER,
            application_status TEXT DEFAULT 'Not Applied',
            link TEXT UNIQUE,
            source TEXT,
            salary TEXT,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def job_exists(link: str) -> bool:
    """Check if a job with this link already exists."""
    if not link:
        return False
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM jobs WHERE link = ?", (link,)).fetchone()
    conn.close()
    return row is not None


def insert_job(job: dict) -> bool:
    """Insert a job if it doesn't already exist. Returns True if inserted."""
    link = job.get("link", "")
    if job_exists(link):
        logger.debug(f"Skipping duplicate: {job.get('title')} @ {job.get('company')}")
        return False

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO jobs (date_found, company, title, location, job_type,
                              match_score, application_status, link, source, salary, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.get("date_posted", datetime.now().strftime("%Y-%m-%d")),
                job.get("company", "Unknown"),
                job.get("title", "Unknown"),
                job.get("location", ""),
                job.get("type", "Internship"),
                job.get("match_score", 0),
                "Not Applied",
                link,
                job.get("source", ""),
                job.get("salary"),
                job.get("description", ""),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def insert_jobs(jobs: list[dict]) -> int:
    """Insert multiple jobs. Returns count of newly inserted jobs."""
    inserted = 0
    for job in jobs:
        if insert_job(job):
            inserted += 1
    logger.info(f"Inserted {inserted} new jobs into database ({len(jobs) - inserted} duplicates skipped)")
    return inserted


def get_all_jobs() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM jobs ORDER BY match_score DESC, date_found DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_status(link: str, status: str):
    """Update application status for a job."""
    valid_statuses = {"Not Applied", "Applied", "Interview", "Rejected", "Offer"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
    conn = get_connection()
    conn.execute("UPDATE jobs SET application_status = ? WHERE link = ?", (status, link))
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    by_status = {}
    for row in conn.execute("SELECT application_status, COUNT(*) FROM jobs GROUP BY application_status"):
        by_status[row[0]] = row[1]
    avg_score = conn.execute("SELECT AVG(match_score) FROM jobs WHERE match_score > 0").fetchone()[0]
    conn.close()
    return {"total": total, "by_status": by_status, "avg_score": round(avg_score, 1) if avg_score else 0}


# Initialize on import
init_db()
