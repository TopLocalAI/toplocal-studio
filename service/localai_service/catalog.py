"""Model catalog: what each feature needs, where the files live, and the memory floor.

Sizes and memory floors come from the measurements in results/*-benchmark.md.
`needsToken` marks models whose Hugging Face repo is gated: the user accepts the license on
`licensePage` and saves an access token first. `files` are relative to config.MODELS_DIR; the first existing entry of a `choices`
list is used, so a better build can replace a fallback without code changes.
"""
from . import config
from .i18n import tr
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
        "id": "music.ace", "short": "ACE-Step 1.5",
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
        "id": "music.yue2", "short": "YuE2 3B",
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
    {"id": "speech.asr", "short": "Qwen3-ASR 0.6B", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Qwen3-ASR-0.6B-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Qwen3-ASR-0.6B-GGUF"}], "module": "speech", "name": "Qwen3-ASR 0.6B", "engine": "audio.cpp",
     "files": ["audio/Qwen3-ASR-0.6B-GGUF/qwen3-asr-0.6b-q8_0.gguf"], "sizeBytes": int(1.2 * GB), "license": "Apache-2.0"},
    {"id": "speech.asr-hq", "short": "Qwen3-ASR 1.7B", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Qwen3-ASR-1.7B-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Qwen3-ASR-1.7B-GGUF"}], "module": "speech", "name": "Qwen3-ASR 1.7B", "engine": "audio.cpp",
     "files": ["audio/Qwen3-ASR-1.7B-GGUF/qwen3-asr-1.7b-q8_0.gguf"], "sizeBytes": int(2.5 * GB), "license": "Apache-2.0"},
    {"id": "speech.asr-fast", "short": "SenseVoice", "sources": [{"repo": "FunAudioLLM/SenseVoiceSmall-GGUF-audiocpp", "include": r"\.gguf$", "dest": "audio/sensevoice-small"}], "module": "speech", "name": "SenseVoice Small（极速识别）", "engine": "audio.cpp",
     "files": ["audio/sensevoice-small/sensevoice-small-q8-audiocpp-v1.gguf"], "sizeBytes": int(0.25 * GB),
     "license": "FunASR Model License"},
    {"id": "speech.tts-fast", "short": "Kokoro", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Kokoro-82M-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Kokoro-82M-GGUF"}], "module": "speech", "name": "Kokoro 82M（快速配音）", "engine": "audio.cpp",
     "files": ["audio/Kokoro-82M-GGUF/kokoro-82m-q8_0.gguf"], "sizeBytes": int(0.2 * GB), "license": "Apache-2.0"},
    {"id": "speech.tts", "short": "Qwen3-TTS", "sources": [{"repo": "audio-cpp/audio.cpp-gguf", "sub": "Qwen3-TTS-12Hz-0.6B-Base-GGUF", "include": r"q8_0\.gguf$", "dest": "audio/Qwen3-TTS-12Hz-0.6B-Base-GGUF"}], "module": "speech", "name": "Qwen3-TTS 0.6B", "engine": "audio.cpp",
     "files": ["audio/Qwen3-TTS-12Hz-0.6B-Base-GGUF/qwen3-tts-12hz-0.6b-base-q8_0.gguf"], "sizeBytes": int(2.0 * GB),
     "license": "Apache-2.0"},
]

