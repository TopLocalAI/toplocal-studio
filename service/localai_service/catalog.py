"""Model catalog: what each feature needs, where the files live, and the memory floor.

Sizes and memory floors come from the measurements in results/*-benchmark.md.
`files` are relative to config.MODELS_DIR; the first existing entry of a `choices`
list is used, so a better build can replace a fallback without code changes.
"""
from . import config
from .system import tier as memory_tier

GB = 1024**3

MODELS = [
    {
        "id": "llm.writer",
        "sources": [{"repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF", "include": r"Instruct-2507-Q4_K_M\.gguf$", "dest": "llm"}],
        "module": "shared",
        "name": "写作助手（歌词与提示词）",
        "engine": "llama.cpp",
        "files": ["llm/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"],
        "sizeBytes": int(2.5 * GB),
        "license": "Apache-2.0",
    },
    {
        "id": "music.ace",
        "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "ACE-Step1.5-GGUF", "include": r"turbo/.*q8_0\.gguf$", "dest": "music/ace-step-1.5"}],
        "module": "music",
        "name": "ACE-Step 1.5 Turbo",
        "engine": "audio.cpp",
        # Fully Q8 package: in an A/B on the Chinese benchmark song the DiT-only Q8 build
        # (planner kept at bf16) used 5.6 GB more memory and sang the lyrics less accurately.
        "choices": ["music/ace-step-1.5/turbo/ace-step-1.5-turbo-q8_0.gguf"],
        "sizeBytes": int(6.2 * GB),
        "license": "MIT",
    },
    {
        "id": "music.yue2",
        "sources": [{"repo": "audio-cpp/Yue2-3B-GGUF", "include": r"(yue2-3b-q8_0|yue2-vae-f16)\.gguf$|^sidecars/", "dest": "music/yue2-3b"}],
        "module": "music",
        "name": "YuE2 3B（中文精唱）",
        "engine": "audio.cpp",
        "files": [
            "music/yue2-3b/yue2-3b-q8_0.gguf",
            "music/yue2-3b/yue2-vae-f16.gguf",
            "music/yue2-3b/sidecars/yue2-model-config.json",
        ],
        "sizeBytes": int(4.6 * GB),
        "license": "CC BY-NC 4.0（仅限非商用）",
        "licenseUrl": "https://creativecommons.org/licenses/by-nc/4.0/",
        "licenseNote": "YuE2 采用 CC BY-NC 4.0：仅限非商业用途，生成的歌曲请勿用于商业目的。",
    },
    {"id": "speech.asr", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Qwen3-ASR-0.6B-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Qwen3-ASR-0.6B-GGUF"}], "module": "speech", "name": "Qwen3-ASR 0.6B", "engine": "audio.cpp",
     "files": ["audio/Qwen3-ASR-0.6B-GGUF/qwen3-asr-0.6b-q8_0.gguf"], "sizeBytes": int(1.2 * GB), "license": "Apache-2.0"},
    {"id": "speech.asr-hq", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Qwen3-ASR-1.7B-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Qwen3-ASR-1.7B-GGUF"}], "module": "speech", "name": "Qwen3-ASR 1.7B", "engine": "audio.cpp",
     "files": ["audio/Qwen3-ASR-1.7B-GGUF/qwen3-asr-1.7b-q8_0.gguf"], "sizeBytes": int(2.5 * GB), "license": "Apache-2.0"},
    {"id": "speech.asr-fast", "sources": [{"repo": "FunAudioLLM/SenseVoiceSmall-GGUF-audiocpp", "include": r"\.gguf$", "dest": "audio/sensevoice-small"}], "module": "speech", "name": "SenseVoice Small（极速识别）", "engine": "audio.cpp",
     "files": ["audio/sensevoice-small/sensevoice-small-q8-audiocpp-v1.gguf"], "sizeBytes": int(0.25 * GB),
     "license": "FunASR Model License"},
    {"id": "speech.tts-fast", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Kokoro-82M-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Kokoro-82M-GGUF"}], "module": "speech", "name": "Kokoro 82M（快速配音）", "engine": "audio.cpp",
     "files": ["audio/Kokoro-82M-GGUF/kokoro-82m-q8_0.gguf"], "sizeBytes": int(0.2 * GB), "license": "Apache-2.0"},
    {"id": "speech.tts", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Qwen3-TTS-12Hz-0.6B-Base-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Qwen3-TTS-12Hz-0.6B-Base-GGUF"}], "module": "speech", "name": "Qwen3-TTS 0.6B", "engine": "audio.cpp",
     "files": ["audio/Qwen3-TTS-12Hz-0.6B-Base-GGUF/qwen3-tts-12hz-0.6b-base-q8_0.gguf"], "sizeBytes": int(2.0 * GB),
     "license": "Apache-2.0"},
]

