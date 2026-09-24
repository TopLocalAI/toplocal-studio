"""User-provided inputs (images to edit or animate, audio to transcribe, voices to clone).

Inputs are referenced in job params either as {"upload": "<id>"} or as
{"library": "<job id>", "file": "<name>"} for an earlier result.
"""
import re
import uuid
from pathlib import Path

from . import config
from .jobs import JobFailed

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".bmp"}
AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".mp4", ".mov", ".mkv", ".webm", ".amr"}
MAX_BYTES = 2 * 1024**3
UPLOAD_ID = re.compile(r"^[0-9a-f]{16}$")
JOB_ID = re.compile(r"^[0-9a-f]{12}$")
FILE_NAME = re.compile(r"^[\w.-]+$")


def kind_of(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in AUDIO_EXT:
        return "audio"
    return None


def new_path(filename: str) -> tuple[str, Path]:
    upload_id = uuid.uuid4().hex[:16]
    ext = Path(filename).suffix.lower()
    return upload_id, config.UPLOADS_DIR / f"{upload_id}{ext}"


def find_upload(upload_id: str) -> Path | None:
    if not UPLOAD_ID.match(upload_id or ""):
        return None
    matches = list(config.UPLOADS_DIR.glob(f"{upload_id}.*"))
    return matches[0] if matches else None


def resolve(ref) -> Path:
    """Turn a job-param reference into a file path, or fail with a user-facing message."""
    if isinstance(ref, dict):
        if ref.get("upload"):
            path = find_upload(str(ref["upload"]))
            if path:
                return path
        elif ref.get("library") and ref.get("file"):
            job_id, name = str(ref["library"]), str(ref["file"])
            if JOB_ID.match(job_id) and FILE_NAME.match(name):
                path = config.LIBRARY_DIR / job_id / name
                if path.is_file():
                    return path
    raise JobFailed("找不到输入文件，请重新选择")
