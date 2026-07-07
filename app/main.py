from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import db
from app.config import load_settings, update_settings
from app.files import copy_file_to_dir, save_upload
from app.mimika_client import MimikaClient
from app.models import OUTPUT_FORMATS, SUBTITLE_FORMATS
from app.security import (
    SESSION_COOKIE,
    admin_username,
    create_session_token,
    has_access,
    password_enabled,
    redirect_to_login,
    valid_credentials,
)
from app.system_metrics import collect_system_metrics
from app.worker import worker_loop


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bookforge")
templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    settings = load_settings()
    if not os.getenv("BOOKFORGE_ADMIN_PASSWORD"):
        log.warning("BOOKFORGE_ADMIN_PASSWORD is not set; only loopback clients bypass login.")
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(worker_loop(stop_event))
    app.state.settings = settings
    yield
    stop_event.set()
    await worker_task


app = FastAPI(title="BookForge", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def require_login(request: Request, call_next):
    public_paths = {"/login"}
    if request.url.path.startswith("/static") or request.url.path in public_paths:
        return await call_next(request)
    if not has_access(request):
        if "text/html" in request.headers.get("accept", "") or request.method == "GET":
            return redirect_to_login(request)
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str = "/") -> HTMLResponse:
    if has_access(request):
        return RedirectResponse(url=next, status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "next": next,
            "username": admin_username(),
            "password_required": password_enabled(request),
            "error": None,
        },
    )


@app.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/",
):
    if valid_credentials(username, password):
        response = RedirectResponse(url=next or "/", status_code=303)
        response.set_cookie(
            SESSION_COOKIE,
            create_session_token(username),
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 12,
        )
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "next": next,
            "username": admin_username(),
            "password_required": password_enabled(request),
            "error": "Invalid username or password.",
        },
        status_code=401,
    )


@app.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        await dashboard_context(request),
    )


@app.get("/partials/dashboard", response_class=HTMLResponse)
async def dashboard_partial(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "partials/dashboard_sections.html",
        await dashboard_context(request),
    )


@app.get("/events/dashboard")
async def dashboard_events() -> StreamingResponse:
    async def event_stream():
        tick = 0
        while True:
            settings = load_settings()
            payload = await dashboard_state(include_health=tick % 8 == 0)
            yield f"event: dashboard\ndata: {json.dumps(payload)}\n\n"
            tick += 1
            await asyncio.sleep(clamp_sse_interval(settings.sse_interval_seconds))

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/dashboard-state")
async def dashboard_state_endpoint() -> dict[str, Any]:
    return await dashboard_state(include_health=True)


async def dashboard_context(request: Request) -> dict[str, Any]:
    settings = load_settings()
    state = await dashboard_state(include_health=True)
    return {
        "settings": settings,
        **state,
        "request": request,
    }


async def dashboard_state(include_health: bool = False) -> dict[str, Any]:
    settings = load_settings()
    counts = db.status_counts()
    health = await MimikaClient(settings.mimika_base_url).health() if include_health else None
    return {
        "health": health,
        "counts": counts,
        "running_count": counts["running"],
        "available_slots": max(settings.max_parallel_jobs - counts["running"], 0),
        "max_parallel_jobs": settings.max_parallel_jobs,
        "sse_interval_seconds": settings.sse_interval_seconds,
        "system": collect_system_metrics(),
        "jobs": [serialize_job(job) for job in db.list_jobs(limit=200)],
    }


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request) -> HTMLResponse:
    settings = load_settings()
    voices = await safe_voices(settings.mimika_base_url)
    if settings.default_voice and settings.default_voice not in {voice["id"] for voice in voices}:
        voices.insert(0, {"id": settings.default_voice, "label": settings.default_voice})
    return templates.TemplateResponse(
        request,
        "upload.html",
        {
            "settings": settings,
            "voices": voices,
            "voices_json": json.dumps(voices),
            "output_formats": OUTPUT_FORMATS,
            "subtitle_formats": SUBTITLE_FORMATS,
        },
    )


