import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
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

export function App() {
  const [page, setPage] = useState("music");
  const [theme, setTheme] = useState(initialTheme);
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

  const refreshSystem = useCallback(async () => {
    try {
      setSystem(await api.system());
      setService("ready");
    } catch {
      setService("offline");
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

  const features = system?.features || [];
  const clearVideoSource = useCallback(() => setVideoSource(null), []);

  return (
    <div className="app-shell">
      <Rail page={page} onNavigate={setPage} features={features} service={service} />
      <div className="app-main">
        {page === "music" && <MusicPage onModelsChanged={refreshSystem} features={features} serviceReady={service === "ready"} />}
        {page === "image" && (
          <ImagePage onModelsChanged={refreshSystem}
            features={features}
            serviceReady={service === "ready"}
            onAnimate={(source) => {
              setVideoSource(source);
              setPage("video");
            }}
          />
        )}
        {page === "speech" && <SpeechPage onModelsChanged={refreshSystem} features={features} serviceReady={service === "ready"} />}
        {page === "video" && (
          <VideoPage onModelsChanged={refreshSystem}
            features={features}
            serviceReady={service === "ready"}
            system={system}
            initialSource={videoSource}
            onSourceUsed={clearVideoSource}
          />
        )}
        {page === "library" && <LibraryPage onOpenModule={setPage} />}
        {page === "settings" && (
          <SettingsPage system={system} theme={theme} onThemeChange={setTheme} onRefresh={refreshSystem} />
        )}
      </div>
    </div>
  );
}
