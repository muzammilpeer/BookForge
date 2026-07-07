from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app import db
from app.config import load_settings
from app.files import copy_file_to_dir, move_file_to_dir
from app.mimika_client import MimikaClient
from app.models import Job


log = logging.getLogger("bookforge.worker")
TERMINAL_COMPLETED = {"completed", "done", "finished", "success", "succeeded"}
TERMINAL_FAILED = {"failed", "error", "errored"}
TERMINAL_CANCELED = {"canceled", "cancelled"}


async def worker_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        try:
            await tick()
        except Exception:
            log.exception("BookForge worker tick failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=3)
        except TimeoutError:
            pass


async def tick() -> None:
    settings = load_settings()
    running_count = db.count_status("running")
    slots = max(settings.max_parallel_jobs - running_count, 0)
    if slots:
        for job in db.next_queued_jobs(slots):
            await start_job(job)
    for job in db.list_jobs(status="running", limit=25):
        await poll_job(job)


async def start_job(job: Job) -> None:
    settings = load_settings()
    client = MimikaClient(settings.mimika_base_url)
    db.update_job(job.id, status="running", started_at=db.now_iso(), error=None)
    try:
        mimika_job_id = await client.start_audiobook_job(
            file_path=job.input_path,
            title=job.title,
            voice=job.voice,
            speed=job.speed,
            output_format=job.output_format,
            subtitle_format=job.subtitle_format,
        )
        db.update_job(job.id, mimika_job_id=mimika_job_id)
    except Exception as exc:
        move_file_to_dir(job.input_path, settings.failed_dir)
        db.update_job(job.id, status="failed", completed_at=db.now_iso(), error=str(exc))


async def poll_job(job: Job) -> None:
    if not job.mimika_job_id:
        return
    settings = load_settings()
    client = MimikaClient(settings.mimika_base_url)
    try:
        status = await client.status(job.mimika_job_id)
    except Exception as exc:
        db.update_job(job.id, error=str(exc))
        return

    normalized_status = str(status.get("status") or "running").lower()
    changes = {
        "progress": _as_float(status.get("progress")),
        "chars_per_sec": _as_float(status.get("chars_per_sec")),
        "eta_seconds": _as_int(status.get("eta_seconds")),
        "eta_formatted": status.get("eta_formatted"),
        "error": status.get("error"),
    }
    changes = {key: value for key, value in changes.items() if value is not None}

    if normalized_status in TERMINAL_COMPLETED:
        output_path = await resolve_output_path(client, job, status)
        copied_path = None
        if output_path:
            try:
                copied_path = copy_file_to_dir(output_path, settings.completed_dir, job.title)
            except Exception as exc:
                db.update_job(job.id, status="failed", completed_at=db.now_iso(), error=f"Copy failed: {exc}")
                return
        copied_to_abs = False
        if copied_path and job.auto_copy_to_audiobookshelf:
            try:
                copy_file_to_dir(str(copied_path), settings.audiobookshelf_dir)
                copied_to_abs = True
            except Exception as exc:
                log.warning("Audiobookshelf copy failed for job %s: %s", job.id, exc)
        db.update_job(
            job.id,
            **changes,
            status="completed",
            progress=100.0,
            output_path=str(copied_path) if copied_path else None,
            copied_to_audiobookshelf=int(copied_to_abs),
            completed_at=db.now_iso(),
        )
    elif normalized_status in TERMINAL_FAILED:
        move_file_to_dir(job.input_path, settings.failed_dir)
        db.update_job(job.id, **changes, status="failed", completed_at=db.now_iso())
    elif normalized_status in TERMINAL_CANCELED:
        db.update_job(job.id, **changes, status="canceled", completed_at=db.now_iso())
    else:
        db.update_job(job.id, **changes, status="running")


async def resolve_output_path(client: MimikaClient, job: Job, status: dict[str, Any]) -> str | None:
    direct = status.get("output_path")
    if direct and Path(str(direct)).exists():
        return str(direct)
    try:
        listing = await client.audiobook_list()
    except Exception as exc:
        log.info("Unable to inspect audiobook list for job %s: %s", job.id, exc)
        return None
    matches = _flatten_listing(listing)
    for item in matches:
        candidate_job_id = str(item.get("job_id") or item.get("id") or item.get("mimika_job_id") or "")
        title = str(item.get("title") or item.get("name") or item.get("filename") or "")
        path = item.get("path") or item.get("output_path") or item.get("file_path")
        if path and Path(str(path)).exists() and (candidate_job_id == job.mimika_job_id or job.title in title):
            return str(path)
    return None


def _flatten_listing(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("items", "audio", "audiobooks", "files", "data"):
            if isinstance(value.get(key), list):
                return [item for item in value[key] if isinstance(item, dict)]
    return []


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
