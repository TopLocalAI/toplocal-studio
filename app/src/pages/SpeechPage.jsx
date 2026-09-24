import { useCallback, useEffect, useState } from "react";
import { DownloadSimple, Microphone, Sparkle, Subtitles, TextAa, UserSound } from "@phosphor-icons/react";
import { api, fileUrl, formatDuration, saveResult } from "../api";
import { JobOverlay } from "../components/JobOverlay";
import { SourcePicker } from "../components/SourcePicker";
import { ModelGate } from "../components/ModelGate";
import { Toast, useToast } from "../components/Toast";
import { useJob } from "../hooks/useJob";

const QUALITIES = [
  { id: "standard", name: "标准", note: "准确又快" },
  { id: "accurate", name: "精准", note: "方言口音更稳" },
  { id: "fast", name: "极速", note: "长录音首选" },
];
const LANGUAGES = [
  { id: "", name: "自动识别" },
  { id: "zh", name: "普通话" },
  { id: "yue", name: "粤语" },
  { id: "en", name: "英语" },
  { id: "ja", name: "日语" },
  { id: "ko", name: "韩语" },
];

export function SpeechPage({ features, serviceReady , onModelsChanged }) {
  const [mode, setMode] = useState("transcribe");
  const [source, setSource] = useState(null);
  const [quality, setQuality] = useState("standard");
  const [language, setLanguage] = useState("");
  const [text, setText] = useState("");
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("zf_xiaoxiao");
  const [cloneSource, setCloneSource] = useState(null);
  const [current, setCurrent] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");
  const toast = useToast();

  const ready = (id) => features.find((f) => f.id === id)?.ready;

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("speech");
      setRecent(items);
    } catch {
      /* not ready */
    }
  }, []);

  useEffect(() => {
    if (!serviceReady) return;
    loadRecent();
    api.voices().then((r) => setVoices(r.voices)).catch(() => setVoices([]));
  }, [serviceReady, loadRecent]);

  const job = useJob((finished) => {
    if (finished.status === "done") {
      setCurrent(finished);
      loadRecent();
    } else if (finished.status === "error") setError(finished.error || "处理失败");
  });

  const run = async () => {
    setError("");
    try {
      if (mode === "transcribe") {
        await job.submit("speech", "transcribe", { source, sourceName: source?.name, quality, language });
      } else {
        const v = voice === "clone" ? { clone: cloneSource } : { preset: voice };
        await job.submit("speech", "synthesize", { text, voice: v });
      }
    } catch (e) {
      setError(e.message);
    }
  };

  const save = (file, suffix = "") =>
    saveResult(current.id, file, current.title + suffix).then(toast.show, (e) => setError(e.message));

  const canRun =
    serviceReady &&
    !job.running &&
    (mode === "transcribe"
      ? source && ready("speech.transcribe")
      : text.trim() && ready("speech.synthesize") && (voice !== "clone" || cloneSource));

  const shown = current && current.task === mode ? current : null;

  return (
    <div className="studio">
      <aside className="composer-panel" aria-label="语音">
        <div className="composer-heading">
          <Sparkle size={24} weight="fill" />
          <h1>声音和文字</h1>
        </div>
        <div className="mode-switch mode-switch-2" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "transcribe"} className={mode === "transcribe" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("transcribe")}>
            <Subtitles size={20} />
            <span>转文字</span>
          </button>
          <button type="button" role="tab" aria-selected={mode === "synthesize"} className={mode === "synthesize" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("synthesize")}>
            <Microphone size={20} />
            <span>配音</span>
          </button>
        </div>

        {mode === "transcribe" ? (
          <>
            <div className="field-group">
              <span className="field-label">录音或视频</span>
              <SourcePicker kind="audio" value={source} onChange={setSource} label="上传录音或视频" />
              <small className="field-hint">支持 mp3、m4a、wav、mp4、mov 等，长度不限</small>
            </div>
            <div className="field-group">
              <span className="field-label">识别模式</span>
              <div className="segmented segmented-3" role="radiogroup">
                {QUALITIES.map((q) => (
                  <button key={q.id} type="button" role="radio" aria-checked={quality === q.id} className={quality === q.id ? "is-active" : ""} onClick={() => setQuality(q.id)}>
                    <strong>{q.name}</strong>
                    <small>{q.note}</small>
                  </button>
                ))}
              </div>
            </div>
            <div className="field-group duration-group">
              <label htmlFor="asr-lang" className="field-label">语言</label>
              <div className="select-wrap">
                <TextAa size={19} />
                <select id="asr-lang" value={language} onChange={(e) => setLanguage(e.target.value)}>
                  {LANGUAGES.map((l) => (
                    <option key={l.id} value={l.id}>{l.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="field-group prompt-group">
              <div className="field-label-row">
                <label htmlFor="tts-text">要朗读的文字</label>
                <span>{text.length} / 5000</span>
              </div>
              <textarea id="tts-text" className="prompt-input" maxLength={5000} value={text} placeholder="输入或粘贴一段文字，中英文混排也可以" onChange={(e) => setText(e.target.value)} />
            </div>
            <div className="field-group">
              <span className="field-label">音色</span>
              <div className="voice-grid">
                {voices.map((v) => (
                  <button key={v.id} type="button" className={voice === v.id ? "voice is-active" : "voice"} onClick={() => setVoice(v.id)}>
                    {v.name}
                  </button>
                ))}
                <button type="button" className={voice === "clone" ? "voice voice-clone is-active" : "voice voice-clone"} onClick={() => setVoice("clone")}>
                  <UserSound size={16} /> 用我的声音
                </button>
              </div>
            </div>
            {voice === "clone" ? (
              <div className="field-group">
                <span className="field-label">一段 5–20 秒的清晰录音</span>
                <SourcePicker kind="audio" value={cloneSource} onChange={setCloneSource} label="上传你的录音" />
                <small className="field-hint">只用于本次配音，全程在本机处理</small>
              </div>
            ) : null}
          </>
        )}

        <button type="button" className="generate-button" disabled={!canRun} onClick={run}>
          <Sparkle size={21} weight="fill" />
          <span>{job.running ? "处理中…" : mode === "transcribe" ? "开始转文字" : "生成配音"}</span>
        </button>
        <p className="generate-note">
          {!serviceReady ? "正在连接本地引擎" : mode === "transcribe" ? "1 小时录音约 2–5 分钟，全部在本机完成" : "几秒到几十秒，全部在本机完成"}
        </p>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        {serviceReady ? <ModelGate features={features} featureIds={mode === "transcribe" ? ["speech.transcribe"] : ["speech.synthesize"]} onInstalled={onModelsChanged} /> : null}
      </aside>

      <main className="studio-stage">
        <div className="result-frame result-text">
          {shown?.task === "transcribe" ? (
            <article className="transcript">
              <header>
                <strong>{shown.title}</strong>
                <span>{formatDuration(shown.result.duration)} 录音</span>
              </header>
              <p>{shown.result.preview}{shown.result.preview?.length >= 2000 ? "……（完整内容请下载）" : ""}</p>
            </article>
          ) : shown?.task === "synthesize" ? (
            <article className="transcript">
              <header>
                <strong>{shown.title}</strong>
                <span>{formatDuration(shown.result.duration)}</span>
              </header>
              <audio controls src={fileUrl(shown.id, shown.result.audio)} />
              <p>{shown.result.text}</p>
            </article>
          ) : (
            <div className="result-empty">
              {mode === "transcribe" ? <Subtitles size={40} weight="duotone" /> : <Microphone size={40} weight="duotone" />}
              <p>{mode === "transcribe" ? "上传录音，得到文字稿和字幕" : "输入文字，选一个音色"}</p>
            </div>
          )}
          <JobOverlay job={job} />
        </div>
        {shown ? (
          <div className="song-actions">
            {shown.task === "transcribe" ? (
              <>
                <button type="button" className="button button-secondary" onClick={() => save(shown.result.text)}>
                  <DownloadSimple size={18} /> 下载文字稿（TXT）
                </button>
                <button type="button" className="button button-secondary" onClick={() => save(shown.result.srt, " 字幕")}>
                  <DownloadSimple size={18} /> 下载字幕（SRT）
                </button>
              </>
            ) : (
              <button type="button" className="button button-secondary" onClick={() => save(shown.result.audio)}>
                <DownloadSimple size={18} /> 下载音频
              </button>
            )}
          </div>
        ) : null}
        {recent.filter((r) => r.task === mode).length ? (
          <div className="recent-strip recent-strip-flat">
            {recent
              .filter((r) => r.task === mode)
              .slice(0, 8)
              .map((item) => (
                <button key={item.id} type="button" className={current?.id === item.id ? "recent-item is-active" : "recent-item"} onClick={() => setCurrent(item)}>
                  <strong>{item.title}</strong>
                  <span>{formatDuration(item.result?.duration)}</span>
                </button>
              ))}
          </div>
        ) : null}
      </main>
      <Toast message={toast.message} />
    </div>
  );
}
