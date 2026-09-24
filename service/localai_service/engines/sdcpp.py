"""stable-diffusion.cpp runner, used for images and video where MLX is not available.

sd-cli prints a text progress bar per sampling pass (`| 3/8 - 1.2s/it`) and INFO lines
for the loading and decoding stages; both are turned into job progress.
"""
import asyncio
import re
import time

from .. import config
from ..jobs import Job

STEP = re.compile(r"\|\s*(\d+)/(\d+)\s+-")


def base_args() -> list:
    # No --mmap: with it, sd.cpp builds before 500ef5f decode flat gray images on Metal.
    return [config.SDCPP_CLI, "--diffusion-fa"]


def env() -> dict:
    # Apple M5 tensor-API path decodes blank white images (sd.cpp #1990); harmless elsewhere.
    return {"GGML_METAL_TENSOR_DISABLE": "1"} if config.IS_MAC else {}


async def run(job: Job, args: list, *, steps: int, expected: float, span=(15, 92),
              label="正在绘制", decode_label="正在解码", log_name="sdcpp.log") -> None:
    """Run sd-cli; progress moves through `span` while sampling, then to the decode stage."""
    lo, hi = span
    start = time.time()

    def on_line(line: str) -> None:
        m = STEP.search(line)
        if m and int(m.group(2)) == steps:
            job.update(lo + (hi - lo) * int(m.group(1)) / steps, label)
        elif "sampling completed" in line:
            job.update(hi, decode_label)

    async def tick():  # model loading prints nothing useful: creep forward by time
        while True:
            await asyncio.sleep(1)
            if job.progress < lo:
                frac = min(0.95, (time.time() - start) / max(1.0, expected * 0.3))
                job.update(3 + (lo - 4) * frac, "正在加载模型")

    ticker = asyncio.create_task(tick())
    try:
        await job.run(args, log_name=log_name, on_line=on_line, env=env())
    finally:
        ticker.cancel()
