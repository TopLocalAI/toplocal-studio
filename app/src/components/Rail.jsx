import { GearSix, SquaresFour } from "@phosphor-icons/react";
import { MODULES } from "../data";

export function Rail({ page, onNavigate, features, service }) {
  const moduleState = (id) => {
    const list = features.filter((f) => f.module === id);
    if (!list.length) return "";
    if (list.some((f) => f.ready)) return "";
    return list.some((f) => f.supported) ? "需下载" : "配置不足";
  };

  const item = (id, label, Icon, note = "") => (
    <button
      key={id}
      type="button"
      className={page === id ? "rail-item is-active" : "rail-item"}
      aria-current={page === id ? "page" : undefined}
      onClick={() => onNavigate(id)}
      title={note ? `${label}（${note}）` : label}
    >
      <Icon size={24} weight={page === id ? "fill" : "regular"} />
      <span>{label}</span>
      {note ? <i className="rail-dot" aria-label={note} /> : null}
    </button>
  );

  return (
    <nav className="rail" aria-label="功能导航">
      <div className="rail-brand" title="TopLocal Studio" aria-hidden="true">TL</div>
      <div className="rail-group">{MODULES.map((m) => item(m.id, m.label, m.icon, moduleState(m.id)))}</div>
      <div className="rail-group rail-bottom">
        {item("library", "作品", SquaresFour)}
        {item("settings", "设置", GearSix)}
        <span
          className={`rail-status is-${service}`}
          title={service === "ready" ? "本地引擎已就绪" : service === "offline" ? "本地引擎未连接" : "正在连接本地引擎"}
        />
      </div>
    </nav>
  );
}
