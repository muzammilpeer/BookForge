from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Row


STATUSES = ("queued", "running", "completed", "failed", "canceled")
ALLOWED_EXTENSIONS = {".pdf", ".epub", ".txt", ".md", ".docx"}
OUTPUT_FORMATS = ("wav", "mp3", "m4b")
SUBTITLE_FORMATS = ("none", "srt", "vtt")


@dataclass(frozen=True)
class Job:
    id: int
    mimika_job_id: str | None
    input_path: str
    original_filename: str
    title: str
    voice: str
    speed: float
    output_format: str
    subtitle_format: str
    status: str
    progress: float | None
    chars_per_sec: float | None
    eta_seconds: int | None
    eta_formatted: str | None
    output_path: str | None
    auto_copy_to_audiobookshelf: bool
    copied_to_audiobookshelf: bool
    error: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None
    updated_at: str


def job_from_row(row: Row) -> Job:
    data = dict(row)
    data["auto_copy_to_audiobookshelf"] = bool(data["auto_copy_to_audiobookshelf"])
    data["copied_to_audiobookshelf"] = bool(data["copied_to_audiobookshelf"])
    return Job(**data)
