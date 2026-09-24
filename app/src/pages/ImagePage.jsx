import { useCallback, useEffect, useState } from "react";
import { ArrowsClockwise, DownloadSimple, FilmSlate, MagicWand, PencilSimple, Sparkle } from "@phosphor-icons/react";
import { api, fileUrl, saveResult } from "../api";
import { SourcePicker } from "../components/SourcePicker";
import { JobOverlay } from "../components/JobOverlay";
import { ModelGate } from "../components/ModelGate";
import { Toast, useToast } from "../components/Toast";
import { useJob } from "../hooks/useJob";

const ASPECTS = ["1:1", "4:3", "3:4", "16:9", "9:16"];
const STYLES = ["写实照片", "插画", "动漫", "3D", "水墨", "海报", "电影感"];

export function ImagePage({ features, serviceReady, onAnimate , onModelsChanged }) {
  const [mode, setMode] = useState("generate");
  const [text, setText] = useState("");
  const [editText, setEditText] = useState("");
  const [styles, setStyles] = useState([]);
  const [aspect, setAspect] = useState("1:1");
  const [quality, setQuality] = useState("standard");
  const [source, setSource] = useState(null);
  const [current, setCurrent] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");
  const toast = useToast();

  const ready = (id) => features.find((f) => f.id === id)?.ready;
  const createReady = ready("image.create");
  const editReady = ready("image.edit") || createReady; // edit falls back to klein 4B on 16 GB

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("image");
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

  const run = async (overrides = {}) => {
    setError("");
    try {
      if (mode === "generate") {
        await job.submit("image", "generate", { text, styles, aspect, quality, ...overrides });
      } else {
        await job.submit("image", "edit", { text: editText, source, ...overrides });
      }
    } catch (e) {
      setError(e.message);
    }
  };

  const editThis = () => {
    if (!current) return;
    setMode("edit");
    setSource({ library: current.id, file: current.result.image, preview: fileUrl(current.id, current.result.image) });
  };

  const canRun =
    serviceReady && !job.running && (mode === "generate" ? text.trim() && createReady : editText.trim() && source && editReady);
  const estimate = mode === "generate" ? (quality === "fast" ? "约 15 秒" : "约 40 秒") : "约 20–40 秒";

  return (
    <div className="studio">
      <aside className="composer-panel" aria-label="图片创作">
        <div className="composer-heading">
          <Sparkle size={24} weight="fill" />
          <h1>画一张图</h1>
        </div>

        <div className="mode-switch mode-switch-2" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "generate"} className={mode === "generate" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("generate")}>
            <MagicWand size={20} />
            <span>生成</span>
          </button>
          <button type="button" role="tab" aria-selected={mode === "edit"} className={mode === "edit" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("edit")}>
            <PencilSimple size={20} />
            <span>编辑</span>
          </button>
        </div>

        {mode === "generate" ? (
          <>
            <div className="field-group prompt-group">
              <div className="field-label-row">
                <label htmlFor="img-text">描述画面</label>
                <span>{text.length} / 500</span>
              </div>
              <textarea
                id="img-text"
                className="prompt-input"
                maxLength={500}
                value={text}
                placeholder="例如：一张咖啡馆菜单海报，标题写着“秋日限定”，下方是南瓜拿铁的插画"
                onChange={(e) => setText(e.target.value)}
              />
              <small className="field-hint">想让图里出现文字，就用引号写出来</small>
            </div>
            <div className="field-group">
              <span className="field-label">风格</span>
              <div className="style-chips">
                {STYLES.map((s) => (
                  <button key={s} type="button" className={styles.includes(s) ? "chip is-active" : "chip"} aria-pressed={styles.includes(s)} onClick={() => setStyles((l) => (l.includes(s) ? l.filter((x) => x !== s) : [...l, s].slice(-3)))}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-group">
              <span className="field-label">画面比例</span>
              <div className="aspect-row">
                {ASPECTS.map((a) => {
                  const [w, h] = a.split(":").map(Number);
                  return (
                    <button key={a} type="button" className={aspect === a ? "aspect is-active" : "aspect"} onClick={() => setAspect(a)} title={a}>
                      <i style={{ aspectRatio: `${w} / ${h}` }} />
                      <span>{a}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="field-group">
              <span className="field-label">模式</span>
              <div className="segmented" role="radiogroup">
                <button type="button" role="radio" aria-checked={quality === "standard"} className={quality === "standard" ? "is-active" : ""} onClick={() => setQuality("standard")}>
                  <strong>精细</strong>
                  <small>画质好，中英文字准确</small>
                </button>
                <button type="button" role="radio" aria-checked={quality === "fast"} className={quality === "fast" ? "is-active" : ""} onClick={() => setQuality("fast")}>
                  <strong>极速</strong>
                  <small>约 15 秒，不适合写字</small>
                </button>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="field-group">
              <span className="field-label">要修改的图片</span>
              <SourcePicker value={source} onChange={setSource} label="上传一张图片" />
            </div>
            <div className="field-group prompt-group">
              <div className="field-label-row">
                <label htmlFor="img-edit">想怎么改</label>
              </div>
              <textarea
                id="img-edit"
                className="prompt-input prompt-short"
                maxLength={300}
                value={editText}
                placeholder="例如：把招牌上的字改成“TopLocal Studio”，换成下雪的冬夜"
                onChange={(e) => setEditText(e.target.value)}
              />
            </div>
          </>
        )}

        <button type="button" className="generate-button" disabled={!canRun} onClick={() => run()}>
          <Sparkle size={21} weight="fill" />
          <span>{job.running ? "正在生成…" : mode === "generate" ? "生成图片" : "开始修改"}</span>
        </button>
        <p className="generate-note">
          {!serviceReady ? "正在连接本地引擎" : !createReady ? "图片模型未安装，请到设置里下载" : `预计${estimate}，全部在本机完成`}
        </p>
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        {serviceReady ? <ModelGate features={features} featureIds={mode === "generate" ? ["image.create"] : ["image.edit"]} onInstalled={onModelsChanged} /> : null}
      </aside>

      <main className="studio-stage">
        <div className="result-frame">
          {current?.result?.image ? (
            <img className="result-image" src={fileUrl(current.id, current.result.image)} alt={current.title} />
          ) : (
            <div className="result-empty">
              <MagicWand size={40} weight="duotone" />
              <p>描述一个画面，点“生成图片”</p>
            </div>
          )}
          <JobOverlay job={job} />
        </div>
        {current ? (
          <div className="song-actions">
            <button type="button" className="button button-secondary" onClick={() => saveResult(current.id, current.result.image, current.title).then(toast.show, (e) => setError(e.message))}>
              <DownloadSimple size={18} /> 下载
            </button>
            {current.task === "generate" ? (
              <button type="button" className="button button-secondary" disabled={job.running} onClick={() => { setMode("generate"); job.submit("image", "generate", { ...current.params, seed: 0 }).catch((e) => setError(e.message)); }}>
                <ArrowsClockwise size={18} /> 换一张
              </button>
            ) : null}
            <button type="button" className="button button-secondary" onClick={editThis}>
              <PencilSimple size={18} /> 编辑这张
            </button>
            <button type="button" className="button button-secondary" onClick={() => onAnimate({ library: current.id, file: current.result.image, preview: fileUrl(current.id, current.result.image) })}>
              <FilmSlate size={18} /> 让它动起来
            </button>
          </div>
        ) : null}
        {recent.length > 1 ? (
          <div className="thumb-strip" aria-label="最近生成">
            {recent.slice(0, 12).map((item) => (
              <button key={item.id} type="button" className={current?.id === item.id ? "thumb is-active" : "thumb"} onClick={() => setCurrent(item)} title={item.title}>
                <img src={fileUrl(item.id, item.result.image)} alt={item.title} />
              </button>
            ))}
          </div>
        ) : null}
      </main>
      <Toast message={toast.message} />
    </div>
  );
}
