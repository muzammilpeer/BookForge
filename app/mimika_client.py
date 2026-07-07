from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx


log = logging.getLogger("bookforge.mimika")


class MimikaClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=60) as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return response.text

    async def health(self) -> dict[str, Any]:
        try:
            data = await self._request("GET", "/api/jobs")
            return {"ok": True, "detail": "Backend reachable", "sample": data}
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    async def voices(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/kokoro/voices")
        if isinstance(data, list):
            return [self._normalize_voice(item) for item in data]
        if isinstance(data, dict):
            voices = data.get("voices") or data.get("data") or data.get("items") or []
            if isinstance(voices, dict):
                return [
                    {"id": str(key), "label": str(value.get("label") or value.get("name") or key)}
                    if isinstance(value, dict)
                    else {"id": str(key), "label": str(value)}
                    for key, value in voices.items()
                ]
            if isinstance(voices, list):
                return [self._normalize_voice(item) for item in voices]
        return []

    def _normalize_voice(self, item: Any) -> dict[str, Any]:
        if isinstance(item, str):
            return {"id": item, "label": item}
        if isinstance(item, dict):
            voice_id = item.get("id") or item.get("voice_id") or item.get("code") or item.get("name") or item.get("key")
            label = item.get("label") or item.get("display_name") or item.get("name") or voice_id
            return {"id": str(voice_id), "label": str(label), **item}
        return {"id": str(item), "label": str(item)}

    async def start_audiobook_job(
        self,
        *,
        file_path: str,
        title: str,
        voice: str,
        speed: float,
        output_format: str,
        subtitle_format: str,
    ) -> str:
        with Path(file_path).open("rb") as handle:
            files = {"file": (Path(file_path).name, handle)}
            data = {
                "title": title,
                "voice": voice,
                "speed": str(speed),
                "output_format": output_format,
                "subtitle_format": subtitle_format,
            }
            response = await self._request("POST", "/api/audiobook/generate-from-file", data=data, files=files)
        job_id = self._extract_job_id(response)
        if not job_id:
            log.warning("Mimika generate response did not contain a job id: %r", response)
            raise ValueError("Mimika response did not include job_id")
        return job_id

    def _extract_job_id(self, response: Any) -> str | None:
        if isinstance(response, dict):
            for key in ("job_id", "id"):
                if response.get(key):
                    return str(response[key])
            job = response.get("job")
            if isinstance(job, dict):
                for key in ("job_id", "id"):
                    if job.get(key):
                        return str(job[key])
        return None

    async def status(self, job_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/api/audiobook/status/{job_id}")
        return self.normalize_status(data)

    def normalize_status(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {"status": "running", "raw": data}
        source = data.get("job") if isinstance(data.get("job"), dict) else data
        error = source.get("error") or source.get("message") if isinstance(source, dict) else None
        return {
            "status": source.get("status") or source.get("state") or "running",
            "progress": source.get("progress") or source.get("percent") or source.get("percentage"),
            "chars_per_sec": source.get("chars_per_sec") or source.get("charsPerSec"),
            "eta_seconds": source.get("eta_seconds") or source.get("etaSeconds"),
            "eta_formatted": source.get("eta_formatted") or source.get("eta"),
            "output_path": source.get("output_path") or source.get("output_file") or source.get("file_path"),
            "error": error,
            "raw": data,
        }

    async def audiobook_list(self) -> Any:
        return await self._request("GET", "/api/audiobook/list")

    async def jobs(self) -> Any:
        return await self._request("GET", "/api/jobs")

    async def job(self, job_id: str) -> Any:
        return await self._request("GET", f"/api/jobs/{job_id}")

    async def metrics(self, job_id: str) -> Any:
        return await self._request("GET", f"/api/jobs/{job_id}/metrics")

    async def cancel_audiobook(self, job_id: str) -> None:
        await self._request("POST", f"/api/audiobook/cancel/{job_id}")

    async def delete_job(self, job_id: str) -> None:
        try:
            await self._request("DELETE", f"/api/jobs/{job_id}")
        except Exception as exc:
            log.info("DELETE /api/jobs/%s failed: %s", job_id, exc)
        try:
            await self._request("DELETE", f"/api/audiobook/{job_id}")
        except Exception as exc:
            log.info("DELETE /api/audiobook/%s failed: %s", job_id, exc)

    async def kokoro_audio_list(self) -> Any:
        return await self._request("GET", "/api/kokoro/audio/list")

    async def tts_audio_list(self) -> Any:
        return await self._request("GET", "/api/tts/audio/list")

    async def delete_kokoro_audio(self, filename: str) -> None:
        await self._request("DELETE", f"/api/kokoro/audio/{filename}")

    async def delete_tts_audio(self, filename: str) -> None:
        await self._request("DELETE", f"/api/tts/audio/{filename}")
