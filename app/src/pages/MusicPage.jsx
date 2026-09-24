import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChatCircleDots,
  DownloadSimple,
  FileText,
  FilmStrip,
  MusicNotes,
  Sparkle,
  Timer,
} from "@phosphor-icons/react";
import { api, fileUrl, formatDuration, saveResult } from "../api";
import { ModelGate } from "../components/ModelGate";
import { Toast, useToast } from "../components/Toast";
import { ExportDialog } from "../components/ExportDialog";
import { JobOverlay } from "../components/JobOverlay";
import { MusicPlayer } from "../components/MusicPlayer";
import { MUSIC_MODES, MUSIC_STYLES, VISUAL_STYLES } from "../data";
import { useAudioPlayer } from "../hooks/useAudioPlayer";
import { useJob } from "../hooks/useJob";
import { t } from "../i18n";

const MODE_ICONS = { prompt: ChatCircleDots, lyrics: FileText, instrumental: MusicNotes };
const DURATIONS = [60, 120, 180, 240];

function estimate(engine, mode, duration, text) {
  if (engine === "chinese" && mode !== "instrumental") {
    const lines = text.split("\n").filter((l) => l.trim() && !l.trim().startsWith("[")).length;
    return 25 + 7 * Math.max(mode === "prompt" ? 20 : 8, lines);
  }
  return 15 + 0.65 * duration + (mode === "prompt" ? 15 : 0);
}