# Image and video models exist per diffusion engine under the same ids, so the UI and the
# feature list do not care which engine runs them.
MLX_MODELS = [
    {"id": "image.zimage", "sources": [{"repo": "filipstrand/Z-Image-Turbo-mflux-4bit", "exclude": r"\.(png|jpg)$", "dest": "image/mlx/z-image-turbo-4bit"}], "module": "image", "name": "Z-Image-Turbo", "engine": "mflux",
     "files": ["image/mlx/z-image-turbo-4bit/transformer"], "sizeBytes": int(5.5 * GB), "license": "Apache-2.0"},
    {"id": "image.klein9b", "sources": [{"repo": "mflux-community/flux2-klein-9b-mflux-q4", "dest": "image/mlx/flux2-klein-9b-q4"}], "module": "image", "name": "FLUX.2 klein 9B", "engine": "mflux",
     "files": ["image/mlx/flux2-klein-9b-q4/transformer"], "sizeBytes": int(8.9 * GB), "license": "FLUX Non-Commercial",
     "licenseUrl": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B", "licenseNote": "FLUX.2 klein 9B 采用 FLUX 非商用许可证：仅限个人和非商业用途。"},
    {"id": "image.klein4b", "sources": [{"repo": "Runpod/FLUX.2-klein-4B-mflux-4bit", "dest": "image/mlx/flux2-klein-4b-4bit"}], "module": "image", "name": "FLUX.2 klein 4B", "engine": "mflux",
     "files": ["image/mlx/flux2-klein-4b-4bit/transformer"], "sizeBytes": int(4.3 * GB), "license": "Apache-2.0"},
    {"id": "video.ltx25", "sources": [{"repo": "dgrauet/ltx-2.5-mlx-q4", "exclude": r"transformer-dev|distilled-lora", "dest": "video/ltx-2.5-mlx-q4"}], "licenseUrl": "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x", "licenseNote": "LTX-2.x 社区许可证：个人和非商用免费；年收入超过 1000 万美元的公司商用需另行授权；须遵守其使用政策。", "module": "video", "name": "LTX-2.5 Distilled", "engine": "ltx-2-mlx",
     "files": ["video/ltx-2.5-mlx-q4/transformer-distilled.safetensors"], "sizeBytes": int(30.5 * GB),
     "license": "LTX-2.x Community License"},
]

_LTX_NOTE = "LTX-2.x 社区许可证：个人和非商用免费；年收入超过 1000 万美元的公司商用需另行授权；须遵守其使用政策。"
_FLUX1_VAE = {"repo": "Comfy-Org/z_image_turbo", "sub": "split_files/vae", "include": r"^ae\.safetensors$", "dest": "image/sdcpp/vae-flux1"}
_FLUX2_VAE = {"repo": "Comfy-Org/flux2-dev", "sub": "split_files/vae", "include": r"^flux2-vae\.safetensors$", "dest": "image/sdcpp/vae-flux2"}
_WRITER_GGUF = {"repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF", "include": r"Instruct-2507-Q4_K_M\.gguf$", "dest": "llm"}

# stable-diffusion.cpp (Windows, Vulkan). `parts` names each file the engine is given.
SDCPP_MODELS = [
    {"id": "image.zimage", "module": "image", "name": "Z-Image-Turbo", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "leejet/Z-Image-Turbo-GGUF", "include": r"^z_image_turbo-Q4_K\.gguf$", "dest": "image/sdcpp/z-image-turbo"},
                 _FLUX1_VAE, _WRITER_GGUF],
     "parts": {"diffusion": "image/sdcpp/z-image-turbo/z_image_turbo-Q4_K.gguf",
               "vae": "image/sdcpp/vae-flux1/ae.safetensors",
               "llm": "llm/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"},
     "sizeBytes": int(6.7 * GB), "license": "Apache-2.0"},
    {"id": "image.klein9b", "module": "image", "name": "FLUX.2 klein 9B", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "leejet/FLUX.2-klein-9B-GGUF", "include": r"^flux-2-klein-9b-Q4_0\.gguf$", "dest": "image/sdcpp/flux2-klein"},
                 _FLUX2_VAE, {"repo": "unsloth/Qwen3-8B-GGUF", "include": r"^Qwen3-8B-Q4_K_M\.gguf$", "dest": "image/sdcpp/text-encoders"}],
     "parts": {"diffusion": "image/sdcpp/flux2-klein/flux-2-klein-9b-Q4_0.gguf",
               "vae": "image/sdcpp/vae-flux2/flux2-vae.safetensors",
               "llm": "image/sdcpp/text-encoders/Qwen3-8B-Q4_K_M.gguf"},
     "sizeBytes": int(10.2 * GB), "license": "FLUX Non-Commercial",
     "licenseUrl": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B", "licenseNote": "FLUX.2 klein 9B 采用 FLUX 非商用许可证：仅限个人和非商业用途。"},
    {"id": "image.klein4b", "module": "image", "name": "FLUX.2 klein 4B", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "leejet/FLUX.2-klein-4B-GGUF", "include": r"^flux-2-klein-4b-Q4_0\.gguf$", "dest": "image/sdcpp/flux2-klein"},
                 _FLUX2_VAE, {"repo": "unsloth/Qwen3-4B-GGUF", "include": r"^Qwen3-4B-Q4_K_M\.gguf$", "dest": "image/sdcpp/text-encoders"}],
     "parts": {"diffusion": "image/sdcpp/flux2-klein/flux-2-klein-4b-Q4_0.gguf",
               "vae": "image/sdcpp/vae-flux2/flux2-vae.safetensors",
               "llm": "image/sdcpp/text-encoders/Qwen3-4B-Q4_K_M.gguf"},
     "sizeBytes": int(4.9 * GB), "license": "Apache-2.0"},
    {"id": "video.ltx25", "module": "video", "name": "LTX-2.5 Distilled（实验）", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "vantagewithai/LTX-2.5-GGUF", "sub": "distilled", "include": r"distilled-transformer-Q4_K_S\.gguf$", "dest": "video/ltx-2.5-gguf"},
                 {"repo": "Lightricks/LTX-2.5", "sub": "text_encoders", "include": r"comfy-int8-convrot\.safetensors$", "dest": "video/ltx-2.5-gguf"},
                 {"repo": "Lightricks/LTX-2.5", "sub": "vae", "include": r"^ltx-2\.5-(video-vae-conv|audio-vae)-bf16\.safetensors$", "dest": "video/ltx-2.5-gguf"}],
     "parts": {"diffusion": "video/ltx-2.5-gguf/ltx-2.5-22b-distilled-transformer-Q4_K_S.gguf",
               "llm": "video/ltx-2.5-gguf/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors",
               "vae": "video/ltx-2.5-gguf/ltx-2.5-video-vae-conv-bf16.safetensors",
               "audioVae": "video/ltx-2.5-gguf/ltx-2.5-audio-vae-bf16.safetensors"},
     "sizeBytes": int(30.3 * GB), "license": "LTX-2.x Community License",
     "licenseUrl": "https://huggingface.co/Lightricks/LTX-2.5",
     "licenseNote": _LTX_NOTE + "文本编码器和解码器来自 Lightricks 官方仓库：请先登录 Hugging Face 同意许可证，并在设置里填写访问令牌。"},
]

