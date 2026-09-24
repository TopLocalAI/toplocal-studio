import { useCallback, useEffect, useState } from "react";
import { DownloadSimple, ImageSquare, Lock, MonitorPlay, Sparkle, TextT, Timer } from "@phosphor-icons/react";
import { api, fileUrl, saveResult } from "../api";
import { JobOverlay } from "../components/JobOverlay";
import { SourcePicker } from "../components/SourcePicker";
import { ModelGate } from "../components/ModelGate";
import { ModelPicker } from "../components/ModelPicker";
import { PromptBox } from "../components/PromptBox";
import { Welcome } from "../components/Welcome";
import { VIDEO_EXAMPLES } from "../examples";
import { useModels } from "../hooks/useModels";
import { useTaskModel } from "../hooks/useTaskModel";
import { Toast, useToast } from "../components/Toast";
import { useJob } from "../hooks/useJob";
import { t } from "../i18n";

const SECONDS = [3, 5, 8];

function estimate(seconds, resolution, withImage) {
  const base = 90 * (seconds / 5) * (resolution === "720p" ? 2.8 : 1);
  const s = Math.round(base * (withImage ? 1.5 : 1));
  return s < 90 ? t("约 {s} 秒", { s }) : t("约 {m} 分钟", { m: Math.round(s / 60) });
}

export function VideoPage({ active = true, features, serviceReady, system, initialSource, onSourceUsed , onModelsChanged }) {
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
  const { models, tasks } = useModels(onModelsChanged);
  const [model, setModel] = useTaskModel("video.generate", tasks["video.generate"]);
  const ready = Boolean(model?.installed);
  const writerReady = Boolean(models.find((m) => m.id === "llm.writer")?.installed);

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("video");
      setRecent(items);
      setCurrent((c) => (c && !items.some((i) => i.id === c.id) ? null : c)); // deleted in the library
    } catch {
      /* not ready */
    }
  }, []);

  useEffect(() => {
    if (serviceReady && active) loadRecent();
  }, [serviceReady, active, loadRecent]);

  const job = useJob((finished) => {
    if (finished.status === "done") {
      setCurrent(finished);
      loadRecent();
    } else if (finished.status === "error") setError(finished.error || t("生成失败"));
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
        model: model?.model,
      });
    } catch (e) {
      setError(e.message);
    }
  };

  const runExample = async (ex) => {
    const prompt = t(ex.prompt);
    setMode("text");
    setText(prompt);
    setError("");
    try {
      await job.submit("video", "generate", { text: prompt, seconds, resolution, enhance, source: null, model: model?.model });
    } catch (e) {
      setError(e.message);
    }
  };

  if (feature && !supported) {
    return (
      <section className="placeholder-page">
        <div className="placeholder-card">
          <Lock size={44} weight="duotone" />
          <h1>{t("这台电脑暂不支持视频生成")}</h1>
          <p>
            {t("视频模型运行时需要约 16–21 GB 内存，需要 24 GB 以上内存的电脑（本机 {memory} GB）。", { memory: system?.memoryGb ?? "?" })}{" "}
            {t("图片、音乐、语音功能都可以正常使用。")}
          </p>
        </div>
      </section>
    );
  }

  const canRun = serviceReady && ready && !job.running && text.trim() && (mode === "text" || source);

  return (
    <div className="studio">
      <aside className="composer-panel" aria-label={t("视频创作")}>
        <div className="mode-switch mode-switch-2" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "text"} className={mode === "text" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("text")}>
            <TextT size={17} />
            <span>{t("文字生成")}</span>
          </button>
          <button type="button" role="tab" aria-selected={mode === "image"} className={mode === "image" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("image")}>
            <ImageSquare size={17} />
            <span>{t("图片生成")}</span>
          </button>
        </div>

        {mode === "image" ? (
          <div className="field-group">
            <span className="field-label">{t("第一帧画面")}</span>
            <SourcePicker value={source} onChange={setSource} label={t("上传一张图片")} />
          </div>
        ) : null}

        <PromptBox
          id="video-text"
          label={mode === "image" ? t("想让它怎么动") : t("描述画面和动作")}
          value={text}
          onChange={setText}
          maxLength={500}
          placeholder={mode === "image" ? t("例如：云雾缓缓流动，镜头慢慢推近") : t("例如：一只橘猫在窗台上伸懒腰，窗外下着小雨")}
          polish={{ ready: writerReady, params: { target: "video", fromImage: mode === "image" } }}
          onError={setError}
        />
        <label className="check-row">
          <input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} />
          {t("自动补充镜头和细节描述（推荐）")}
        </label>

        <div className="field-row">
          <div className="field-group">
            <label htmlFor="video-seconds" className="field-label">{t("时长")}</label>
            <div className="select-wrap">
              <Timer size={17} />
              <select id="video-seconds" value={seconds} onChange={(e) => setSeconds(Number(e.target.value))}>
                {SECONDS.map((s) => (
                  <option key={s} value={s}>{t("{s} 秒", { s })}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="field-group">
            <label htmlFor="video-resolution" className="field-label">{t("清晰度")}</label>
            <div className="select-wrap">
              <MonitorPlay size={17} />
              <select id="video-resolution" value={resolution} onChange={(e) => setResolution(e.target.value)}>
                <option value="480p">{t("标清 480p")}</option>
                <option value="720p">{t("高清 720p（慢约 3 倍）")}</option>
              </select>
            </div>
          </div>
        </div>

        <div className="field-group">
          <span className="field-label">{t("模型")}</span>
          <ModelPicker options={tasks["video.generate"]} value={model} onChange={setModel} models={models} />
        </div>

        {serviceReady ? <ModelGate modelIds={[model?.model]} onInstalled={onModelsChanged} /> : null}
        <div className="composer-footer">
          <button type="button" className="generate-button" disabled={!canRun} onClick={run}>
            <Sparkle size={20} weight="fill" />
            <span>{job.running ? t("正在生成…") : t("生成视频")}</span>
          </button>
          <p className="generate-note">
            {!serviceReady
              ? t("正在连接本地引擎")
              : !ready
                ? t("先下载所选模型")
                : t("预计{estimate}，带声音，全部在本机完成", { estimate: estimate(seconds, resolution, mode === "image") })}
          </p>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
        </div>
      </aside>

      <main className="studio-stage">
        <div className="result-frame">
          {current?.result?.video ? (
            <video key={current.id} className="result-video" src={fileUrl(current.id, current.result.video)} controls loop playsInline />
          ) : (
            <Welcome
              title="让画面动起来"
              subtitle="用一句话或一张图片，生成几秒钟带声音的短视频。"
              examples={VIDEO_EXAMPLES}
              kind="video"
              onPick={runExample}
              disabled={!serviceReady || job.running || !ready}
            />
          )}
          <JobOverlay job={job} />
        </div>
        {current ? (
          <div className="song-actions">
            <button type="button" className="button button-secondary" onClick={() => saveResult(current.id, current.result.video, current.title).then(toast.show, (e) => setError(e.message))}>
              <DownloadSimple size={18} /> {t("下载视频")}
            </button>
          </div>
        ) : null}
        {recent.length ? (
          <div className="thumb-strip">
            <button type="button" className={current ? "thumb thumb-wide thumb-examples" : "thumb thumb-wide thumb-examples is-active"} onClick={() => setCurrent(null)} title={t("示例")}>
              <Sparkle size={20} weight="fill" />
              <span>{t("示例")}</span>
            </button>
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
