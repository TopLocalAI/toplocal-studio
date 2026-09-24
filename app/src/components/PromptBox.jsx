import { useState } from "react";
import { ArrowCounterClockwise, MagicWand } from "@phosphor-icons/react";
import { api } from "../api";
import { t } from "../i18n";

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// Prompt input as a card: the text box with a toolbar underneath (polish button, counter).
// "Polish" asks the local writing assistant to expand a short idea into a fuller prompt;
// the previous text can be restored with one click.
export function PromptBox({ id, label, value, onChange, maxLength, placeholder, tall = false, hint, polish, onError }) {
  const [busy, setBusy] = useState(false);
  const [previous, setPrevious] = useState(null);

  const run = async () => {
    setBusy(true);
    try {
      const job = await api.submit("shared", "enhance", { text: value, ...polish.params });
      let state = job;
      while (!["done", "error", "cancelled"].includes(state.status)) {
        await wait(700);
        state = await api.job(job.id);
      }
      if (state.status === "done" && state.result?.text) {
        setPrevious(value);
        onChange(state.result.text.slice(0, maxLength));
      } else if (state.status === "error") {
        onError?.(state.error || t("润色失败，请重试"));
      }
    } catch (e) {
      onError?.(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="field-group prompt-group">
      <label htmlFor={id} className="field-label">{label}</label>
      <div className={tall ? "prompt-card is-tall" : "prompt-card"}>
        <textarea
          id={id}
          className="prompt-input"
          maxLength={maxLength}
          value={value}
          placeholder={placeholder}
          onChange={(e) => {
            setPrevious(null);
            onChange(e.target.value);
          }}
        />
        <div className="prompt-bar">
          {polish ? (
            <button
              type="button"
              className="prompt-tool"
              disabled={busy || !value.trim() || !polish.ready}
              title={polish.ready ? t("用本地写作助手把想法扩写成更完整的描述") : t("需要先下载写作助手")}
              onClick={run}
            >
              <MagicWand size={14} weight={busy ? "fill" : "regular"} className={busy ? "is-spinning" : ""} />
              {busy ? t("润色中…") : t("帮我润色")}
            </button>
          ) : null}
          {previous !== null && !busy ? (
            <button type="button" className="prompt-tool is-quiet" onClick={() => { onChange(previous); setPrevious(null); }}>
              <ArrowCounterClockwise size={14} /> {t("撤销")}
            </button>
          ) : null}
          <span className="prompt-count">
            {value.length} / {maxLength}
          </span>
        </div>
      </div>
      {hint ? <small className="field-hint">{hint}</small> : null}
    </div>
  );
}
