"""Music module: ACE-Step 1.5 Turbo (standard) and YuE2 (Chinese vocal) through audio.cpp."""
import asyncio
import json
import random
import re
import time

from .. import catalog, config
from ..i18n import tr
from ..jobs import Job, JobFailed
from . import llm, media

STYLE_CAPTIONS = {
    "华语流行": "Mandopop", "流行": "pop", "摇滚": "rock", "民谣": "acoustic folk", "电子": "electronic",
    "说唱": "hip hop", "R&B": "R&B", "爵士": "jazz", "古风": "Chinese traditional instruments, guofeng",
    "城市夜色": "neon city night atmosphere", "温柔": "warm and tender", "欢快": "upbeat and joyful",
    "伤感": "melancholic", "热血": "energetic and anthemic", "治愈": "soothing and healing",
    "女声": "female lead vocal", "男声": "male lead vocal", "钢琴": "piano", "吉他": "guitar",
    "合成器": "analog synthesizers", "弦乐": "strings", "电影感": "cinematic",
}
SECTION_TAGS = {"主歌": "Verse", "副歌": "Chorus", "前副歌": "Pre-Chorus", "预副歌": "Pre-Chorus",
                "桥段": "Bridge", "间奏": "Instrumental", "前奏": "Intro", "尾奏": "Outro"}


def _normalize_lyrics(text: str) -> str:
    for zh, en in SECTION_TAGS.items():
        text = text.replace(f"[{zh}]", f"[{en}]").replace(f"【{zh}】", f"[{en}]")
    return text.strip()


def _language(text: str) -> str:
    cjk = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "zh" if cjk >= latin / 3 else "en"


def _caption(styles: list[str], description: str, instrumental: bool) -> str:
    parts = [STYLE_CAPTIONS.get(s, s) for s in styles]
    caption = ", ".join(parts) if parts else "polished contemporary pop"
    if description:
        caption += f". {description}"
    caption += ". Instrumental only, no vocals." if instrumental else ". Clear lead vocal, memorable chorus."
    return caption + " Modern, detailed stereo production."


def _title(lyrics: str, description: str) -> str:
    for line in lyrics.splitlines():
        line = line.strip()
        if line and not line.startswith("["):
            return line[:14]
    return (description or tr("本地新作"))[:14]


async def _tick(job: Job, expected: float, start: float, stop: asyncio.Event, lo: float, hi: float, labels):
    while not stop.is_set():
        frac = min(1.0, (time.time() - start) / expected)
        label = labels[min(len(labels) - 1, int(frac * len(labels)))]
        job.update(lo + (hi - lo) * frac * 0.97, tr(label))
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass


async def generate(job: Job) -> dict:
    p = job.params
    mode = p.get("mode", "prompt")
    text = str(p.get("text", "")).strip()
    styles = [str(s) for s in p.get("styles", [])][:6]
    engine = "chinese" if p.get("engine") == "chinese" else "standard"
    duration = max(30, min(300, int(p.get("duration", 120))))
    seed = int(p.get("seed") or random.randint(1, 2**31 - 1))
    if not text:
        raise JobFailed(tr("请先输入歌曲描述或歌词"))

    instrumental = mode == "instrumental"
    description = "" if mode == "lyrics" else text
    if mode == "lyrics":
        lyrics = _normalize_lyrics(text)
    elif instrumental:
        lyrics = "[instrumental]"
    else:
        job.update(3, tr("正在写歌词"))
        lyrics = await llm.write_lyrics(job, text, styles, seed)
    job.title = tr("纯音乐 · {text}", text=text[:10]) if instrumental else _title(lyrics, description)
    job.params = {**p, "seed": seed, "lyrics": lyrics}
    job.save()

    wav = job.dir / "audio.wav"
    if engine == "chinese" and not instrumental:
        model_dir = catalog.model_path("music.yue2").parent
        style = ("Chinese, " if _language(lyrics) == "zh" else "English, ") + _caption(styles, description, False)
        cmd = [config.AUDIOCPP_CLI, "--task", "gen", "--backend", config.AUDIOCPP_BACKEND, "--family", "yue2",
               "--model", model_dir, "--lyrics", lyrics, "--request-option", f"style={style}",
               "--seed", seed, "--out", wav]
        expected = 25 + 7.0 * max(8, len([l for l in lyrics.splitlines() if l and not l.startswith("[")]))
    else:
        model = catalog.model_path("music.ace")
        if model is None:
            raise JobFailed(tr("音乐模型未安装，请在设置里下载"))
        cmd = [config.AUDIOCPP_CLI, "--task", "gen", "--backend", config.AUDIOCPP_BACKEND, "--family", "ace_step",
               "--model", model, "--task-route", "text2music", "--text", _caption(styles, description, instrumental),
               "--duration-seconds", duration, "--seed", seed, "--out", wav]
        if not instrumental:
            cmd += ["--lyrics", lyrics, "--language", _language(lyrics)]
        expected = 15 + 0.65 * duration

    stop = asyncio.Event()
    ticker = asyncio.create_task(_tick(job, expected, time.time(), stop, 10, 92,
                                       ["正在规划旋律与结构", "正在生成演唱与编曲", "正在完成混音"]))
    try:
        await job.run(cmd, cwd=config.AUDIOCPP_ROOT, log_name="music.log")
    finally:
        stop.set()
        await ticker
    if not wav.exists():
        raise JobFailed(tr("生成完成，但没有找到音频文件"))

    job.update(95, tr("正在完成音频文件"))
    m4a = job.dir / "audio.m4a"
    await media.finish_audio(job, wav, m4a)
    return {"audio": "audio.m4a", "wav": "audio.wav", "duration": await media.probe_duration(m4a),
            "lyrics": lyrics, "engine": engine}


async def export_video(job: Job) -> dict:
    source_id = re.sub(r"[^0-9a-f]", "", str(job.params.get("source", "")))
    source_dir = config.LIBRARY_DIR / source_id
    audio = source_dir / "audio.m4a"
    if not source_id or not audio.exists():
        raise JobFailed(tr("请先生成一首可用的歌曲"))
    try:
        title = json.loads((source_dir / "job.json").read_text(encoding="utf-8")).get("title") or tr("歌曲")
    except (OSError, ValueError):
        title = tr("歌曲")
    job.title = tr("{title} · 动效视频", title=title)
    out = job.dir / "video.mp4"
    await media.export_visual_video(job, audio, str(job.params.get("visual", "flow")), out)
    return {"video": "video.mp4", "duration": await media.probe_duration(out)}
