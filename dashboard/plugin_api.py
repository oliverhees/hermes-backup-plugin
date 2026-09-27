"""Hermes Backup - Backend.

Vollstaendige lokale Hermes-Backups in einen externen Ordner. Ruft
ausschliesslich ``hermes backup`` per argv auf, veroeffentlicht ZIPs atomar
und kann optional eigene Archive im Ziel-Root begrenzt aufbewahren.

Routen liegen unter /api/plugins/hermes-backup/ (siehe dashboard/manifest.json),
hinter dem Auth-Gate des Dashboards.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()


def hermes_home() -> Path:
    """Wo Hermes seine Daten haelt, plattformuebergreifend.

    Reihenfolge wie in Hermes' eigenem scripts/install.ps1:
      1. HERMES_HOME, wenn gesetzt (gilt ueberall, auch fuer Profile)
      2. natives Windows: %LOCALAPPDATA%\\hermes
      3. sonst (Linux, macOS, WSL): ~/.hermes
    """
    env = os.environ.get("HERMES_HOME", "").strip()
    if env:
        return Path(env)
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA", "").strip()
        if local:
            return Path(local) / "hermes"
        return Path.home() / "AppData" / "Local" / "hermes"
    return Path.home() / ".hermes"


HERMES_HOME = hermes_home()
STATE_DIR = HERMES_HOME / "aiianer"

RESTORE_CONFIRM = "HERMES-IMPORT {name} ÜBERSCHREIBEN"


def _backup_state_file() -> Path:
    return STATE_DIR / "backup-state.json"


def _backup_runner() -> Path:
    return HERMES_HOME / "scripts" / "aiianer-backup-runner.py"


def _backup_state() -> dict:
    try:
        value = json.loads(_backup_state_file().read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {
            "schemaVersion": 1,
            "enabled": False,
            "target_dir": "",
            "schedule": "manual",
            "retention": {"enabled": False, "keep": 5},
            "state": "never_run",
            "lastRun": None,
            "lastArchive": None,
            "lastErrorCode": None,
        }


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _backup_save(value: dict) -> None:
    _write_json_atomic(_backup_state_file(), value)


def _backup_target(raw: str, create: bool = True) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("TARGET_REQUIRED")
    p = Path(raw).expanduser()
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError("TARGET_ABSOLUTE_REQUIRED")
    if create:
        p.mkdir(parents=True, exist_ok=True)
    target = p.resolve(strict=True)
    home = hermes_home().resolve(strict=False)
    try:
        target.relative_to(home)
    except ValueError:
        pass
    else:
        raise ValueError("TARGET_INSIDE_HERMES_HOME")
    if not target.is_dir() or not os.access(target, os.W_OK):
        raise ValueError("TARGET_NOT_WRITABLE")
    if os.name == "nt" and str(target).startswith("\\\\"):
        raise ValueError("TARGET_NETWORK_OR_UNSUPPORTED")
    return target


def _backup_schedule_expression(schedule: str, at: str, weekday: int) -> str:
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", at):
        raise ValueError("SCHEDULE_TIME_INVALID")
    if not isinstance(weekday, int) or isinstance(weekday, bool) or not 0 <= weekday <= 6:
        raise ValueError("SCHEDULE_WEEKDAY_INVALID")
    hour, minute = at.split(":")
    if schedule == "daily":
        return f"{int(minute)} {int(hour)} * * *"
    if schedule == "weekly":
        return f"{int(minute)} {int(hour)} * * {weekday}"
    raise ValueError("SCHEDULE_INVALID")


def _backup_browse_path(raw: str | None) -> Path:
    if not raw:
        return Path.home().resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("BROWSER_PATH_INVALID")
    path = candidate.resolve(strict=True)
    home = HERMES_HOME.resolve(strict=False)
    try:
        path.relative_to(home)
    except ValueError:
        pass
    else:
        raise ValueError("BROWSER_INSIDE_HERMES_HOME")
    if not path.is_dir():
        raise ValueError("BROWSER_PATH_INVALID")
    return path


def _archive_is_valid(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None and bool(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return False


def _archive_count(raw) -> int:
    try:
        return sum(
            1
            for p in _backup_target(raw, False).iterdir()
            if p.is_file() and p.name.startswith("aiianer-backup-") and p.name.endswith(".zip")
        )
    except (ValueError, OSError, TypeError):
        return 0


def _backup_public(state: dict) -> dict:
    retention = state.get("retention") if isinstance(state.get("retention"), dict) else {}
    history = state.get("history") if isinstance(state.get("history"), list) else []
    return {
        "configured": bool(state.get("target_dir")),
        "enabled": bool(state.get("enabled")),
        "targetDir": state.get("target_dir") or None,
        "schedule": state.get("schedule", "manual"),
        "scheduleTime": state.get("scheduleTime", "02:00"),
        "scheduleWeekday": state.get("scheduleWeekday", 0),
        "retention": {"enabled": bool(retention.get("enabled")), "keep": int(retention.get("keep", 5))},
        "state": state.get("state", "never_run"),
        "lastRun": state.get("lastRun"),
        "lastArchive": state.get("lastArchive"),
        "lastErrorCode": state.get("lastErrorCode"),
        "scheduleErrorCode": state.get("scheduleErrorCode"),
        "nextRun": None,
        "archiveCount": _archive_count(state.get("target_dir")),
        "history": history[:20],
    }


@router.get("/status")
async def backup_status() -> dict:
    return _backup_public(_backup_state())


@router.get("/config")
async def backup_config() -> dict:
    return _backup_public(_backup_state())


def _backup_cron_args(expression: str, action: str, job_id: str | None = None) -> list[str]:
    base = [shutil.which("hermes") or "hermes", "cron", action]
    if job_id:
        base.append(job_id)
    base.extend([expression, "--name", "aiianer-backup", "--script", "aiianer-backup-runner.py", "--no-agent", "--deliver", "local"])
    if action == "edit":
        base.remove(expression)
        base.extend(["--schedule", expression])
    return base


def _backup_cron_job() -> tuple[str, str] | None:
    try:
        listed = subprocess.run(
            [shutil.which("hermes") or "hermes", "cron", "list", "--all"],
            capture_output=True, text=True, timeout=30, shell=False, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("CRON_SETUP_FAILED") from exc
    if listed.returncode != 0:
        raise RuntimeError("CRON_SETUP_FAILED")
    matches = list(re.finditer(r"(?m)^[ \t]*([0-9a-f]{12}) \[(active|paused)\]", listed.stdout or ""))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(listed.stdout or "")
        if re.search(r"(?m)^[ \t]*Name:[ \t]+aiianer-backup[ \t]*$", (listed.stdout or "")[match.start():end]):
            return match.group(1), match.group(2)
    return None


def _backup_cron_id() -> str | None:
    job = _backup_cron_job()
    return job[0] if job else None


def _ensure_backup_cron(schedule: str, at: str = "02:00", weekday: int = 0) -> None:
    expression = _backup_schedule_expression(schedule, at, weekday)
    job = _backup_cron_job()
    job_id = job[0] if job else None
    action = "edit" if job_id else "create"
    argv = _backup_cron_args(expression, action, job_id)
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30, shell=False, check=False)
        if result.returncode != 0:
            raise RuntimeError("CRON_SETUP_FAILED")
        if job and job[1] == "paused":
            result = subprocess.run(
                [shutil.which("hermes") or "hermes", "cron", "resume", job[0]],
                capture_output=True, text=True, timeout=30, shell=False, check=False,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("CRON_SETUP_FAILED") from exc
    if result.returncode != 0:
        raise RuntimeError("CRON_SETUP_FAILED")


def _pause_backup_cron() -> None:
    job_id = _backup_cron_id()
    if not job_id:
        return
    try:
        result = subprocess.run(
            [shutil.which("hermes") or "hermes", "cron", "pause", job_id],
            capture_output=True, text=True, timeout=30, shell=False, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("CRON_SETUP_FAILED") from exc
    if result.returncode != 0:
        raise RuntimeError("CRON_SETUP_FAILED")


@router.put("/settings")
async def backup_settings(body: dict) -> dict:
    body = body or {}
    schedule = body.get("schedule", "manual")
    if schedule not in {"manual", "daily", "weekly"}:
        raise HTTPException(422, "SCHEDULE_INVALID")
    schedule_time = body.get("scheduleTime", "02:00")
    schedule_weekday = body.get("scheduleWeekday", 0)
    if schedule != "manual":
        try:
            _backup_schedule_expression(schedule, schedule_time, schedule_weekday)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
    retention = body.get("retention") or {}
    keep = retention.get("keep", 5)
    if not isinstance(keep, int) or isinstance(keep, bool) or not 1 <= keep <= 100:
        raise HTTPException(422, "RETENTION_INVALID")
    target = body.get("target_dir", body.get("targetDir", ""))
    try:
        canonical = str(_backup_target(target)) if target else ""
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    settings = {
        "schemaVersion": 1,
        "enabled": bool(body.get("enabled", False)),
        "target_dir": canonical,
        "schedule": schedule,
        "scheduleTime": schedule_time,
        "scheduleWeekday": schedule_weekday,
        "retention": {"enabled": bool(retention.get("enabled", False)), "keep": keep},
    }
    _backup_save({**_backup_state(), **settings})
    try:
        if settings["enabled"] and schedule != "manual":
            _ensure_backup_cron(schedule, schedule_time, schedule_weekday)
        else:
            _pause_backup_cron()
        state = {**_backup_state(), **settings}
        state.pop("scheduleErrorCode", None)
        _backup_save(state)
    except RuntimeError:
        state = {**_backup_state(), **settings, "scheduleErrorCode": "CRON_SETUP_FAILED"}
        _backup_save(state)
    return _backup_public(_backup_state())


@router.post("/browse")
async def backup_browse(body: dict) -> dict:
    try:
        path = _backup_browse_path((body or {}).get("path"))
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc))
    directories = []
    try:
        for child in sorted(path.iterdir(), key=lambda p: p.name.casefold()):
            if child.is_dir():
                directories.append({"name": child.name, "path": str(child.resolve())})
            if len(directories) >= 200:
                break
    except OSError:
        raise HTTPException(422, "BROWSER_PATH_UNREADABLE")
    return {"path": str(path), "parent": str(path.parent) if path.parent != path else None, "directories": directories}


@router.get("/archives")
async def backup_archives() -> dict:
    state = _backup_state()
    result = []
    try:
        for p in sorted(_backup_target(state.get("target_dir"), False).glob("aiianer-backup-*.zip"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_file():
                result.append({
                    "name": p.name,
                    "bytes": p.stat().st_size,
                    "modified": datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).isoformat(),
                    "valid": _archive_is_valid(p),
                })
    except (ValueError, OSError, TypeError):
        pass
    return {"archives": result}


@router.post("/run")
async def backup_run() -> dict:
    state = _backup_state()
    if not state.get("target_dir"):
        raise HTTPException(409, "NOT_CONFIGURED")
    if not _backup_runner().is_file():
        raise HTTPException(500, "RUNNER_NOT_INSTALLED")
    try:
        proc = subprocess.run([sys.executable, str(_backup_runner())], capture_output=True, text=True, timeout=3600, shell=False)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "BACKUP_TIMEOUT")
    if proc.returncode != 0:
        fresh = _backup_state()
        return {"ok": False, **_backup_public(fresh)}
    fresh = _backup_state()
    return {"ok": True, **_backup_public(fresh)}


@router.post("/restore/prepare")
async def backup_restore_prepare(body: dict) -> dict:
    name = (body or {}).get("name", "")
    if not re.fullmatch(r"aiianer-backup-[A-Za-z0-9T_-]+\.zip", name):
        raise HTTPException(422, "ARCHIVE_INVALID_NAME")
    state = _backup_state()
    try:
        target = _backup_target(state.get("target_dir"), False).resolve()
        archive = (target / name).resolve(strict=True)
        archive.relative_to(target)
    except (ValueError, OSError):
        raise HTTPException(404, "ARCHIVE_MISSING_OR_INVALID")
    if not archive.is_file() or not _archive_is_valid(archive):
        raise HTTPException(404, "ARCHIVE_MISSING_OR_INVALID")
    nonce = os.urandom(16).hex()
    state["restoreNonce"] = nonce
    _backup_save(state)
    return {
        "name": name,
        "bytes": archive.stat().st_size,
        "targetHome": str(hermes_home()),
        "confirmationText": RESTORE_CONFIRM.format(name=name),
        "confirmationToken": nonce,
        "warning": "Der Import kann bestehende Hermes-Daten überschreiben.",
    }


@router.post("/restore/confirm")
async def backup_restore_confirm(body: dict) -> dict:
    body = body or {}
    name = body.get("name", "")
    state = _backup_state()
    if not isinstance(name, str) or not re.fullmatch(r"aiianer-backup-[A-Za-z0-9T_-]+\.zip", name):
        raise HTTPException(422, "ARCHIVE_INVALID_NAME")
    expected = RESTORE_CONFIRM.format(name=name)
    if (
        not state.get("restoreNonce")
        or body.get("confirmationToken") != state.get("restoreNonce")
        or body.get("confirmationText") != expected
        or not body.get("acknowledged")
    ):
        raise HTTPException(409, "RESTORE_CONFIRMATION_REQUIRED")
    try:
        target = _backup_target(state.get("target_dir"), False).resolve()
        archive = (target / name).resolve(strict=True)
        archive.relative_to(target)
    except (ValueError, OSError):
        raise HTTPException(404, "ARCHIVE_MISSING_OR_INVALID")
    proc = subprocess.run([shutil.which("hermes") or "hermes", "import", "--force", str(archive)], capture_output=True, text=True, timeout=3600, shell=False)
    state.pop("restoreNonce", None)
    state["state"] = "success" if proc.returncode == 0 else "failed"
    state["lastErrorCode"] = None if proc.returncode == 0 else "RESTORE_FAILED"
    _backup_save(state)
    if proc.returncode != 0:
        raise HTTPException(500, "RESTORE_FAILED")
    return {"ok": True, **_backup_public(_backup_state())}
