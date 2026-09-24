import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";

const ACTIVE = ["running", "verifying"];

// Model list with live download progress. Polls while any download is active and calls
// `onInstalled` once a download finishes so feature availability can be refreshed.
export function useModels(onInstalled) {
  const [models, setModels] = useState([]);
  const timer = useRef(null);
  const installedRef = useRef(onInstalled);
  installedRef.current = onInstalled;
  const previous = useRef({});

  const refresh = useCallback(async () => {
    try {
      const { models: list } = await api.models();
      setModels(list);
      let active = false;
      for (const m of list) {
        const state = m.download?.state;
        if (ACTIVE.includes(state)) active = true;
        if (state === "done" && ACTIVE.includes(previous.current[m.id])) installedRef.current?.();
        previous.current[m.id] = state;
      }
      clearTimeout(timer.current);
      if (active) timer.current = setTimeout(refresh, 1000);
    } catch {
      clearTimeout(timer.current);
      timer.current = setTimeout(refresh, 3000);
    }
  }, []);

  useEffect(() => {
    refresh();
    return () => clearTimeout(timer.current);
  }, [refresh]);

  const download = useCallback(
    async (id) => {
      await api.downloadModel(id);
      refresh();
    },
    [refresh],
  );
  const cancel = useCallback(
    async (id) => {
      await api.cancelDownload(id);
      refresh();
    },
    [refresh],
  );
  const remove = useCallback(
    async (id) => {
      await api.deleteModel(id);
      await refresh();
      installedRef.current?.();
    },
    [refresh],
  );

  return { models, refresh, download, cancel, remove };
}

export function formatBytes(bytes) {
  if (!bytes) return "0 MB";
  return bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(1)} GB` : `${Math.round(bytes / 1024 ** 2)} MB`;
}

export function isDownloading(model) {
  return ACTIVE.includes(model?.download?.state);
}