@app.post("/upload")
async def upload_files(
    files: Annotated[list[UploadFile], File()],
    title: Annotated[str, Form()] = "",
    voice: Annotated[str, Form()] = "",
    speed: Annotated[float, Form()] = 1.0,
    output_format: Annotated[str, Form()] = "m4b",
    subtitle_format: Annotated[str, Form()] = "none",
    auto_copy_to_audiobookshelf: Annotated[bool, Form()] = False,
) -> RedirectResponse:
    settings = load_settings()
    if output_format not in OUTPUT_FORMATS or subtitle_format not in SUBTITLE_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid output or subtitle format.")
    for upload in files:
        saved_path = await save_upload(upload, settings.incoming_dir, settings.max_upload_size_bytes)
        display_title = title.strip() or Path(upload.filename or saved_path.name).stem
        db.create_job(
            input_path=str(saved_path),
            original_filename=upload.filename or saved_path.name,
            title=display_title,
            voice=voice or settings.default_voice,
            speed=speed,
            output_format=output_format,
            subtitle_format=subtitle_format,
            auto_copy_to_audiobookshelf=auto_copy_to_audiobookshelf,
        )
    return RedirectResponse(url="/", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: int) -> HTMLResponse:
    job = require_job(job_id)
    return templates.TemplateResponse(request, "job_detail.html", {"job": job, "settings": load_settings()})


@app.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: int) -> RedirectResponse:
    job = require_job(job_id)
    await cancel_job_record(job)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int) -> RedirectResponse:
    job = require_job(job_id)
    retry_job_record(job)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.post("/jobs/bulk-action")
