import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";

const ACTIVE = ["running", "verifying"];

// One model list for the whole app. Every page and dialog mounts at startup (KeepAlive), so
// separate copies went stale: a model downloaded in the first-run dialog still showed as
// missing on the image page. All hooks read this store, and one poller runs while any
// download is active.
const store = { models: [], tasks: {}, hasHfToken: false };
const listeners = new Set();
const previous = {};
let timer = null;
let inflight = null;

function notify(installed) {
  for (const listener of listeners) listener(installed);
}

async function load() {
  try {
    const { models: list, hasHfToken, tasks } = await api.models();
    let active = false;
    let installed = false;
    for (const m of list) {
      const state = m.download?.state;
      if (ACTIVE.includes(state)) active = true;
      if (state === "done" && ACTIVE.includes(previous[m.id])) installed = true;
      previous[m.id] = state;
    }
    Object.assign(store, { models: list, tasks: tasks || {}, hasHfToken: Boolean(hasHfToken) });
    notify(installed);
    clearTimeout(timer);
    if (active) timer = setTimeout(refreshModels, 1000);
  } catch {
    clearTimeout(timer);
    timer = setTimeout(refreshModels, 3000);
  }
}

export function refreshModels() {
  inflight ??= load().finally(() => {
    inflight = null;
  });
  return inflight;
}

if (typeof window !== "undefined") {
  window.addEventListener("toplocal:language", refreshModels);
  window.addEventListener("focus", refreshModels);
}

// Model list with live download progress. Calls `onInstalled` once a download finishes so
// feature availability can be refreshed.
export function useModels(onInstalled) {
  const [snapshot, setSnapshot] = useState(store);
  const installedRef = useRef(onInstalled);
  installedRef.current = onInstalled;

  useEffect(() => {
    const listener = (installed) => {
      setSnapshot({ ...store });
      if (installed) installedRef.current?.();
    };
    listeners.add(listener);
    if (store.models.length) setSnapshot({ ...store });
    refreshModels();
    return () => listeners.delete(listener);
  }, []);

  const download = useCallback(async (id) => {
    await api.downloadModel(id);
    await refreshModels();
  }, []);
  const cancel = useCallback(async (id) => {
    await api.cancelDownload(id);
    await refreshModels();
  }, []);
  const remove = useCallback(async (id) => {
    await api.deleteModel(id);
    await refreshModels();
    installedRef.current?.();
  }, []);

  return { ...snapshot, refresh: refreshModels, download, cancel, remove };
}

export function formatBytes(bytes) {
  if (!bytes) return "0 MB";
  return bytes >= 1024 ** 3 ? `${(bytes / 1024 ** 3).toFixed(1)} GB` : `${Math.round(bytes / 1024 ** 2)} MB`;
}

export function isDownloading(model) {
  return ACTIVE.includes(model?.download?.state);
}
