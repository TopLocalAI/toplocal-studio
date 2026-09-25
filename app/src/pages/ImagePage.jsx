import { useCallback, useEffect, useState } from "react";
import { ArrowsClockwise, DownloadSimple, FilmSlate, MagicWand, PencilSimple, Sparkle } from "@phosphor-icons/react";
import { api, fileUrl, saveResult } from "../api";
import { SourcePicker } from "../components/SourcePicker";
import { JobOverlay } from "../components/JobOverlay";
import { ModelGate } from "../components/ModelGate";
import { ModelPicker } from "../components/ModelPicker";
import { PromptBox } from "../components/PromptBox";
import { Welcome } from "../components/Welcome";
import { IMAGE_EXAMPLES } from "../examples";
import { useModels } from "../hooks/useModels";
import { useTaskModel } from "../hooks/useTaskModel";
import { Toast, useToast } from "../components/Toast";
import { useJob } from "../hooks/useJob";
import { t } from "../i18n";

const ASPECTS = ["1:1", "4:3", "3:4", "16:9", "9:16"];
const SIZES = [
  { id: "standard", label: "标准", hint: "约 100 万像素" },
  { id: "hd", label: "高清", hint: "约 200 万像素，耗时约两倍" },
];

// The ratio's outline inside a 16 px box.
function AspectGlyph({ ratio }) {
  const [w, h] = ratio.split(":").map(Number);
  const style = w >= h ? { width: 16, height: (16 * h) / w } : { width: (16 * w) / h, height: 16 };
  return <i className="aspect-glyph" style={style} />;
}

function SizePicker({ value, onChange }) {
  return (
    <div className="segmented size-picker" role="radiogroup" aria-label={t("清晰度")}>
      {SIZES.map((s) => (
        <button key={s.id} type="button" role="radio" aria-checked={value === s.id} title={t(s.hint)}
          className={value === s.id ? "is-active" : ""} onClick={() => onChange(s.id)}>
          {t(s.label)}
        </button>
      ))}
    </div>
  );
}
const STYLES = ["写实照片", "插画", "动漫", "3D", "水墨", "海报", "电影感"];

