"""Job queue. One job runs at a time because every engine wants the whole GPU.

Each job owns a directory under LIBRARY_DIR holding its outputs, its log and a
job.json snapshot, which is also what the library view lists after a restart.
"""
import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

from . import config, procs
from .i18n import tr

ACTIVE = ("queued", "running")
# Engines must never fetch weights on their own (the model manager owns downloads), and
# Python engines must flush output so progress can be parsed while they run.
ENGINE_ENV = {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONUNBUFFERED": "1"}


def _engine_path() -> str:
    """PATH for engines: the bundled ffmpeg first (ltx-2-mlx looks it up on PATH)."""
    path = os.environ.get("PATH", "")
    ffmpeg = Path(config.FFMPEG)
    return f"{ffmpeg.parent}{os.pathsep}{path}" if ffmpeg.is_absolute() else path


class JobCancelled(Exception):
    pass


class JobFailed(Exception):
    """An error whose message is safe to show to the user."""


@dataclass
class Job:
    module: str
    task: str
    params: dict
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "queued"
    progress: float = 0.0
    label: str = field(default_factory=lambda: tr("排队中"))
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    result: dict | None = None
    error: str | None = None
    title: str = ""
    _proc: asyncio.subprocess.Process | None = None
    _cancelled: bool = False

    @property
    def dir(self) -> Path:
        return config.LIBRARY_DIR / self.id

    def public(self) -> dict:
        end = self.finished or time.time()
        return {
            "id": self.id,
            "module": self.module,
            "task": self.task,
            "title": self.title,
            "status": self.status,
            "progress": round(self.progress, 1),
            "label": self.label,
            "created": self.created,
            "elapsedSeconds": round(end - (self.started or end)),
            "params": self.params,
            "result": self.result,
            "error": self.error,
        }

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "job.json").write_text(json.dumps(self.public(), ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, progress: float | None = None, label: str | None = None) -> None:
        if progress is not None:
            self.progress = max(self.progress, min(99.0, progress))
        if label is not None:
            self.label = label

    async def run(self, cmd: list, *, cwd: Path | None = None, log_name: str = "engine.log",
                  on_line: Callable[[str], None] | None = None, env: dict | None = None) -> str:
        """Run a subprocess, logging stdout+stderr to separate files; returns stdout."""
        if self._cancelled:
            raise JobCancelled()
        self.dir.mkdir(parents=True, exist_ok=True)
        out_path, err_path = self.dir / log_name, self.dir / (log_name + ".err")
        self._proc = await asyncio.create_subprocess_exec(
            *[str(c) for c in cmd], cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **ENGINE_ENV, "PATH": _engine_path(), **(env or {})}, **procs.spawn_kwargs(),
        )
        stdout_chunks: list[str] = []

        async def pump(stream, path, keep):
            with open(path, "ab") as log:
                buf = b""
                while chunk := await stream.read(4096):
                    log.write(chunk)
                    buf += chunk
                    *lines, buf = buf.replace(b"\r", b"\n").split(b"\n")
                    for raw in lines:
                        line = raw.decode(errors="replace")
                        if keep:
                            stdout_chunks.append(line)
                        if on_line:
                            on_line(line)
                if buf:
                    line = buf.decode(errors="replace")
                    if keep:
                        stdout_chunks.append(line)
                    if on_line:
                        on_line(line)

        await asyncio.gather(pump(self._proc.stdout, out_path, True), pump(self._proc.stderr, err_path, False))
        code = await self._proc.wait()
        self._proc = None
        if self._cancelled:
            raise JobCancelled()
        if code != 0:
            tail = err_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
            raise RuntimeError(f"{Path(str(cmd[0])).name} exited with {code}: {' | '.join(tail)}")
        return "\n".join(stdout_chunks)

    def cancel(self) -> None:
        self._cancelled = True
        if self._proc and self._proc.returncode is None:
            procs.kill_tree(self._proc.pid)


Runner = Callable[[Job], Awaitable[dict]]


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.runners: dict[tuple[str, str], Runner] = {}
        self.queue: asyncio.Queue[Job] = asyncio.Queue()
        self._worker: asyncio.Task | None = None

    def register(self, module: str, task: str, runner: Runner) -> None:
        self.runners[(module, task)] = runner

    def start(self) -> None:
        self._worker = asyncio.create_task(self._loop())

    def submit(self, module: str, task: str, params: dict, title: str = "") -> Job:
        if (module, task) not in self.runners:
            raise KeyError(f"unknown task {module}/{task}")
        job = Job(module=module, task=task, params=params, title=title)
        self.jobs[job.id] = job
        job.save()
        self.queue.put_nowait(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> Job | None:
        job = self.jobs.get(job_id)
        if job and job.status in ACTIVE:
            job.cancel()
            if job.status == "queued":
                self._finish(job, "cancelled", label=tr("已取消"))
        return job

    def _finish(self, job: Job, status: str, *, label: str, error: str | None = None) -> None:
        job.status, job.label, job.error, job.finished = status, label, error, time.time()
        if status == "done":
            job.progress = 100.0
        job.save()

    async def _loop(self) -> None:
        while True:
            job = await self.queue.get()
            if job.status != "queued":
                continue
            job.status, job.started, job.label = "running", time.time(), tr("正在准备")
            job.save()
            try:
                job.result = await self.runners[(job.module, job.task)](job)
                self._finish(job, "done", label=tr("完成"))
            except JobCancelled:
                self._finish(job, "cancelled", label=tr("已取消"))
            except JobFailed as exc:
                self._finish(job, "error", label=tr("生成失败"), error=str(exc))
            except Exception as exc:  # engine crash: keep details in the log, show a short message
                (job.dir / "error.log").write_text(repr(exc), encoding="utf-8")
                self._finish(job, "error", label=tr("生成失败"), error=tr("本地引擎出错：{error}", error=exc)[:300])


def library(module: str | None = None) -> list[dict]:
    items = []
    if not config.LIBRARY_DIR.exists():
        return items
    for meta in config.LIBRARY_DIR.glob("*/job.json"):
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("status") == "done" and (module is None or data.get("module") == module):
            items.append(data)
    return sorted(items, key=lambda d: d.get("created", 0), reverse=True)
