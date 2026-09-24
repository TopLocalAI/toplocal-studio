# TopLocal Studio · 本地创作台

在自己的电脑上生成图片、视频、音乐和语音，不需要联网或账号，内容不离开本机。开源，非商业。

*Create images, video, music and speech entirely on your own computer. No account, no cloud.*

| 模块 | 能做什么 | 模型 |
| --- | --- | --- |
| 图片 | 文字生成图片、按描述修改图片 | Z-Image-Turbo，FLUX.2 klein 4B / 9B |
| 视频 | 文字或图片生成带声音的短视频（3 / 5 / 8 秒） | LTX-2.5 Distilled |
| 音乐 | 一句话写歌、用自己的歌词、纯音乐；导出动效视频 | ACE-Step 1.5，YuE2（中文精唱），Qwen3-4B 写词 |
| 语音 | 录音转文字（带 SRT 字幕）、配音、声音克隆 | Qwen3-ASR，SenseVoice，Kokoro，Qwen3-TTS |

安装包包含全部运行环境（Python 和推理引擎）。模型在应用内按需下载：支持断点续传、sha256 校验和国内镜像，下载前会显示模型的许可证。

## 系统要求

| | macOS | Windows |
| --- | --- | --- |
| 硬件 | Apple Silicon（M1 及以上） | x64，支持 Vulkan 的显卡（NVIDIA / AMD / Intel） |
| 内存 | 16 GB 起；视频需要 24 GB 以上 | 16 GB 起；视频需要 24 GB 以上 |
| 推理引擎 | MLX（图片、视频），audio.cpp Metal | stable-diffusion.cpp、audio.cpp、llama.cpp（Vulkan） |
| 状态 | 已在 M5 Pro 64 GB 上完整测试 | GitHub Actions 自动构建；还没有在真实显卡上测试，视频为实验功能 |

Windows 版的已知限制：

- 需要安装显卡驱动。驱动会带上 Vulkan 运行库（`vulkan-1.dll`），音乐和语音引擎启动时要用到它。
- 视频模型的文本编码器来自 Lightricks 官方仓库，需要先在 Hugging Face 同意许可证，再在设置里填写访问令牌。
- Windows 用户名里有中文时，引擎读取模型的情况还没有验证。

应用会按内存档位（16 / 32 / 64 GB）决定开放哪些功能。各模型的速度、内存和质量实测见 [`results/model-selection.md`](results/model-selection.md)。

## 下载

在 [Releases](https://github.com/TopLocalAI/toplocal-studio/releases) 下载：

- Windows：`TopLocal Studio_<版本>_x64-setup.exe`，由 GitHub Actions 构建。安装包暂未做代码签名，SmartScreen 提示时选择“仍要运行”。
- macOS：`.dmg`，本地构建，使用 Developer ID 签名。

## 开发

需要 Node 22、Rust、[uv](https://docs.astral.sh/uv/)。

```bash
cd app && npm install
npx tauri dev          # 桌面窗口，自动启动 Vite 和本地服务
npm run dev:all        # 只用浏览器：服务在 :4318，页面在 :5173
```

结构：

```
app/        Tauri 2 桌面壳 + React 界面
service/    本地推理服务（Python aiohttp）：任务队列、模型目录、下载器、各模块引擎
packaging/  macOS / Windows 打包脚本
results/    模型选型和实测报告
```

本地服务只监听 127.0.0.1 的随机端口，并校验桌面壳生成的随机令牌。引擎和模型路径都可以用 `LOCALAI_*` 环境变量覆盖（见 `service/localai_service/config.py`），开发时默认使用这个仓库旁边的引擎和 `models/` 目录。设置 `LOCALAI_DIFFUSION_ENGINE=sdcpp` 可以在 Mac 上走 Windows 的 stable-diffusion.cpp 图片路径。

界面端到端测试（WebKit，会真实生成内容）：

```bash
npm run dev:all   # 在 app/ 下
uv run --with playwright python app/tests/ui_e2e.py
```

## 打包

**Windows**：推送到 `main` 或打 `v*` 标签时，[`.github/workflows/windows.yml`](.github/workflows/windows.yml) 会：

1. 用 `packaging/build_windows.ps1` 打包独立 CPython 3.12 和本地服务；
2. 下载 [`packaging/windows-engines.json`](packaging/windows-engines.json) 里固定版本、带 sha256 的 Vulkan 版引擎；
3. 运行冒烟测试；
4. 构建 NSIS 安装包。

打标签时，安装包会附到 Release 草稿上。

**macOS**（本地构建）：

```bash
packaging/build_macos.sh
APPLE_SIGNING_IDENTITY="Developer ID Application: …" NOTARY_PROFILE=<profile> packaging/build_macos.sh
```

`packaging/build_runtime.sh` 会打包私有的 CPython 3.12，里面包含本地服务、mflux 和 ltx-2-mlx，不带 PyTorch，另外还有 audio.cpp、静态链接的 llama-completion 和 ffmpeg。

## 许可证

代码采用 [Apache-2.0](LICENSE)。打包的引擎和可下载模型各有自己的许可证，见 [NOTICE.md](NOTICE.md)。其中 YuE2、FLUX.2 klein 9B 和 LTX-2.5 限制商业使用。
