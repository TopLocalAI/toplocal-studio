"""HTTP API for the desktop app. Binds to 127.0.0.1 and requires the shell's token."""
import asyncio
import hmac
import os
import re
import shutil
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import web

from . import __version__, catalog, config, downloads, jobs, procs, settings, system, uploads
from .i18n import tr
from .engines import image, music, speech, video

MANAGER: jobs.JobManager | None = None
DOWNLOADS = downloads.DownloadManager()
LOG_REQUESTS = bool(os.environ.get("LOCALAI_LOG_REQUESTS"))
JOB_ID = re.compile(r"^[0-9a-f]{12}$")
# Explicit media types: WebKit (the desktop webview) will not play audio sent as octet-stream.
MEDIA_TYPES = {
    ".m4a": "audio/mp4", ".mp4": "video/mp4", ".wav": "audio/wav", ".mp3": "audio/mpeg",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".srt": "application/x-subrip; charset=utf-8", ".txt": "text/plain; charset=utf-8",
}


def _file_response(path: Path) -> web.FileResponse:
    response = web.FileResponse(path)
    media_type = MEDIA_TYPES.get(path.suffix.lower())
    if media_type:
        response.headers["Content-Type"] = media_type
    return response
FILE_NAME = re.compile(r"^[\w.-]+$")


def _authorized(request: web.Request) -> bool:
    if not config.TOKEN:
        return True
    supplied = request.headers.get("X-LocalAI-Token") or request.query.get("token", "")
    return hmac.compare_digest(supplied, config.TOKEN)


@web.middleware
async def security(request: web.Request, handler):
    origin = request.headers.get("Origin")
    if LOG_REQUESTS:
        print(f"{request.method} {request.path} origin={origin}", flush=True)
    if origin and origin not in config.ALLOWED_ORIGINS:
        return web.json_response({"error": "forbidden origin"}, status=403)
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    elif request.path != "/api/health" and not _authorized(request):
        response = web.json_response({"error": "unauthorized"}, status=401)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as exc:
            response = web.json_response({"error": exc.reason}, status=exc.status)
    if origin:
        response.headers.update({
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Headers": "Content-Type, X-LocalAI-Token",
            "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
            "Vary": "Origin",
        })
    return response


async def health(_):
    return web.json_response({"ok": True, "version": __version__})


async def system_info(_):
    info = system.info()
    return web.json_response(info | {"features": catalog.features_status(info["memoryGb"])})


async def models(_):
    status = DOWNLOADS.status()
    return web.json_response({"models": [m | {"download": status.get(m["id"])} for m in catalog.models_status()],
                              "tasks": catalog.tasks_status(system.memory_gb()),
                              "hasHfToken": bool(settings.get("hfToken"))})


# Hosts the UI may open in the system browser (license pages, the project page).
OPEN_HOSTS = {"huggingface.co", "hf-mirror.com", "github.com", "creativecommons.org"}


async def open_url(request):
    """Open an allowlisted https link in the default browser (the webview cannot)."""
    body = await request.json()
    url = str(body.get("url", ""))
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in OPEN_HOSTS:
        return web.json_response({"error": tr("不支持打开这个链接")}, status=400)
    webbrowser.open(url)
    return web.json_response({"ok": True})


async def download_model(request):
    try:
        dl = DOWNLOADS.start(request.match_info["id"])
    except KeyError:
        raise web.HTTPNotFound(reason=tr("模型不存在"))
    return web.json_response(dl.public(), status=202)


async def cancel_download(request):
    DOWNLOADS.cancel(request.match_info["id"])
    return web.json_response({"ok": True})


async def delete_model(request):
    model_id = request.match_info["id"]
    if any(j.status in jobs.ACTIVE for j in MANAGER.jobs.values()):
        return web.json_response({"error": tr("有任务正在进行，请完成后再删除模型")}, status=409)
    try:
        downloads.remove(model_id)
    except KeyError:
        raise web.HTTPNotFound(reason=tr("模型不存在"))
    DOWNLOADS.downloads.pop(model_id, None)
    return web.json_response({"ok": True})


async def get_settings(_):
    return web.json_response(settings.public())


async def put_settings(request):
    settings.update(await request.json())
    return web.json_response(settings.public())


async def voices(_):
    return web.json_response({"voices": [{"id": k, "name": tr(v)} for k, v in speech.KOKORO_VOICES.items()]})


async def create_job(request: web.Request):
    body = await request.json()
    module, task = str(body.get("module", "")), str(body.get("task", ""))
    try:
        job = MANAGER.submit(module, task, dict(body.get("params") or {}))
    except KeyError:
        return web.json_response({"error": tr("未知的任务类型")}, status=400)
    return web.json_response(job.public(), status=202)


def _job_or_404(request: web.Request) -> jobs.Job:
    job = MANAGER.get(request.match_info["id"])
    if job is None:
        raise web.HTTPNotFound(reason=tr("任务不存在"))
    return job


async def get_job(request):
    return web.json_response(_job_or_404(request).public())


async def cancel_job(request):
    MANAGER.cancel(request.match_info["id"])
    return web.json_response(_job_or_404(request).public())


async def list_jobs(_):
    active = [j.public() for j in MANAGER.jobs.values() if j.status in jobs.ACTIVE]
    return web.json_response({"jobs": active})


async def library(request):
    return web.json_response({"items": jobs.library(request.query.get("module"))})


