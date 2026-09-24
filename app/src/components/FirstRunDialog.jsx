import { useEffect, useMemo, useState } from "react";
import { FilmSlate, ImageSquare, MusicNotes, Waveform } from "@phosphor-icons/react";
import { t } from "../i18n";
import { formatBytes, useModels } from "../hooks/useModels";

const DONE_KEY = "toplocal-first-run-done";

// What each module needs to be usable with its recommended model.
const BUNDLES = [
  { id: "image", label: "图片", icon: ImageSquare, models: ["image.zimage"], note: "文字生成图片，中英文字准确" },
  { id: "music", label: "音乐", icon: MusicNotes, models: ["music.ace", "llm.writer"], note: "一句话写歌，含写词助手" },
  { id: "speech", label: "语音", icon: Waveform, models: ["speech.asr", "speech.tts-fast"], note: "录音转文字和配音" },
  { id: "video", label: "视频", icon: FilmSlate, models: ["video.ltx25"], note: "带声音的短视频，文件较大" },
];

function seen() {
  try {
    return window.localStorage.getItem(DONE_KEY) === "1";
  } catch {
    return true;
  }
}

// First launch: suggest a set of models that fits this computer and download them in one
// click. Skipping is fine; every page still offers the download when a model is missing.
export function FirstRunDialog({ system, serviceReady, onInstalled }) {
  const { models, hasHfToken, download } = useModels(onInstalled);
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState(null);
  const [error, setError] = useState("");

  const features = system?.features || [];
  const supported = (bundle) =>
    bundle.id !== "video" || features.some((f) => f.module === "video" && f.supported);
  const byId = useMemo(() => Object.fromEntries(models.map((m) => [m.id, m])), [models]);
  const missing = (bundle) => bundle.models.filter((id) => byId[id] && !byId[id].installed);

  useEffect(() => {
    if (!serviceReady || !models.length || seen()) return;
    // Nothing installed yet: a fresh install. Otherwise the user already set things up.
    if (models.some((m) => m.installed)) {
      try {
        window.localStorage.setItem(DONE_KEY, "1");
      } catch {
        /* ignore */
      }
      return;
    }
    setPicked(new Set(BUNDLES.filter((b) => b.id !== "video" && supported(b)).map((b) => b.id)));
    setOpen(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serviceReady, models.length]);

  if (!open || !picked) return null;

  const finish = () => {
    try {
      window.localStorage.setItem(DONE_KEY, "1");
    } catch {
      /* ignore */
    }
    setOpen(false);
  };
  const wanted = [...new Set(BUNDLES.filter((b) => picked.has(b.id)).flatMap(missing))];
  // Gated models (LTX-2.5) need a Hugging Face token first; download the rest now.
  const ids = wanted.filter((id) => hasHfToken || !byId[id]?.needsToken);
  const total = ids.reduce((s, id) => s + (byId[id]?.sizeBytes || 0), 0);
  const free = (system?.diskFreeGb || 0) * 1024 ** 3;
  const needsToken = wanted.length > ids.length;

  const start = async () => {
    setError("");
    try {
      for (const id of ids) await download(id);
      finish();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="export-dialog first-run" role="dialog" aria-modal="true" aria-labelledby="first-run-title">
        <h2 id="first-run-title">{t("欢迎使用 TopLocal Studio")}</h2>
        <p className="first-run-lead">
          {t("所有内容都在这台电脑上生成。先选好要用的功能，我们帮你下载对应的模型，之后随时可以在设置里增删。")}
        </p>
        <ul className="first-run-list">
          {BUNDLES.map((b) => {
            const Icon = b.icon;
            const ok = supported(b);
            const size = missing(b).reduce((s, id) => s + (byId[id]?.sizeBytes || 0), 0);
            return (
              <li key={b.id}>
                <label className={ok ? "first-run-item" : "first-run-item is-disabled"}>
                  <input
                    type="checkbox"
                    disabled={!ok}
                    checked={picked.has(b.id)}
                    onChange={(e) => {
                      const next = new Set(picked);
                      if (e.target.checked) next.add(b.id);
                      else next.delete(b.id);
                      setPicked(next);
                    }}
                  />
                  <Icon size={20} />
                  <span>
                    <strong>{t(b.label)}</strong>
                    <small>{ok ? t(b.note) : t("需要 24 GB 以上内存")}</small>
                  </span>
                  <em>{size ? formatBytes(size) : t("已安装")}</em>
                </label>
              </li>
            );
          })}
        </ul>
        <p className={total > free - 2 * 1024 ** 3 ? "first-run-total is-low" : "first-run-total"}>
          {t("共需下载 {size}，这台电脑剩余 {free} GB", { size: formatBytes(total), free: Math.round(system?.diskFreeGb || 0) })}
        </p>
        {needsToken ? <p className="first-run-note">{t("视频模型需要先在设置里填写 Hugging Face 令牌，可以之后再下载。")}</p> : null}
        {error ? <p className="form-error">{error}</p> : null}
        <div className="first-run-actions">
          <button type="button" className="button button-secondary" onClick={finish}>
            {t("稍后再说")}
          </button>
          <button type="button" className="button button-primary" disabled={!ids.length} onClick={start}>
            {t("下载所选模型")}
          </button>
        </div>
      </section>
    </div>
  );
}
