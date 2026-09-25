"""End-to-end UI test in WebKit (the engine behind the macOS desktop webview).

Runs against the dev server (npm run dev:all). Real generations are performed, so the
full run takes a few minutes. Screenshots go to $UI_SHOTS (default ./ui-shots).

  uv run --with playwright python app/tests/ui_e2e.py
  UI_FULL=1 uv run --with playwright python app/tests/ui_e2e.py   # also every other mode
"""
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("UI_BASE", "http://localhost:5173")
SHOTS = Path(os.environ.get("UI_SHOTS", "ui-shots"))
ROOT = Path(__file__).resolve().parents[2]
TESTDATA = ROOT / "audio" / "testdata"
SAMPLE_AUDIO = TESTDATA / "paraformer" / "3-sichuan.wav"
LONG = 240_000
VERY_LONG = 900_000  # YuE2 and 720p video

results: list[tuple[str, bool, str]] = []


def step(name):
    def wrap(fn):
        def run(page):
            t = time.time()
            try:
                fn(page)
                results.append((name, True, f"{time.time() - t:.0f}s"))
            except Exception as exc:  # keep going; report at the end
                results.append((name, False, str(exc).splitlines()[0][:160]))
                page.screenshot(path=SHOTS / f"FAIL-{name}.png")
        return run
    return wrap


def here(page, selector, **kwargs):
    """Locator limited to the visible page (creation pages stay mounted while hidden)."""
    return page.locator(".app-main > :not([hidden]) " + selector, **kwargs)


def nav(page, label):
    page.locator(".rail-item", has_text=label).click()


def pick_model(page, name):
    """Choose a model in the visible page's model picker (no-op if already chosen)."""
    button = here(page, ".model-picker-button")
    if name in button.inner_text():
        return
    button.click()
    here(page, ".model-option").filter(has_text=name).click()


@step("导航与各页面加载")
def pages(page):
    for label in ["图片", "视频", "音乐", "语音", "作品", "设置"]:
        nav(page, label)
        expect(page.locator(".rail-item.is-active")).to_contain_text(label)
        page.wait_for_timeout(300)


@step("音乐-播放")
def music_play(page):
    nav(page, "音乐")
    here(page, ".quiet-play").click()
    page.wait_for_timeout(2500)
    t = here(page, ".quiet-time").inner_text()
    assert not t.startswith("0:00 /"), f"playback did not advance: {t}"
    here(page, ".quiet-play").click()


@step("音乐-自己的歌词生成")
def music_generate(page):
    nav(page, "音乐")
    page.get_by_role("tab", name="我的歌词").click()
    here(page, "#song-text").fill("[主歌]\n清晨的风吹过窗台\n阳光落在你的发梢\n[副歌]\n我们一起向前走\n把今天唱成歌")
    pick_model(page, "ACE-Step")
    here(page, "#song-duration").select_option("60")
    before = here(page, ".recent-item").count()
    page.get_by_role("button", name="生成歌曲").click()
    expect(here(page, ".generation-overlay")).to_be_visible(timeout=10_000)
    page.screenshot(path=SHOTS / "music-generating.png")
    expect(here(page, ".generation-overlay")).to_be_hidden(timeout=LONG)
    expect(here(page, ".quiet-player h2")).to_contain_text("清晨的风吹过窗台")
    assert here(page, ".recent-item").count() >= before


@step("音乐-导出动效视频")
def music_export(page):
    # The style is picked under the live preview; export starts right away.
    expect(here(page, ".visual-switch button")).to_have_count(3)
    here(page, ".visual-switch button").nth(1).click()
    page.screenshot(path=SHOTS / "music-visual-preview.png")
    page.get_by_role("button", name="导出动效视频").click()
    expect(page.get_by_text("视频已准备好")).to_be_visible(timeout=LONG)
    page.get_by_role("button", name="关闭").click()


@step("图片-极速生成")
def image_generate(page):
    nav(page, "图片")
    page.get_by_role("tab", name="生成").click()
    here(page, "#img-text").fill("一只纸鹤停在木桌上，柔和的晨光")
    pick_model(page, "FLUX.2 klein 4B")
    page.get_by_role("button", name="生成图片").click()
    wait_job(page)
    expect(here(page, ".result-image")).to_be_visible()
    page.screenshot(path=SHOTS / "image-result.png")


