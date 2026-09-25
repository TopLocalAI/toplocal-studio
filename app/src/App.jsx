import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { refreshModels } from "./hooks/useModels";
import { useLanguage } from "./i18n";
import { FirstRunDialog } from "./components/FirstRunDialog";
import { Rail } from "./components/Rail";
import { LibraryPage } from "./pages/LibraryPage";
import { ImagePage } from "./pages/ImagePage";
import { MusicPage } from "./pages/MusicPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SpeechPage } from "./pages/SpeechPage";
import { VideoPage } from "./pages/VideoPage";

function initialTheme() {
  try {
    const saved = window.localStorage.getItem("localai-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage unavailable */
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// Hides an inactive page without unmounting it; videos pause when their page is hidden.
function KeepAlive({ active, children }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!active) ref.current?.querySelectorAll("video").forEach((v) => v.pause());
  }, [active]);
  return (
    <div ref={ref} className="page-slot" hidden={!active}>
      {children}
    </div>
  );
}

export function App() {
  const [page, setPage] = useState("image");
  const [theme, setTheme] = useState(initialTheme);
  const [language, setLanguage] = useLanguage();
  const [system, setSystem] = useState(null);
  const [service, setService] = useState("checking");
  const [videoSource, setVideoSource] = useState(null); // image handed over from the image page

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem("localai-theme", theme);
    } catch {
      /* storage unavailable */
    }
  }, [theme]);

  const failures = useRef(0);
  const refreshSystem = useCallback(async () => {
    try {
      setSystem(await api.system());
      refreshModels(); // feature readiness and the model list must agree
      failures.current = 0;
      setService("ready");
    } catch {
      // The service needs a few seconds to start with the app: only report it as
      // unreachable after ~10 s of failed attempts, or once it had been running.
      failures.current += 1;
      setService((s) => (s === "ready" || failures.current >= 5 ? "offline" : s));
    }
  }, []);

  // Poll until the local service answers (it may still be starting with the app).
  useEffect(() => {
    refreshSystem();
    const id = setInterval(() => {
      if (service !== "ready") refreshSystem();
    }, 2000);
    return () => clearInterval(id);
  }, [refreshSystem, service]);

  const [settingsFocus, setSettingsFocus] = useState(null);
  const navigate = useCallback((id) => {
    setSettingsFocus(null);
    setPage(id);
  }, []);
  const showAbout = useCallback(() => {
    setSettingsFocus({ section: "about", at: Date.now() });
    setPage("settings");
  }, []);

  // The service writes progress labels and errors in the UI language.
  // Once saved, reload what the service translates (feature and model names).
  const [serviceLanguage, setServiceLanguage] = useState(null);
  useEffect(() => {
    if (service !== "ready") return;
    api
      .saveSettings({ language })
      .then(() => {
        setServiceLanguage(language);
        refreshSystem();
        window.dispatchEvent(new Event("toplocal:language")); // model lists reload translated
      })
      .catch(() => {});
  }, [language, service, refreshSystem]);

  const features = system?.features || [];
  const clearVideoSource = useCallback(() => setVideoSource(null), []);

  return (
    <div className="app-shell">
      <Rail page={page} onNavigate={navigate} onAbout={showAbout} features={features} service={service} onRetry={refreshSystem} />
      <div className="app-main">
        {/* Creation pages stay mounted so a result, typed text and running jobs survive
            switching tabs; library and settings reload each time they are opened. */}
        <KeepAlive active={page === "music"}>
          <MusicPage active={page === "music"} onModelsChanged={refreshSystem} features={features} serviceReady={service === "ready"} />
        </KeepAlive>
        <KeepAlive active={page === "image"}>
          <ImagePage
            active={page === "image"}
            onModelsChanged={refreshSystem}
            features={features}
            serviceReady={service === "ready"}
            onAnimate={(source) => {
              setVideoSource(source);
              setPage("video");
            }}
          />
        </KeepAlive>
        <KeepAlive active={page === "speech"}>
          <SpeechPage active={page === "speech"} onModelsChanged={refreshSystem} features={features} serviceReady={service === "ready"} />
        </KeepAlive>
        <KeepAlive active={page === "video"}>
          <VideoPage
            active={page === "video"}
            onModelsChanged={refreshSystem}
            features={features}
            serviceReady={service === "ready"}
            system={system}
            initialSource={videoSource}
            onSourceUsed={clearVideoSource}
          />
        </KeepAlive>
        {page === "library" && <LibraryPage onOpenModule={setPage} />}
        {page === "settings" && (
          <SettingsPage system={system} theme={theme} onThemeChange={setTheme} language={language} serviceLanguage={serviceLanguage} onLanguageChange={setLanguage} onRefresh={refreshSystem} focus={settingsFocus} />
        )}
      </div>
      <FirstRunDialog system={system} serviceReady={service === "ready"} onInstalled={refreshSystem} />
    </div>
  );
}
