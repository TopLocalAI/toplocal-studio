# Video 模块本地实测：LTX-2.5 (MLX) vs Wan2.2 5B (stable-diffusion.cpp)

- 测试日期：2026-09-23 至 24
- 机器：MacBook Pro M5 Pro，64 GB 统一内存

## 结论

- **Mac 端用 LTX-2.5 加速版 + ltx-2-mlx（int4 权重包）。**
  - 5 秒 480p 视频连同声音约 80–95 秒生成完，720p 约 255 秒，图生视频约 133 秒。
  - 画面质量好，人物外观前后一致，镜头运动自然；同时生成环境音，比如雨声。
- **内存门槛是 24 GB 起步，32 GB 才宽裕。**
  - 即使把 VAE 预算压到 8 GB 并打开低内存模式，峰值仍有 15.8 GB，主要被权重本身占掉。
  - 16 GB 的 Mac 上 GPU 实际只能用约 10–11 GB，**跑不了**。
- **stable-diffusion.cpp 在 Mac 上做视频不可用。**
  - Wan2.2 5B 的去噪部分正常：FastWan 3 步 28 秒，完整版每步约 17 秒。
  - 但 Wan 的 VAE 解码在 Metal 上等了 8–10 分钟没有结束，只能人为终止；改放 CPU 上解码，1.4 秒视频要 **879 秒**。
  - 所以 sd.cpp 的视频路径只留给 Windows（CUDA），Windows 端还需要另外实测。
- **16 GB 的 Mac 目前没有可用的视频方案。**
  - Wan 5B 的 MLX 版在第三方 M2 Max 32 GB 上实测：5 秒 480p 要 311 秒，峰值 15 GB（[来源](https://huggingface.co/jboone100/FastWan2.2-TI2V-5B-MLX-q8)），同样装不进 16 GB。
  - 建议产品对 16 GB 机器直接提示"视频需要 24 GB 以上内存"。
- **许可证**：
  - LTX-2.x 社区许可允许非商用；允许再分发，但必须附上许可证全文、标注修改、并把使用限制条款传递给用户。所以产品可以自己托管权重，下载前向用户展示许可证即可。
  - 官方 HF 仓库需要先点同意，匿名下载会被拒绝。

## LTX-2.5 实测

测试条件：ltx-2-mlx `7296f23`；权重 `dgrauet/ltx-2.5-mlx-q4`；distilled 两阶段流程；121 帧，24 fps。所有时间都是端到端，包括加载模型、生成、解码和合成音视频。

| 用例 | 分辨率 | 时长 | 墙钟时间 | 峰值内存 | 备注 |
|---|---|---:|---:|---:|---|
| 文生视频：雨夜上海街头 | 832×448 | 5.04 s | 88 s | 20.7 GiB | 默认设置，VAE 预算 32 GB，不分块 |
| 文生视频：草地上的小狗 | 832×448 | 5.04 s | 80 s | 20.5 GiB | |
| 图生视频：茶饮海报动起来 | 704×704 | 5.04 s | 133 s | 20.0 GiB | 开头忠于原图，后段镜头下移，标题和茶杯移出画面 |
| 文生视频：雨夜街头 720p | 1280×704 | 5.04 s | 255 s | 20.5 GiB | |
| 模拟 32 GB Mac：低内存 + VAE 预算 16 GB | 832×448 | 5.04 s | 95 s | 15.8 GiB | VAE 解码峰值 15.2 GB |
| 模拟 16 GB Mac：低内存 + VAE 预算 8 GB | 832×448 | 5.04 s | 89 s | 15.8 GiB | VAE 解码峰值 9.8 GB，但进程整体峰值仍有 15.8 GB |

- 每条视频都带 48 kHz AAC 环境音。以雨夜街头为例，平均音量 −32 dB，峰值 −17 dB。
- 按每个用例取 3 帧的截图，放在 `results/video/frames/`。

## Wan2.2 TI2V-5B 在 stable-diffusion.cpp 上的实测

测试条件：832×480，33 帧，Q8 GGUF，umT5-XXL Q8 文本编码器；和图片测试一样设置了 `GGML_METAL_TENSOR_DISABLE=1`。

| 模型 | 步数 | 去噪 | VAE 解码 | 结果 |
|---|---:|---:|---:|---|
| Wan2.2 5B 完整版 | 10 | 176 s（每步 17.6 s） | Metal 上等了 10 分钟以上仍未完成 | 人为终止 |
| FastWan 5B（3 步加速版） | 3 | 24–28 s | Metal 上等了 8 分钟以上仍未完成；**改用 CPU 解码要 879 s** | 生成 1.4 秒视频共 915 s，画面尚可，脸部偏糊 |

## 16 GB Mac 为什么不行

- 权重本身就很大：LTX-2.5 int4 的 transformer 11.3 GB，Gemma 文本编码器 10.6 GB。
- ltx-2-mlx 的低内存模式可以分块加载 transformer，但这次的测量里没有看到进程峰值降下来。
- VAE 解码可以通过 `LTX2_VAE_DECODE_BUDGET_GB` 压到 10 GB 以内，但整个进程的峰值还是 15.8 GB。
- 要让 16 GB 的机器跑起来，只能等更小的视频模型，或者把文本编码器单独放在一个进程里、用完就释放。后者值得作为后续优化项。

## 复现

```bash
video/run_video_case.sh ltx25-mlx-q4 t2v_city
LTX2_VAE_DECODE_BUDGET_GB=8 LOW_RAM=1 TAG=-sim16gb video/run_video_case.sh ltx25-mlx-q4 t2v_city
STEPS=10 TAG=-smoke video/run_video_case.sh wan5b-q8 smoke   # sd.cpp，VAE 在 Metal 上会卡住
```