@step("图片-Qwen-Image 2.1 生成与改图")
def image_qwen(page):
    nav(page, "图片")
    page.get_by_role("tab", name="生成").click()
    here(page, "#img-text").fill("一张复古电影海报，标题写着“长安夜话”，唐代长安城夜景，灯笼与飞檐")
    pick_model(page, "Qwen-Image 2.1")
    page.get_by_role("radio", name="3:4").click()
    page.get_by_role("radio", name="标准").first.click()
    page.get_by_role("button", name="生成图片").click()
    wait_job(page)
    expect(here(page, ".result-image")).to_be_visible()
    page.get_by_role("button", name="编辑这张").click()
    here(page, "#img-edit").fill("把标题“长安夜话”改成“洛阳花开”")
    pick_model(page, "Qwen-Image 2.1")
    page.get_by_role("button", name="开始修改").click()
    wait_job(page)
    expect(here(page, ".result-image")).to_be_visible()
    page.screenshot(path=SHOTS / "image-qwen-edit.png")


@step("图片-高清 16:9")
def image_hd(page):
    nav(page, "图片")
    page.get_by_role("tab", name="生成").click()
    here(page, "#img-text").fill("雨后的城市街道，霓虹倒映在积水里，电影感")
    pick_model(page, "Z-Image")
    page.get_by_role("radio", name="16:9").click()
    page.get_by_role("radio", name="高清").first.click()
    page.get_by_role("button", name="生成图片").click()
    wait_job(page)
    img = here(page, ".result-image")
    expect(img).to_be_visible()
    size = img.evaluate("i => [i.naturalWidth, i.naturalHeight]")
    assert size == [1920, 1088], size
    page.get_by_role("radio", name="标准").first.click()


@step("图片-编辑这张")
def image_edit_handoff(page):
    page.get_by_role("button", name="编辑这张").click()
    expect(page.get_by_role("tab", name="编辑")).to_have_attribute("aria-selected", "true")
    expect(here(page, ".source-chosen img")).to_be_visible()


@step("图片-让它动起来→视频")
def image_to_video(page):
    nav(page, "图片")
    page.get_by_role("button", name="让它动起来").click()
    expect(page.locator(".rail-item.is-active")).to_contain_text("视频")
    expect(here(page, ".source-chosen img")).to_be_visible()


@step("视频-图片生成 3 秒")
def video_generate(page):
    here(page, "#video-text").fill("晨光慢慢移动，纸鹤轻轻晃动")
    here(page, "#video-seconds").select_option("3")
    page.get_by_role("button", name="生成视频").click()
    wait_job(page)
    expect(here(page, "video.result-video")).to_be_visible()
    page.screenshot(path=SHOTS / "video-result.png")


@step("语音-预设音色配音")
def speech_tts(page):
    nav(page, "语音")
    page.get_by_role("tab", name="配音").click()
    here(page, "#tts-text").fill("欢迎使用本地创作台，所有内容都在这台电脑上生成。")
    here(page, ".voice", has_text="云希").click()
    page.get_by_role("button", name="生成配音").click()
    expect(here(page, ".transcript audio")).to_be_visible(timeout=LONG)


@step("语音-上传录音转文字")
def speech_asr(page):
    nav(page, "语音")
    page.get_by_role("tab", name="转文字").click()
    here(page, 'input[type="file"]').set_input_files(str(SAMPLE_AUDIO))
    expect(here(page, ".source-chosen")).to_be_visible(timeout=20_000)
    pick_model(page, "Qwen3-ASR 1.7B")
    page.get_by_role("button", name="开始转文字").click()
    expect(here(page, ".transcript p")).to_contain_text("特别好", timeout=LONG)
    expect(page.get_by_role("button", name="下载字幕（SRT）")).to_be_visible()
    page.screenshot(path=SHOTS / "speech-transcript.png")


def wait_job(page, timeout=LONG):
    expect(here(page, ".generation-overlay")).to_be_visible(timeout=10_000)
    expect(here(page, ".generation-overlay")).to_be_hidden(timeout=timeout)
    expect(here(page, ".form-error")).to_have_count(0)


@step("音乐-一句话写歌")
def music_prompt(page):
    nav(page, "音乐")
    page.get_by_role("tab", name="一句话").click()
    here(page, "#song-text").fill("一首关于夏天海边的轻快华语流行歌，清爽男声")
    pick_model(page, "ACE-Step")
    here(page, "#song-duration").select_option("60")
    page.get_by_role("button", name="生成歌曲").click()
    wait_job(page)
    expect(here(page, ".quiet-lyrics p").first).to_be_visible()  # the writer produced lyrics
    page.screenshot(path=SHOTS / "music-prompt.png")


@step("音乐-纯音乐")
def music_instrumental(page):
    page.get_by_role("tab", name="纯音乐").click()
    here(page, "#song-text").fill("清晨的森林，木吉他与长笛，安静温暖")
    here(page, "#song-duration").select_option("60")
    page.get_by_role("button", name="生成歌曲").click()
    wait_job(page)
    expect(here(page, ".quiet-lyrics")).to_have_count(0)
    expect(here(page, ".quiet-player header p")).to_contain_text("标准")