async def bulk_job_action(
    action: Annotated[str, Form()],
    job_ids: Annotated[list[int], Form()] = [],
) -> RedirectResponse:
    if not job_ids:
        return RedirectResponse(url="/", status_code=303)
    for job_id in job_ids:
        job = db.get_job(job_id)
        if not job:
            continue
        if action == "cancel":
            await cancel_job_record(job)
        elif action == "retry":
            if job.status in {"failed", "canceled", "completed"}:
                retry_job_record(job)
        elif action == "copy":
            if job.output_path:
                copy_file_to_dir(job.output_path, load_settings().audiobookshelf_dir)
                db.update_job(job.id, copied_to_audiobookshelf=1)
        elif action == "delete":
            db.delete_job(job.id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported bulk action.")
    return RedirectResponse(url="/", status_code=303)


def retry_job_record(job) -> None:
    if job.status not in {"failed", "canceled", "completed"}:
        raise HTTPException(status_code=400, detail="Only terminal jobs can be retried.")
    db.update_job(
        job.id,
        status="queued",
        mimika_job_id=None,
        progress=None,
        chars_per_sec=None,
        eta_seconds=None,
        eta_formatted=None,
        error=None,
        started_at=None,
        completed_at=None,
        output_path=None,
        auto_copy_to_audiobookshelf=int(job.auto_copy_to_audiobookshelf),
        copied_to_audiobookshelf=0,
    )


async def cancel_job_record(job) -> None:
    if job.status == "queued":
        db.update_job(job.id, status="canceled", completed_at=db.now_iso())
    elif job.status == "running" and job.mimika_job_id:
        await MimikaClient(load_settings().mimika_base_url).cancel_audiobook(job.mimika_job_id)
        db.update_job(job.id, status="canceled", completed_at=db.now_iso())


@app.post("/jobs/{job_id}/delete")
async def delete_job(
    job_id: int,
    delete_input: Annotated[bool, Form()] = False,
    delete_output: Annotated[bool, Form()] = False,
    delete_mimika: Annotated[bool, Form()] = False,
) -> RedirectResponse:
    job = require_job(job_id)
    if delete_input:
        Path(job.input_path).unlink(missing_ok=True)
    if delete_output and job.output_path:
        Path(job.output_path).unlink(missing_ok=True)
    if delete_mimika and job.mimika_job_id:
        await MimikaClient(load_settings().mimika_base_url).delete_job(job.mimika_job_id)
    db.delete_job(job.id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/jobs/{job_id}/download")
async def download_job(job_id: int) -> FileResponse:
    job = require_job(job_id)
    if not job.output_path:
        raise HTTPException(status_code=404, detail="No output file recorded.")
    path = Path(job.output_path).resolve()
    completed = Path(load_settings().completed_dir).resolve()
    if completed not in path.parents and path.parent != completed:
        raise HTTPException(status_code=403, detail="Refusing to serve a file outside completed_dir.")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file is missing.")
    return FileResponse(path, filename=path.name)


@app.post("/jobs/{job_id}/copy-to-audiobookshelf")
async def copy_to_audiobookshelf(job_id: int) -> RedirectResponse:
    job = require_job(job_id)
    if not job.output_path:
        raise HTTPException(status_code=400, detail="Job has no completed output.")
    copy_file_to_dir(job.output_path, load_settings().audiobookshelf_dir)
    db.update_job(job.id, copied_to_audiobookshelf=1)
    return RedirectResponse(url=f"/jobs/{job_id}", status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "settings": load_settings(),
            "output_formats": OUTPUT_FORMATS,
            "subtitle_formats": SUBTITLE_FORMATS,
        },
    )


@app.post("/settings")
async def save_settings(
    mimika_base_url: Annotated[str, Form()],
    max_parallel_jobs: Annotated[int, Form()],
    default_voice: Annotated[str, Form()],
    default_speed: Annotated[float, Form()],
    default_output_format: Annotated[str, Form()],
    default_subtitle_format: Annotated[str, Form()],
    incoming_dir: Annotated[str, Form()],
    work_dir: Annotated[str, Form()],
    completed_dir: Annotated[str, Form()],
    failed_dir: Annotated[str, Form()],
    audiobookshelf_dir: Annotated[str, Form()],
    max_upload_size_gb: Annotated[float, Form()],
    sse_interval_seconds: Annotated[float, Form()],
    auto_copy_to_audiobookshelf: Annotated[bool, Form()] = False,
) -> RedirectResponse:
    if max_parallel_jobs < 1 or max_parallel_jobs > 4:
        raise HTTPException(status_code=400, detail="max_parallel_jobs must be between 1 and 4.")
    if default_output_format not in OUTPUT_FORMATS or default_subtitle_format not in SUBTITLE_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid default format.")
    if max_upload_size_gb <= 0:
        raise HTTPException(status_code=400, detail="Upload size limit must be greater than zero.")
    if sse_interval_seconds < 1 or sse_interval_seconds > 60:
        raise HTTPException(status_code=400, detail="SSE interval must be between 1 and 60 seconds.")
    required_strings = {
        "MimikaStudio backend URL": mimika_base_url,
        "incoming_dir": incoming_dir,
        "work_dir": work_dir,
        "completed_dir": completed_dir,
        "failed_dir": failed_dir,
        "audiobookshelf_dir": audiobookshelf_dir,
    }
    empty_fields = [label for label, value in required_strings.items() if not value.strip()]
    if empty_fields:
        raise HTTPException(status_code=400, detail=f"Missing required setting: {', '.join(empty_fields)}")
    update_settings(
        mimika_base_url=mimika_base_url.strip().rstrip("/"),
        max_parallel_jobs=max_parallel_jobs,
        default_voice=default_voice.strip(),
        default_speed=default_speed,
        default_output_format=default_output_format,
        default_subtitle_format=default_subtitle_format,
        incoming_dir=incoming_dir.strip(),
        work_dir=work_dir.strip(),
        completed_dir=completed_dir.strip(),
        failed_dir=failed_dir.strip(),
        audiobookshelf_dir=audiobookshelf_dir.strip(),
        max_upload_size_bytes=int(max_upload_size_gb * 1024 * 1024 * 1024),
        sse_interval_seconds=sse_interval_seconds,
        auto_copy_to_audiobookshelf=auto_copy_to_audiobookshelf,
    )
    return RedirectResponse(url="/settings", status_code=303)


@app.get("/voices", response_class=HTMLResponse)
async def voices_page(request: Request) -> HTMLResponse:
    settings = load_settings()
    return templates.TemplateResponse(
        request,
        "voices.html",
        {"settings": settings, "voices": await safe_voices(settings.mimika_base_url)},
    )


@app.post("/voices/default")
async def set_default_voice(default_voice: Annotated[str, Form()]) -> RedirectResponse:
    update_settings(default_voice=default_voice.strip())
    return RedirectResponse(url="/voices", status_code=303)


@app.get("/mimika", response_class=HTMLResponse)
async def mimika_page(request: Request) -> HTMLResponse:
    settings = load_settings()
    client = MimikaClient(settings.mimika_base_url)
    payload = {
        "jobs": await safe_call(client.jobs),
        "audiobooks": await safe_call(client.audiobook_list),
        "kokoro_audio": await safe_call(client.kokoro_audio_list),
        "tts_audio": await safe_call(client.tts_audio_list),
    }
    audio_items = {
        "kokoro_audio": extract_audio_filenames(payload["kokoro_audio"].get("data")),
        "tts_audio": extract_audio_filenames(payload["tts_audio"].get("data")),
    }
    return templates.TemplateResponse(
        request,
        "mimika.html",
        {"settings": settings, "payload": payload, "audio_items": audio_items},
    )


@app.post("/mimika/kokoro/delete/{filename:path}")
async def delete_kokoro_audio(filename: str) -> RedirectResponse:
    await MimikaClient(load_settings().mimika_base_url).delete_kokoro_audio(Path(filename).name)
    return RedirectResponse(url="/mimika", status_code=303)


@app.post("/mimika/tts/delete/{filename:path}")
async def delete_tts_audio(filename: str) -> RedirectResponse:
    await MimikaClient(load_settings().mimika_base_url).delete_tts_audio(Path(filename).name)
    return RedirectResponse(url="/mimika", status_code=303)


async def safe_voices(base_url: str) -> list[dict[str, Any]]:
    try:
        return [with_voice_preview(voice, base_url) for voice in await MimikaClient(base_url).voices()]
    except Exception as exc:
        log.info("Unable to fetch voices: %s", exc)
        return []


async def safe_call(func):
    try:
        return {"ok": True, "data": await func()}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "data": None}


