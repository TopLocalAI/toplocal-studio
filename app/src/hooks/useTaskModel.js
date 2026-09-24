import { useCallback, useEffect, useState } from "react";

const key = (task) => `toplocal-model:${task}`;

function saved(task) {
  try {
    return window.localStorage.getItem(key(task));
  } catch {
    return null;
  }
}

// The model chosen for a task: the user's last pick if this machine can run it, else the
// recommended one that is installed, else the recommended one.
export function useTaskModel(task, options) {
  const [choice, setChoice] = useState(() => saved(task));
  const supported = (options || []).filter((o) => o.supported);
  const valid = supported.find((o) => o.model === choice);
  const fallback = supported.find((o) => o.installed) || supported[0] || null;
  const current = valid || fallback;

  useEffect(() => setChoice(saved(task)), [task]);

  const choose = useCallback(
    (model) => {
      setChoice(model);
      try {
        window.localStorage.setItem(key(task), model);
      } catch {
        /* storage unavailable */
      }
    },
    [task],
  );
  return [current, choose];
}