# Qwen-Image 2.1 (Viggle 4-step turbo, GGUF) runs on stable-diffusion.cpp on every platform:
# about 75 s per image on an M5 Pro, generate and edit. `vision` is only needed for editing.
QWEN21 = {
    "id": "image.qwen21", "short": "Qwen-Image 2.1", "module": "image", "name": "Qwen-Image 2.1 Turbo",
    "engine": "stable-diffusion.cpp",
    "sources": [{"repo": "Abiray/Qwen-Image-2.1-viggle-4-steps-turbo-GGUF", "include": r"^qwen_image_2\.1_turbo_Q4_K_M\.gguf$", "dest": "image/qwen21"},
                {"repo": "Comfy-Org/Qwen-Image-2.1", "sub": "vae", "include": r"^qwen_image_2\.1_vae_bf16\.safetensors$", "dest": "image/qwen21"},
                {"repo": "Qwen/Qwen3-VL-8B-Instruct-GGUF", "include": r"^(Qwen3VL-8B-Instruct-Q4_K_M|mmproj-Qwen3VL-8B-Instruct-Q8_0)\.gguf$", "dest": "image/qwen21"}],
    "parts": {"diffusion": "image/qwen21/qwen_image_2.1_turbo_Q4_K_M.gguf",
              "vae": "image/qwen21/qwen_image_2.1_vae_bf16.safetensors",
              "llm": "image/qwen21/Qwen3VL-8B-Instruct-Q4_K_M.gguf",
              "vision": "image/qwen21/mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf"},
    "sizeBytes": int(10.7 * GB), "license": "Qwen Research License",
    "licenseUrl": "https://huggingface.co/Qwen/Qwen-Image-2.1",
    "licenseNote": "Qwen-Image 2.1 采用通义千问研究许可证：仅限研究和非商业用途。",
}