export function MusicPage({ features, serviceReady , onModelsChanged }) {
  const [mode, setMode] = useState("prompt");
  // Unedited modes fall back to the default text in the current UI language.
  const [texts, setTexts] = useState({});
  const [styles, setStyles] = useState(["华语流行", "温柔", "女声"]);
  const [duration, setDuration] = useState(120);
  const [engine, setEngine] = useState("standard");
  const [visual, setVisual] = useState("flow");
  const [song, setSong] = useState(null);
  const [recent, setRecent] = useState([]);
  const [exportState, setExportState] = useState({ open: false });
  const [error, setError] = useState("");
  const toast = useToast();
  const save = async (id, file, title) => {
    try {
      toast.show(await saveResult(id, file, title));
    } catch (e) {
      setError(e.message);
    }
  };

  const feature = (id) => features.find((f) => f.id === id);
  const standardReady = feature("music.standard")?.ready;
  const chineseReady = feature("music.chinese")?.ready;
  const writerReady = feature("music.writer")?.ready;
  const modeInfo = MUSIC_MODES.find((m) => m.id === mode);
  const text = texts[mode] ?? t(modeInfo.defaultValue);
  const effectiveEngine = mode === "instrumental" ? "standard" : engine;

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("music");
      const songs = items.filter((i) => i.task === "generate");
      setRecent(songs);
      setSong((current) => current || songs[0] || null);
    } catch {
      /* service not ready yet */
    }
  }, []);

  useEffect(() => {
    if (serviceReady) loadRecent();
  }, [serviceReady, loadRecent]);

  const generation = useJob((finished) => {
    if (finished.status === "done") {
      setSong(finished);
      loadRecent();
    } else if (finished.status === "error") {
      setError(finished.error || t("生成失败"));
    }
  });

  const exporter = useJob((finished) =>
    setExportState((s) => ({ ...s, status: finished.status, progress: 100, label: finished.error || "", result: finished })),
  );

  useEffect(() => {
    if (exporter.job && exportState.open && exporter.running) {
      setExportState((s) => ({ ...s, progress: Math.round(exporter.job.progress), label: exporter.job.label }));
    }
  }, [exporter.job, exporter.running, exportState.open]);

  const audioSrc = useMemo(() => (song?.result?.audio ? fileUrl(song.id, song.result.audio) : ""), [song]);
  const player = useAudioPlayer(audioSrc, 0);

  const blocked =
    (effectiveEngine === "standard" && !standardReady) ||
    (effectiveEngine === "chinese" && !chineseReady) ||
    (mode === "prompt" && !writerReady);
  const blockedReason = !serviceReady
    ? t("正在连接本地引擎")
    : effectiveEngine === "chinese" && !chineseReady
      ? t("中文精唱模型未安装")
      : !standardReady
        ? t("音乐模型未安装")
        : mode === "prompt" && !writerReady
          ? t("一句话写歌需要先下载写作助手")
          : "";

  const start = async () => {
    setError("");
    try {
      await generation.submit("music", "generate", { mode, text, styles, duration, engine: effectiveEngine });
    } catch (e) {
      setError(e.message);
    }
  };

  const startExport = async () => {
    if (!song) return;
    setExportState({ open: true, status: "running", progress: 0, label: t("正在准备"), result: null });
    try {
      await exporter.submit("music", "export-video", { source: song.id, visual });
    } catch (e) {
      setExportState({ open: true, status: "error", progress: 0, label: e.message });
    }
  };

  const toggleStyle = (style) =>
    setStyles((list) => (list.includes(style) ? list.filter((s) => s !== style) : [...list, style].slice(-4)));

  const expected = Math.round(estimate(effectiveEngine, mode, duration, text));

  return (
    <div className="studio music-page">
      <aside className="composer-panel" aria-label={t("歌曲创作")}>
        <div className="composer-heading">
          <Sparkle size={24} weight="fill" />
          <h1>{t("写一首歌")}</h1>
        </div>

        <div className="mode-switch" role="tablist" aria-label={t("创作方式")}>
          {MUSIC_MODES.map((m) => {
            const Icon = MODE_ICONS[m.id];
            return (
              <button
                key={m.id}
                type="button"
                role="tab"
                aria-selected={mode === m.id}
                className={mode === m.id ? "mode-item is-active" : "mode-item"}
                onClick={() => setMode(m.id)}
              >
                <Icon size={20} />
                <span>{t(m.label)}</span>
              </button>
            );
          })}
        </div>

        <div className="field-group prompt-group">
          <div className="field-label-row">
            <label htmlFor="song-text">{t(modeInfo.inputLabel)}</label>
            <span>
              {text.length} / {modeInfo.maxLength}
            </span>
          </div>
          <textarea
            id="song-text"
            value={text}
            maxLength={modeInfo.maxLength}
            placeholder={t(modeInfo.placeholder)}
            className={mode === "lyrics" ? "prompt-input is-lyrics" : "prompt-input"}
            onChange={(e) => setTexts((prev) => ({ ...prev, [mode]: e.target.value }))}
          />
        </div>

        <div className="field-group">
          <span className="field-label">{t("风格（最多 4 个）")}</span>
          <div className="style-chips">
            {MUSIC_STYLES.map((s) => (
              <button
                key={s}
                type="button"
                className={styles.includes(s) ? "chip is-active" : "chip"}
                aria-pressed={styles.includes(s)}
                onClick={() => toggleStyle(s)}
              >
                {t(s)}
              </button>
            ))}
          </div>
        </div>

        {mode !== "instrumental" ? (
          <div className="field-group">
            <span className="field-label">{t("演唱")}</span>
            <div className="segmented" role="radiogroup" aria-label={t("演唱引擎")}>
              <button
                type="button"
                role="radio"
                aria-checked={engine === "standard"}
                className={engine === "standard" ? "is-active" : ""}
                onClick={() => setEngine("standard")}
              >
                <strong>{t("标准")}</strong>
                <small>{t("速度快，可定时长")}</small>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={engine === "chinese"}
                className={engine === "chinese" ? "is-active" : ""}
                onClick={() => setEngine("chinese")}
                disabled={!chineseReady}
              >
                <strong>{t("中文精唱")}</strong>
                <small>{chineseReady ? t("咬字最准，时长随歌词") : t("未安装")}</small>
              </button>
            </div>
          </div>
        ) : null}

        {effectiveEngine === "standard" ? (
          <div className="field-group duration-group">
            <label htmlFor="song-duration" className="field-label">{t("时长")}</label>
            <div className="select-wrap">
              <Timer size={19} />
              <select id="song-duration" value={duration} onChange={(e) => setDuration(Number(e.target.value))}>
                {DURATIONS.map((d) => (
                  <option key={d} value={d}>{t("{n} 分钟", { n: d / 60 })}</option>
                ))}
              </select>
            </div>
          </div>
        ) : null}

        <button
          type="button"
          className="generate-button"
          disabled={!serviceReady || generation.running || blocked || !text.trim()}
          onClick={start}
        >
          <Sparkle size={21} weight="fill" />
          <span>{generation.running ? t("正在生成…") : t("生成歌曲")}</span>
        </button>
        <p className="generate-note">
          {blockedReason || t("预计约 {time}，全部在本机完成", { time: formatDuration(expected) })}
        </p>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        {serviceReady ? <ModelGate features={features} featureIds={effectiveEngine === "chinese" ? ["music.chinese"] : mode === "prompt" ? ["music.standard", "music.writer"] : ["music.standard"]} onInstalled={onModelsChanged} /> : null}

      </aside>

      <main className="studio-stage">
        <MusicPlayer song={song} player={player} overlay={<JobOverlay job={generation} />} />
        <div className="song-actions">
          <button type="button" className="button button-secondary" disabled={!song} onClick={() => save(song.id, song.result.audio, song.title)}>
            <DownloadSimple size={18} /> {t("下载音频")}
          </button>
          <button type="button" className="button button-secondary" disabled={!song} onClick={() => setExportState({ open: true, status: "choose" })}>
            <FilmStrip size={18} /> {t("导出动效视频")}
          </button>
        </div>
        {recent.length > 1 ? (
          <div className="recent-strip recent-strip-flat" aria-label={t("最近生成")}>
            {recent.slice(0, 8).map((item) => (
              <button key={item.id} type="button" className={song?.id === item.id ? "recent-item is-active" : "recent-item"} onClick={() => setSong(item)}>
                <strong>{item.title || t("未命名")}</strong>
                <span>{formatDuration(item.result?.duration)}</span>
              </button>
            ))}
          </div>
        ) : null}
      </main>

      <Toast message={toast.message} />

      <ExportDialog
        visuals={VISUAL_STYLES}
        visual={visual}
        onVisualChange={setVisual}
        onStart={startExport}
        exportState={{ ...exportState, progress: exportState.progress || 0 }}
        onClose={() => setExportState({ open: false })}
        onDownloadVideo={() => {
          const r = exportState.result;
          if (r?.result?.video) save(r.id, r.result.video, r.title);
        }}
      />
    </div>
  );
}
