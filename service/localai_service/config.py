"""Paths and runtime settings.

Every location can be overridden with an environment variable so the packaged app
(Tauri sidecar) and the development checkout share the same code. The defaults point
at the development checkout.
"""
import os
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent.parent


def _path(env: str, default: Path) -> Path:
    value = os.environ.get(env)
    return Path(value).expanduser().resolve() if value else default


DATA_DIR = _path("LOCALAI_DATA_DIR", REPO_DIR / "runtime" / "app-data")
LIBRARY_DIR = DATA_DIR / "library"
MODELS_DIR = _path("LOCALAI_MODELS_DIR", REPO_DIR / "models")
ASSETS_DIR = PACKAGE_DIR / "assets"

# Native engines. audio.cpp resolves its bundled VAD assets relative to its checkout,
# so it runs with that directory as the working directory.
IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"

AUDIOCPP_ROOT = _path("LOCALAI_AUDIOCPP_ROOT", REPO_DIR / "music" / "audio.cpp-latest")
AUDIOCPP_CLI = _path("LOCALAI_AUDIOCPP_CLI", AUDIOCPP_ROOT / "build" / "macos-metal-release" / "bin" / "audiocpp_cli")
LLAMA_COMPLETION = _path("LOCALAI_LLAMA_COMPLETION", REPO_DIR / "engines" / "llama.cpp" / "build" / "bin" / "llama-completion")
MFLUX_BIN = _path("LOCALAI_MFLUX_BIN", REPO_DIR / "image" / "mflux-venv" / "bin")
LTX_BIN = _path("LOCALAI_LTX_BIN", REPO_DIR / "video" / "ltx-2-mlx" / ".venv" / "bin" / "ltx-2-mlx")
SDCPP_CLI = _path("LOCALAI_SDCPP_CLI", REPO_DIR / "image" / "stable-diffusion.cpp" / "build" / "bin" / "sd-cli")
# Image and video engine family: MLX (mflux, ltx-2-mlx) on Apple Silicon, stable-diffusion.cpp
# (Vulkan/CUDA) everywhere else. LOCALAI_DIFFUSION_ENGINE=sdcpp exercises the Windows path on a Mac.
DIFFUSION_ENGINE = os.environ.get("LOCALAI_DIFFUSION_ENGINE") or ("mlx" if IS_MAC else "sdcpp")
# Packaged app: mflux and ltx-2-mlx live in the same runtime as this service and are
# started through localai_service.entry instead of per-venv bin/ wrappers.
BUNDLED = os.environ.get("LOCALAI_BUNDLED") == "1"


def engine_cmd(script: str) -> list:
    """Command prefix for a Python engine CLI (mflux-*, ltx-2-mlx)."""
    if BUNDLED:
        return [sys.executable, "-m", "localai_service.entry", script]
    if script == "ltx-2-mlx":
        return [LTX_BIN]
    return [MFLUX_BIN / script]
UPLOADS_DIR = DATA_DIR / "uploads"
FFMPEG = os.environ.get("LOCALAI_FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("LOCALAI_FFPROBE", "ffprobe")

HOST = "127.0.0.1"
PORT = int(os.environ.get("LOCALAI_PORT", "4318"))
# Shared secret between the desktop shell and this service. Empty disables the check
# (development only; the Tauri shell always sets it).
TOKEN = os.environ.get("LOCALAI_TOKEN", "")
ALLOWED_ORIGINS = {
    o.strip()
    for o in os.environ.get(
        "LOCALAI_ALLOWED_ORIGINS",
        "tauri://localhost,http://tauri.localhost,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
}

# GPU backend passed to audio.cpp; the Windows build ships the Vulkan binaries.
AUDIOCPP_BACKEND = os.environ.get("LOCALAI_GPU_BACKEND") or ("metal" if IS_MAC else "vulkan")


def ensure_dirs() -> None:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