async def delete_item(request):
    item_id = request.match_info["id"]
    if not JOB_ID.match(item_id):
        raise web.HTTPNotFound(reason=tr("作品不存在"))
    job = MANAGER.get(item_id)
    if job and job.status in jobs.ACTIVE:
        return web.json_response({"error": tr("任务仍在进行，请先取消")}, status=409)
    shutil.rmtree(config.LIBRARY_DIR / item_id, ignore_errors=True)
    MANAGER.jobs.pop(item_id, None)
    return web.json_response({"ok": True})


def _downloads_dir():
    return Path.home() / "Downloads"


async def save_item(request):
    """Copy a result into ~/Downloads (webviews cannot download) and reveal it."""
    item_id = request.match_info["id"]
    body = await request.json()
    name = str(body.get("file", ""))
    if not JOB_ID.match(item_id) or not FILE_NAME.match(name):
        raise web.HTTPNotFound(reason=tr("文件不存在"))
    src = config.LIBRARY_DIR / item_id / name
    if not src.is_file():
        raise web.HTTPNotFound(reason=tr("文件不存在"))
    title = re.sub(r'[\\/:*?"<>|\n]+', " ", str(body.get("title") or item_id)).strip()[:60] or item_id
    target_dir = _downloads_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{title}{src.suffix}"
    n = 2
    while target.exists():
        target = target_dir / f"{title} ({n}){src.suffix}"
        n += 1
    shutil.copy2(src, target)
    if body.get("reveal"):
        procs.reveal(target)
    return web.json_response({"path": str(target), "name": target.name})


async def upload(request: web.Request):
    """Stream one multipart file to disk; images are verified by decoding them."""
    reader = await request.multipart()
    field = await reader.next()
    if field is None or not field.filename:
        return web.json_response({"error": tr("没有收到文件")}, status=400)
    kind = uploads.kind_of(field.filename)
    if kind is None:
        return web.json_response({"error": tr("不支持这种文件格式")}, status=400)
    upload_id, path = uploads.new_path(field.filename)
    size = 0
    with open(path, "wb") as out:
        while chunk := await field.read_chunk(1024 * 1024):
            size += len(chunk)
            if size > uploads.MAX_BYTES:
                out.close()
                path.unlink(missing_ok=True)
                return web.json_response({"error": tr("文件太大（上限 2 GB）")}, status=413)
            out.write(chunk)
    info = {"id": upload_id, "kind": kind, "name": field.filename, "file": path.name, "size": size}
    if kind == "image":
        try:
            from PIL import Image
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                info["width"], info["height"] = im.size
        except Exception:
            path.unlink(missing_ok=True)
            return web.json_response({"error": tr("图片文件已损坏或无法识别")}, status=400)
    return web.json_response(info, status=201)


async def serve_upload(request):
    name = request.match_info["name"]
    path = uploads.find_upload(name.split(".")[0])
    if path is None or path.name != name:
        raise web.HTTPNotFound(reason=tr("文件不存在"))
    return _file_response(path)


async def serve_file(request):
    item_id, name = request.match_info["id"], request.match_info["name"]
    if not JOB_ID.match(item_id) or not FILE_NAME.match(name) or name.endswith((".json", ".log", ".err")):
        raise web.HTTPNotFound(reason=tr("文件不存在"))
    path = config.LIBRARY_DIR / item_id / name
    if not path.is_file():
        raise web.HTTPNotFound(reason=tr("文件不存在"))
    response = _file_response(path)
    if request.query.get("download"):
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{name}"
    return response


async def _watch_parent(pid: int) -> None:
    """Exit when the desktop shell is gone, even if it crashed or was force-quit."""
    while True:
        await asyncio.sleep(2)
        if not procs.is_alive(pid):
            for job in list(MANAGER.jobs.values()):
                job.cancel()
            os._exit(0)


async def _on_startup(app):
    MANAGER.start()
    parent = os.environ.get("LOCALAI_PARENT_PID", "")
    if parent.isdigit():
        app["parent_watch"] = asyncio.create_task(_watch_parent(int(parent)))


def create_app() -> web.Application:
    global MANAGER
    config.ensure_dirs()
    MANAGER = jobs.JobManager()
    MANAGER.register("music", "generate", music.generate)
    MANAGER.register("music", "export-video", music.export_video)
    MANAGER.register("image", "generate", image.generate)
    MANAGER.register("image", "edit", image.edit)
    MANAGER.register("speech", "transcribe", speech.transcribe)
    MANAGER.register("speech", "synthesize", speech.synthesize)
    MANAGER.register("video", "generate", video.generate)

    app = web.Application(middlewares=[security], client_max_size=uploads.MAX_BYTES)
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/system", system_info)
    app.router.add_get("/api/models", models)
    app.router.add_get("/api/voices", voices)
    app.router.add_post("/api/models/{id}/download", download_model)
    app.router.add_post("/api/models/{id}/cancel", cancel_download)
    app.router.add_delete("/api/models/{id}", delete_model)
    app.router.add_post("/api/open", open_url)
    app.router.add_get("/api/settings", get_settings)
    app.router.add_post("/api/settings", put_settings)
    app.router.add_get("/api/jobs", list_jobs)
    app.router.add_post("/api/jobs", create_job)
    app.router.add_get("/api/jobs/{id}", get_job)
    app.router.add_post("/api/jobs/{id}/cancel", cancel_job)
    app.router.add_get("/api/library", library)
    app.router.add_delete("/api/library/{id}", delete_item)
    app.router.add_post("/api/library/{id}/save", save_item)
    app.router.add_get("/files/{id}/{name}", serve_file)
    app.router.add_post("/api/uploads", upload)
    app.router.add_get("/uploads/{name}", serve_upload)
    app.router.add_route("OPTIONS", "/{tail:.*}", health)
    app.on_startup.append(_on_startup)
    return app
