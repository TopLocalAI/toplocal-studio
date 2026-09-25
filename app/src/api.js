import { t } from "./i18n";

// The desktop shell injects window.__LOCALAI__ = { baseUrl, token }. In development the
// Vite proxy serves /api and /files on the same origin and adds the token itself.
const runtime = window.__LOCALAI__ || {};
const BASE = runtime.baseUrl || "";
const TOKEN = runtime.token || "";

async function request(path, options = {}) {
  const response = await fetch(BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(TOKEN ? { "X-LocalAI-Token": TOKEN } : {}),
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || t("本地服务返回 {status}", { status: response.status }));
  return body;
}

export const api = {
  health: () => request("/api/health"),
  system: () => request("/api/system"),
  models: () => request("/api/models"),
  voices: () => request("/api/voices"),
  downloadModel: (id) => request(`/api/models/${id}/download`, { method: "POST", body: "{}" }),
  cancelDownload: (id) => request(`/api/models/${id}/cancel`, { method: "POST", body: "{}" }),
  deleteModel: (id) => request(`/api/models/${id}`, { method: "DELETE" }),
  settings: () => request("/api/settings"),
  saveSettings: (values) => request("/api/settings", { method: "POST", body: JSON.stringify(values) }),
  submit: (module, task, params) =>
    request("/api/jobs", { method: "POST", body: JSON.stringify({ module, task, params }) }),
  job: (id) => request(`/api/jobs/${id}`),
  activeJobs: () => request("/api/jobs"),
  errorReport: () => request("/api/error-report"),
  cancel: (id) => request(`/api/jobs/${id}/cancel`, { method: "POST" }),
  library: (module) => request(`/api/library${module ? `?module=${module}` : ""}`),
  remove: (id) => request(`/api/library/${id}`, { method: "DELETE" }),
  openUrl: (url) => request("/api/open", { method: "POST", body: JSON.stringify({ url }) }),
  save: (id, file, title) =>
    request(`/api/library/${id}/save`, { method: "POST", body: JSON.stringify({ file, title, reveal: true }) }),
};

export const IN_DESKTOP = Boolean(runtime.baseUrl);

// Save a result for the user: into Downloads inside the desktop app, a normal
// browser download otherwise. Returns a short message for a toast.
export async function saveResult(id, file, title) {
  if (IN_DESKTOP) {
    const { name } = await api.save(id, file, title);
    return t("已保存到“下载”文件夹：{name}", { name });
  }
  const a = document.createElement("a");
  a.href = fileUrl(id, file, { download: true });
  a.download = title || file;
  document.body.appendChild(a);
  a.click();
  a.remove();
  return "";
}

export async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file, file.name);
  const response = await fetch(BASE + "/api/uploads", {
    method: "POST",
    headers: TOKEN ? { "X-LocalAI-Token": TOKEN } : {},
    body: form,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || t("上传失败（{status}）", { status: response.status }));
  return body;
}

export function uploadUrl(name) {
  return `${BASE}/uploads/${encodeURIComponent(name)}${TOKEN ? `?token=${TOKEN}` : ""}`;
}

export function fileUrl(id, name, { download = false } = {}) {
  const query = new URLSearchParams();
  if (TOKEN) query.set("token", TOKEN);
  if (download) query.set("download", "1");
  const suffix = query.toString() ? `?${query}` : "";
  return `${BASE}/files/${id}/${encodeURIComponent(name)}${suffix}`;
}

export function formatDuration(seconds) {
  const s = Math.max(0, Math.round(seconds || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// Open a web page (license, project page) in the system browser. The desktop webview
// cannot open new windows itself, so the local service does it.
export function openExternal(url) {
  if (IN_DESKTOP) return api.openUrl(url).catch(() => {});
  window.open(url, "_blank", "noopener");
  return Promise.resolve();
}
