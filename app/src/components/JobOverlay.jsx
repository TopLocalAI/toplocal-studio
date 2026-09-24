import { formatDuration } from "../api";

// Progress card shown over a result area while a job runs.
export function JobOverlay({ job, note = "所有处理均在本机完成" }) {
  if (!job.running) return null;
  const j = job.job || {};
  const progress = Math.round(j.progress || 0);
  return (
    <div className="generation-overlay" role="status" aria-live="polite">
      <div className="generation-orb" aria-hidden="true" />
      <strong>{j.status === "queued" ? "排队中，前一个任务完成后开始" : j.label}</strong>
      <span>
        {progress}% · 已用 {formatDuration(j.elapsedSeconds)}
      </span>
      <div className="generation-progress">
        <span style={{ width: `${progress}%` }} />
      </div>
      <small>{note}</small>
      <button type="button" className="cancel-generation" onClick={job.cancel}>
        取消
      </button>
    </div>
  );
}
