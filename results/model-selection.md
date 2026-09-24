# Local AI Desktop 模型选型（实测版）

- 测试日期：2026-09-23 至 24
- 机器：MacBook Pro M5 Pro，64 GB 统一内存
- 各模块的详细报告：
  - [图片](image-benchmark.md)
  - [视频](video-benchmark.md)
  - [音乐](music-benchmark.md)
  - [语音](audio-benchmark.md)

## 推理引擎：Mac 端只需要三套

| 引擎 | 负责的模块 | 形式 | 说明 |
|---|---|---|---|
| **audio.cpp**（Metal） | 语音识别、语音合成、声音克隆、音乐 | C++ 单个二进制，不需要 Python | 一个引擎覆盖全部音频类功能 |
| **mflux**（MLX） | 图片 | Python + MLX | 比 sd.cpp 快 3–5 倍 |
| **ltx-2-mlx**（MLX） | 视频 | Python + MLX | sd.cpp 在 Mac 上做视频不可用 |

- 两个 MLX 引擎可以共用一个内置的 Python 运行时，体积估计 300–400 MB。
- stable-diffusion.cpp 留给 Windows 用（CUDA/Vulkan），Windows 端尚未实测。

## 每个模块用哪个模型

| 模块 | 默认 | 高配 / 高质量 | 低配 / 极速 | 不采用 |
|---|---|---|---|---|
| 图片：文生图 | Z-Image-Turbo 4bit（40 s，6.3 GB，中英文字全对） | Qwen-Image-2.1（160 s，15 GB，仅限研究用途） | FLUX.2 klein 4B（11 s，写不了中文字） | — |
| 图片：编辑 | FLUX.2 klein 9B 4bit（20–40 s，12 GB） | Qwen-Image-2.1（仅 sd.cpp 有编辑功能，Mac 上太慢） | klein 4B（21 s） | — |
| 视频 | LTX-2.5 加速版 int4（5 s 480p 带声音，约 90 s，16–21 GB） | 同一模型出 720p（255 s） | **16 GB Mac 没有可用方案** | Wan 5B（sd.cpp 的 VAE 解码卡住或极慢） |
| 音乐 | ACE-Step 1.5 Turbo Q8（2 分钟的歌 89 s，7.9 GB） | YuE2 Q8，中文精唱（2.4 分钟 166 s，7 GB） | — | MiniMax Music 3（慢 7.8 倍，峰值 50 GB）、HeartMuLa |
| 语音识别 | Qwen3-ASR-0.6B（1.9 GB，30–60 倍实时） | Qwen3-ASR-1.7B（3 GB，最准） | SenseVoice（0.5 GB，纯 CPU 也有约 40 倍实时） | Fun-ASR-Nano（加噪后错误率 42%） |
| 语音合成 / 克隆 | Qwen3-TTS-0.6B（中、英、粤语都准，GPU 约 3 倍实时） | — | Kokoro-82M（12 倍实时，<1 GB，只做中文） | CosyVoice3（粤语差，有凭空加字） |

## 按内存自动分档

| 机器 | 能用的功能 |
|---|---|
| **16 GB Mac** | 图片（Z-Image、klein 4B）、音乐（ACE-Step、YuE2）、全部语音功能。视频不可用 |
| **24–32 GB Mac** | 上面全部，再加 klein 9B 编辑和 LTX-2.5 视频 |
| **32 GB 以上** | 再加 Qwen-Image-2.1；视频可以出 720p |

## 已知问题和待办

1. **M5 上的 Metal tensor API 问题**：sd.cpp 在 M5 上 VAE 会输出白图（上游 #1990），需要设置 `GGML_METAL_TENSOR_DISABLE=1` 绕开。
2. **音乐导出要加限幅器**：ACE-Step、YuE2、MiniMax 的输出峰值都到了 0 dBFS。
3. **Kokoro 英文依赖 eSpeak-ng**，它是 GPL-3.0 许可。可以改成英文统一用 Qwen3-TTS。
4. **LTX-2.5 权重需要自己托管**：官方仓库需要先点同意许可证；许可证允许再分发，条件是附带许可证。
5. **Qwen-Image-2.1 要预先量化**：现在每次运行都读 31 GB 原版权重再现场量化，应改为提供 8–9 GB 的 4bit 版本。
6. **还没验证的**：
   - 16 GB 的 M1–M4 实机表现，目前只有估算；
   - Windows 和 NVIDIA 显卡全部没测；
   - 所有主观质量（歌曲好不好听、音色像不像）都需要人来听。
