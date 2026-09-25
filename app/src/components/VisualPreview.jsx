import { useEffect, useRef } from "react";
import { t } from "../i18n";

// Same colors as the exported video (service engines/media.py WAVE_COLORS).
const WAVE_COLORS = { flow: ["#e780ff", "#4bb9ff"], spectrum: ["#ec68ff", "#2e9dff"], nebula: ["#8190ff", "#d063ff"] };

// Live preview of the "animated video" export: the style's backdrop slowly zooming in, with
// the song's waveform drawn from the playing audio. Matches what the export renders.
export function VisualPreview({ visuals, visual, onVisualChange, analyserRef, isPlaying }) {
  const canvas = useRef(null);
  const style = visuals.find((v) => v.id === visual) || visuals[0];

  useEffect(() => {
    const el = canvas.current;
    if (!el) return undefined;
    const ctx = el.getContext("2d");
    const [c1, c2] = WAVE_COLORS[style.id] || WAVE_COLORS.flow;
    let frame = 0;
    let data = null;

    const draw = () => {
      const w = (el.width = el.clientWidth * devicePixelRatio);
      const h = (el.height = el.clientHeight * devicePixelRatio);
      ctx.clearRect(0, 0, w, h);
      const grad = ctx.createLinearGradient(0, 0, w, 0);
      grad.addColorStop(0, c1);
      grad.addColorStop(1, c2);
      ctx.fillStyle = grad;
      const analyser = analyserRef.current;
      const mid = h / 2;
      const step = Math.max(1, Math.round(2 * devicePixelRatio));
      if (analyser && isPlaying) {
        if (!data || data.length !== analyser.fftSize) data = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(data);
        for (let x = 0; x < w; x += step) {
          const v = Math.abs(data[Math.floor((x / w) * data.length)] - 128) / 128;
          const bar = Math.max(step / 2, v * h);
          ctx.fillRect(x, mid - bar / 2, Math.max(1, step - 1), bar);
        }
        frame = requestAnimationFrame(draw);
      } else {
        ctx.fillRect(0, mid - devicePixelRatio / 2, w, devicePixelRatio);
      }
    };
    draw();
    return () => cancelAnimationFrame(frame);
  }, [style.id, analyserRef, isPlaying]);

  return (
    <div className="visual-preview">
      <div className={isPlaying ? "visual-stage is-playing" : "visual-stage"}>
        <img key={style.id} src={style.src} alt="" />
        <canvas ref={canvas} aria-hidden="true" />
      </div>
      <div className="visual-switch" role="radiogroup" aria-label={t("画面风格")}>
        {visuals.map((v) => (
          <button key={v.id} type="button" role="radio" aria-checked={v.id === style.id}
            className={v.id === style.id ? "is-active" : ""} onClick={() => onVisualChange(v.id)}>
            <img src={v.src} alt="" />
            {t(v.name)}
          </button>
        ))}
      </div>
    </div>
  );
}
