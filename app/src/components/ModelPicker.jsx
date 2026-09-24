import { useEffect, useRef, useState } from "react";
import { CaretDown, Check, CloudArrowDown, Lock } from "@phosphor-icons/react";
import { t } from "../i18n";
import { TIER_NEED } from "../data";
import { formatBytes } from "../hooks/useModels";

// Choose which model runs a task. Every option says what it is good at; models that are
// not installed can still be picked (the download prompt below the button then shows them),
// models this computer cannot run are listed but disabled.
export function ModelPicker({ options, value, onChange, models }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const byId = Object.fromEntries(models.map((m) => [m.id, m]));

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => {
      if (!ref.current?.contains(e.target)) setOpen(false);
    };
    const esc = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("mousedown", close);
    window.addEventListener("keydown", esc);
    return () => {
      window.removeEventListener("mousedown", close);
      window.removeEventListener("keydown", esc);
    };
  }, [open]);

  if (!options?.length || !value) return null;
  const name = (id) => byId[id]?.name || id;
  const single = options.length === 1;

  return (
    <div className="model-picker" ref={ref}>
      <button
        type="button"
        className="model-picker-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={single}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="model-picker-main">
          <strong>
            {name(value.model)}
            {value.recommended ? <em className="model-badge">{t("推荐")}</em> : null}
          </strong>
          <small>{value.strength}</small>
        </span>
        {single ? null : <CaretDown size={16} />}
      </button>
      {open ? (
        <ul className="model-picker-list" role="listbox" aria-label={t("选择模型")}>
          {options.map((o) => {
            const m = byId[o.model];
            const selected = o.model === value.model;
            return (
              <li key={o.model}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={selected ? "model-option is-selected" : "model-option"}
                  disabled={!o.supported}
                  onClick={() => {
                    onChange(o.model);
                    setOpen(false);
                  }}
                >
                  <span className="model-option-text">
                    <strong>
                      {name(o.model)}
                      {o.recommended ? <em className="model-badge">{t("推荐")}</em> : null}
                    </strong>
                    <span>{o.strength}</span>
                    <small>
                      {o.speed}
                      {m ? ` · ${formatBytes(m.sizeBytes)}` : ""}
                      {!o.supported ? (
                        <b className="model-note is-muted">
                          <Lock size={11} /> {t("需要 {memory} 以上内存", { memory: TIER_NEED[o.minTier] })}
                        </b>
                      ) : !o.installed ? (
                        <b className="model-note">
                          <CloudArrowDown size={11} /> {t("未下载")}
                        </b>
                      ) : null}
                    </small>
                  </span>
                  {selected ? <Check size={16} weight="bold" /> : null}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
