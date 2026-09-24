# Third-party notices

TopLocal Studio is licensed under the Apache License 2.0 (see `LICENSE`). The installers
bundle the following programs, each under its own license. Their license files are
shipped next to the binaries inside the installed app.

| Component | Used for | License |
| --- | --- | --- |
| [audio.cpp](https://github.com/0xShug0/audio.cpp) | music, speech recognition, text to speech | Apache-2.0 |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | lyric and prompt writer | MIT |
| [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) | images and video (Windows) | MIT |
| [mflux](https://github.com/filipstrand/mflux) | images (macOS) | MIT |
| [ltx-2-mlx](https://github.com/dgrauet/ltx-2-mlx) | video (macOS) | MIT |
| [MLX](https://github.com/ml-explore/mlx) | macOS inference | MIT |
| [FFmpeg](https://ffmpeg.org) (build from [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)) | audio and video encoding | GPL-3.0 (separate executable) |
| [CPython](https://www.python.org) ([python-build-standalone](https://github.com/astral-sh/python-build-standalone)) | service runtime | PSF-2.0 |
| [Tauri](https://tauri.app), [React](https://react.dev), [Phosphor Icons](https://phosphoricons.com) | desktop shell and UI | MIT / Apache-2.0 |

## Models

Models are not bundled. They are downloaded on demand from Hugging Face, and the app
shows each model's license before download. Some licenses restrict use:

| Model | License |
| --- | --- |
| Z-Image-Turbo, FLUX.2 klein 4B, Qwen3 (ASR, TTS, writer), Kokoro | Apache-2.0 |
| ACE-Step 1.5 | MIT |
| YuE2 | CC BY-NC 4.0 (non-commercial) |
| FLUX.2 klein 9B | FLUX Non-Commercial License |
| LTX-2.5 | LTX-2.x Community License |
| SenseVoice Small | FunASR Model License |
