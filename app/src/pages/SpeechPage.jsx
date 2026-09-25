import { useCallback, useEffect, useState } from "react";
import { DownloadSimple, Microphone, Sparkle, Subtitles, TextAa, UserSound } from "@phosphor-icons/react";
import { api, fileUrl, formatDuration, saveResult, uploadFile } from "../api";
import { JobOverlay } from "../components/JobOverlay";
import { SourcePicker } from "../components/SourcePicker";
import { ModelGate } from "../components/ModelGate";
import { ModelPicker } from "../components/ModelPicker";
import { PromptBox } from "../components/PromptBox";
import { Welcome } from "../components/Welcome";
import { ASR_EXAMPLES, TTS_EXAMPLES } from "../examples";
import { useModels } from "../hooks/useModels";
import { useTaskModel } from "../hooks/useTaskModel";
import { Toast, useToast } from "../components/Toast";
import { useJob } from "../hooks/useJob";
import { t } from "../i18n";

const LANGUAGES = [
  { id: "", name: "自动识别" },
  { id: "zh", name: "普通话" },
  { id: "yue", name: "粤语" },
  { id: "en", name: "英语" },
  { id: "ja", name: "日语" },
  { id: "ko", name: "韩语" },
];

export function SpeechPage({ active = true, features, serviceReady , onModelsChanged }) {
  const [mode, setMode] = useState("transcribe");
  const [source, setSource] = useState(null);
  const [language, setLanguage] = useState("");
  const [text, setText] = useState("");
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("zf_xiaoxiao");
  const [cloneSource, setCloneSource] = useState(null);
  const [current, setCurrent] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");
  const toast = useToast();

  const { models, tasks } = useModels(onModelsChanged);
  const [asrModel, setAsrModel] = useTaskModel("speech.transcribe", tasks["speech.transcribe"]);
  const [ttsModel, setTtsModel] = useTaskModel("speech.synthesize", tasks["speech.synthesize"]);
  const qwenInstalled = Boolean(models.find((m) => m.id === "speech.tts")?.installed);
  // Cloning always runs on Qwen3-TTS, whichever model is picked.
  const ttsReady = Boolean(ttsModel?.installed) && (voice !== "clone" || qwenInstalled);

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("speech");
      setRecent(items);
      setCurrent((c) => (c && !items.some((i) => i.id === c.id) ? null : c)); // deleted in the library
    } catch {
      /* not ready */
    }
  }, []);

  useEffect(() => {
    if (!serviceReady || !active) return;
    loadRecent();
    api.voices().then((r) => setVoices(r.voices)).catch(() => setVoices([]));
  }, [serviceReady, active, loadRecent]);

  const job = useJob((finished) => {
    if (finished.status === "done") {
      setCurrent(finished);
      loadRecent();
    } else if (finished.status === "error") setError(finished.error || t("处理失败"));
  });

  const run = async () => {
    setError("");
    try {
      if (mode === "transcribe") {
        await job.submit("speech", "transcribe", { source, sourceName: source?.name, language, model: asrModel?.model });
      } else {
        const v = voice === "clone" ? { clone: cloneSource } : { preset: voice };
        await job.submit("speech", "synthesize", { text, voice: v, model: ttsModel?.model });
      }
    } catch (e) {
      setError(e.message);
    }
  };

  // Examples only fill in the form (text and voice, or the sample recording); the user
  // starts the job.
  const fillExample = async (ex) => {
    setError("");
    if (mode !== "transcribe") {
      setText(t(ex.prompt));
      setVoice(ex.voice);
      return;
    }
    if (!serviceReady) return;
    try {
      // The sample recording ships with the app; upload it like a user file.
      const blob = await (await fetch(ex.audio)).blob();
      const name = ex.audio.split("/").pop();
      const info = await uploadFile(new File([blob], name, { type: blob.type || "audio/mp4" }));
      setSource({ upload: info.id, preview: "", name });
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
      ? source && asrModel?.installed
      : text.trim() && ttsReady && (voice !== "clone" || cloneSource));

  const shown = current && current.task === mode ? current : null;

  return (
    <div className="studio">
      <aside className="composer-panel" aria-label={t("语音")}>
        <div className="mode-switch mode-switch-2" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "transcribe"} className={mode === "transcribe" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("transcribe")}>
            <Subtitles size={17} />
            <span>{t("转文字")}</span>
          </button>
          <button type="button" role="tab" aria-selected={mode === "synthesize"} className={mode === "synthesize" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("synthesize")}>
            <Microphone size={17} />
            <span>{t("配音")}</span>
          </button>
        </div>

        {mode === "transcribe" ? (
          <>
            <div className="field-group">
              <span className="field-label">{t("录音或视频")}</span>
              <SourcePicker kind="audio" value={source} onChange={setSource} label={t("上传录音或视频")} />
              <small className="field-hint">{t("支持 mp3、m4a、wav、mp4、mov 等，长度不限")}</small>
            </div>
            <div className="field-group">
              <label htmlFor="asr-lang" className="field-label">{t("语言")}</label>
              <div className="select-wrap">
                <TextAa size={17} />
                <select id="asr-lang" value={language} onChange={(e) => setLanguage(e.target.value)}>
                  {LANGUAGES.map((l) => (
                    <option key={l.id} value={l.id}>{t(l.name)}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field-group">
              <span className="field-label">{t("模型")}</span>
              <ModelPicker options={tasks["speech.transcribe"]} value={asrModel} onChange={setAsrModel} models={models} />
            </div>
          </>
        ) : (
          <>
            <PromptBox
              id="tts-text"
              label={t("要朗读的文字")}
              value={text}
              onChange={setText}
              maxLength={5000}
              placeholder={t("输入或粘贴一段文字，中英文混排也可以")}
            />
            <div className="field-group">
              <span className="field-label">{t("音色")}</span>
              <div className="voice-grid">
                {voices.map((v) => (
                  <button key={v.id} type="button" className={voice === v.id ? "voice is-active" : "voice"} onClick={() => setVoice(v.id)}>
                    {v.name}
                  </button>
                ))}
                <button type="button" className={voice === "clone" ? "voice voice-clone is-active" : "voice voice-clone"} onClick={() => setVoice("clone")}>
                  <UserSound size={16} /> {t("用我的声音")}
                </button>
              </div>
            </div>
            {voice === "clone" ? (
              <div className="field-group">
                <span className="field-label">{t("一段 5–20 秒的清晰录音")}</span>
                <SourcePicker kind="audio" value={cloneSource} onChange={setCloneSource} label={t("上传你的录音")} />
                <small className="field-hint">{t("只用于本次配音，全程在本机处理")}</small>
              </div>
            ) : null}
            <div className="field-group">
              <span className="field-label">{t("模型")}</span>
              <ModelPicker options={tasks["speech.synthesize"]} value={ttsModel} onChange={setTtsModel} models={models} />
            </div>
          </>
        )}

        {serviceReady ? (
          <ModelGate
            modelIds={mode === "transcribe" ? [asrModel?.model] : [ttsModel?.model, voice === "clone" ? "speech.tts" : null]}
            onInstalled={onModelsChanged}
          />
        ) : null}
        <div className="composer-footer">
          <button type="button" className="generate-button" disabled={!canRun} onClick={run}>
            <Sparkle size={20} weight="fill" />
            <span>{job.running ? t("处理中…") : mode === "transcribe" ? t("开始转文字") : t("生成配音")}</span>
          </button>
          <p className="generate-note">
            {!serviceReady ? t("正在连接本地引擎") : mode === "transcribe" ? t("1 小时录音约 2–5 分钟，全部在本机完成") : t("几秒到几十秒，全部在本机完成")}
          </p>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
        </div>
      </aside>

      <main className="studio-stage">
        <div className="result-frame result-text">
          {shown?.task === "transcribe" ? (
            <article className="transcript">
              <header>
                <strong>{shown.title}</strong>
                <span>{t("{duration} 录音", { duration: formatDuration(shown.result.duration) })}</span>
              </header>
              <p>{shown.result.preview}{shown.result.preview?.length >= 2000 ? t("……（完整内容请下载）") : ""}</p>
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
          ) : mode === "transcribe" ? (
            <Welcome
              title="录音转文字"
              subtitle="上传录音或视频，得到文字稿和字幕，长度不限，方言也能听懂。"
              examples={ASR_EXAMPLES}
              kind="text"
              onPick={fillExample}
              copyable={false}
            />
          ) : (
            <Welcome
              title="文字转语音"
              subtitle="选一个音色把文字读出来，也可以用几秒钟录音克隆你自己的声音。"
              examples={TTS_EXAMPLES}
              kind="text"
              onPick={fillExample}
            />
          )}
          <JobOverlay job={job} />
        </div>
        {shown ? (
          <div className="song-actions">
            {shown.task === "transcribe" ? (
              <>
                <button type="button" className="button button-secondary" onClick={() => save(shown.result.text)}>
                  <DownloadSimple size={18} /> {t("下载文字稿（TXT）")}
                </button>
                <button type="button" className="button button-secondary" onClick={() => save(shown.result.srt, t(" 字幕"))}>
                  <DownloadSimple size={18} /> {t("下载字幕（SRT）")}
                </button>
              </>
            ) : (
              <button type="button" className="button button-secondary" onClick={() => save(shown.result.audio)}>
                <DownloadSimple size={18} /> {t("下载音频")}
              </button>
            )}
          </div>
        ) : null}
        {recent.filter((r) => r.task === mode).length ? (
          <div className="recent-strip recent-strip-flat">
            <button type="button" className={shown ? "recent-item recent-examples" : "recent-item recent-examples is-active"} onClick={() => setCurrent(null)}>
              <strong><Sparkle size={14} weight="fill" /> {t("示例")}</strong>
              <span>{t("灵感和例子")}</span>
            </button>
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