@step("音乐-中文精唱")
def music_chinese(page):
    page.get_by_role("tab", name="我的歌词").click()
    here(page, "#song-text").fill("[主歌]\n窗外的桂花开了\n我们走过那条小街\n[副歌]\n月亮挂在屋檐上\n照亮回家的路")
    pick_model(page, "YuE2")
    page.get_by_role("button", name="生成歌曲").click()
    wait_job(page, VERY_LONG)
    expect(here(page, ".quiet-player header p")).to_contain_text("中文精唱")
    expect(here(page, ".quiet-player h2")).to_contain_text("窗外的桂花开了")
    pick_model(page, "ACE-Step")


@step("图片-精细生成（带中文字）")
def image_standard(page):
    nav(page, "图片")
    page.get_by_role("tab", name="生成").click()
    here(page, "#img-text").fill("一张简洁的咖啡店海报，大字写着“晨光咖啡”，暖色调")
    pick_model(page, "Z-Image")
    page.get_by_role("button", name="生成图片").click()
    wait_job(page)
    expect(here(page, ".result-image")).to_be_visible()
    page.screenshot(path=SHOTS / "image-standard.png")


@step("图片-执行编辑")
def image_edit_run(page):
    before = here(page, ".result-image").get_attribute("src")
    page.get_by_role("button", name="编辑这张").click()
    here(page, "#img-edit").fill("把背景换成下雪的冬夜")
    page.get_by_role("button", name="开始修改").click()
    wait_job(page)
    expect(here(page, ".result-image")).not_to_have_attribute("src", before)
    page.screenshot(path=SHOTS / "image-edit.png")


@step("视频-文字生成 5 秒 480p")
def video_text(page):
    nav(page, "视频")
    page.get_by_role("tab", name="文字生成").click()
    here(page, "#video-text").fill("海浪拍打礁石，夕阳下的海鸥飞过")
    here(page, "#video-seconds").select_option("5")
    here(page, "#video-resolution").select_option("480p")
    page.get_by_role("button", name="生成视频").click()
    wait_job(page)
    expect(here(page, "video.result-video")).to_be_visible()


@step("视频-文字生成 3 秒 720p")
def video_720(page):
    here(page, "#video-text").fill("城市街道的雨夜，霓虹灯倒映在积水里")
    here(page, "#video-seconds").select_option("3")
    here(page, "#video-resolution").select_option("720p")
    page.get_by_role("button", name="生成视频").click()
    wait_job(page, VERY_LONG)
    expect(here(page, "video.result-video")).to_be_visible()
    here(page, "#video-resolution").select_option("480p")


@step("语音-中英混排配音")
def speech_mixed(page):
    nav(page, "语音")
    page.get_by_role("tab", name="配音").click()
    here(page, "#tts-text").fill("今天我们发布了 TopLocal Studio 的第一个版本。")
    here(page, ".voice").first.click()
    page.get_by_role("button", name="生成配音").click()
    expect(here(page, ".transcript p")).to_contain_text("TopLocal", timeout=LONG)


@step("语音-声音克隆")
def speech_clone(page):
    here(page, ".voice-clone").click()
    here(page, 'input[type="file"]').set_input_files(str(TESTDATA / "paraformer" / "1.wav"))
    expect(here(page, ".source-chosen")).to_be_visible(timeout=20_000)
    here(page, "#tts-text").fill("这是用我自己的声音读出来的一句话。")
    page.get_by_role("button", name="生成配音").click()
    expect(here(page, ".transcript p")).to_contain_text("我自己的声音", timeout=LONG)
    expect(here(page, ".transcript audio")).to_be_visible()


@step("语音-标准与极速转文字")
def speech_asr_modes(page):
    nav(page, "语音")
    page.get_by_role("tab", name="转文字").click()
    for model, clip, words in [("Qwen3-ASR 0.6B", "sensevoice/zh.wav", "九点"), ("SenseVoice", "paraformer/1.wav", "金融")]:
        if here(page, ".source-chosen").count():
            here(page, "[title=\"移除\"]").click()
        here(page, 'input[type="file"]').set_input_files(str(TESTDATA / clip))
        expect(here(page, ".source-chosen")).to_be_visible(timeout=20_000)
        pick_model(page, model)
        page.get_by_role("button", name="开始转文字").click()
        expect(here(page, ".transcript p")).to_contain_text(words, timeout=LONG)


