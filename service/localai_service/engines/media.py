"""ffmpeg helpers shared by all modules."""
import asyncio
import re
from pathlib import Path

from .. import config, procs
from ..i18n import tr
from ..jobs import Job

VISUALS = {"flow": "visual-flow-city.png", "spectrum": "visual-spectrum.png", "nebula": "visual-nebula.png"}
WAVE_COLORS = {"flow": "#e780ff|#4bb9ff", "spectrum": "#ec68ff|#2e9dff", "nebula": "#8190ff|#d063ff"}


async def probe_duration(path: Path) -> float:
    """Media duration in seconds, read from ffmpeg's header dump (ffprobe is not bundled)."""
    proc = await asyncio.create_subprocess_exec(
        config.FFMPEG, "-hide_banner", "-i", str(path),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE, **procs.spawn_kwargs())
    _, err = await proc.communicate()
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", err.decode(errors="replace"))
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


async def finish_audio(job: Job, wav: Path, m4a: Path) -> None:
    """Peak-limit to -1 dBFS (several music models hit 0 dBFS) and encode AAC for playback."""
    await job.run([
        config.FFMPEG, "-y", "-v", "error", "-i", wav,
        "-af", "alimiter=limit=0.891:level=false", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", m4a,
    ], log_name="ffmpeg.log")


async def export_visual_video(job: Job, audio: Path, visual: str, out: Path) -> None:
    visual = visual if visual in VISUALS else "flow"
    duration = await probe_duration(audio) or 1.0
    filt = (
        "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "zoompan=z='min(zoom+0.00012,1.08)':d=1:s=1280x720:fps=30[bg];"
        f"[1:a]asplit=2[vis][aud];[vis]showwaves=s=1060x118:mode=cline:rate=30:colors={WAVE_COLORS[visual]}[wave];"
        "[bg][wave]overlay=(W-w)/2:H-h-58,format=yuv420p[v]"
    )

    def on_line(line: str) -> None:
        m = re.match(r"out_time_us=(\d+)", line)
        if m:
            job.update(int(m.group(1)) / 1e6 / duration * 98, tr("正在渲染声音动效画面"))

    await job.run([
        config.FFMPEG, "-y", "-loop", "1", "-framerate", "30", "-i", config.ASSETS_DIR / VISUALS[visual],
        "-i", audio, "-filter_complex", filt, "-map", "[v]", "-map", "[aud]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "256k",
        "-shortest", "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", out,
    ], log_name="ffmpeg.log", on_line=on_line)
