# Image 模块本地实测：stable-diffusion.cpp vs mflux (MLX)

测试日期：2026-09-23。机器：MacBook Pro M5 Pro（20 核 GPU）、64 GB 统一内存。

## 结论

- **Mac 端推理引擎选 MLX（mflux）。** 同一模型、相同或更低内存下，mflux 比 stable-diffusion.cpp 快 3–5 倍。
- **默认文生图模型：Z-Image-Turbo（MLX 4bit，低内存模式）。**
  - 中、英文字都完全正确，写实和插画质量也都很好。
  - 1024² 出图约 40 秒，峰值内存 6.3 GB，16 GB 的 Mac 能跑。
- **默认编辑模型：FLUX.2 klein 9B（MLX 4bit）。**
  - 编辑效果好：改字、换季节都能做到，原构图保持得好。
  - 约 20–40 秒一张，低内存模式峰值 12 GB，需要 24 GB 以上的 Mac。
  - 缺点：中文字偶有错字，英文拼写也不稳定。
- **极速档：FLUX.2 klein 4B（MLX 4bit）。**
  - 约 11 秒一张，适合写实照片、插画和编辑。
  - **写不了中文字**，英文字也经常拼错。
- **高配档：Qwen-Image-2.1。**
  - 整体质量最好，书法字、排版和编辑都很出色。
  - 但慢，40 步要 160 秒；低内存模式峰值也有 15 GB，建议 32 GB 以上的 Mac。
  - 许可证只允许研究或评估用途。
- **stable-diffusion.cpp 保留给 Windows**（CUDA / Vulkan），也作为 Mac 上的兜底方案。它在 Mac 上跑 Qwen-Image-2.1 要 13 分钟一张，不可用。

## M5 上的 Metal 问题（已绕开）

