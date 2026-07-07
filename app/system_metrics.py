from __future__ import annotations

import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any


def collect_system_metrics() -> dict[str, Any]:
    total_ram, available_ram = memory_bytes()
    cpu_count = os.cpu_count() or 1
    load_1m, load_5m, load_15m = os.getloadavg()
    cpu_percent = min((load_1m / cpu_count) * 100, 100)
    gpu = gpu_metrics()
    return {
        "host": platform.node() or "localhost",
        "platform": platform.system(),
        "cpu": {
            "usage_percent": round(cpu_percent, 1),
            "cores": cpu_count,
            "load_1m": round(load_1m, 2),
            "load_5m": round(load_5m, 2),
            "load_15m": round(load_15m, 2),
        },
        "memory": {
            "total_bytes": total_ram,
            "available_bytes": available_ram,
            "used_percent": round(((total_ram - available_ram) / total_ram) * 100, 1)
            if total_ram
            else None,
            "available_human": human_bytes(available_ram),
            "total_human": human_bytes(total_ram),
        },
        "gpu": gpu,
    }


def memory_bytes() -> tuple[int, int]:
    if Path("/proc/meminfo").exists():
        return linux_memory_bytes()
    if platform.system() == "Darwin":
        return macos_memory_bytes()
    return 0, 0


def linux_memory_bytes() -> tuple[int, int]:
    values: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, raw_value = line.split(":", 1)
        match = re.search(r"(\d+)", raw_value)
        if match:
            values[key] = int(match.group(1)) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", values.get("MemFree", 0))
    return total, available


def macos_memory_bytes() -> tuple[int, int]:
    total = int(run_text(["sysctl", "-n", "hw.memsize"]) or 0)
    page_size = int(run_text(["sysctl", "-n", "hw.pagesize"]) or 4096)
    vm_stat = run_text(["vm_stat"])
    free_pages = 0
    speculative_pages = 0
    inactive_pages = 0
    for line in vm_stat.splitlines():
        number = parse_vm_stat_number(line)
        if line.startswith("Pages free:"):
            free_pages = number
        elif line.startswith("Pages speculative:"):
            speculative_pages = number
        elif line.startswith("Pages inactive:"):
            inactive_pages = number
    available = (free_pages + speculative_pages + inactive_pages) * page_size
    return total, available


def parse_vm_stat_number(line: str) -> int:
    match = re.search(r"(\d+)", line.replace(".", ""))
    return int(match.group(1)) if match else 0


def gpu_metrics() -> dict[str, Any]:
    if platform.system() == "Linux":
        vcgencmd = run_text(["/usr/bin/env", "vcgencmd", "measure_temp"])
        if vcgencmd:
            return {"usage_percent": None, "detail": vcgencmd.strip()}
    if platform.system() == "Darwin":
        return macos_gpu_metrics()
    return {"usage_percent": None, "detail": "GPU metric unavailable on this host."}


def macos_gpu_metrics() -> dict[str, Any]:
    output = run_text(
        [
            "sudo",
            "-n",
            "/usr/bin/powermetrics",
            "--samplers",
            "gpu_power",
            "-i",
            "1000",
            "-n",
            "1",
        ],
        timeout=4,
    )
    if not output:
        return {
            "usage_percent": None,
            "detail": "Allow passwordless sudo for /usr/bin/powermetrics gpu_power.",
        }
    active = parse_float(r"GPU HW active residency:\s*([0-9.]+)%", output)
    idle = parse_float(r"GPU idle residency:\s*([0-9.]+)%", output)
    frequency = parse_float(r"GPU HW active frequency:\s*([0-9.]+)\s*MHz", output)
    power_mw = parse_float(r"GPU Power:\s*([0-9.]+)\s*mW", output)
    usage = active if active is not None else (100 - idle if idle is not None else None)
    detail_parts = []
    if frequency is not None:
        detail_parts.append(f"{frequency:.0f} MHz")
    if power_mw is not None:
        detail_parts.append(f"{power_mw / 1000:.1f} W")
    if idle is not None:
        detail_parts.append(f"{idle:.1f}% idle")
    return {
        "usage_percent": round(usage, 1) if usage is not None else None,
        "frequency_mhz": round(frequency, 0) if frequency is not None else None,
        "power_mw": round(power_mw, 0) if power_mw is not None else None,
        "idle_percent": round(idle, 1) if idle is not None else None,
        "detail": " | ".join(detail_parts) if detail_parts else "powermetrics GPU data available",
    }


def parse_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def run_text(command: list[str], timeout: float = 1) -> str:
    try:
        return subprocess.check_output(
            command,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        ).strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def human_bytes(value: int | None) -> str:
    if not value:
        return "Unknown"
    units = ("B", "KB", "MB", "GB", "TB")
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"
