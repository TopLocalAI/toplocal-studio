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
HD_ASPECTS = {  # ~2 MP, multiples of 16
    "1:1": (1440, 1440), "4:3": (1664, 1248), "3:4": (1248, 1664),
    "16:9": (1920, 1088), "9:16": (1088, 1920),
}
HD_TIME = 2.2  # rough slowdown of a ~2 MP image over ~1 MP


def _hd(p: dict) -> bool:
    return p.get("size") == "hd"
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


# Keeps fp16 attention and linear layers from overflowing (sd.cpp docs/troubleshooting.md).
SAFE_SCALE = ["--attn-scale", "0.0078125", "--linear-scale", "0.0078125"]
# ~2 MP decodes in one piece misbehave on Vulkan (blank pictures, seams across the middle);
# decoding in small overlapping tiles avoids the large kernels and costs little.
HD_DECODE = ["--vae-tiling"]


def _flat(path) -> bool:
    """True when the engine produced a blank (all white or all black) picture."""
    with Image.open(path) as im:
        lo, hi = im.convert("L").getextrema()
    return hi - lo < 4


async def _run_sdcpp_checked(job: Job, args: list, out, *, hd: bool, steps: int, expected: float) -> None:
    """Run sd-cli; if the picture comes out blank, retry once the safest way: overflow-safe
    scaling, tiled decode and no flash attention."""
    await sdcpp.run(job, [*args, *(HD_DECODE if hd else [])], steps=steps, expected=expected)
    if out.exists() and _flat(out):
        out.unlink()
        safe = [a for a in args if a != "--diffusion-fa"]
        await sdcpp.run(job, [*safe, *SAFE_SCALE, *HD_DECODE], steps=steps, expected=expected * 1.5, label="正在重新绘制")
    if out.exists() and _flat(out):
        raise JobFailed(tr("生成的图片是空白的，请换个提示词或改用标准清晰度再试"))


def _prepare_source(src, dest, max_pixels=1024 * 1024, multiple=16) -> tuple[int, int]:
    """Flatten to RGB PNG of at most `max_pixels` with sides divisible by `multiple`; returns the new size."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(1.0, (max_pixels / (w * h)) ** 0.5)
        nw, nh = max(256, int(w * scale) // multiple * multiple), max(256, int(h * scale) // multiple * multiple)
        im.resize((nw, nh), Image.LANCZOS).save(dest)
    return nw, nh


KLEIN = {"image.klein4b": "flux2-klein-4b", "image.klein9b": "flux2-klein-9b"}  # model id → mflux base model
QWEN = "image.qwen21"  # stable-diffusion.cpp on every platform; sides must be multiples of 32


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
    hd = _hd(p)
    sizes = HD_ASPECTS if hd else ASPECTS
    width, height = sizes.get(p.get("aspect"), sizes["1:1"])
    slow = HD_TIME if hd else 1
    seed = int(p.get("seed") or random.randint(1, 2**31 - 1))
    # Older clients send quality=fast instead of a model.
    requested = p.get("model") or ("image.klein4b" if p.get("quality") == "fast" else None)
    model_id = catalog.task_model("image.generate", requested, system.memory_gb())
    klein = model_id in KLEIN
    qwen = model_id == QWEN
    if not catalog.installed(model_id):
        raise JobFailed(tr("图片模型未安装，请在设置里下载"))
    job.title = text[:16]
    job.params = {**p, "seed": seed, "model": model_id}
    out = job.dir / "image.png"
    if config.DIFFUSION_ENGINE == "sdcpp" or qwen:
        steps = 4 if klein or qwen else 8
        if qwen:
            width, height = width // 32 * 32, height // 32 * 32
        expected = 80 if qwen else 20 if model_id == "image.klein4b" else 40
        job.dir.mkdir(parents=True, exist_ok=True)
        await _run_sdcpp_checked(job, [*_sdcpp_model(model_id), "--cfg-scale", "1.0", "--steps", steps,
                                       *(["--sampling-method", "euler"] if klein or qwen else []),
                                       "-p", _prompt(text, styles), "-W", width, "-H", height, "-s", seed, "-o", out],
                                 out, hd=hd, steps=steps, expected=expected * slow)
        if not out.exists():
            raise JobFailed(tr("生成完成，但没有找到图片"))
        return {"image": "image.png", "width": width, "height": height, "model": model_id}
    model_dir = catalog.model_path(model_id).parent
    if klein:
        cmd = [*config.engine_cmd("mflux-generate-flux2"), "--model", model_dir, "--base-model", KLEIN[model_id],
               "--steps", "4"]
        steps, expected = 4, 15 if model_id == "image.klein4b" else 35
    else:
        cmd = [*config.engine_cmd("mflux-generate-z-image-turbo"), "--model", model_dir, "--steps", "8"]
        steps, expected = 8, 40
    cmd += ["--prompt", _prompt(text, styles), "--width", width, "--height", height, "--seed", seed,
            "--low-ram", "--output", out]
    await _run_mflux(job, cmd, steps, expected * slow)
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
    model_id = catalog.task_model("image.edit", p.get("model"), system.memory_gb())
    big = model_id == "image.klein9b"
    qwen = model_id == QWEN
    if not catalog.installed(model_id):
        raise JobFailed(tr("图片编辑模型未安装，请在设置里下载"))
    seed = int(p.get("seed") or random.randint(1, 2**31 - 1))
    job.title = tr("编辑 · {text}", text=text[:12])
    job.params = {**p, "seed": seed, "model": model_id}
    job.dir.mkdir(parents=True, exist_ok=True)
    src = job.dir / "source.png"
    hd = _hd(p)
    slow = HD_TIME if hd else 1
    width, height = _prepare_source(source, src, max_pixels=(1440 * 1440) if hd else 1024 * 1024,
                                    multiple=32 if qwen else 16)
    out = job.dir / "image.png"
    if config.DIFFUSION_ENGINE == "sdcpp" or qwen:
        vision = ["--llm_vision", catalog.part(model_id, "vision")] if qwen else []
        expected = 100 if qwen else 60 if big else 30
        await _run_sdcpp_checked(job, [*_sdcpp_model(model_id), *vision, "-r", src, "--cfg-scale", "1.0", "--steps", 4,
                                       "--sampling-method", "euler", "-p", text, "-W", width, "-H", height, "-s", seed,
                                       "-o", out], out, hd=hd, steps=4, expected=expected * slow)
        if not out.exists():
            raise JobFailed(tr("编辑完成，但没有找到图片"))
        return {"image": "image.png", "source": "source.png", "width": width, "height": height, "model": model_id}
    model_dir = catalog.model_path(model_id)
    cmd = [*config.engine_cmd("mflux-generate-flux2-edit"), "--image-paths", src, "--model", model_dir.parent,
           "--base-model", KLEIN[model_id], "--steps", "4",
           "--prompt", text, "--width", width, "--height", height, "--seed", seed, "--low-ram", "--output", out]
    await _run_mflux(job, cmd, 4, (40 if big else 22) * slow)
    if not out.exists():
        raise JobFailed(tr("编辑完成，但没有找到图片"))
    return {"image": "image.png", "source": "source.png", "width": width, "height": height, "model": model_id}
