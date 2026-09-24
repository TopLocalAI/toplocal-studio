# Music 模块本地实测：ACE-Step 1.5 / YuE2 / HeartMuLa / MiniMax Music 3

- 测试日期：2026-09-23
- 机器：MacBook Pro M5 Pro，64 GB 统一内存
- 引擎：audio.cpp `487800f5`（Metal 后端）；MiniMax Music 3 对照组用 mlx-audio MXFP8

## 结论

- **默认模型用 ACE-Step 1.5 Turbo（Q8）。**
  - 2 分钟的歌 89 秒生成完，比实时还快，峰值内存 7.9 GB。
  - 中文歌词错误率 7.7%，英文 5.7%，是英文最好的。
  - 支持用 `--duration-seconds` 精确控制时长。
  - MIT 许可。
- **"中文精唱"档用 YuE2 3B（Q8）。**
  - 中文歌词最准，错误率 3.8%。
  - 2 分 24 秒的歌 166 秒生成完，内存 7.0 GB。
  - 时长由歌词长度决定，无法精确控制。
  - 许可证为 CC BY-NC，仅限非商用，本项目可以用。
  - Q4 版内存降到 5.6 GB，但中文错误率升到 13%，**不建议使用 Q4**。
- **HeartMuLa 3B 没有优势。**
  - 2 分钟的歌需 153 秒，内存 9.9 GB，都比 ACE-Step 差。
  - 中文 9.1%、英文 19.5%，歌词准确度也不如前两者。
  - 纯音乐输出音量偏小，平均 −23 dB。
- **MiniMax Music 3 可以退出默认方案。**
  - 同一首 2 分钟的歌要 696 秒，峰值内存 50 GiB。
  - 中文歌词错误率 15.9%，反而是几个模型里最差的。
  - 以上与 ACE-Step 1.5 Turbo 相比：慢 7.8 倍，内存高 6 倍多。
- **导出需要加限幅器。** ACE-Step、YuE2 和 MiniMax 的输出峰值都到了 0 dBFS，很可能已经削波。

## 结果

每首歌都用独立进程冷启动，墙钟时间包含模型加载。

| 模型 | 用例 | 音频时长 | 墙钟时间 | 实时倍率 | 峰值内存 |
|---|---|---:|---:|---:|---:|
| ACE-Step 1.5 Turbo Q8 | 中文 city pop | 120 s | 89 s | 1.35× | 7.9 GiB |
| ACE-Step 1.5 Turbo Q8 | 英文摇滚 | 90 s | 73 s | 1.23× | 7.7 GiB |
| ACE-Step 1.5 Turbo Q8 | 纯音乐 | 60 s | 59 s | 1.02× | 7.5 GiB |
| YuE2 3B Q8 | 中文 city pop | 144 s | 166 s | 0.87× | 7.0 GiB |
| YuE2 3B Q8 | 英文摇滚 | 120 s | 130 s | 0.92× | 6.9 GiB |
| YuE2 3B Q4 | 中文 city pop | 132 s | 109 s | 1.21× | 5.6 GiB |
| HeartMuLa 3B Q8 | 中文 city pop | 120 s | 153 s | 0.78× | 9.9 GiB |
| HeartMuLa 3B Q8 | 英文摇滚 | 90 s | 111 s | 0.81× | 9.3 GiB |
| HeartMuLa 3B Q8 | 纯音乐 | 60 s | 79 s | 0.76× | 8.3 GiB |
| MiniMax Music 3（MLX MXFP8） | 中文 city pop | 120 s | 696 s | 0.17× | 50.4 GiB |

YuE2 这一项没有纯音乐数据：它生成纯音乐需要额外的适配器，本次没有测。

## 歌词准确度

先把生成的歌曲交给 Qwen3-ASR-1.7B 转写，再和输入歌词比对，计算字错率（中文）或词错率（英文）。

识别唱歌比识别说话难，这个数字里也包含了识别模型自身的错误，所以只适合用来横向比较，不能当作绝对值。

| 歌曲 | 歌词错误率 |
|---|---:|
| YuE2 Q8 中文 | **3.8%** |
| ACE-Step Turbo 中文 | 7.7% |
| HeartMuLa 中文 | 9.1% |
| YuE2 Q4 中文 | 13.0% |
| MiniMax Music 3 中文 | 15.9% |
| ACE-Step Turbo 英文 | **5.7%** |
| YuE2 Q8 英文 | 13.8%（开头多唱了一句歌词里没有的内容） |
| HeartMuLa 英文 | 19.5% |

## 响度

用 ffmpeg volumedetect 测，mean 是平均音量，max 是峰值：

- ACE-Step：mean −13 dB，max **0.0 dB**
- YuE2：mean −16 dB，max **0.0 dB**
- MiniMax：mean −18.6 dB，max **0.0 dB**
- HeartMuLa：mean −19 至 −23 dB，max −3 至 −8 dB

## 还需要人耳确认

旋律、编曲、人声音色这些主观质量，只能靠人来听。建议你至少听下面三首，它们都在 `outputs/music/` 里：

- `ace-turbo-song_zh.wav`
- `yue2-q8-song_zh.wav`
- `heartmula-song_zh.wav`

MiniMax 的对照结果在 `outputs/mlx-mxfp8-song-zh-120.wav`。

## 复现

```bash
music/run_music_suite.sh     # 结果写到 results/music/*.log，音频写到 outputs/music/
music/score_lyrics.sh        # 歌词准确度，结果写到 results/music/lyrics-summary.md
```

## 补测：ACE-Step 打包方式与语言参数（2026-09-24）

同一首中文歌（song_zh），seed 11，120 秒：

| 权重包 | `--language` | 墙钟时间 | 峰值内存 | 歌词错误率 |
|---|---|---:|---:|---:|
| 全部 Q8（`turbo-q8_0`，当前使用） | zh | 69 s | 7.9 GiB | 7.7% |
| 只把 DiT 量化成 Q8，规划器保留 bf16（`q8dit`，文档推荐） | zh | 70 s | 13.5 GiB | 15.9% |
| 同上（`q8dit`） | en（默认值） | 89 s | 13.5 GiB | 15.9% |

- `--language` 参数对输出没有影响：同一个权重包，设 zh 和不设时生成结果完全一样。
- 文档推荐的 q8dit 包在这次测试里内存多用了 5.6 GB，歌词也没有更准（漏唱了一句）。**继续使用全部 Q8 的包。**
- 这只是单个 seed 的结果，不算定论。
