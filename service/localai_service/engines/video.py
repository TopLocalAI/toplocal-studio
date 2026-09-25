"""Video module: LTX-2.5 distilled, text-to-video or image-to-video, with sound. Runs as int4
through ltx-2-mlx on Apple Silicon and as GGUF through stable-diffusion.cpp elsewhere (not yet
measured on Windows hardware). Needs the 24–32 GB memory class; below that it is not offered.
"""
import asyncio
import json
import random
import time

from PIL import Image

from .. import catalog, config, system, uploads
from ..i18n import tr
from ..jobs import Job, JobFailed
from . import llm, media, sdcpp

PIXELS = {"480p": 832 * 480, "720p": 1280 * 704}
SECONDS = {3: 73, 5: 121, 8: 193}  # LTX frame counts are 8k + 1
STAGES = [  # stdout marker -> (progress, label); labels are tr() keys
    ("[Loading text encoder", 5, "正在加载模型"),
    ("[Encoding prompt", 10, "正在理解描述"),
    ("[Loading transformer", 14, "正在加载视频模型"),
    ("[estimate] denoising", 18, "正在生成画面与声音"),
    ("[Loading decoders", 82, "正在解码视频"),
    ("[Decoding video", 86, "正在合成视频与声音"),
]
# Sigma schedule of the LTX-2 distilled checkpoints (8 steps, no CFG).
DISTILLED_SIGMAS = "1.0,0.99375,0.9875,0.98125,0.975,0.909375,0.725,0.421875,0.0"


def _source_description(ref) -> str:
    """What an image from the library was generated from (text + styles), if known."""
    if not isinstance(ref, dict) or not ref.get("library"):
        return ""
    try:
        meta = json.loads((config.LIBRARY_DIR / str(ref["library"]) / "job.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    params = meta.get("params") or {}
    styles = "、".join(params.get("styles") or [])
    return (str(params.get("text", "")) + (f"（风格：{styles}）" if styles else ""))[:300]


def _size(aspect: float, budget: int) -> tuple[int, int]:
    h = (budget / aspect) ** 0.5
    w = h * aspect
    return max(256, int(w) // 32 * 32), max(256, int(h) // 32 * 32)


async def generate(job: Job) -> dict:
    p = job.params
    text = str(p.get("text", "")).strip()
    if not text:
        raise JobFailed(tr("请描述想看到的画面和动作"))
    mem = system.memory_gb()
    if system.tier(mem) == "16":
        raise JobFailed(tr("视频生成需要 24 GB 以上内存，这台电脑暂不支持"))
    model = catalog.model_path("video.ltx25")
    if not catalog.installed("video.ltx25"):
        raise JobFailed(tr("视频模型未安装，请在设置里下载"))
    seconds = int(p.get("seconds", 5)) if int(p.get("seconds", 5)) in SECONDS else 5
    resolution = p.get("resolution") if p.get("resolution") in PIXELS else "480p"
    seed = int(p.get("seed") or random.randint(1, 2**31 - 1))
    job.title = text[:16]
    job.params = {**p, "seed": seed}
    job.dir.mkdir(parents=True, exist_ok=True)

    prompt = text
    if p.get("enhance", True) and catalog.installed("llm.writer"):
        job.update(2, tr("正在补充镜头描述"))
        prompt = await llm.video_prompt(job, text, bool(p.get("source")), _source_description(p.get("source")))
        (job.dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    aspect, first = 16 / 9, None
    if p.get("source"):
        src = uploads.resolve(p["source"])
        first = job.dir / "first-frame.png"
        with Image.open(src) as im:
            im = im.convert("RGB")
            aspect = im.width / im.height
            im.save(first)
        job.title = tr("动起来 · {text}", text=text[:12])
    width, height = _size(aspect, PIXELS[resolution])
    job.save()
    out = job.dir / "video.mp4"
    if config.DIFFUSION_ENGINE == "sdcpp":
        await _generate_sdcpp(job, prompt, seconds, width, height, seed, first)
    else:
        await _generate_mlx(job, model, prompt, seconds, width, height, seed, first, mem)
    if not out.exists():
        raise JobFailed(tr("生成完成，但没有找到视频"))
    return {"video": "video.mp4", "duration": await media.probe_duration(out), "width": width, "height": height,
            "poster": "first-frame.png" if first else None, "prompt": prompt}


async def _generate_sdcpp(job: Job, prompt, seconds, width, height, seed, first) -> None:
    raw = job.dir / "video.webm"
    args = [*sdcpp.base_args(), "-M", "vid_gen", "--diffusion-model", catalog.part("video.ltx25", "diffusion"),
            "--llm", catalog.part("video.ltx25", "llm"), "--vae", catalog.part("video.ltx25", "vae"),
            "--audio-vae", catalog.part("video.ltx25", "audioVae"), "--cfg-scale", "1.0", "--steps", 8,
            "--sampling-method", "euler", "--sigmas", DISTILLED_SIGMAS, "--video-frames", SECONDS[seconds],
            # Weights wait in RAM so the VAE decode has the GPU to itself, and 12×12-latent tiles
            # (384 px) keep that decode within a few GB: with the defaults a 720p clip needed ~20 GB.
            "--fps", 24, "--offload-to-cpu", "--vae-tiling", "--vae-tile-size", "12x12", "--temporal-tiling",
            "-p", prompt, "-W", width, "-H", height, "-s", seed,
            "-o", raw]
    if first:
        args += ["-i", first]
    expected = 240 * (seconds / 5) * (width * height / PIXELS["480p"]) ** 1.2
    await sdcpp.run(job, args, steps=8, expected=expected, span=(18, 85), label="正在生成画面与声音",
                    decode_label="正在解码视频", log_name="ltx.log")
    if not raw.exists():
        raise JobFailed(tr("生成完成，但没有找到视频"))
    job.update(92, tr("正在合成视频与声音"))
    await job.run([config.FFMPEG, "-y", "-v", "error", "-i", raw, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", job.dir / "video.mp4"],
                  log_name="ffmpeg.log")
    raw.unlink(missing_ok=True)


async def _generate_mlx(job: Job, model, prompt, seconds, width, height, seed, first, mem) -> None:
    cmd = [*config.engine_cmd("ltx-2-mlx"), "generate", "--distilled", "--model", model.parent, "--prompt", prompt,
           "--frames", SECONDS[seconds], "--frame-rate", "24", "--seed", seed, "--output", job.dir / "video.mp4",
           "--width", width, "--height", height]
    if first:
        cmd += ["--image", first]
    env = {}
    if system.tier(mem) == "32":
        cmd.append("--low-ram")
        env["LTX2_VAE_DECODE_BUDGET_GB"] = str(max(8, int(mem * 0.4)))

    base = 90 * (seconds / 5) * (width * height / PIXELS["480p"]) ** 1.2
    expected = base * (1.5 if first else 1.0)
    start = time.time()

    def on_line(line: str) -> None:
        for marker, prog, label in STAGES:
            if line.startswith(marker):
                job.update(prog, tr(label))

    async def tick():
        while True:
            await asyncio.sleep(1)
            if 18 <= job.progress < 82:  # denoising has no step output: interpolate by time
                frac = min(0.95, (time.time() - start) / (expected * 0.8))
                job.update(18 + 64 * frac, tr("正在生成画面与声音"))

    ticker = asyncio.create_task(tick())
    try:
        await job.run(cmd, log_name="ltx.log", on_line=on_line, env=env)
    finally:
        ticker.cancel()
