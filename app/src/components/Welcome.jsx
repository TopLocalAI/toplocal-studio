import { Play, Sparkle } from "@phosphor-icons/react";
import { t } from "../i18n";

// Spread cards over `n` columns, each into the currently shortest one (image aspect aware).
function masonry(items, n) {
  const columns = Array.from({ length: n }, () => ({ height: 0, items: [] }));
  for (const item of items) {
    const [w, h] = (item.aspect || "1:1").split(":").map(Number);
    const target = columns.reduce((a, b) => (b.height < a.height ? b : a));
    target.items.push(item);
    target.height += h / w + 0.35; // + text block
  }
  return columns.map((c) => c.items);
}

// Shown on the result side before anything is selected: a greeting and example cards.
// Clicking an example runs it right away.
export function Welcome({ title, subtitle, examples, onPick, disabled, kind = "image" }) {
  const card = (ex) => (
    <button key={ex.id} type="button" className="example-card" disabled={disabled} onClick={() => onPick(ex)}>
      {ex.thumb ? (
        <span className="example-thumb" style={kind === "image" && ex.aspect ? { aspectRatio: ex.aspect.replace(":", " / ") } : undefined}>
          {ex.video ? (
            <video src={ex.video} poster={ex.thumb} muted loop playsInline preload="none"
              onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
              onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }} />
          ) : (
            <img src={ex.thumb} alt="" />
          )}
          <i className="example-go"><Play size={14} weight="fill" /> {t("生成")}</i>
        </span>
      ) : null}
      <span className="example-text">
        <strong>{t(ex.title)}</strong>
        <small>{t(ex.prompt)}</small>
      </span>
    </button>
  );

  return (
    <div className="welcome">
      <header className="welcome-head">
        <Sparkle size={22} weight="fill" />
        <div>
          <h2>{t(title)}</h2>
          <p>{t(subtitle)}</p>
        </div>
      </header>
      <p className="welcome-label">{t("试试这些例子，点一下就开始生成")}</p>
      {kind === "image" ? (
        <div className="welcome-masonry">
          {masonry(examples, 3).map((column, i) => (
            <div key={i} className="welcome-column">
              {column.map((ex) => card(ex))}
            </div>
          ))}
        </div>
      ) : (
        <div className={`welcome-grid is-${kind}`}>{examples.map((ex) => card(ex))}</div>
      )}
    </div>
  );
}
