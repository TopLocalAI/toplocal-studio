import { ArrowClockwise, GearSix, SquaresFour } from "@phosphor-icons/react";
import logo from "../assets/logo.svg";
import { MODULES } from "../data";
import { t } from "../i18n";

export function Rail({ page, onNavigate, onAbout, features, service, onRetry }) {
  const moduleState = (id) => {
    const list = features.filter((f) => f.module === id);
    if (!list.length) return "";
    if (list.some((f) => f.ready)) return "";
    return list.some((f) => f.supported) ? t("需下载") : t("配置不足");
  };

  const item = (id, label, Icon, note = "") => (
    <button
      key={id}
      type="button"
      className={page === id ? "rail-item is-active" : "rail-item"}
      aria-current={page === id ? "page" : undefined}
      onClick={() => onNavigate(id)}
      title={note ? t("{label}（{note}）", { label, note }) : label}
    >
      <Icon size={24} weight={page === id ? "fill" : "regular"} />
      <span>{label}</span>
      {note ? <i className="rail-dot" aria-label={note} /> : null}
    </button>
  );

  return (
    <nav className="rail" aria-label={t("功能导航")} data-service={service}>
      <button type="button" className="rail-logo" onClick={onAbout} title={t("关于 TopLocal Studio")}>
        <img src={logo} alt="TopLocal Studio" width="40" height="40" />
      </button>
      <div className="rail-group">{MODULES.map((m) => item(m.id, t(m.label), m.icon, moduleState(m.id)))}</div>
      <div className="rail-group rail-bottom">
        {item("library", t("作品"), SquaresFour)}
        {item("settings", t("设置"), GearSix)}
        {/* Only shown when something needs attention: the engine is starting or unreachable. */}
        {service === "checking" ? (
          <span className="rail-status" role="status">
            <i className="rail-spinner" /> {t("启动中")}
          </span>
        ) : service === "offline" ? (
          <button type="button" className="rail-status is-offline" onClick={onRetry} title={t("本地引擎没有响应，点击重试")}>
            <ArrowClockwise size={13} /> {t("未连接")}
          </button>
        ) : null}
      </div>
    </nav>
  );
}