export function ImagePage({ active = true, features, serviceReady, onAnimate , onModelsChanged }) {
  const [mode, setMode] = useState("generate");
  const [text, setText] = useState("");
  const [editText, setEditText] = useState("");
  const [styles, setStyles] = useState([]);
  const [aspect, setAspect] = useState("1:1");
  const [size, setSize] = useState("standard");
  const [source, setSource] = useState(null);
  const [current, setCurrent] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");
  const toast = useToast();

  const { models, tasks } = useModels(onModelsChanged);
  const [genModel, setGenModel] = useTaskModel("image.generate", tasks["image.generate"]);
  const [editModel, setEditModel] = useTaskModel("image.edit", tasks["image.edit"]);
  const selected = mode === "generate" ? genModel : editModel;
  const createReady = Boolean(genModel?.installed);
  const writerReady = Boolean(models.find((m) => m.id === "llm.writer")?.installed);
  const editReady = Boolean(editModel?.installed);

  const loadRecent = useCallback(async () => {
    try {
      const { items } = await api.library("image");
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

  const run = async (overrides = {}) => {
    setError("");
    try {
      if (mode === "generate") {
        await job.submit("image", "generate", { text, styles, aspect, size, model: genModel?.model, ...overrides });
      } else {
        await job.submit("image", "edit", { text: editText, source, size, model: editModel?.model, ...overrides });
      }
    } catch (e) {
      setError(e.message);
    }
  };

  // Examples only fill in the form; the user starts the generation.
  const fillExample = (ex) => {
    setMode("generate");
    setText(t(ex.prompt));
    setStyles(ex.styles);
    setAspect(ex.aspect);
    setError("");
  };

  const editThis = () => {
    if (!current) return;
    setMode("edit");
    setSource({ library: current.id, file: current.result.image, preview: fileUrl(current.id, current.result.image) });
  };

  const canRun =
    serviceReady && !job.running && (mode === "generate" ? text.trim() && createReady : editText.trim() && source && editReady);
  const estimate = (selected?.speed || "") + (size === "hd" ? t("（高清约两倍）") : "");

  return (
    <div className="studio">
      <aside className="composer-panel" aria-label={t("图片创作")}>
        <div className="mode-switch mode-switch-2" role="tablist">
          <button type="button" role="tab" aria-selected={mode === "generate"} className={mode === "generate" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("generate")}>
            <MagicWand size={17} />
            <span>{t("生成")}</span>
          </button>
          <button type="button" role="tab" aria-selected={mode === "edit"} className={mode === "edit" ? "mode-item is-active" : "mode-item"} onClick={() => setMode("edit")}>
            <PencilSimple size={17} />
            <span>{t("编辑")}</span>
          </button>
        </div>

        {mode === "generate" ? (
          <>
            <PromptBox
              id="img-text"
              label={t("描述画面")}
              value={text}
              onChange={setText}
              maxLength={500}
              placeholder={t("例如：一张咖啡馆菜单海报，标题写着“秋日限定”，下方是南瓜拿铁的插画")}
              hint={t("想让图里出现文字，就用引号写出来")}
              polish={{ ready: writerReady, params: { target: "image" } }}
              onError={setError}
            />
            <div className="field-group">
              <span className="field-label">{t("风格")}</span>
              <div className="style-chips">
                {STYLES.map((s) => (
                  <button key={s} type="button" className={styles.includes(s) ? "chip is-active" : "chip"} aria-pressed={styles.includes(s)} onClick={() => setStyles((l) => (l.includes(s) ? l.filter((x) => x !== s) : [...l, s].slice(-3)))}>
                    {t(s)}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-group">
              <span className="field-label">{t("画面比例")}</span>
              <div className="segmented aspect-picker" role="radiogroup" aria-label={t("画面比例")}>
                {ASPECTS.map((a) => (
                  <button key={a} type="button" role="radio" aria-checked={aspect === a}
                    className={aspect === a ? "is-active" : ""} onClick={() => setAspect(a)}>
                    <span className="aspect-box"><AspectGlyph ratio={a} /></span>
                    {a}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-row">
              <div className="field-group">
                <span className="field-label">{t("清晰度")}</span>
                <SizePicker value={size} onChange={setSize} />
              </div>
              <div className="field-group">
                <span className="field-label">{t("模型")}</span>
                <ModelPicker compact options={tasks["image.generate"]} value={genModel} onChange={setGenModel} models={models} />
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="field-group">
              <span className="field-label">{t("要修改的图片")}</span>
              <SourcePicker value={source} onChange={setSource} label={t("上传一张图片")} />
            </div>
            <PromptBox
              id="img-edit"
              label={t("想怎么改")}
              value={editText}
              onChange={setEditText}
              maxLength={300}
              placeholder={t("例如：把招牌上的字改成“TopLocal Studio”，换成下雪的冬夜")}
            />
            <div className="field-row">
              <div className="field-group">
                <span className="field-label">{t("清晰度")}</span>
                <SizePicker value={size} onChange={setSize} />
              </div>
              <div className="field-group">
                <span className="field-label">{t("模型")}</span>
                <ModelPicker compact options={tasks["image.edit"]} value={editModel} onChange={setEditModel} models={models} />
              </div>
            </div>
          </>
        )}

        {serviceReady ? <ModelGate modelIds={[selected?.model]} onInstalled={onModelsChanged} /> : null}
        <div className="composer-footer">
          <button type="button" className="generate-button" disabled={!canRun} onClick={() => run()}>
            <Sparkle size={20} weight="fill" />
            <span>{job.running ? t("正在生成…") : mode === "generate" ? t("生成图片") : t("开始修改")}</span>
          </button>
          <p className="generate-note">
            {!serviceReady ? t("正在连接本地引擎") : !selected?.installed ? t("先下载所选模型") : t("预计{estimate}，全部在本机完成", { estimate })}
          </p>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
        </div>
      </aside>

      <main className="studio-stage">
        <div className="result-frame">
          {current?.result?.image ? (
            <img className="result-image" src={fileUrl(current.id, current.result.image)} alt={current.title} />
          ) : (
            <Welcome
              title="画一张图，或改一张图"
              subtitle="用一句话描述画面，中英文字也能写对；也可以上传图片，说说想怎么改。"
              examples={IMAGE_EXAMPLES}
              onPick={fillExample}
            />
          )}
          <JobOverlay job={job} />
        </div>
        {current ? (
          <div className="song-actions">
            <button type="button" className="button button-secondary" onClick={() => saveResult(current.id, current.result.image, current.title).then(toast.show, (e) => setError(e.message))}>
              <DownloadSimple size={18} /> {t("下载")}
            </button>
            {current.task === "generate" ? (
              <button type="button" className="button button-secondary" disabled={job.running} onClick={() => { setMode("generate"); job.submit("image", "generate", { ...current.params, seed: 0 }).catch((e) => setError(e.message)); }}>
                <ArrowsClockwise size={18} /> {t("换一张")}
              </button>
            ) : null}
            <button type="button" className="button button-secondary" onClick={editThis}>
              <PencilSimple size={18} /> {t("编辑这张")}
            </button>
            <button type="button" className="button button-secondary" onClick={() => onAnimate({ library: current.id, file: current.result.image, preview: fileUrl(current.id, current.result.image) })}>
              <FilmSlate size={18} /> {t("让它动起来")}
            </button>
          </div>
        ) : null}
        {recent.length ? (
          <div className="thumb-strip" aria-label={t("最近生成")}>
            <button type="button" className={current ? "thumb thumb-examples" : "thumb thumb-examples is-active"} onClick={() => setCurrent(null)} title={t("示例")}>
              <Sparkle size={20} weight="fill" />
              <span>{t("示例")}</span>
            </button>
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
