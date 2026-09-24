"""End-to-end UI test in WebKit (the engine behind the macOS desktop webview).

Runs against the dev server (npm run dev:all). Real generations are performed, so the
full run takes a few minutes. Screenshots go to $UI_SHOTS (default ./ui-shots).

  uv run --with playwright python app/tests/ui_e2e.py
"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("UI_BASE", "http://localhost:5173")
SHOTS = Path(os.environ.get("UI_SHOTS", "ui-shots"))
ROOT = Path(__file__).resolve().parents[2]
SAMPLE_AUDIO = ROOT / "audio" / "testdata" / "paraformer" / "3-sichuan.wav"
LONG = 240_000

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


def nav(page, label):
    page.locator(".rail-item", has_text=label).click()


@step("导航与各页面加载")
def pages(page):
    for label in ["图片", "视频", "音乐", "语音", "作品", "设置"]:
        nav(page, label)
        expect(page.locator(".rail-item.is-active")).to_contain_text(label)
        page.wait_for_timeout(300)


@step("音乐-播放")
def music_play(page):
    nav(page, "音乐")
    page.locator(".quiet-play").click()
    page.wait_for_timeout(2500)
    t = page.locator(".quiet-time").inner_text()
    assert not t.startswith("0:00 /"), f"playback did not advance: {t}"
    page.locator(".quiet-play").click()


@step("音乐-自己的歌词生成")
def music_generate(page):
    nav(page, "音乐")
    page.get_by_role("tab", name="我的歌词").click()
    page.locator("#song-text").fill("[主歌]\n清晨的风吹过窗台\n阳光落在你的发梢\n[副歌]\n我们一起向前走\n把今天唱成歌")
    page.locator("#song-duration").select_option("60")
    before = page.locator(".recent-item").count()
    page.get_by_role("button", name="生成歌曲").click()
    expect(page.locator(".generation-overlay")).to_be_visible(timeout=10_000)
    page.screenshot(path=SHOTS / "music-generating.png")
    expect(page.locator(".generation-overlay")).to_be_hidden(timeout=LONG)
    expect(page.locator(".quiet-player h2")).to_contain_text("清晨的风吹过窗台")
    assert page.locator(".recent-item").count() >= before


@step("音乐-导出动效视频")
def music_export(page):
    page.get_by_role("button", name="导出动效视频").click()
    expect(page.locator(".visual-choice .thumb")).to_have_count(3)
    page.screenshot(path=SHOTS / "music-export-choose.png")
    page.locator(".visual-choice .thumb").nth(1).click()
    page.get_by_role("button", name="开始导出").click()
    expect(page.get_by_text("视频已准备好")).to_be_visible(timeout=LONG)
    page.get_by_role("button", name="关闭").click()


@step("图片-极速生成")
def image_generate(page):
    nav(page, "图片")
    page.get_by_role("tab", name="生成").click()
    page.locator("#img-text").fill("一只纸鹤停在木桌上，柔和的晨光")
    page.get_by_role("radio", name="极速").click()
    page.get_by_role("button", name="生成图片").click()
    expect(page.locator(".generation-overlay")).to_be_visible(timeout=10_000)
    expect(page.locator(".generation-overlay")).to_be_hidden(timeout=LONG)
    expect(page.locator(".result-image")).to_be_visible()
    page.screenshot(path=SHOTS / "image-result.png")


@step("图片-编辑这张")
def image_edit_handoff(page):
    page.get_by_role("button", name="编辑这张").click()
    expect(page.get_by_role("tab", name="编辑")).to_have_attribute("aria-selected", "true")
    expect(page.locator(".source-chosen img")).to_be_visible()


@step("图片-让它动起来→视频")
def image_to_video(page):
    nav(page, "图片")
    page.get_by_role("button", name="让它动起来").click()
    expect(page.locator(".rail-item.is-active")).to_contain_text("视频")
    expect(page.locator(".source-chosen img")).to_be_visible()


@step("视频-图片生成 3 秒")
def video_generate(page):
    page.locator("#video-text").fill("晨光慢慢移动，纸鹤轻轻晃动")
    page.get_by_role("radio", name="3 秒").click()
    page.get_by_role("button", name="生成视频").click()
    expect(page.locator(".generation-overlay")).to_be_visible(timeout=10_000)
    expect(page.locator(".generation-overlay")).to_be_hidden(timeout=LONG)
    expect(page.locator("video.result-video")).to_be_visible()
    page.screenshot(path=SHOTS / "video-result.png")


@step("语音-预设音色配音")
def speech_tts(page):
    nav(page, "语音")
    page.get_by_role("tab", name="配音").click()
    page.locator("#tts-text").fill("欢迎使用本地创作台，所有内容都在这台电脑上生成。")
    page.locator(".voice", has_text="云希").click()
    page.get_by_role("button", name="生成配音").click()
    expect(page.locator(".transcript audio")).to_be_visible(timeout=LONG)


@step("语音-上传录音转文字")
def speech_asr(page):
    page.get_by_role("tab", name="转文字").click()
    page.locator('input[type="file"]').set_input_files(str(SAMPLE_AUDIO))
    expect(page.locator(".source-chosen")).to_be_visible(timeout=20_000)
    page.get_by_role("radio", name="精准").click()
    page.get_by_role("button", name="开始转文字").click()
    expect(page.locator(".transcript p")).to_contain_text("特别好", timeout=LONG)
    expect(page.get_by_role("button", name="下载字幕（SRT）")).to_be_visible()
    page.screenshot(path=SHOTS / "speech-transcript.png")


@step("作品库-筛选与删除确认")
def library(page):
    nav(page, "作品")
    for tab in ["音乐", "图片", "视频", "语音", "全部"]:
        page.get_by_role("tab", name=tab).click()
        page.wait_for_timeout(300)
    assert page.locator(".library-card").count() > 0, "library is empty"
    card = page.locator(".library-card").first
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
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto(BASE)
        expect(page.locator(".rail-status.is-ready")).to_be_visible(timeout=30_000)
        for test in [pages, music_play, music_generate, music_export, image_generate, image_edit_handoff,
                     image_to_video, video_generate, speech_tts, speech_asr, library, dark_mode]:
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
