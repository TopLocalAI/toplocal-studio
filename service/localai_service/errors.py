"""Plain-language messages for engine failures.

Engines fail for reasons that are about the computer, not the app: the GPU runs out of
memory, a driver resets, the disk fills up. The raw engine output means nothing to users,
so it stays in the job's logs (and in "copy error details") while the UI gets a short
explanation of what happened and what to try.
"""
import re
from pathlib import Path

from .i18n import tr

# (kind, pattern over the error text and the engine's stderr), most specific first.
_KINDS = [
    ("disk", r"no space left on device|ENOSPC|disk full|磁盘已满"),
    ("cpu", r"3221225501|0xC000001D|illegal instruction|STATUS_ILLEGAL_INSTRUCTION"),
    ("driver", r"ErrorDeviceLost|DEVICE_LOST|device lost|VK_ERROR_DEVICE_LOST|kIOGPUCommandBufferCallbackErrorHang"
               r"|\bTDR\b|display driver.*stopped responding"),
    ("no_gpu", r"vulkan-1\.dll|no vulkan devices|failed to initialize vulkan|ErrorIncompatibleDriver"
               r"|VK_ERROR_INCOMPATIBLE_DRIVER|no suitable (gpu|device)"),
    ("vram", r"out of (device|video) memory|ErrorOutOfDeviceMemory|OutOfDeviceMemory|CUDA out of memory"
             r"|cannot make enough memory available|failed during weight preparation"
             r"|device memory allocation of size .* failed|Requested buffer size exceeds"
             r"|kIOGPUCommandBufferCallbackErrorOutOfMemory|Insufficient Memory"
             r"|(vae|decode|encode) (decode |encode )?compute failed|failed to allocate .* buffer"),
    ("ram", r"std::bad_alloc|MemoryError|cannot allocate memory|out of host memory|ErrorOutOfHostMemory"
            r"|exited with -9\b|exited with 137\b|\bkilled\b"),
]

_ADVICE = {
    "video": "可以把清晰度调到 480p 或缩短时长后再试，",
    "image": "可以换成标准清晰度或更小的模型后再试，",
    "music": "可以缩短歌曲时长后再试，",
    "speech": "",
}


def classify(text: str) -> str | None:
    for kind, pattern in _KINDS:
        if re.search(pattern, text, re.I):
            return kind
    return None


def _engine_output(job_dir: Path) -> str:
    """The last lines of every engine's stderr for this job."""
    parts = []
    for err in sorted(job_dir.glob("*.err")) if job_dir.exists() else []:
        parts.append("\n".join(err.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]))
    return "\n".join(parts)


def friendly(module: str, job_dir: Path, exc: BaseException) -> str:
    kind = classify(f"{exc}\n{_engine_output(job_dir)}")
    advice = tr(_ADVICE.get(module, "")) if _ADVICE.get(module) else ""
    if kind == "vram":
        return tr("显卡显存不够用了：这次生成需要的显存超过了显卡当前能提供的。{advice}"
                  "也可以关掉游戏、视频等占用显卡的程序。", advice=advice)
    if kind == "ram":
        return tr("电脑内存不够用了。{advice}也可以关掉一些正在运行的程序后再试。", advice=advice)
    if kind == "disk":
        return tr("磁盘空间不足，结果没法保存。请清理一些空间后再试。")
    if kind == "driver":
        return tr("显卡驱动中途停止了响应。请重试一次；如果经常出现，建议更新显卡驱动或重启电脑。")
    if kind == "no_gpu":
        return tr("没有找到可用的显卡加速。请安装显卡厂商的最新驱动（NVIDIA、AMD 或 Intel）后再试。")
    if kind == "cpu":
        return tr("这台电脑的处理器暂时不支持这个功能，我们正在适配。")
    return tr("这次生成没有成功，可能是电脑资源暂时紧张。请再试一次；如果仍然失败，点“复制错误详情”发给我们。")
