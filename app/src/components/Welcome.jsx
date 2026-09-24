import { Play, Sparkle } from "@phosphor-icons/react";
import { t } from "../i18n";

// Shown on the result side before anything is selected: a greeting and example cards.
// Clicking an example runs it right away.
export function Welcome({ title, subtitle, examples, onPick, disabled, kind = "image" }) {
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
      <div className={`welcome-grid is-${kind}`}>
        {examples.map((ex) => (
          <button key={ex.id} type="button" className="example-card" disabled={disabled} onClick={() => onPick(ex)}>
            {ex.thumb ? (
              <span className="example-thumb">
                {ex.video ? (
                  <video src={ex.video} poster={ex.thumb} muted loop playsInline preload="none"
                    onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
                    onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }} />
                ) : (
                  <img src={ex.thumb} alt="" loading="lazy" style={ex.focus ? { objectPosition: ex.focus } : undefined} />
                )}
                <i className="example-go"><Play size={14} weight="fill" /> {t("生成")}</i>
              </span>
            ) : null}
            <span className="example-text">
              <strong>{t(ex.title)}</strong>
              <small>{t(ex.prompt)}</small>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
