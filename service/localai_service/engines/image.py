"""Image module: Z-Image-Turbo for text-to-image, FLUX.2 klein for editing and the fast tier.

On Apple Silicon the models run through mflux (MLX) in low-RAM mode, which in the benchmark
kept speed while cutting peak memory by 50–70 %. Elsewhere they run as GGUF through
stable-diffusion.cpp.
"""
import asyncio
import random
import re
import time

from PIL import Image

from .. import catalog, config, system, uploads
from ..i18n import tr
from ..jobs import Job, JobFailed
from . import sdcpp

ASPECTS = {  # ~1 MP, multiples of 16
    "1:1": (1024, 1024), "4:3": (1152, 864), "3:4": (864, 1152),
    "16:9": (1280, 720), "9:16": (720, 1280),
}
STYLE_PROMPTS = {
    "写实照片": "photorealistic photograph, natural light, high detail",
    "插画": "clean digital illustration, soft colors",
    "动漫": "anime style illustration",
    "3D": "3D render, soft studio lighting",
    "水墨": "Chinese ink wash painting style",
    "海报": "graphic poster design, bold typography, clean layout",
    "电影感": "cinematic still, dramatic lighting, shallow depth of field",
}


def _prompt(text: str, styles: list[str]) -> str:
    extras = [STYLE_PROMPTS[s] for s in styles if s in STYLE_PROMPTS]
    return text + ("。" + ", ".join(extras) if extras else "")


def _prepare_source(src, dest, max_pixels=1024 * 1024) -> tuple[int, int]:
    """Flatten to RGB PNG around 1 MP with sides divisible by 16; returns the new size."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, (max_pixels / (w * h)) ** 0.5)
        nw, nh = max(256, int(w * scale) // 16 * 16), max(256, int(h * scale) // 16 * 16)
        im.resize((nw, nh), Image.LANCZOS).save(dest)
    return nw, nh


def _sdcpp_model(model_id: str) -> list:
    return [*sdcpp.base_args(), "--diffusion-model", catalog.part(model_id, "diffusion"),
            "--vae", catalog.part(model_id, "vae"), "--llm", catalog.part(model_id, "llm")]


async def _run_mflux(job: Job, cmd: list, steps: int, expected: float) -> None:
    start = time.time()

    def on_line(line: str) -> None:
        m = re.search(r"(\d+)/(\d+) \[", line)  # tqdm step counter
        if m and int(m.group(2)) == steps:
            job.update(15 + 80 * int(m.group(1)) / steps, tr("正在绘制"))

    async def tick():
        while True:
            await asyncio.sleep(1)
            frac = min(0.95, (time.time() - start) / expected)
            if job.progress < 15:
                job.update(3 + 12 * frac / 0.3 if frac < 0.3 else 14, tr("正在加载模型"))

    ticker = asyncio.create_task(tick())
    try:
        await job.run(cmd, log_name="mflux.log", on_line=on_line)
    finally:
        ticker.cancel()


async def generate(job: Job) -> dict:
    p = job.params
    text = str(p.get("text", "")).strip()
    if not text:
        raise JobFailed(tr("请先描述你想要的画面"))
    styles = [str(s) for s in p.get("styles", [])][:3]
    width, height = ASPECTS.get(p.get("aspect"), ASPECTS["1:1"])
    seed = int(p.get("seed") or random.randint(1, 2**31 - 1))
    fast = p.get("quality") == "fast"
    model_id = "image.klein4b" if fast else "image.zimage"
    if not catalog.installed(model_id):
        raise JobFailed(tr("图片模型未安装，请在设置里下载"))
    job.title = text[:16]
    job.params = {**p, "seed": seed}
    out = job.dir / "image.png"
    if config.DIFFUSION_ENGINE == "sdcpp":
        steps = 4 if fast else 8
        job.dir.mkdir(parents=True, exist_ok=True)
        await sdcpp.run(job, [*_sdcpp_model(model_id), "--cfg-scale", "1.0", "--steps", steps,
                              *(["--sampling-method", "euler"] if fast else []),
                              "-p", _prompt(text, styles), "-W", width, "-H", height, "-s", seed, "-o", out],
                        steps=steps, expected=20 if fast else 40)
        if not out.exists():
            raise JobFailed(tr("生成完成，但没有找到图片"))
        return {"image": "image.png", "width": width, "height": height, "model": model_id}
    model_dir = catalog.model_path(model_id).parent
    if fast:
        cmd = [*config.engine_cmd("mflux-generate-flux2"), "--model", model_dir, "--base-model", "flux2-klein-4b",
               "--steps", "4"]
        steps, expected = 4, 15
    else:
        cmd = [*config.engine_cmd("mflux-generate-z-image-turbo"), "--model", model_dir, "--steps", "8"]
        steps, expected = 8, 40
    cmd += ["--prompt", _prompt(text, styles), "--width", width, "--height", height, "--seed", seed,
            "--low-ram", "--output", out]
    await _run_mflux(job, cmd, steps, expected)
    if not out.exists():
        raise JobFailed(tr("生成完成，但没有找到图片"))
    return {"image": "image.png", "width": width, "height": height, "model": model_id}


async def edit(job: Job) -> dict:
    p = job.params
    text = str(p.get("text", "")).strip()
    if not text:
        raise JobFailed(tr("请描述想怎么修改这张图"))
    source = uploads.resolve(p.get("source"))
    # klein 9B edits best but needs the 24–32 GB class; 16 GB machines use klein 4B.
    big = system.tier(system.memory_gb()) != "16" and catalog.installed("image.klein9b")
    model_id = "image.klein9b" if big else "image.klein4b"
    if not catalog.installed(model_id):
        raise JobFailed(tr("图片编辑模型未安装，请在设置里下载"))
    seed = int(p.get("seed") or random.randint(1, 2**31 - 1))
    job.title = tr("编辑 · {text}", text=text[:12])
    job.params = {**p, "seed": seed}
    job.dir.mkdir(parents=True, exist_ok=True)
    src = job.dir / "source.png"
    width, height = _prepare_source(source, src)
    out = job.dir / "image.png"
    if config.DIFFUSION_ENGINE == "sdcpp":
        await sdcpp.run(job, [*_sdcpp_model(model_id), "-r", src, "--cfg-scale", "1.0", "--steps", 4,
                              "--sampling-method", "euler", "-p", text, "-W", width, "-H", height, "-s", seed,
                              "-o", out], steps=4, expected=60 if big else 30)
        if not out.exists():
            raise JobFailed(tr("编辑完成，但没有找到图片"))
        return {"image": "image.png", "source": "source.png", "width": width, "height": height, "model": model_id}
    model_dir = catalog.model_path(model_id)
    cmd = [*config.engine_cmd("mflux-generate-flux2-edit"), "--image-paths", src, "--model", model_dir.parent,
           "--base-model", "flux2-klein-9b" if big else "flux2-klein-4b", "--steps", "4",
           "--prompt", text, "--width", width, "--height", height, "--seed", seed, "--low-ram", "--output", out]
    await _run_mflux(job, cmd, 4, 40 if big else 22)
    if not out.exists():
        raise JobFailed(tr("编辑完成，但没有找到图片"))
    return {"image": "image.png", "source": "source.png", "width": width, "height": height, "model": model_id}
