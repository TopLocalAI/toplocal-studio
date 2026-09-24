//! Desktop shell: starts the local inference service on a private port with a random
//! token, opens the window with those two values injected, and stops the service on exit.

use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

struct Service(Mutex<Option<Child>>);

fn free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .unwrap_or(4318)
}

fn random_token() -> String {
    let mut bytes = [0u8; 24];
    getrandom::getrandom(&mut bytes).expect("system randomness unavailable");
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Directory holding the Python service project (development layout).
/// A packaged build will ship its own runtime; LOCALAI_SERVICE_DIR overrides both.
fn service_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("LOCALAI_SERVICE_DIR") {
        return PathBuf::from(dir);
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../service")
}

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

/// Bundled executable name: `.exe` on Windows.
fn exe(name: &str) -> String {
    if cfg!(windows) {
        format!("{name}.exe")
    } else {
        name.to_string()
    }
}

/// Command for the service: the bundled runtime in release builds, `uv run` in development.
fn service_command(resources: Option<&PathBuf>, data_dir: Option<&PathBuf>, port: u16) -> Command {
    match resources {
        Some(res) => {
            let engines = res.join("engines");
            let python = if cfg!(windows) {
                res.join("runtime/python/python.exe")
            } else {
                res.join("runtime/python/bin/python3.12")
            };
            // macOS ships one static llama-completion; Windows ships llama.cpp's exe with its DLLs.
            let llama = if cfg!(windows) {
                engines.join("llama").join(exe("llama-completion"))
            } else {
                engines.join("llama-completion")
            };
            let mut cmd = Command::new(python);
            cmd.args(["-m", "localai_service", "--port", &port.to_string()])
                .current_dir(res)
                .env("LOCALAI_BUNDLED", "1")
                .env("PYTHONDONTWRITEBYTECODE", "1")
                .env("PYTHONNOUSERSITE", "1")
                .env("PYTHONUTF8", "1")
                .env("LOCALAI_AUDIOCPP_ROOT", engines.join("audiocpp"))
                .env("LOCALAI_AUDIOCPP_CLI", engines.join("audiocpp").join(exe("audiocpp_cli")))
                .env("LOCALAI_LLAMA_COMPLETION", llama)
                .env("LOCALAI_SDCPP_CLI", engines.join("sdcpp").join(exe("sd-cli")))
                .env("LOCALAI_FFMPEG", engines.join(exe("ffmpeg")));
            if let Some(dir) = data_dir {
                cmd.env("LOCALAI_MODELS_DIR", dir.join("models"));
            }
            cmd
        }
        None => {
            let mut cmd = Command::new("uv");
            cmd.args(["run", "localai-service", "--port", &port.to_string()]).current_dir(service_dir());
            cmd
        }
    }
}

fn spawn_service(port: u16, token: &str, resources: Option<PathBuf>, data_dir: Option<PathBuf>) -> std::io::Result<Child> {
    let mut cmd = service_command(resources.as_ref(), data_dir.as_ref(), port);
    cmd.env("LOCALAI_TOKEN", token)
        .env("LOCALAI_PORT", port.to_string())
        // The service exits by itself if this process disappears (crash, force quit).
        .env("LOCALAI_PARENT_PID", std::process::id().to_string());
    if let Some(dir) = data_dir {
        cmd.env("LOCALAI_DATA_DIR", dir);
    }
    // macOS launches GUI apps with a minimal PATH; make Homebrew and uv installs visible.
    if cfg!(target_os = "macos") {
        let home = std::env::var("HOME").unwrap_or_default();
        let path = std::env::var("PATH").unwrap_or_default();
        cmd.env("PATH", format!("{home}/.local/bin:/opt/homebrew/bin:/usr/local/bin:{path}"));
    }
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        cmd.process_group(0); // so shutdown can stop uv and the Python child together
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(CREATE_NO_WINDOW); // no console window next to the app
    }
    cmd.spawn()
}

fn stop_service(child: &mut Child) {
    #[cfg(unix)]
    {
        let _ = Command::new("kill").args(["-TERM", &format!("-{}", child.id())]).status();
    }
    #[cfg(windows)]
    {
        // Stop the service and any engine it started.
        use std::os::windows::process::CommandExt;
        let _ = Command::new("taskkill")
            .args(["/PID", &child.id().to_string(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW)
            .status();
    }
    let _ = child.kill();
    let _ = child.wait();
}

pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let port = free_port();
            let token = random_token();
            // Development runs the service from the checkout with its default data dir;
            // release builds use the bundled runtime and the per-user data dir
            // (~/Library/Application Support on macOS, %LOCALAPPDATA% on Windows, which
            // unlike the roaming AppData is not synced and can hold tens of GB of models).
            let (resources, data_dir) = if cfg!(debug_assertions) {
                (None, None)
            } else {
                (app.path().resource_dir().ok(), app.path().app_local_data_dir().ok())
            };
            let child = spawn_service(port, &token, resources, data_dir)?;
            app.manage(Service(Mutex::new(Some(child))));

            let init = format!(
                "window.__LOCALAI__ = {};",
                serde_json::json!({ "baseUrl": format!("http://127.0.0.1:{port}"), "token": token })
            );
            WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
                .title("TopLocal Studio")
                .inner_size(1360.0, 880.0)
                .min_inner_size(1080.0, 720.0)
                .center()
                .initialization_script(&init)
                .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building TopLocal Studio");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = handle.try_state::<Service>() {
                if let Some(mut child) = state.0.lock().unwrap().take() {
                    stop_service(&mut child);
                }
            }
        }
    });
}