def extract_audio_filenames(data: Any) -> list[str]:
    if isinstance(data, dict):
        items = data.get("audio_files") or data.get("files") or data.get("items") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    filenames: list[str] = []
    for item in items:
        if isinstance(item, str):
            filenames.append(Path(item).name)
        elif isinstance(item, dict):
            filename = item.get("filename") or item.get("name") or item.get("path")
            if filename:
                filenames.append(Path(str(filename)).name)
    return filenames


def with_voice_preview(voice: dict[str, Any], base_url: str) -> dict[str, Any]:
    preview = (
        voice.get("preview_url")
        or voice.get("sample_url")
        or voice.get("demo_url")
        or voice.get("audio_url")
        or voice.get("preview")
        or voice.get("sample")
        or voice.get("demo")
    )
    normalized = dict(voice)
    normalized["preview_url"] = absolute_mimika_url(str(preview), base_url) if preview else None
    return normalized


def absolute_mimika_url(value: str, base_url: str) -> str:
    if value.startswith(("http://", "https://", "/")):
        return value if value.startswith(("http://", "https://")) else f"{base_url.rstrip('/')}{value}"
    return f"{base_url.rstrip('/')}/{value.lstrip('/')}"


def serialize_job(job) -> dict[str, Any]:
    output_filename = Path(job.output_path).name if job.output_path else None
    return {
        "id": job.id,
        "mimika_job_id": job.mimika_job_id,
        "title": job.title,
        "status": job.status,
        "progress": job.progress or 0,
        "chars_per_sec": job.chars_per_sec,
        "eta_formatted": job.eta_formatted,
        "eta_seconds": job.eta_seconds,
        "input_filename": job.original_filename,
        "output_filename": output_filename,
        "has_output": bool(job.output_path),
        "voice": job.voice,
        "tts_model": "Kokoro",
        "output_format": job.output_format,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "can_cancel": job.status in {"queued", "running"},
    }


def clamp_sse_interval(value: float) -> float:
    return min(max(float(value or 2), 1.0), 60.0)


def require_job(job_id: int):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