MODELS += MLX_MODELS if config.DIFFUSION_ENGINE == "mlx" else SDCPP_MODELS

# Features the UI offers. `minTier` is the memory class that can run them (see system.tier).
FEATURES = [
    {"id": "music.standard", "module": "music", "name": "写歌 · 标准", "models": ["music.ace"], "minTier": "16"},
    {"id": "music.chinese", "module": "music", "name": "写歌 · 中文精唱", "models": ["music.yue2"], "minTier": "16"},
    {"id": "music.writer", "module": "music", "name": "一句话写词", "models": ["llm.writer"], "minTier": "16"},
    {"id": "image.create", "module": "image", "name": "文字生成图片", "models": ["image.zimage"], "minTier": "16"},
    {"id": "image.edit", "module": "image", "name": "图片编辑", "models": ["image.klein9b"], "minTier": "32"},
    {"id": "video.create", "module": "video", "name": "文字 / 图片生成视频", "models": ["video.ltx25"], "minTier": "32"},
    {"id": "speech.transcribe", "module": "speech", "name": "语音转文字", "models": ["speech.asr"], "minTier": "16"},
    {"id": "speech.synthesize", "module": "speech", "name": "文字转语音 / 声音克隆",
     "models": ["speech.tts", "speech.tts-fast"], "minTier": "16"},
]

_TIER_ORDER = {"16": 0, "32": 1, "64": 2}


def _by_id():
    return {m["id"]: m for m in MODELS}


def by_id(model_id: str):
    return _by_id().get(model_id)


def _files(model: dict) -> list[str]:
    return list(model["parts"].values()) if "parts" in model else model.get("files", [])


def part(model_id: str, name: str):
    """Path of one named file of a multi-file (stable-diffusion.cpp) model."""
    return config.MODELS_DIR / _by_id()[model_id]["parts"][name]


def model_path(model_id: str):
    """Main file of an installed model, or None."""
    model = _by_id()[model_id]
    candidates = model.get("choices") or _files(model)[:1]
    for rel in candidates:
        path = config.MODELS_DIR / rel
        if path.exists():
            return path
    return None


def installed(model_id: str) -> bool:
    model = _by_id()[model_id]
    if "choices" in model:
        return model_path(model_id) is not None
    return all((config.MODELS_DIR / rel).exists() for rel in _files(model))


def models_status() -> list[dict]:
    return [
        {k: v for k, v in m.items() if k not in ("files", "choices", "sources", "parts")} | {"installed": installed(m["id"])}
        for m in MODELS
    ]


def features_status(mem_gb: float) -> list[dict]:
    machine = _TIER_ORDER[memory_tier(mem_gb)]
    out = []
    for f in FEATURES:
        supported = machine >= _TIER_ORDER[f["minTier"]]
        ready = supported and all(installed(m) for m in f["models"])
        out.append(f | {"supported": supported, "ready": ready})
    return out