@step("示例-图片填入后生成")
def example_image(page):
    nav(page, "图片")
    if here(page, ".thumb-examples").count():
        here(page, ".thumb-examples").click()
    here(page, ".example-card", has_text="浇花机器人").click()
    expect(here(page, ".generation-overlay")).to_have_count(0)  # filling in never starts a job
    here(page, ".generate-button").click()
    wait_job(page)
    expect(here(page, ".result-image")).to_be_visible()
    expect(here(page, "#img-text")).to_have_value("一个可爱的小机器人在阳台上给花浇水")


@step("示例-纯音乐填入后生成")
def example_music(page):
    nav(page, "音乐")
    here(page, ".recent-examples").click()
    here(page, ".example-card", has_text="雨天学习").click()
    here(page, ".generate-button").click()
    wait_job(page)
    expect(here(page, ".quiet-player h2")).to_be_visible()
    expect(here(page, ".quiet-lyrics")).to_have_count(0)


@step("示例-录音转文字（中英）")
def example_asr(page):
    nav(page, "语音")
    page.get_by_role("tab", name="转文字").click()
    for card, words in [("示例录音", "创作台"), ("英文录音", "computer")]:
        if here(page, ".recent-examples").count():
            here(page, ".recent-examples").click()
        here(page, ".example-card", has_text=card).click()
        here(page, ".generate-button").click()
        expect(here(page, ".transcript p")).to_contain_text(words, timeout=LONG)


@step("示例-配音填入后生成")
def example_tts(page):
    page.get_by_role("tab", name="配音").click()
    if here(page, ".recent-examples").count():
        here(page, ".recent-examples").click()
    here(page, ".example-card", has_text="睡前故事").click()
    here(page, ".generate-button").click()
    expect(here(page, ".transcript p")).to_contain_text("小兔子", timeout=LONG)
    expect(here(page, ".transcript audio")).to_be_visible()


@step("作品库-筛选与删除确认")
def library(page):
    nav(page, "作品")
    for tab in ["音乐", "图片", "视频", "语音", "全部"]:
        page.get_by_role("tab", name=tab).click()
        page.wait_for_timeout(300)
    assert here(page, ".library-card").count() > 0, "library is empty"
    card = here(page, ".library-card").first
    card.get_by_title("删除").click()
    expect(card.get_by_text("确认删除")).to_be_visible()
    card.get_by_title("取消").click()
    expect(card.get_by_text("确认删除")).to_be_hidden()
    page.screenshot(path=SHOTS / "library.png")


@step("设置-深色模式与各页截图")
def dark_mode(page):
    nav(page, "设置")
    page.get_by_role("radio", name="深色").click()
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    for label, name in [("音乐", "music"), ("图片", "image"), ("视频", "video"), ("语音", "speech"),
                        ("作品", "library"), ("设置", "settings")]:
        nav(page, label)
        page.wait_for_timeout(500)
        page.screenshot(path=SHOTS / f"dark-{name}.png")
    nav(page, "设置")
    page.get_by_role("radio", name="浅色").click()
    for label, name in [("音乐", "music"), ("图片", "image"), ("视频", "video"), ("语音", "speech"),
                        ("作品", "library"), ("设置", "settings")]:
        nav(page, label)
        page.wait_for_timeout(500)
        page.screenshot(path=SHOTS / f"light-{name}.png")


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.webkit.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script("localStorage.setItem('toplocal-language', 'zh')")  # tests use the Chinese labels
        # UI_RUNTIME='{"baseUrl": "http://127.0.0.1:PORT", "token": "..."}' drives a packaged app's service
        # the way the desktop shell does (serve app/dist and point UI_BASE at it).
        if os.environ.get("UI_RUNTIME"):
            page.add_init_script(f"window.__LOCALAI__ = {os.environ['UI_RUNTIME']};")
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto(BASE)
        expect(page.locator(".rail[data-service=ready]")).to_be_visible(timeout=30_000)
        suite = [pages, music_generate, music_play, music_export, image_generate, image_edit_handoff,
                 image_to_video, video_generate, speech_tts, speech_asr, library, dark_mode]
        if os.environ.get("UI_FULL") == "1":  # every mode; about 20 extra minutes of generation
            suite[-2:-2] = [music_prompt, music_instrumental, music_chinese, image_standard, image_edit_run,
                            image_qwen, image_hd, video_text, video_720, speech_mixed, speech_clone, speech_asr_modes,
                            example_image, example_music, example_asr, example_tts]
        for test in suite:
            test(page)
        browser.close()
    width = max(len(n) for n, _, _ in results)
    for name, ok, info in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {info}")
    print(f"\n{sum(ok for _, ok, _ in results)}/{len(results)} passed")
    if errors:
        print("\nBrowser errors:")
        for e in errors[:20]:
            print("  ", e[:200])
    return 0 if all(ok for _, ok, _ in results) and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
