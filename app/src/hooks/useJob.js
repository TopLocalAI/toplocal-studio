import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";

const DONE = ["done", "error", "cancelled"];

// Submit one job and poll it until it finishes. `onDone` receives the final job.
export function useJob(onDone) {
  const [job, setJob] = useState(null);
  const timer = useRef(null);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  const stop = () => {
    clearInterval(timer.current);
    timer.current = null;
  };

  const watch = useCallback((id) => {
    stop();
    timer.current = setInterval(async () => {
      try {
        const next = await api.job(id);
        setJob(next);
        if (DONE.includes(next.status)) {
          stop();
          doneRef.current?.(next);
        }
      } catch (error) {
        stop();
        setJob((prev) => ({ ...(prev || {}), status: "error", error: error.message }));
      }
    }, 1000);
  }, []);

  const submit = useCallback(
    async (module, task, params) => {
      const created = await api.submit(module, task, params);
      setJob(created);
      watch(created.id);
      return created;
    },
    [watch],
  );

  const cancel = useCallback(async () => {
    if (job?.id) setJob(await api.cancel(job.id));
  }, [job]);

  useEffect(() => stop, []);

  const running = Boolean(job && !DONE.includes(job.status));
  return { job, running, submit, cancel, reset: () => setJob(null) };
}
