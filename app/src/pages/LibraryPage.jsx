import { useCallback, useEffect, useState } from "react";
import { DownloadSimple, FileText, FilmStrip, MusicNotes, Trash, Waveform } from "@phosphor-icons/react";
import { api, fileUrl, formatDuration, saveResult } from "../api";
import { Toast, useToast } from "../components/Toast";
import { MODULES } from "../data";

const FILTERS = [{ id: "", label: "全部" }, ...MODULES.map((m) => ({ id: m.id, label: m.label }))];

function mainFile(item) {
  const r = item.result || {};
  return r.video || r.image || r.audio || r.text || null;
}

export function LibraryPage() {
  const [filter, setFilter] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const toast = useToast();
  const [confirming, setConfirming] = useState(null);

  const load = useCallback(async () => {
    try {
      setItems((await api.library(filter || undefined)).items);
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  // Two-step delete: the first click arms the button, the second deletes.
  const remove = async (item) => {
    if (confirming !== item.id) {
      setConfirming(item.id);
      return;
    }
    setConfirming(null);
    try {
      await api.remove(item.id);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <section className="library-page">
      <header className="page-header">
        <h1>我的作品</h1>
        <div className="filter-tabs" role="tablist">
          {FILTERS.map((f) => (
            <button
              key={f.id || "all"}
              type="button"
              role="tab"
              aria-selected={filter === f.id}
              className={filter === f.id ? "is-active" : ""}
              onClick={() => setFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </header>
      {error ? <p className="form-error">{error}</p> : null}
      {items.length === 0 && !error ? <p className="empty-note">还没有作品，去生成一个吧。</p> : null}
      <div className="library-grid">
        {items.map((item) => {
          const file = mainFile(item);
          const isVideo = Boolean(item.result?.video);
          return (
            <article key={item.id} className="library-card">
              <div className="library-thumb">
                {isVideo ? (
                  <video src={`${fileUrl(item.id, file)}#t=0.5`} preload="metadata" muted playsInline />
                ) : item.result?.image ? (
                  <img src={fileUrl(item.id, file)} alt={item.title} />
                ) : item.task === "transcribe" ? (
                  <FileText size={34} />
                ) : item.module === "speech" ? (
                  <Waveform size={34} />
                ) : (
                  <MusicNotes size={34} />
                )}
                {isVideo ? <FilmStrip size={18} className="library-badge" /> : null}
              </div>
              <div className="library-meta">
                <strong title={item.title}>{item.title || "未命名"}</strong>
                <span>
                  {new Date(item.created * 1000).toLocaleString("zh-CN", { dateStyle: "short", timeStyle: "short" })}
                  {item.result?.duration ? ` · ${formatDuration(item.result.duration)}` : ""}
                </span>
              </div>
              {item.result?.audio && !isVideo ? <audio controls preload="none" src={fileUrl(item.id, file)} /> : null}
              <div className="library-actions">
                {file ? (
                  <button
                    type="button"
                    className="icon-button"
                    title="下载"
                    onClick={() => saveResult(item.id, file, item.title).then(toast.show, (e) => setError(e.message))}
                  >
                    <DownloadSimple size={18} />
                  </button>
                ) : null}
                {confirming === item.id ? (
                  <>
                    <button type="button" className="icon-button is-danger" onClick={() => remove(item)}>
                      <Trash size={16} />
                      <span>确认删除</span>
                    </button>
                    <button type="button" className="icon-button" onClick={() => setConfirming(null)} title="取消">
                      取消
                    </button>
                  </>
                ) : (
                  <button type="button" className="icon-button" onClick={() => remove(item)} title="删除">
                    <Trash size={18} />
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
      <Toast message={toast.message} />
    </section>
  );
}
