from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.models import ALLOWED_EXTENSIONS


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip().replace("/", "_").replace("\\", "_")
    name = SAFE_NAME_RE.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name or f"upload-{uuid4().hex}"


def ensure_allowed_extension(filename: str) -> None:
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )


async def save_upload(upload: UploadFile, target_dir: str, max_bytes: int) -> Path:
    safe_name = sanitize_filename(upload.filename or "upload")
    ensure_allowed_extension(safe_name)
    target = Path(target_dir) / f"{uuid4().hex}-{safe_name}"
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                handle.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Upload exceeds configured size limit.")
            handle.write(chunk)
    return target


def safe_child_path(base_dir: str, filename: str) -> Path:
    base = Path(base_dir).resolve()
    candidate = (base / Path(filename).name).resolve()
    if base != candidate.parent and base not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    return candidate


def copy_file_to_dir(source: str, target_dir: str, title: str | None = None) -> Path:
    source_path = Path(source)
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source)
    target_base = sanitize_filename(title or source_path.name)
    if source_path.suffix and not target_base.lower().endswith(source_path.suffix.lower()):
        target_base = f"{target_base}{source_path.suffix}"
    target = Path(target_dir) / target_base
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target = target.with_name(f"{target.stem}-{uuid4().hex[:8]}{target.suffix}")
    shutil.copy2(source_path, target)
    return target


def move_file_to_dir(source: str, target_dir: str) -> Path | None:
    source_path = Path(source)
    if not source_path.exists():
        return None
    target = Path(target_dir) / source_path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target = target.with_name(f"{target.stem}-{uuid4().hex[:8]}{target.suffix}")
    shutil.move(str(source_path), target)
    return target