stable-diffusion.cpp 在 M5 上默认启用 ggml 的 Metal tensor API，结果会输出**全白图**，同上游 issue [#1990](https://github.com/leejet/stable-diffusion.cpp/issues/1990)。

排查结果：
- **出问题的是 VAE 解码**，去噪阶段在 tensor API 下是正常的。
  - 把 VAE 放到 CPU（`--backend vae=cpu`），出图正常。
  - VAE 改用 direct conv（`--vae-conv-direct`），也正常，但解码慢约 10 倍。
  - 把 VAE 权重转成 f16，**仍然是白图**，所以不是权重精度的问题。
- 对照数据，Z-Image Q4、512²、8 步：
  - tensor API 开：采样约 24 秒，VAE 白图。
  - tensor API 关：采样约 35 秒，出图正常。
- 本次测试统一设置 `GGML_METAL_TENSOR_DISABLE=1`。这样也和 M1–M4 的默认行为一致，ggml 在 M5 之前的芯片上默认就不启用 tensor API。

## 性能（1024×1024，单张，冷启动进程，含加载）

说明：
- 墙钟时间用 `/usr/bin/time` 测得。
- sd.cpp 的"采样"和"VAE"两列来自它自己的日志；mflux 只有总时间。
- mflux 的时间里包含加载权重；Qwen-Image-2.1 另外还包含每次现场量化的时间。
- 峰值内存取 macOS 报告的 `peak memory footprint`。
- 完整明细见 [`image/summary-table.md`](image/summary-table.md)。

| 模型 | 引擎 / 量化 | 步数 | 墙钟时间 | 采样 | VAE | 峰值内存 |
|---|---|---:|---:|---:|---:|---:|
| Z-Image-Turbo | sd.cpp Q4_K | 8 | 136–146 s | 126–135 s | 7.5 s | 6.5 GB |
| Z-Image-Turbo | sd.cpp Q8_0 | 8 | 122–146 s | 114–135 s | 7 s | 9.2 GB |
| Z-Image-Turbo | **mflux 4bit** | 8 | **34–40 s** | — | — | 20.4 GB |
| Z-Image-Turbo | **mflux 4bit 低内存** | 8 | **39.7 s** | — | — | **6.3 GB** |
| FLUX.2 klein 4B | sd.cpp Q4_0 | 4 | 45–48 s | 37 s | 6.7 s | 5.1 GB |
| FLUX.2 klein 4B | sd.cpp Q8_0 | 4 | 42–48 s | 34–40 s | 6.5 s | 7.2 GB |
| FLUX.2 klein 4B | **mflux 4bit** | 4 | **10.7–15 s** | — | — | 22.5 GB |
| FLUX.2 klein 4B | **mflux 4bit 低内存** | 4 | **11.1 s** | — | — | **9.4 GB** |
| FLUX.2 klein 9B | sd.cpp Q4_0 | 4 | 72–83 s | 63–72 s | 6.5 s | 9.9 GB |
| FLUX.2 klein 9B | **mflux 4bit** | 4 | **19.5–23 s** | — | — | 25.2 GB |
| FLUX.2 klein 9B | **mflux 4bit 低内存** | 4 | **20.4 s** | — | — | **12.1 GB** |
| Qwen-Image-2.1 | sd.cpp Q4_K | 40 | 770–817 s | 652–696 s | 114 s | 9.6 GB |
| Qwen-Image-2.1 | mflux 4bit | 40 | 167 s | — | — | 49.6 GB |
| Qwen-Image-2.1 | **mflux 4bit 低内存** | 40 | **159–163 s** | — | — | **15.2 GB** |

图片编辑（`edit_sign`：把招牌改成 "Local AI Studio"，并改成雪夜）：

| 模型 | 引擎 | 墙钟时间 | 峰值内存 |
|---|---|---:|---:|
| klein 4B | sd.cpp Q4_0 / Q8_0 | 93 s / 87 s | 5.1 / 7.1 GB |
| klein 4B | mflux 4bit | **21.2 s** | 22.6 GB |
| klein 9B | sd.cpp Q4_0 | 179 s | 10.1 GB |
| klein 9B | mflux 4bit | **39.2 s** | 25.2 GB |
| Qwen-Image-2.1 | sd.cpp Q4_K | 1555 s | 10.7 GB |

mflux 的 Qwen-Image-2.1 没有编辑入口；Z-Image-Turbo 没有开源的编辑模型。

## 画质

对比图在 [`image/sheets/`](image/sheets/) 下，每个用例一张。原图在 `outputs/image/`。

| 能力 | Z-Image-Turbo | klein 4B | klein 9B | Qwen-Image-2.1 |
|---|---|---|---|---|
| 中文字（"山间清茶 / 春日限定 · 新品上市"） | ✅ 全对，三个版本一致 | ❌ 乱码 | ⚠️ 基本对，"新品上市"写成"新品上用" | ✅ 全对，书法效果最好 |
| 英文字（"The Midnight Library / Open Late · Hot Cocoa"） | ✅ 全对 | ❌ 拼写错误 | ⚠️ 部分错误 | ✅ sd.cpp Q4 全对；mflux 4bit 有小错 |
| 写实人像 | ✅ 很好 | ✅ 好 | ✅ 好 | ✅ 很好 |
| 扁平插画 | ✅ 好 | ✅ 好 | ✅ 好 | 未测 |
| 编辑（改字 + 换季节 + 保持构图） | 不支持 | ✅ 好 | ✅ 很好 | ✅ 很好，保真度最高 |

量化对画质影响很小：Z-Image 的 Q4、Q8 和 MLX 4bit 出图几乎一样。

## 对产品的影响

1. **Mac 端需要带 Python 运行时。** mflux 是 Python 包，打包时要附带独立的 Python 运行时加 mlx/mflux，按约 300–400 MB 估算。Music 模块的 mlx-audio 也可以共用这个运行时。sd.cpp 在 Mac 上只是一个 39 MB、只依赖系统框架的二进制，但速度明显吃亏。
2. **按内存分档：**
   - **16 GB Mac**：Z-Image-Turbo 4bit 低内存，约 6.3 GB；klein 4B 4bit 低内存，约 9.4 GB，但可能要和系统抢内存。
   - **24–32 GB Mac**：再加 klein 9B 编辑，约 12 GB。
   - **32 GB 以上**：再加 Qwen-Image-2.1，约 15 GB。
3. **一律开低内存模式。** 各模型速度基本不变，峰值内存降 50–70%。
4. **Qwen-Image-2.1 要预先量化再分发。** 现在每次运行都要读 31 GB 原版权重再现场量化。应改为用 `mflux-save` 预先量化，存成约 8–9 GB 的 4bit 版供用户下载，这样加载时间会明显缩短。
5. **16 GB Mac 的实际表现还需验证。** 本次数据来自 64 GB 机器，低内存模式的峰值只能作为参考，最好找一台 16 GB 的 M1 或 M2 复测。M1–M4 的 GPU 比 M5 Pro 弱，按经验同样任务要慢 1.5–3 倍，这是估算。

## 版本

- stable-diffusion.cpp `c92d73c408515c94beef32161bb5960764fde7a0`（2026-09-23），Metal 构建，`sd-cli` 39 MB
- mflux 0.20.0，MLX 0.32.2，Python 3.12
- 权重：
  - GGUF：`leejet/Z-Image-Turbo-GGUF`、`leejet/FLUX.2-klein-{4B,9B}-GGUF`、`leejet/Qwen-Image-2.1-GGUF`，以及 unsloth 的 Qwen3 文本编码器 GGUF、`Qwen/Qwen3-VL-8B-Instruct-GGUF`
  - MLX：`filipstrand/Z-Image-Turbo-mflux-4bit`、`Runpod/FLUX.2-klein-4B-mflux-4bit`、`mflux-community/flux2-klein-9b-mflux-q4`、`Qwen/Qwen-Image-2.1`（加载时量化为 4bit）

## 复现

```bash
./image/download_models.sh                       # GGUF 权重 → models/image/
./image/run_image_suite.sh zimage-q4 klein4b-q4  # sd.cpp，结果写到 results/image/*.log
./image/run_mflux_case.sh mlx-zimage-4bit zh_poster
LOW_RAM=1 ./image/run_mflux_case.sh mlx-klein9b-4bit edit_sign
python3 image/summarize.py                       # 汇总表
image/mflux-venv/bin/python image/make_sheets.py # 对比图
```

测试用例在 `image/cases/*.env`，统一用 1024×1024、seed 42。

## 补测：Unsloth Dynamic 2.0 版 Qwen-Image-2.1（2026-09-24）

测试条件：stable-diffusion.cpp，按 Unsloth 推荐的设置跑（20 步，cfg 6，euler），1024²，中文海报用例。

| 主模型 | 文本编码器 | 采样 | VAE 解码 | 总耗时 | 峰值内存 | 中文字 |
|---|---|---:|---:|---:|---:|---|
| `qwen-image-2.1-Q4_K_M.gguf`（4.2 GB） | Qwen3-VL-8B Q4_K_M（5.0 GB） | 607 s | 112 s | **723 s** | **9.5 GB** | ✅ 全对 |
| `qwen-image-2.1-Q2_K.gguf`（2.5 GB） | Qwen3-VL-8B Q2_K（3.3 GB） | 644 s | 112 s | **759 s** | **6.1 GB** | ⚠️ "春日限定"的"定"字写错 |

- 内存：4-bit 在 16 GB Mac 上确实能跑。2-bit 峰值 6.1 GB，8 GB 的 Mac 上理论上装得下，但系统加上其他应用之后会非常紧张。
- 速度：两者都要 12 分钟左右，量化方法不会让 Mac 上的计算变快。同一个模型走 mflux（MLX 4bit）只要 160 s，快约 4.5 倍，但峰值 15 GB。
- 对照图：`results/image/sheets/qwen21-unsloth-q4-vs-q2.jpg`
