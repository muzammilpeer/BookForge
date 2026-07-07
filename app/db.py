from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.models import Job, job_from_row


DB_PATH = Path("bookforge.sqlite3")
_LOCK = threading.RLock()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterable[sqlite3.Connection]:
    with _LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            create table if not exists jobs (
                id integer primary key,
                mimika_job_id text nullable,
                input_path text not null,
                original_filename text not null,
                title text not null,
                voice text not null,
                speed real not null,
                output_format text not null,
                subtitle_format text not null,
                status text not null,
                progress real nullable,
                chars_per_sec real nullable,
                eta_seconds integer nullable,
                eta_formatted text nullable,
                output_path text nullable,
                auto_copy_to_audiobookshelf integer not null default 1,
                copied_to_audiobookshelf integer not null default 0,
                error text nullable,
                created_at text not null,
                started_at text nullable,
                completed_at text nullable,
                updated_at text not null
            )
            """
        )
        columns = {row["name"] for row in conn.execute("pragma table_info(jobs)").fetchall()}
        if "auto_copy_to_audiobookshelf" not in columns:
            conn.execute(
                "alter table jobs add column auto_copy_to_audiobookshelf integer not null default 1"
            )


def create_job(
    *,
    input_path: str,
    original_filename: str,
    title: str,
    voice: str,
    speed: float,
    output_format: str,
    subtitle_format: str,
    auto_copy_to_audiobookshelf: bool,
) -> int:
    stamp = now_iso()
    with connect() as conn:
        cur = conn.execute(
            """
            insert into jobs (
                input_path, original_filename, title, voice, speed, output_format,
                subtitle_format, auto_copy_to_audiobookshelf, status, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)
            """,
            (
                input_path,
                original_filename,
                title,
                voice,
                speed,
                output_format,
                subtitle_format,
                int(auto_copy_to_audiobookshelf),
                stamp,
                stamp,
            ),
        )
        return int(cur.lastrowid)


def get_job(job_id: int) -> Job | None:
    with connect() as conn:
        row = conn.execute("select * from jobs where id = ?", (job_id,)).fetchone()
        return job_from_row(row) if row else None


def list_jobs(status: str | None = None, limit: int = 200) -> list[Job]:
    with connect() as conn:
        if status:
            rows = conn.execute(
                "select * from jobs where status = ? order by created_at desc limit ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "select * from jobs order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [job_from_row(row) for row in rows]


def count_status(status: str) -> int:
    with connect() as conn:
        return int(conn.execute("select count(*) from jobs where status = ?", (status,)).fetchone()[0])


def status_counts() -> dict[str, int]:
    with connect() as conn:
        rows = conn.execute("select status, count(*) as total from jobs group by status").fetchall()
        counts = {row["status"]: int(row["total"]) for row in rows}
    for status in ("queued", "running", "completed", "failed", "canceled"):
        counts.setdefault(status, 0)
    return counts


def next_queued_jobs(limit: int) -> list[Job]:
    with connect() as conn:
        rows = conn.execute(
            "select * from jobs where status = 'queued' order by created_at asc limit ?",
            (limit,),
        ).fetchall()
        return [job_from_row(row) for row in rows]


def update_job(job_id: int, **changes: Any) -> None:
    if not changes:
        return
    changes["updated_at"] = now_iso()
    assignments = ", ".join(f"{key} = ?" for key in changes)
    values = list(changes.values()) + [job_id]
    with connect() as conn:
        conn.execute(f"update jobs set {assignments} where id = ?", values)


def delete_job(job_id: int) -> None:
    with connect() as conn:
        conn.execute("delete from jobs where id = ?", (job_id,))


def dashboard_groups() -> dict[str, list[Job]]:
    return {status: list_jobs(status=status, limit=50) for status in ("running", "queued", "completed", "failed", "canceled")}
