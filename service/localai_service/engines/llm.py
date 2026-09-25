"""Small local LLM (llama.cpp) used as a writing assistant: song lyrics, prompt expansion."""
import re

from .. import catalog, config
from ..i18n import tr
from ..jobs import Job, JobFailed

LYRICS_SYSTEM = (
    "你是一位专业作词人。根据用户对歌曲的描述写一首可以直接演唱的歌词。"
    "要求：使用和描述相同的语言；结构为 [Verse]、[Pre-Chorus]、[Chorus]、[Verse]、[Chorus]、[Bridge]、[Chorus]；"
    "每段 2 到 4 行，每行不超过 14 个字；副歌押韵、朗朗上口；"
    "中文歌词里不要夹杂任何英文单词；英文歌词全部用英文。"
    "只输出歌词本身，每段前用英文方括号标出段落名，不要解释，不要标题。"
)


def _chatml(system: str, user: str) -> str:
    return (f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n")


async def complete(job: Job, system: str, user: str, *, max_tokens: int = 700, temperature: float = 0.8,
                   seed: int = -1) -> str:
    model = catalog.model_path("llm.writer")
    if model is None:
        raise JobFailed(tr("写作助手模型未安装，请在设置里下载后再试，或切换到“我的歌词”模式"))
    out = await job.run([
        config.LLAMA_COMPLETION, "-m", model, "-p", _chatml(system, user), "-no-cnv", "--no-display-prompt",
        "-n", str(max_tokens), "--temp", str(temperature), "-s", str(seed), "-ngl", "99", "-c", "4096",
        "--simple-io", "--no-warmup",
    ], log_name="llm.log")
    return out.split("<|im_end|>")[0].replace("[end of text]", "").strip()


def clean_lyrics(text: str) -> str:
    """Keep bracketed section tags and lyric lines; drop chatter the model may add."""
    lines = []
    for line in text.splitlines():
        line = line.strip().strip("*")
        if not line:
            if lines and lines[-1]:
                lines.append("")
            continue
        if re.match(r"^(歌词|标题|Title|Lyrics)[:：]", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


async def write_lyrics(job: Job, description: str, styles: list[str], seed: int) -> str:
    chinese = bool(re.search(r"[\u4e00-\u9fff]", description))
    style = f"风格：{'、'.join(styles)}。" if styles else ""
    # Style tags are Chinese labels; state the lyric language explicitly so an English
    # description still gets English lyrics.
    language = "歌词全部使用中文。" if chinese else "Write the lyrics entirely in English."
    text = await complete(job, LYRICS_SYSTEM, f"{style}歌曲描述：{description}\n{language}", seed=seed)
    lyrics = clean_lyrics(text)
    if chinese:
        # Chinese song: drop stray Latin words inside lyric lines (section tags stay).
        lyrics = "\n".join(
            l if l.startswith("[") else re.sub(r"\s*[A-Za-z][A-Za-z'’-]*", "", l).strip()
            for l in lyrics.splitlines()
        )
    if "[" not in lyrics or len(lyrics) < 20:
        raise JobFailed(tr("歌词生成失败，请换个描述再试一次"))
    return lyrics


VIDEO_SYSTEM = (
    "You write prompts for a text-to-video model. Rewrite the user's idea as one English paragraph "
    "of 60 to 110 words describing, in present tense: the main subject and its appearance, the action "
    "as it unfolds over a few seconds, the setting, lighting and colors, the camera movement, and the "
    "ambient sounds. Keep every concrete detail the user gave. Do not add text overlays or dialogue "
    "unless asked. Output only the paragraph."
)


async def video_prompt(job: Job, idea: str, from_image: bool, image_desc: str = "") -> str:
    """Expand a short idea into the detailed English prompt LTX works best with."""
    hint = ""
    if from_image:
        hint = ("The first frame is given as an image; describe the motion that follows and keep the exact "
                "visual style of that image (for a painting or illustration, say so explicitly in the first "
                "sentence and keep it that medium, never turn it into a photograph). ")
        if image_desc:
            hint += f"The image shows: {image_desc}. "
        hint += "Motion requested: "
    text = await complete(job, VIDEO_SYSTEM, hint + idea, max_tokens=260, temperature=0.6)
    text = " ".join(text.split())
    return text if len(text) > 40 else idea


IMAGE_SYSTEM = (
    "你是文生图提示词助手。把用户的一句话扩写成一段适合图像模型的画面描述，"
    "包含主体、环境、光线、构图、色调和风格，60 到 120 字。"
    "用户写在引号里的文字必须原样保留在引号里。使用和用户相同的语言。只输出描述本身，不要解释。"
)
MUSIC_SYSTEM = (
    "你是音乐制作助手。把用户对歌曲的简单描述扩写得更具体：情绪、节奏、乐器、人声和段落起伏，"
    "40 到 80 字。使用和用户相同的语言。只输出描述本身，不要写歌词，不要解释。"
)


async def enhance(job: Job) -> dict:
    """"Polish" button: expand a short idea into a fuller prompt for the chosen module."""
    p = job.params
    text = str(p.get("text", "")).strip()[:500]
    if not text:
        raise JobFailed(tr("先写一句想法，再让写作助手润色"))
    target = p.get("target")
    job.update(10, tr("正在润色"))
    if target == "video":
        out = await video_prompt(job, text, bool(p.get("fromImage")))
    else:
        system = MUSIC_SYSTEM if target == "music" else IMAGE_SYSTEM
        out = await complete(job, system, text, max_tokens=300, temperature=0.7)
    out = out.strip().strip("“”\"").strip()
    # The model sometimes repeats the user's line after its answer.
    if out.endswith(text) and len(out) > len(text) + 10:
        out = out[: -len(text)].rstrip()
    if not out:
        raise JobFailed(tr("润色失败，请重试"))
    return {"text": out}
