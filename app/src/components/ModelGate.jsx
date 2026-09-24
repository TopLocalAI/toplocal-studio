import { useState } from "react";
import { CloudArrowDown, Key, X } from "@phosphor-icons/react";
import { openExternal } from "../api";
import { formatBytes, isDownloading, useModels } from "../hooks/useModels";
import { t } from "../i18n";

// Shown in place of a module's controls when the models a feature needs are missing.
// Downloads them in one click; models with restrictive licenses ask for consent first.
export function ModelGate({ features, featureIds, onInstalled }) {
  const { models, hasHfToken, download, cancel } = useModels(onInstalled);
  const [consent, setConsent] = useState(null);
  const [error, setError] = useState("");

  const needed = [
    ...new Set(
      features.filter((f) => featureIds.includes(f.id) && f.supported && !f.ready).flatMap((f) => f.models),
    ),
  ]
    .map((id) => models.find((m) => m.id === id))
    .filter((m) => m && !m.installed);
  if (!needed.length) return null;

  const total = needed.reduce((s, m) => s + m.sizeBytes, 0);
  const active = needed.filter(isDownloading);
  const done = needed.reduce((s, m) => s + (m.download?.doneBytes || 0), 0);
  const failed = needed.find((m) => m.download?.state === "error");
  const gated = hasHfToken ? [] : needed.filter((m) => m.needsToken);

  const start = async () => {
    setError("");
    const restricted = needed.filter((m) => m.licenseNote);
    if (restricted.length && !consent) {
      setConsent(restricted);
      return;
    }
    try {
      for (const m of needed) if (!isDownloading(m)) await download(m.id);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="model-gate">
      <div className="model-gate-head">
        <CloudArrowDown size={22} />
        <div>
          <strong>{active.length ? t("正在下载模型") : t("首次使用需要下载模型")}</strong>
          <small>{t("{names} · 共 {size}", { names: needed.map((m) => m.name).join(t("、")), size: formatBytes(total) })}</small>
        </div>
      </div>
      {active.length ? (
        <>
          <div className="export-progress">
            <span style={{ width: `${Math.min(100, (done / total) * 100)}%` }} />
          </div>
          <div className="model-gate-row">
            <small>
              {formatBytes(done)} / {formatBytes(total)}
              {active[0].download?.speed ? ` · ${formatBytes(active[0].download.speed)}/s` : ""}
              {active[0].download?.state === "verifying" ? ` · ${t("正在校验")}` : ""}
            </small>
            <button type="button" className="link-button" onClick={() => active.forEach((m) => cancel(m.id))}>
              {t("暂停")}
            </button>
          </div>
        </>
      ) : gated.length ? (
        <div className="model-gate-token">
          <p>
            <Key size={14} />{" "}
            {t("{names} 需要 Hugging Face 令牌：先在模型页面同意许可证，再到“设置 → 模型下载”填写令牌。", {
              names: gated.map((m) => m.name).join(t("、")),
            })}
          </p>
          <button type="button" className="link-button" onClick={() => openExternal(gated[0].licensePage)}>
            {t("打开模型页面")}
          </button>
        </div>
      ) : (
        <button type="button" className="button button-primary model-gate-button" onClick={start}>
          {needed.some((m) => m.download?.doneBytes) ? t("继续下载") : t("下载模型")}
        </button>
      )}
      {failed ? <p className="form-error">{failed.download.error}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}

      {consent ? (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setConsent(null)}>
          <section className="export-dialog license-dialog" role="dialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}>
            <button type="button" className="dialog-close" aria-label={t("关闭")} onClick={() => setConsent(null)}>
              <X size={19} />
            </button>
            <h2>{t("下载前请阅读许可证")}</h2>
            {consent.map((m) => (
              <div key={m.id} className="license-item">
                <strong>{m.name}</strong>
                <p>{m.licenseNote}</p>
                {m.licenseUrl ? (
                  <button type="button" className="link-button" onClick={() => openExternal(m.licenseUrl)}>
                    {t("查看许可证全文")}
                  </button>
                ) : null}
              </div>
            ))}
            <button
              type="button"
              className="button button-primary dialog-download"
              onClick={async () => {
                const list = needed;
                setConsent(null);
                try {
                  for (const m of list) if (!isDownloading(m)) await download(m.id);
                } catch (e) {
                  setError(e.message);
                }
              }}
            >
              {t("我已阅读并同意，开始下载")}
            </button>
          </section>
        </div>
      ) : null}
    </div>
  );
}
