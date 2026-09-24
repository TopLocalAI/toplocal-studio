// UI language. Strings in the code are the Chinese source text; t() returns the English
// version from ./en when English is selected. Placeholders: t("共 {n} 个", { n: 3 }).
import { useEffect, useState } from "react";
import EN from "./en/index.js";

export const LANGUAGES = [
  { id: "zh", label: "中文" },
  { id: "en", label: "English" },
];

function detect() {
  try {
    const saved = window.localStorage.getItem("toplocal-language");
    if (saved === "zh" || saved === "en") return saved;
  } catch {
    /* storage unavailable */
  }
  return (navigator.language || "zh").toLowerCase().startsWith("zh") ? "zh" : "en";
}

let current = detect();
const listeners = new Set();
document.documentElement.lang = current === "zh" ? "zh-CN" : "en";

export function t(text, values) {
  let out = current === "en" ? EN[text] ?? text : text;
  if (values) out = out.replace(/\{(\w+)\}/g, (_, k) => (values[k] ?? ""));
  return out;
}

export function getLanguage() {
  return current;
}

export function setLanguage(lang) {
  if (lang === current || !LANGUAGES.some((l) => l.id === lang)) return;
  current = lang;
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  try {
    window.localStorage.setItem("toplocal-language", lang);
  } catch {
    /* storage unavailable */
  }
  listeners.forEach((fn) => fn(lang));
}

// Re-renders the calling component (the app root) when the language changes.
export function useLanguage() {
  const [lang, setLang] = useState(current);
  useEffect(() => {
    listeners.add(setLang);
    return () => listeners.delete(setLang);
  }, []);
  return [lang, setLanguage];
}
