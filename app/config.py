from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path("config.yaml")
EXAMPLE_CONFIG_PATH = Path("config.yaml.example")


@dataclass(frozen=True)
class Settings:
    mimika_base_url: str = "http://127.0.0.1:7693"
    max_parallel_jobs: int = 1
    default_voice: str = "bf_emma"
    default_speed: float = 1.0
    default_output_format: str = "m4b"
    default_subtitle_format: str = "none"
    auto_copy_to_audiobookshelf: bool = True
    incoming_dir: str = "/Volumes/media/apps/bookforge/incoming"
    work_dir: str = "/Volumes/media/apps/bookforge/work"
    completed_dir: str = "/Volumes/media/apps/bookforge/completed"
    failed_dir: str = "/Volumes/media/apps/bookforge/failed"
    audiobookshelf_dir: str = "/Volumes/media/apps/audiobookshelf/audiobooks"
    max_upload_size_bytes: int = 2 * 1024 * 1024 * 1024
    sse_interval_seconds: float = 2.0

    def ensure_dirs(self) -> None:
        for value in (
            self.incoming_dir,
            self.work_dir,
            self.completed_dir,
            self.failed_dir,
            self.audiobookshelf_dir,
        ):
            Path(value).mkdir(parents=True, exist_ok=True)


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_settings() -> Settings:
    if not CONFIG_PATH.exists() and EXAMPLE_CONFIG_PATH.exists():
        CONFIG_PATH.write_text(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    data = _read_yaml(CONFIG_PATH)
    settings = Settings(**{k: v for k, v in data.items() if k in Settings.__dataclass_fields__})
    settings.ensure_dirs()
    return settings


def save_settings(settings: Settings) -> None:
    payload = {
        "mimika_base_url": settings.mimika_base_url,
        "max_parallel_jobs": settings.max_parallel_jobs,
        "default_voice": settings.default_voice,
        "default_speed": settings.default_speed,
        "default_output_format": settings.default_output_format,
        "default_subtitle_format": settings.default_subtitle_format,
        "auto_copy_to_audiobookshelf": settings.auto_copy_to_audiobookshelf,
        "incoming_dir": settings.incoming_dir,
        "work_dir": settings.work_dir,
        "completed_dir": settings.completed_dir,
        "failed_dir": settings.failed_dir,
        "audiobookshelf_dir": settings.audiobookshelf_dir,
        "max_upload_size_bytes": settings.max_upload_size_bytes,
        "sse_interval_seconds": settings.sse_interval_seconds,
    }
    CONFIG_PATH.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def update_settings(**changes: Any) -> Settings:
    current = load_settings()
    updated = replace(current, **changes)
    updated.ensure_dirs()
    save_settings(updated)
    return updated
