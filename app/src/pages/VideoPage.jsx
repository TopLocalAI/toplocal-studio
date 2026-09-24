import { useCallback, useEffect, useState } from "react";
import { DownloadSimple, FilmSlate, ImageSquare, Lock, Sparkle, TextT } from "@phosphor-icons/react";
import { api, fileUrl, saveResult } from "../api";
import { JobOverlay } from "../components/JobOverlay";
import { SourcePicker } from "../components/SourcePicker";
import { ModelGate } from "../components/ModelGate";
import { Toast, useToast } from "../components/Toast";
import { useJob } from "../hooks/useJob";

const SECONDS = [3, 5, 8];

function estimate(seconds, resolution, withImage) {
  const base = 90 * (seconds / 5) * (resolution === "720p" ? 2.8 : 1);
  const s = Math.round(base * (withImage ? 1.5 : 1));
  return s < 90 ? `约 ${s} 秒` : `约 ${Math.round(s / 60)} 分钟`;
}

export function VideoPage({ features, serviceReady, system, initialSource, onSourceUsed , onModelsChanged }) {
  const [mode, setMode] = useState(initialSource ? "image" : "text");
  const [text, setText] = useState("");
  const [source, setSource] = useState(initialSource || null);
  const [seconds, setSeconds] = useState(5);
  const [resolution, setResolution] = useState("480p");
  const [enhance, setEnhance] = useState(true);
  const [current, setCurrent] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");
  const toast = useToast();

  useEffect(() => {
    if (initialSource) {
      setMode("image");
      setSource(initialSource);
      onSourceUsed?.();
    }
  }, [initialSource, onSourceUsed]);

  const feature = features.find((f) => f.id === "video.create");
  const supported = feature?.supported;
  const ready = feature?.ready;

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("video");
      setRecent(items);
      setCurrent((c) => c || items[0] || null);
    } catch {
      /* not ready */
    }
  }, []);

  useEffect(() => {
    if (serviceReady) loadRecent();
  }, [serviceReady, loadRecent]);

  const job = useJob((finished) => {
    if (finished.status === "done") {
      setCurrent(finished);
      loadRecent();
    } else if (finished.status === "error") setError(finished.error || "生成失败");
  });

  const run = async () => {
    setError("");
    try {
      await job.submit("video", "generate", {
        text,
        seconds,
        resolution,
        enhance,
        source: mode === "image" ? source : null,
      });
    } catch (e) {
      setError(e.message);
    }
  };

  if (feature && !supported) {
    return (
      <section className="placeholder-page">
        <div className="placeholder-card">
          <Lock size={44} weight="duotone" />
          <h1>这台电脑暂不支持视频生成</h1>
          <p>
            视频模型运行时需要约 16–21 GB 内存，需要 24 GB 以上内存的电脑（本机 {system?.memoryGb ?? "?"} GB）。
            图片、音乐、语音功能都可以正常使用。
          </p>
        </div>
      </section>
    );
  }

  const canRun = serviceReady && ready && !job.running && text.trim() && (mode === "text" || source);

  return (
    <div className="studio">
      <aside className="composer-panel" aria-label="视频创作">
        <div className="composer-heading">
          <Sparkle size={24} weight="fill" />
          <h1>让画面动起来</h1>
        </div>
        <div className="mode-switch mode-switch-2" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "text"} className={mode === "text" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("text")}>
            <TextT size={20} />
            <span>文字生成</span>
          </button>
          <button type="button" role="tab" aria-selected={mode === "image"} className={mode === "image" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("image")}>
            <ImageSquare size={20} />
            <span>图片生成</span>
          </button>
        </div>

        {mode === "image" ? (
          <div className="field-group">
            <span className="field-label">第一帧画面</span>
            <SourcePicker value={source} onChange={setSource} label="上传一张图片" />
          </div>
        ) : null}

        <div className="field-group prompt-group">
          <div className="field-label-row">
            <label htmlFor="video-text">{mode === "image" ? "想让它怎么动" : "描述画面和动作"}</label>
            <span>{text.length} / 500</span>
          </div>
          <textarea
            id="video-text"
            className={mode === "image" ? "prompt-input prompt-short" : "prompt-input"}
            maxLength={500}
            value={text}
            placeholder={mode === "image" ? "例如：云雾缓缓流动，镜头慢慢推近" : "例如：一只橘猫在窗台上伸懒腰，窗外下着小雨"}
            onChange={(e) => setText(e.target.value)}
          />
          <label className="check-row">
            <input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} />
            自动补充镜头和细节描述（推荐）
          </label>
        </div>

        <div className="field-group">
          <span className="field-label">时长</span>
          <div className="segmented segmented-3" role="radiogroup">
            {SECONDS.map((s) => (
              <button key={s} type="button" role="radio" aria-checked={seconds === s} className={seconds === s ? "is-active" : ""} onClick={() => setSeconds(s)}>
                <strong>{s} 秒</strong>
              </button>
            ))}
          </div>
        </div>
        <div className="field-group">
          <span className="field-label">清晰度</span>
          <div className="segmented" role="radiogroup">
            <button type="button" role="radio" aria-checked={resolution === "480p"} className={resolution === "480p" ? "is-active" : ""} onClick={() => setResolution("480p")}>
              <strong>标清 480p</strong>
              <small>快，适合预览</small>
            </button>
            <button type="button" role="radio" aria-checked={resolution === "720p"} className={resolution === "720p" ? "is-active" : ""} onClick={() => setResolution("720p")}>
              <strong>高清 720p</strong>
              <small>慢约 3 倍</small>
            </button>
          </div>
        </div>

        <button type="button" className="generate-button" disabled={!canRun} onClick={run}>
          <Sparkle size={21} weight="fill" />
          <span>{job.running ? "正在生成…" : "生成视频"}</span>
        </button>
        <p className="generate-note">
          {!serviceReady
            ? "正在连接本地引擎"
            : !ready
              ? "视频模型未安装，请到设置里下载"
              : `预计${estimate(seconds, resolution, mode === "image")}，带声音，全部在本机完成`}
        </p>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        {serviceReady ? <ModelGate features={features} featureIds={["video.create"]} onInstalled={onModelsChanged} /> : null}
      </aside>

      <main className="studio-stage">
        <div className="result-frame">
          {current?.result?.video ? (
            <video key={current.id} className="result-video" src={fileUrl(current.id, current.result.video)} controls loop playsInline />
          ) : (
            <div className="result-empty">
              <FilmSlate size={40} weight="duotone" />
              <p>描述一个画面，或者从一张图片开始</p>
            </div>
          )}
          <JobOverlay job={job} />
        </div>
        {current ? (
          <div className="song-actions">
            <button type="button" className="button button-secondary" onClick={() => saveResult(current.id, current.result.video, current.title).then(toast.show, (e) => setError(e.message))}>
              <DownloadSimple size={18} /> 下载视频
            </button>
          </div>
        ) : null}
        {recent.length > 1 ? (
          <div className="thumb-strip">
            {recent.slice(0, 12).map((item) => (
              <button key={item.id} type="button" className={current?.id === item.id ? "thumb thumb-wide is-active" : "thumb thumb-wide"} onClick={() => setCurrent(item)} title={item.title}>
                <video src={`${fileUrl(item.id, item.result.video)}#t=0.5`} preload="metadata" muted playsInline />
              </button>
            ))}
          </div>
        ) : null}
      </main>
      <Toast message={toast.message} />
    </div>
  );
}
