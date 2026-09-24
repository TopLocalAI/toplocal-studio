import { ArrowClockwise, GearSix, SquaresFour } from "@phosphor-icons/react";
import logo from "../assets/logo.svg";
import { MODULES } from "../data";

export function Rail({ page, onNavigate, onAbout, features, service, onRetry }) {
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
    <nav className="rail" aria-label="功能导航" data-service={service}>
      <button type="button" className="rail-logo" onClick={onAbout} title="关于 TopLocal Studio">
        <img src={logo} alt="TopLocal Studio" width="40" height="40" />
      </button>
      <div className="rail-group">{MODULES.map((m) => item(m.id, m.label, m.icon, moduleState(m.id)))}</div>
      <div className="rail-group rail-bottom">
        {item("library", "作品", SquaresFour)}
        {item("settings", "设置", GearSix)}
        {/* Only shown when something needs attention: the engine is starting or unreachable. */}
        {service === "checking" ? (
          <span className="rail-status" role="status">
            <i className="rail-spinner" /> 启动中
          </span>
        ) : service === "offline" ? (
          <button type="button" className="rail-status is-offline" onClick={onRetry} title="本地引擎没有响应，点击重试">
            <ArrowClockwise size={13} /> 未连接
          </button>
        ) : null}
      </div>
    </nav>
  );
}
