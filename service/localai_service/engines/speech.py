"""Speech module through audio.cpp.

Transcribe: ffmpeg → 16 kHz mono → Silero VAD chunks → ASR per chunk → TXT + SRT.
The VAD chunk boundaries give real subtitle timings with every ASR model.

Synthesize: preset voices use Kokoro (fast, Chinese). Text with Latin words (Kokoro skips
unknown ones) and cloned voices go through Qwen3-TTS, whose reference for a preset is a
Kokoro rendering of that preset, so the voice stays the same.
"""
import functools
import json
import re
import wave
from pathlib import Path

import cn2an

from .. import catalog, config, uploads
from ..i18n import tr
from ..jobs import Job, JobFailed
from . import media

VAD_MODEL = "assets/framework/models/silero_vad"  # relative to AUDIOCPP_ROOT
SR = 16000

ASR_MODELS = {
    "standard": ("speech.asr", "qwen3_asr"),
    "accurate": ("speech.asr-hq", "qwen3_asr"),
    "fast": ("speech.asr-fast", "sense_asr"),
}

KOKORO_VOICES = {
    "zf_xiaoxiao": "晓晓 · 女声", "zf_xiaoyi": "晓伊 · 女声", "zf_xiaobei": "晓北 · 女声", "zf_xiaoni": "晓妮 · 女声",
    "zm_yunxi": "云希 · 男声", "zm_yunjian": "云健 · 男声", "zm_yunyang": "云扬 · 男声", "zm_yunxia": "云夏 · 男声",
}
PRESET_REF_TEXT = "你好，很高兴认识你。今天天气不错，我们一起出去走走吧。"


def _cli(*args) -> list:
    return [config.AUDIOCPP_CLI, *args, "--backend", config.AUDIOCPP_BACKEND]


async def to_wav16k(job: Job, src: Path, dest: Path) -> float:
    await job.run([config.FFMPEG, "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR),
                   "-c:a", "pcm_s16le", dest], log_name="ffmpeg.log")
    with wave.open(str(dest)) as w:
        return w.getnframes() / SR


@functools.cache
def _t2s():
    import opencc

    return opencc.OpenCC("t2s")


