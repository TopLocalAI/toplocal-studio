import { CheckCircle, DownloadSimple, FilmStrip, X } from "@phosphor-icons/react";
import { t } from "../i18n";

export function ExportDialog({ exportState, onClose, onDownloadVideo, visuals = [], visual, onVisualChange, onStart }) {
  if (!exportState.open) return null;
  const isDone = exportState.status === "done";
  const isError = exportState.status === "error";
  const choosing = exportState.status === "choose";

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="export-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="export-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="dialog-close" aria-label={t("关闭")} onClick={onClose}>
          <X size={19} />
        </button>

        <div className={isDone ? "export-icon is-done" : isError ? "export-icon is-error" : "export-icon"}>
          {isDone ? <CheckCircle size={30} weight="fill" /> : <FilmStrip size={30} weight="fill" />}
        </div>
        <h2 id="export-dialog-title">
          {choosing ? t("导出动效视频") : isDone ? t("视频已准备好") : isError ? t("视频导出失败") : t("正在导出视频")}
        </h2>
        <p>{choosing ? t("选一个背景，整首歌会配上随音乐跳动的波形。") : isDone ? t("整首歌曲的声音动效视频已经在本机完成。") : exportState.label}</p>
        {choosing ? (
          <div className="visual-choice">
            {visuals.map((v) => (
              <button key={v.id} type="button" className={visual === v.id ? "thumb is-active" : "thumb"} onClick={() => onVisualChange(v.id)}>
                <img src={v.src} alt={t(v.name)} />
                <span>{t(v.name)}</span>
              </button>
            ))}
          </div>
        ) : null}

        <div className="export-meta">
          <span>{t("横屏 16:9")}</span>
          <span>MP4</span>
          <span>{t("包含音频")}</span>
        </div>

        {choosing ? (
          <button type="button" className="button button-primary dialog-download" onClick={onStart}>
            {t("开始导出")}
          </button>
        ) : !isDone && !isError ? (
          <>
            <div className="export-progress" aria-label={t("导出进度 {progress}%", { progress: exportState.progress })}>
              <span style={{ width: `${exportState.progress}%` }} />
            </div>
            <div className="export-progress-label">
              <span>{t("所有处理均在本机完成")}</span>
              <strong>{exportState.progress}%</strong>
            </div>
          </>
        ) : isDone ? (
          <button type="button" className="button button-primary dialog-download" onClick={onDownloadVideo}>
            <DownloadSimple size={19} />
            {t("下载 MP4")}
          </button>
        ) : null}
      </section>
    </div>
  );
}
