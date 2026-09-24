"""Model downloads: resumable, segmented, sha256-verified, with a mirror option.

Each catalog model lists Hugging Face sources. Files are fetched into `<name>.part`
(8 parallel byte ranges, each resumable), verified against the LFS sha256 from the Hub
API, then renamed into place, so a half-finished file is never mistaken for a model.
"""
import asyncio
import hashlib
import json
import re
import shutil
import ssl
import time
from pathlib import Path
from urllib.parse import quote

import aiohttp

from . import catalog, config, settings

def _ssl_context():
    """Prefer the certifi bundle shipped with the runtime; fall back to the system store."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


SEGMENTS = 8
SEGMENT_MIN = 64 * 1024**2
CHUNK = 1024 * 1024


class DownloadError(Exception):
    pass


class Download:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.state = "running"  # running | verifying | done | error | cancelled
        self.done_bytes = 0
        self.total_bytes = 0
        self.error = ""
        self.started = time.time()
        self._speed_mark = (time.time(), 0)
        self.speed = 0.0
        self.task: asyncio.Task | None = None

    def add(self, n: int) -> None:
        self.done_bytes += n
        t0, b0 = self._speed_mark
        now = time.time()
        if now - t0 >= 1.0:
            self.speed = (self.done_bytes - b0) / (now - t0)
            self._speed_mark = (now, self.done_bytes)

    def public(self) -> dict:
        eta = (self.total_bytes - self.done_bytes) / self.speed if self.speed > 0 else None
        return {"state": self.state, "doneBytes": self.done_bytes, "totalBytes": self.total_bytes,
                "speed": round(self.speed), "etaSeconds": round(eta) if eta else None, "error": self.error}


def _base_url() -> str:
    return "https://hf-mirror.com" if settings.get("mirror") == "hf-mirror" else "https://huggingface.co"


def _headers() -> dict:
    token = settings.get("hfToken")
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _list_files(session: aiohttp.ClientSession, source: dict) -> list[dict]:
    url = f"{_base_url()}/api/models/{source['repo']}/tree/main"
    if source.get("sub"):
        url += "/" + quote(source["sub"])
    async with session.get(url + "?recursive=true", headers=_headers()) as r:
        if r.status in (401, 403):
            raise DownloadError("这个模型需要先在 Hugging Face 上同意许可证，并在设置里填写访问令牌")
        if r.status != 200:
            raise DownloadError(f"无法获取模型文件列表（{r.status}）")
        items = [f for f in await r.json() if f.get("type") == "file"]
    # include/exclude patterns match the path below `sub`.
    inc, exc = source.get("include"), source.get("exclude")
    prefix = source["sub"].rstrip("/") + "/" if source.get("sub") else ""
    items = [f for f in items
             if (not inc or re.search(inc, f["path"][len(prefix):])) and not (exc and re.search(exc, f["path"][len(prefix):]))]
    return [{"path": f["path"], "size": f.get("size", 0), "sha256": (f.get("lfs") or {}).get("oid"),
             "dest": config.MODELS_DIR / source["dest"] / f["path"][len(prefix):]} for f in items]


async def _fetch_range(session, url, path: Path, start: int, end: int, dl: Download) -> None:
    """Append bytes [start + len(path), end] to `path`, retrying with resume."""
    for attempt in range(8):
        have = path.stat().st_size if path.exists() else 0
        if start + have > end:
            return
        headers = {**_headers(), "Range": f"bytes={start + have}-{end}"}
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(sock_read=60)) as r:
                if r.status not in (200, 206):
                    raise DownloadError(f"下载服务器返回 {r.status}")
                with open(path, "ab") as out:
                    async for chunk in r.content.iter_chunked(CHUNK):
                        if dl.state == "cancelled":
                            return
                        out.write(chunk)
                        dl.add(len(chunk))
            return
        except (aiohttp.ClientError, asyncio.TimeoutError, DownloadError):
            if attempt == 7:
                raise
            await asyncio.sleep(min(30, 2**attempt))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 * CHUNK):
            h.update(chunk)
    return h.hexdigest()


async def _fetch_file(session, source: dict, f: dict, dl: Download) -> None:
    dest: Path = f["dest"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{_base_url()}/{source['repo']}/resolve/main/{quote(f['path'])}"
    size = f["size"]
    parts = max(1, min(SEGMENTS, size // SEGMENT_MIN)) if size else 1
    step = -(-size // parts) if size else 0
    segs = [(dest.with_name(dest.name + f".part{i}"), i * step, min(size, (i + 1) * step) - 1) for i in range(parts)]
    await asyncio.gather(*[_fetch_range(session, url, p, lo, hi if size else 2**62, dl) for p, lo, hi in segs])
    if dl.state == "cancelled":
        return
    part = dest.with_name(dest.name + ".part")
    with open(part, "wb") as out:
        for p, _, _ in segs:
            with open(p, "rb") as src:
                shutil.copyfileobj(src, out, 16 * CHUNK)
    for p, _, _ in segs:
        p.unlink(missing_ok=True)
    if size and part.stat().st_size != size:
        part.unlink(missing_ok=True)
        raise DownloadError(f"{dest.name} 大小不对，请重试")
    if f["sha256"]:
        dl.state = "verifying"
        digest = await asyncio.to_thread(_sha256, part)
        dl.state = "running"
        if digest != f["sha256"]:
            part.unlink(missing_ok=True)
            raise DownloadError(f"{dest.name} 校验失败，文件已删除，请重试")
    part.replace(dest)


class DownloadManager:
    def __init__(self) -> None:
        self.downloads: dict[str, Download] = {}

    def status(self) -> dict:
        return {k: v.public() for k, v in self.downloads.items()}

    def start(self, model_id: str) -> Download:
        model = catalog.by_id(model_id)
        if model is None or not model.get("sources"):
            raise KeyError(model_id)
        current = self.downloads.get(model_id)
        if current and current.state in ("running", "verifying"):
            return current
        dl = Download(model_id)
        self.downloads[model_id] = dl
        dl.task = asyncio.create_task(self._run(model, dl))
        return dl

    def cancel(self, model_id: str) -> None:
        dl = self.downloads.get(model_id)
        if dl and dl.state in ("running", "verifying"):
            dl.state = "cancelled"
            if dl.task:
                dl.task.cancel()

    async def _run(self, model: dict, dl: Download) -> None:
        try:
            connector = aiohttp.TCPConnector(ssl=_ssl_context())
            async with aiohttp.ClientSession(connector=connector,
                                             timeout=aiohttp.ClientTimeout(total=None, connect=30)) as session:
                plan = []
                for source in model["sources"]:
                    for f in await _list_files(session, source):
                        plan.append((source, f))
                todo = [(s, f) for s, f in plan if not f["dest"].exists()]
                dl.total_bytes = sum(f["size"] for _, f in todo)
                dl.done_bytes = sum(p.stat().st_size for _, f in todo
                                    for p in f["dest"].parent.glob(f["dest"].name + ".part*"))
                free = shutil.disk_usage(config.MODELS_DIR if config.MODELS_DIR.exists() else config.DATA_DIR).free
                if dl.total_bytes - dl.done_bytes > free - 2 * 1024**3:
                    raise DownloadError(f"磁盘空间不足：需要约 {dl.total_bytes / 1024**3:.1f} GB")
                for source, f in todo:
                    if dl.state == "cancelled":
                        return
                    await _fetch_file(session, source, f, dl)
                if dl.state == "cancelled":
                    return
                manifest = _manifest_path(model["id"])
                manifest.parent.mkdir(parents=True, exist_ok=True)
                manifest.write_text(json.dumps([f["dest"].relative_to(config.MODELS_DIR).as_posix() for _, f in plan]), encoding="utf-8")
                dl.state = "done"
        except asyncio.CancelledError:
            dl.state = "cancelled"
        except DownloadError as exc:
            dl.state, dl.error = "error", str(exc)
        except Exception as exc:  # network stack errors
            dl.state, dl.error = "error", f"下载失败：{exc}"[:200]


def _manifest_path(model_id: str) -> Path:
    return config.MODELS_DIR / ".manifests" / f"{model_id}.json"


def _manifest_files(model_id: str) -> list[str]:
    try:
        return json.loads(_manifest_path(model_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def remove(model_id: str) -> None:
    """Delete a model's files: those recorded at download time, else its catalog files."""
    model = catalog.by_id(model_id)
    if model is None:
        raise KeyError(model_id)
    manifest = _manifest_path(model_id)
    files = _manifest_files(model_id) or model.get("files", []) + list(model.get("parts", {}).values()) + model.get("choices", [])
    # Files shared with another installed model (e.g. the Qwen3 text encoder) stay.
    shared = {rel for other in catalog.MODELS if other["id"] != model_id for rel in _manifest_files(other["id"])}
    root = config.MODELS_DIR.resolve()
    for rel in files:
        if rel in shared:
            continue
        path = (config.MODELS_DIR / rel).resolve()
        if root in path.parents:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
    manifest.unlink(missing_ok=True)