# Image and video models exist per diffusion engine under the same ids, so the UI and the
# feature list do not care which engine runs them.
MLX_MODELS = [
    {"id": "image.zimage", "short": "Z-Image", "sources": [{"repo": "filipstrand/Z-Image-Turbo-mflux-4bit", "exclude": r"\.(png|jpg)$", "dest": "image/mlx/z-image-turbo-4bit"}], "module": "image", "name": "Z-Image-Turbo", "engine": "mflux",
     "files": ["image/mlx/z-image-turbo-4bit/transformer"], "sizeBytes": int(5.5 * GB), "license": "Apache-2.0"},
    {"id": "image.klein9b", "short": "klein 9B", "sources": [{"repo": "mflux-community/flux2-klein-9b-mflux-q4", "dest": "image/mlx/flux2-klein-9b-q4"}], "module": "image", "name": "FLUX.2 klein 9B", "engine": "mflux",
     "files": ["image/mlx/flux2-klein-9b-q4/transformer"], "sizeBytes": int(8.9 * GB), "license": "FLUX Non-Commercial",
     "licenseUrl": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B", "licenseNote": "FLUX.2 klein 9B 采用 FLUX 非商用许可证：仅限个人和非商业用途。"},
    {"id": "image.klein4b", "short": "klein 4B", "sources": [{"repo": "Runpod/FLUX.2-klein-4B-mflux-4bit", "dest": "image/mlx/flux2-klein-4b-4bit"}], "module": "image", "name": "FLUX.2 klein 4B", "engine": "mflux",
     "files": ["image/mlx/flux2-klein-4b-4bit/transformer"], "sizeBytes": int(4.3 * GB), "license": "Apache-2.0"},
    {"id": "video.ltx25", "short": "LTX-2.5", "sources": [{"repo": "dgrauet/ltx-2.5-mlx-q4", "exclude": r"transformer-dev|distilled-lora", "dest": "video/ltx-2.5-mlx-q4"}], "licenseUrl": "https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2_x", "licenseNote": "LTX-2.x 社区许可证：个人和非商用免费；年收入超过 1000 万美元的公司商用需另行授权；须遵守其使用政策。", "module": "video", "name": "LTX-2.5 Distilled", "engine": "ltx-2-mlx", "needsToken": True,
     "licensePage": "https://huggingface.co/dgrauet/ltx-2.5-mlx-q4",
     "files": ["video/ltx-2.5-mlx-q4/transformer-distilled.safetensors"], "sizeBytes": int(30.5 * GB),
     "license": "LTX-2.x Community License"},
]

_LTX_NOTE = "LTX-2.x 社区许可证：个人和非商用免费；年收入超过 1000 万美元的公司商用需另行授权；须遵守其使用政策。"
_FLUX1_VAE = {"repo": "Comfy-Org/z_image_turbo", "sub": "split_files/vae", "include": r"^ae\.safetensors$", "dest": "image/sdcpp/vae-flux1"}
_FLUX2_VAE = {"repo": "Comfy-Org/flux2-dev", "sub": "split_files/vae", "include": r"^flux2-vae\.safetensors$", "dest": "image/sdcpp/vae-flux2"}
_WRITER_GGUF = {"repo": "unsloth/Qwen3-4B-Instruct-2507-GGUF", "include": r"Instruct-2507-Q4_K_M\.gguf$", "dest": "llm"}

# stable-diffusion.cpp (Windows, Vulkan). `parts` names each file the engine is given.
SDCPP_MODELS = [
    {"id": "image.zimage", "short": "Z-Image", "module": "image", "name": "Z-Image-Turbo", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "leejet/Z-Image-Turbo-GGUF", "include": r"^z_image_turbo-Q4_K\.gguf$", "dest": "image/sdcpp/z-image-turbo"},
                 _FLUX1_VAE, _WRITER_GGUF],
     "parts": {"diffusion": "image/sdcpp/z-image-turbo/z_image_turbo-Q4_K.gguf",
               "vae": "image/sdcpp/vae-flux1/ae.safetensors",
               "llm": "llm/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"},
     "sizeBytes": int(6.7 * GB), "license": "Apache-2.0"},
    {"id": "image.klein9b", "short": "klein 9B", "module": "image", "name": "FLUX.2 klein 9B", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "leejet/FLUX.2-klein-9B-GGUF", "include": r"^flux-2-klein-9b-Q4_0\.gguf$", "dest": "image/sdcpp/flux2-klein"},
                 _FLUX2_VAE, {"repo": "unsloth/Qwen3-8B-GGUF", "include": r"^Qwen3-8B-Q4_K_M\.gguf$", "dest": "image/sdcpp/text-encoders"}],
     "parts": {"diffusion": "image/sdcpp/flux2-klein/flux-2-klein-9b-Q4_0.gguf",
               "vae": "image/sdcpp/vae-flux2/flux2-vae.safetensors",
               "llm": "image/sdcpp/text-encoders/Qwen3-8B-Q4_K_M.gguf"},
     "sizeBytes": int(10.2 * GB), "license": "FLUX Non-Commercial",
     "licenseUrl": "https://huggingface.co/black-forest-labs/FLUX.2-klein-9B", "licenseNote": "FLUX.2 klein 9B 采用 FLUX 非商用许可证：仅限个人和非商业用途。"},
    {"id": "image.klein4b", "short": "klein 4B", "module": "image", "name": "FLUX.2 klein 4B", "engine": "stable-diffusion.cpp",
     "sources": [{"repo": "leejet/FLUX.2-klein-4B-GGUF", "include": r"^flux-2-klein-4b-Q4_0\.gguf$", "dest": "image/sdcpp/flux2-klein"},
                 _FLUX2_VAE, {"repo": "unsloth/Qwen3-4B-GGUF", "include": r"^Qwen3-4B-Q4_K_M\.gguf$", "dest": "image/sdcpp/text-encoders"}],
     "parts": {"diffusion": "image/sdcpp/flux2-klein/flux-2-klein-4b-Q4_0.gguf",
               "vae": "image/sdcpp/vae-flux2/flux2-vae.safetensors",
               "llm": "image/sdcpp/text-encoders/Qwen3-4B-Q4_K_M.gguf"},
     "sizeBytes": int(4.9 * GB), "license": "Apache-2.0"},
    {"id": "video.ltx25", "short": "LTX-2.5", "module": "video", "name": "LTX-2.5 Distilled（实验）", "engine": "stable-diffusion.cpp",
     "needsToken": True, "licensePage": "https://huggingface.co/Lightricks/LTX-2.5",
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

MODELS += [*(MLX_MODELS if config.DIFFUSION_ENGINE == "mlx" else SDCPP_MODELS), QWEN21]

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

# Models the user can choose from for each task, best default first. `strength` says what
# a model is good at; `minTier` overrides the model's usual memory floor for that task.
# Adding a model to a task is a catalog change here plus its handling in the engine.
TASKS = {
    "image.generate": [
        {"model": "image.zimage", "strength": "画质细腻，中英文字写得最准", "speed": "约 40 秒"},
        {"model": "image.klein4b", "strength": "速度最快，适合快速出草图，写字较弱", "speed": "约 15 秒"},
        {"model": "image.klein9b", "strength": "质感和细节更好，适合人像和写实场景", "speed": "约 40 秒", "minTier": "32"},
        {"model": "image.qwen21", "strength": "画质和排版最好，书法字和长段文字最准（仅限非商用）", "speed": "约 80 秒", "minTier": "32"},
    ],
    "image.edit": [
        {"model": "image.klein9b", "strength": "改图最准，原图细节保留最好", "speed": "约 40 秒", "minTier": "32"},
        {"model": "image.klein4b", "strength": "速度快，16 GB 电脑也能用", "speed": "约 20 秒"},
        {"model": "image.qwen21", "strength": "改字和换物体最准，其余部分几乎不动（仅限非商用）", "speed": "约 100 秒", "minTier": "32"},
    ],
    "video.generate": [
        {"model": "video.ltx25", "strength": "文字或图片生成带声音的短视频，画面稳定", "speed": "5 秒视频约 2 分钟", "minTier": "32"},
    ],
    "music.generate": [
        {"model": "music.ace", "strength": "速度快、风格多，可以设定时长，中英文都能唱", "speed": "1 分钟歌曲约 40 秒"},
        {"model": "music.yue2", "strength": "中文咬字最准，时长跟随歌词（仅限非商用）", "speed": "约 1 分钟"},
    ],
    "speech.transcribe": [
        {"model": "speech.asr", "strength": "准确又快，支持普通话、英语等多种语言", "speed": "1 小时录音约 3 分钟"},
        {"model": "speech.asr-hq", "strength": "方言和口音识别更稳，速度稍慢", "speed": "1 小时录音约 5 分钟"},
        {"model": "speech.asr-fast", "strength": "速度极快，适合很长的录音", "speed": "1 小时录音约 1 分钟"},
    ],
    "speech.synthesize": [
        {"model": "speech.tts-fast", "strength": "速度最快，中文预设音色；遇到英文自动换用 Qwen3-TTS", "speed": "几秒"},
        {"model": "speech.tts", "strength": "更自然，支持中英混读和声音克隆", "speed": "十几秒"},
    ],
}


def task_model(task: str, requested, mem_gb: float):
    """The model to use for `task`: the requested one if it is offered and fits in memory,
    else the first option that fits and is installed, else the first that fits."""
    machine = _TIER_ORDER[memory_tier(mem_gb)]
    options = [o for o in TASKS[task] if machine >= _TIER_ORDER[_option_tier(o)]]
    ids = [o["model"] for o in options]
    if requested in ids:
        return requested
    for mid in ids:
        if installed(mid):
            return mid
    return ids[0] if ids else TASKS[task][0]["model"]


def _option_tier(option: dict) -> str:
    return option.get("minTier") or "16"


def tasks_status(mem_gb: float) -> dict:
    machine = _TIER_ORDER[memory_tier(mem_gb)]
    return {
        task: [
            {"model": o["model"], "strength": tr(o["strength"]), "speed": tr(o["speed"]),
             "recommended": i == 0, "minTier": _option_tier(o),
             "supported": machine >= _TIER_ORDER[_option_tier(o)], "installed": installed(o["model"])}
            for i, o in enumerate(options)
        ]
        for task, options in TASKS.items()
    }


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


# Display fields translated at output time (the UI language can change while running).
_DISPLAY = ("name", "license", "licenseNote")


def _localized(item: dict) -> dict:
    return {k: tr(v) if k in _DISPLAY and isinstance(v, str) else v for k, v in item.items()}


def models_status() -> list[dict]:
    return [
        _localized({k: v for k, v in m.items() if k not in ("files", "choices", "sources", "parts")})
        | {"installed": installed(m["id"])}
        for m in MODELS
    ]


def features_status(mem_gb: float) -> list[dict]:
    machine = _TIER_ORDER[memory_tier(mem_gb)]
    out = []
    for f in FEATURES:
        supported = machine >= _TIER_ORDER[f["minTier"]]
        ready = supported and all(installed(m) for m in f["models"])
        out.append(_localized(f) | {"supported": supported, "ready": ready})
    return out