def _fmt_srt(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def _split_line(text: str, start: float, end: float, limit: int) -> list[tuple[float, float, str]]:
    """Split a long chunk transcript into subtitle lines, timing them by character share."""
    text = re.sub(r"<\|[^|]*\|>", "", text).strip()
    if not text:
        return []
    parts = [p for p in re.split(r"(?<=[，。！？；,.!?;])\s*", text) if p]
    lines, buf = [], ""
    for part in parts:
        if buf and len(buf) + len(part) > limit:
            lines.append(buf)
            buf = part
        else:
            buf += part
    if buf:
        lines.append(buf)
    total = sum(len(l) for l in lines)
    out, t = [], start
    for line in lines:
        dur = (end - start) * len(line) / total
        out.append((t, t + dur, line.strip()))
        t += dur
    return out


async def transcribe(job: Job) -> dict:
    p = job.params
    source = uploads.resolve(p.get("source"))
    tier = p.get("quality") if p.get("quality") in ASR_MODELS else "standard"
    model_id, family = ASR_MODELS[tier]
    model = catalog.model_path(model_id)
    if model is None:
        raise JobFailed(tr("语音识别模型未安装，请在设置里下载"))
    job.title = tr("{name} · 文字稿", name=Path(p.get("sourceName") or source.name).stem[:20])
    job.save()

    job.update(3, tr("正在读取音频"))
    wav = job.dir / "input.wav"
    duration = await to_wav16k(job, source, wav)
    if duration < 0.3:
        raise JobFailed(tr("没有检测到有效的音频"))

    job.update(10, tr("正在切分语句"))
    vad_json = job.dir / "vad.json"
    await job.run(_cli("--task", "vad", "--family", "silero_vad", "--model", VAD_MODEL, "--audio", wav,
                       "--vad-chunks-out", vad_json, "--vad-chunk-max-seconds", "12"),
                  cwd=config.AUDIOCPP_ROOT, log_name="vad.log")
    chunks = json.loads(vad_json.read_text(encoding="utf-8")) if vad_json.exists() else []
    if not chunks:
        raise JobFailed(tr("没有检测到说话的声音"))

    chunk_dir = job.dir / "chunks"
    chunk_dir.mkdir(exist_ok=True)
    with wave.open(str(wav)) as w:
        frames = w.readframes(w.getnframes())
    for c in chunks:
        with wave.open(str(chunk_dir / f"{c['index']:05d}.wav"), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(SR)
            out.writeframes(frames[c["start_sample"] * 2:c["end_sample"] * 2])

    texts: dict[str, str] = {}
    current = {"id": None}

    def on_line(line: str) -> None:
        if line.startswith("request_id="):
            current["id"] = line.split("=", 1)[1]
        elif line.startswith("text_output=") and current["id"]:
            texts[current["id"]] = texts.get(current["id"], "") + line.split("=", 1)[1]
            job.update(15 + 80 * len(texts) / len(chunks), tr("正在识别文字"))

    job.update(15, tr("正在识别文字"))
    args = ["--task", "asr", "--family", family, "--model", model, "--batch-audio-dir", chunk_dir]
    if family == "qwen3_asr":
        args += ["--text", ""]
    if p.get("language") in ("zh", "en", "yue", "ja", "ko"):
        args += ["--request-option", f"language={p['language']}"]
    await job.run(_cli(*args), cwd=config.AUDIOCPP_ROOT, log_name="asr.log", on_line=on_line)

    limit = 24 if re.search(r"[一-鿿]", "".join(texts.values())) else 60
    srt, plain, n = [], [], 0
    # Qwen3-ASR sometimes writes Mandarin in Traditional characters; the app is for
    # Simplified-Chinese users, so convert unless Cantonese was chosen explicitly.
    to_simplified = _t2s().convert if p.get("language") != "yue" else (lambda t: t)
    for c in chunks:
        text = to_simplified(texts.get(f"{c['index']:05d}", "").strip())
        if not text:
            continue
        plain.append(re.sub(r"<\|[^|]*\|>", "", text))
        for start, end, line in _split_line(text, c["start_sample"] / SR, c["end_sample"] / SR, limit):
            n += 1
            srt.append(f"{n}\n{_fmt_srt(start)} --> {_fmt_srt(end)}\n{line}\n")
    if not plain:
        raise JobFailed(tr("没有识别出文字"))
    joiner = "" if limit == 24 else " "
    (job.dir / "transcript.txt").write_text(joiner.join(plain) + "\n", encoding="utf-8")
    (job.dir / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    for f in chunk_dir.iterdir():
        f.unlink()
    chunk_dir.rmdir()
    return {"text": "transcript.txt", "srt": "subtitles.srt", "duration": duration,
            "preview": joiner.join(plain)[:2000], "model": model_id}


def _kokoro_text(text: str) -> str:
    try:
        return cn2an.transform(text, "an2cn")
    except Exception:
        return text


async def _kokoro(job: Job, text: str, voice: str, out: Path, log: str = "tts.log") -> None:
    model = catalog.model_path("speech.tts-fast")
    if model is None:
        raise JobFailed(tr("快速配音模型未安装，请在设置里下载"))
    await job.run(_cli("--task", "tts", "--family", "kokoro_tts", "--model", model, "--language", "zh",
                       "--voice-id", voice, "--text", _kokoro_text(text), "--out", out),
                  cwd=config.AUDIOCPP_ROOT, log_name=log)


async def _preset_reference(job: Job, voice: str) -> tuple[Path, str]:
    """Kokoro rendering of a preset voice, cached, used as a Qwen3-TTS reference."""
    cache = config.DATA_DIR / "voices" / f"{voice}.wav"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        await _kokoro(job, PRESET_REF_TEXT, voice, cache, log="voice-ref.log")
    return cache, PRESET_REF_TEXT


async def synthesize(job: Job) -> dict:
    p = job.params
    text = str(p.get("text", "")).strip()
    if not text:
        raise JobFailed(tr("请输入要朗读的文字"))
    if len(text) > 5000:
        raise JobFailed(tr("一次最多朗读 5000 字，请分段生成"))
    voice = p.get("voice") or {}
    job.title = tr("配音 · {text}", text=text[:14])
    job.save()
    wav = job.dir / "speech.wav"
    has_latin = bool(re.search(r"[A-Za-z]{2,}", text))

    if voice.get("preset") in KOKORO_VOICES and not has_latin:
        job.update(20, tr("正在朗读"))
        await _kokoro(job, text, voice["preset"], wav)
        engine = "kokoro"
    else:
        model = catalog.model_path("speech.tts")
        if model is None:
            raise JobFailed(tr("配音模型未安装，请在设置里下载"))
        if voice.get("preset") in KOKORO_VOICES:
            job.update(8, tr("正在准备音色"))
            ref, ref_text = await _preset_reference(job, voice["preset"])
        else:
            ref = job.dir / "voice-ref.wav"
            job.update(5, tr("正在分析参考声音"))
            dur = await to_wav16k(job, uploads.resolve(voice.get("clone")), ref)
            if dur < 3:
                raise JobFailed(tr("参考录音太短，请提供 5 到 20 秒的清晰人声"))
            if dur > 30:
                await job.run([config.FFMPEG, "-y", "-v", "error", "-i", ref, "-t", "20", str(ref) + ".cut.wav"],
                              log_name="ffmpeg.log")
                Path(str(ref) + ".cut.wav").replace(ref)
            ref_text = await _reference_text(job, ref)
        job.update(20, tr("正在朗读"))
        await job.run(_cli("--task", "tts", "--family", "qwen3_tts", "--model", model, "--voice-ref", ref,
                           "--reference-text", ref_text, "--text", text, "--out", wav),
                      cwd=config.AUDIOCPP_ROOT, log_name="tts.log")
        engine = "qwen3_tts"

    if not wav.exists():
        raise JobFailed(tr("生成完成，但没有找到音频"))
    job.update(95, tr("正在完成音频文件"))
    m4a = job.dir / "speech.m4a"
    await media.finish_audio(job, wav, m4a)
    return {"audio": "speech.m4a", "wav": "speech.wav", "duration": await media.probe_duration(m4a),
            "text": text, "engine": engine}


async def _reference_text(job: Job, ref: Path) -> str:
    """Transcribe the cloning reference so the user never has to type it."""
    model = catalog.model_path("speech.asr")
    if model is None:
        return ""
    out = await job.run(_cli("--task", "asr", "--family", "qwen3_asr", "--model", model, "--text", "",
                             "--audio", ref), cwd=config.AUDIOCPP_ROOT, log_name="ref-asr.log")
    lines = [l.split("=", 1)[1] for l in out.splitlines() if l.startswith("text_output=")]
    return "".join(lines).strip()
