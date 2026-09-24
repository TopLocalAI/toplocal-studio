import { useEffect, useMemo, useRef } from "react";
import { MusicNotes, Pause, Play, SkipBack, SkipForward, SpeakerHigh } from "@phosphor-icons/react";
import { formatDuration } from "../api";
import { t } from "../i18n";

const SECTION_NAMES = {
  verse: "主歌", chorus: "副歌", "pre-chorus": "导歌", bridge: "桥段",
  intro: "前奏", outro: "尾声", instrumental: "间奏", hook: "副歌",
};

// Lyrics with the model's [Verse]/[Chorus] tags shown as small Chinese section labels.
function Lyrics({ text }) {
  return (
    <div className="quiet-lyrics">
      {text.split("\n").map((line, i) => {
        const tag = line.trim().match(/^\[([^\]]+)\]$/);
        if (tag) {
          const key = tag[1].toLowerCase().replace(/\s+\d+$/, "");
          return <span key={i} className="lyric-tag">{SECTION_NAMES[key] ? t(SECTION_NAMES[key]) : tag[1]}</span>;
        }
        return line.trim() ? <p key={i}>{line}</p> : <br key={i} />;
      })}
    </div>
  );
}

// Deterministic pseudo-waveform per song so the bar looks like "this song", not random noise.
function bars(seed, count = 96) {
  let x = 0;
  for (const ch of seed) x = (x * 31 + ch.charCodeAt(0)) >>> 0;
  return Array.from({ length: count }, (_, i) => {
    x = (x * 1103515245 + 12345) >>> 0;
    const base = 0.35 + 0.35 * Math.sin(i / 7) ** 2;
    return Math.max(0.12, Math.min(1, base + ((x % 1000) / 1000 - 0.5) * 0.5));
  });
}

function Waveform({ seed, currentTime, duration, onSeek }) {
  const heights = useMemo(() => bars(seed || "empty"), [seed]);
  const ref = useRef(null);
  const played = duration ? currentTime / duration : 0;
  return (
    <div
      ref={ref}
      className="quiet-wave"
      role="slider"
      tabIndex={0}
      aria-label={t("播放进度")}
      aria-valuemin={0}
      aria-valuemax={Math.round(duration)}
      aria-valuenow={Math.round(currentTime)}
      onClick={(e) => {
        const r = ref.current.getBoundingClientRect();
        onSeek(((e.clientX - r.left) / r.width) * duration);
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowRight") onSeek(currentTime + 5);
        if (e.key === "ArrowLeft") onSeek(currentTime - 5);
      }}
    >
      {heights.map((h, i) => (
        <i key={i} style={{ height: `${h * 100}%` }} className={i / heights.length < played ? "is-played" : ""} />
      ))}
    </div>
  );
}

export function MusicPlayer({ song, player, overlay }) {
  const duration = player.duration || song?.result?.duration || 0;
  const lyrics = song?.result?.lyrics && song.result.lyrics !== "[instrumental]" ? song.result.lyrics : "";

  // Space toggles playback when focus is not in a text field.
  useEffect(() => {
    const onKey = (e) => {
      if (e.code !== "Space" || ["TEXTAREA", "INPUT", "SELECT", "BUTTON"].includes(e.target.tagName)) return;
      e.preventDefault();
      player.toggle();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [player]);

  return (
    <section className="quiet-player" aria-label={t("播放器")}>
      {song ? (
        <>
          <header>
            <h2>{song.title || t("未命名")}</h2>
            <p>
              {formatDuration(duration)} · {song.result?.engine === "chinese" ? t("中文精唱") : t("标准")} · {t("本机生成")}
            </p>
          </header>
          <Waveform seed={song.id} currentTime={player.currentTime} duration={duration} onSeek={player.seek} />
          <div className="quiet-controls">
            <button type="button" className="quiet-play" aria-label={player.isPlaying ? t("暂停") : t("播放")} onClick={player.toggle}>
              {player.isPlaying ? <Pause size={20} weight="fill" /> : <Play size={20} weight="fill" />}
            </button>
            <button type="button" className="icon-button" aria-label={t("后退 10 秒")} onClick={() => player.skip(-10)}>
              <SkipBack size={16} weight="fill" />
            </button>
            <button type="button" className="icon-button" aria-label={t("前进 10 秒")} onClick={() => player.skip(10)}>
              <SkipForward size={16} weight="fill" />
            </button>
            <span className="quiet-time">
              {formatDuration(player.currentTime)} / {formatDuration(duration)}
            </span>
            <SpeakerHigh size={17} className="quiet-volume-icon" />
            <input
              className="volume-range"
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={player.volume}
              aria-label={t("音量")}
              onChange={(e) => player.setVolume(Number(e.target.value))}
            />
          </div>
          {lyrics ? <Lyrics text={lyrics} /> : null}
        </>
      ) : (
        <div className="result-empty">
          <MusicNotes size={40} />
          <p>{t("写好描述，点“生成歌曲”")}</p>
        </div>
      )}
      {overlay}
    </section>
  );
}
