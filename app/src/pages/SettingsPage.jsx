import { useEffect, useRef, useState } from "react";
import { ArrowClockwise, CheckCircle, GithubLogo, Key, Laptop, Moon, Sun } from "@phosphor-icons/react";
import logo from "../assets/logo.svg";
import { api, openExternal } from "../api";
import { MODULES, TIER_NEED } from "../data";
import { formatBytes, isDownloading, useModels } from "../hooks/useModels";

const MODULE_LABEL = { ...Object.fromEntries(MODULES.map((m) => [m.id, m.label])), shared: "通用" };
const REPO_URL = "https://github.com/TopLocalAI/toplocal-studio";
const TOKEN_URL = "https://huggingface.co/settings/tokens";

// What one module can do on this machine: ready, needs a download, or needs more memory.
function moduleStatus(moduleId, features, models) {
  const list = features.filter((f) => f.module === moduleId);
  const supported = list.filter((f) => f.supported);
  if (!supported.length) {
    const need = Math.min(...list.map((f) => Number(f.minTier)));
    return { tone: "muted", text: `需要 ${TIER_NEED[need]} 以上内存` };
  }
  const missing = [...new Set(supported.filter((f) => !f.ready).flatMap((f) => f.models))]
    .map((id) => models.find((m) => m.id === id))
    .filter((m) => m && !m.installed);
  const limited = list.filter((f) => !f.supported).map((f) => f.name.replace(/^.*·\s*/, ""));
  if (missing.length) {
    return { tone: "warn", text: `需下载模型 · ${formatBytes(missing.reduce((s, m) => s + m.sizeBytes, 0))}` };
  }
  return { tone: "ok", text: limited.length ? `可以使用（${limited.join("、")}需更大内存）` : "可以使用" };
}

function DeviceCard({ system, features, models }) {
  const used = system.diskTotalGb ? 1 - system.diskFreeGb / system.diskTotalGb : 0;
  const lowDisk = system.diskFreeGb < 40;
  return (
    <div className="device-card">
      <div className="device-head">
        <div className="device-icon"><Laptop size={26} /></div>
        <div className="device-title">
          <strong>{system.chip}</strong>
          <span>
            {system.os} {system.osVersion} · {system.memoryGb} GB 内存 ·{" "}
            {system.backend === "metal" ? "Apple Metal 加速" : `${system.backend.toUpperCase()} 加速`}
          </span>
        </div>
      </div>

      <div className="device-meters">
        <div className="meter">
          <div className="meter-label">
            <span>内存</span>
            <strong>{system.memoryGb} GB</strong>
          </div>
          <div className="meter-steps" aria-hidden="true">
            {[16, 24, 48].map((gb) => (
              <i key={gb} className={system.memoryGb >= gb - 2 ? "is-on" : ""} />
            ))}
          </div>
          <small>16 GB 可用音乐、语音、图片；24 GB 起解锁视频和精细修图</small>
        </div>
        <div className="meter">
          <div className="meter-label">
            <span>磁盘</span>
            <strong>
              剩余 {Math.round(system.diskFreeGb)} GB
              {system.diskTotalGb ? <em> / 共 {Math.round(system.diskTotalGb)} GB</em> : null}
            </strong>
          </div>
          <div className={lowDisk ? "meter-bar is-low" : "meter-bar"} aria-hidden="true">
            <i style={{ width: `${Math.round(used * 100)}%` }} />
          </div>
          <small>{lowDisk ? "空间偏少：视频模型约需 31 GB" : "模型按需下载，全部模型约 65 GB"}</small>
        </div>
      </div>

      <ul className="module-status">
        {MODULES.map((m) => {
          const status = moduleStatus(m.id, features, models);
          const Icon = m.icon;
          return (
            <li key={m.id} className={`is-${status.tone}`}>
              <Icon size={20} />
              <strong>{m.label}</strong>
              <span>
                {status.tone === "ok" ? <CheckCircle size={14} weight="fill" /> : null}
                {status.text}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function SettingsPage({ system, theme, onThemeChange, onRefresh, focus }) {
  const { models, hasHfToken, refresh, download, cancel, remove } = useModels(onRefresh);
  const aboutRef = useRef(null);
  const tokenRef = useRef(null);
  const [version, setVersion] = useState("");

  useEffect(() => {
    api.health().then((h) => setVersion(h.version)).catch(() => {});
  }, []);
  useEffect(() => {
    if (focus?.section === "about") aboutRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [focus]);
  const [prefs, setPrefs] = useState(null);
  const [token, setToken] = useState("");
  const [confirming, setConfirming] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.settings().then(setPrefs).catch(() => setPrefs(null));
  }, []);

  const savePrefs = async (values) => {
    try {
      setPrefs(await api.saveSettings(values));
      refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  const act = async (fn) => {
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    }
  };

  const installedBytes = models.filter((m) => m.installed).reduce((s, m) => s + m.sizeBytes, 0);

  return (
    <section className="settings-page">
      <header className="page-header">
        <h1>设置</h1>
        <button type="button" className="button button-secondary" onClick={onRefresh}>
          <ArrowClockwise size={17} /> 重新检测
        </button>
      </header>

      <div className="settings-section">
        <h2>这台电脑</h2>
        {system ? (
          <DeviceCard system={system} features={system.features || []} models={models} />
        ) : (
          <p className="empty-note">正在连接本地引擎…</p>
        )}
      </div>

      <div className="settings-section">
        <h2>外观</h2>
        <div className="segmented segmented-inline" role="radiogroup" aria-label="外观">
          <button type="button" role="radio" aria-checked={theme === "light"} className={theme === "light" ? "is-active" : ""} onClick={() => onThemeChange("light")}>
            <Sun size={17} /> 浅色
          </button>
          <button type="button" role="radio" aria-checked={theme === "dark"} className={theme === "dark" ? "is-active" : ""} onClick={() => onThemeChange("dark")}>
            <Moon size={17} /> 深色
          </button>
        </div>
      </div>

      <div className="settings-section">
        <h2>模型下载</h2>
        {prefs ? (
          <div className="download-prefs">
            <label>
              <span>下载来源</span>
              <div className="segmented segmented-inline" role="radiogroup">
                <button type="button" role="radio" aria-checked={prefs.mirror === "huggingface"} className={prefs.mirror === "huggingface" ? "is-active" : ""} onClick={() => savePrefs({ mirror: "huggingface" })}>
                  Hugging Face
                </button>
                <button type="button" role="radio" aria-checked={prefs.mirror === "hf-mirror"} className={prefs.mirror === "hf-mirror" ? "is-active" : ""} onClick={() => savePrefs({ mirror: "hf-mirror" })}>
                  国内镜像
                </button>
              </div>
            </label>
            <label ref={tokenRef}>
              <span>
                Hugging Face 访问令牌
                {prefs.hasHfToken ? <em className="token-saved"> · 已保存</em> : null}
              </span>
              <div className="token-row">
                <input
                  type="password"
                  value={token}
                  placeholder={prefs.hasHfToken ? "已保存，输入新令牌可替换" : "hf_…"}
                  onChange={(e) => setToken(e.target.value)}
                  autoComplete="off"
                />
                <button type="button" className="button button-secondary" disabled={!token} onClick={() => savePrefs({ hfToken: token }).then(() => setToken(""))}>
                  保存
                </button>
              </div>
              <small className="token-help">
                只有下表中标着 <span className="token-tag"><Key size={11} /> 需令牌</span> 的模型需要（
                {models.filter((m) => m.needsToken).map((m) => m.name).join("、") || "当前没有"}），其他模型直接下载。
                获取方法：登录 Hugging Face，打开模型页面同意许可证，再到{" "}
                <button type="button" className="link-button" onClick={() => openExternal(TOKEN_URL)}>Access Tokens</button>{" "}
                创建一个 Read 类型的令牌，粘贴到这里。
              </small>
            </label>
          </div>
        ) : null}
        {error ? <p className="form-error">{error}</p> : null}
        <table className="model-table">
          <thead>
            <tr>
              <th>模块</th>
              <th>模型</th>
              <th>大小</th>
              <th>许可证</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => {
              const d = m.download;
              const busy = isDownloading(m);
              return (
                <tr key={m.id}>
                  <td>{MODULE_LABEL[m.module]}</td>
                  <td>
                    {m.name}
                    {m.needsToken ? (
                      <button
                        type="button"
                        className="token-tag"
                        title="需要 Hugging Face 令牌：点击打开模型页面同意许可证"
                        onClick={() => openExternal(m.licensePage)}
                      >
                        <Key size={11} /> 需令牌
                      </button>
                    ) : null}
                  </td>
                  <td>{formatBytes(m.sizeBytes)}</td>
                  <td className="license-cell">{m.license}</td>
                  <td className="model-status">
                    {m.installed ? (
                      <>
                        <span className="status-ok">
                          <CheckCircle size={16} weight="fill" /> 已安装
                        </span>
                        {confirming === m.id ? (
                          <>
                            <button type="button" className="link-button is-danger-text" onClick={() => act(() => remove(m.id)).then(() => setConfirming(null))}>
                              确认删除
                            </button>
                            <button type="button" className="link-button" onClick={() => setConfirming(null)}>
                              取消
                            </button>
                          </>
                        ) : (
                          <button type="button" className="link-button" onClick={() => setConfirming(m.id)}>
                            删除
                          </button>
                        )}
                      </>
                    ) : busy ? (
                      <>
                        <span className="mini-progress">
                          <i style={{ width: `${d.totalBytes ? (d.doneBytes / d.totalBytes) * 100 : 0}%` }} />
                        </span>
                        <small>{d.state === "verifying" ? "校验中" : `${formatBytes(d.doneBytes)} / ${formatBytes(d.totalBytes)}`}</small>
                        <button type="button" className="link-button" onClick={() => act(() => cancel(m.id))}>
                          暂停
                        </button>
                      </>
                    ) : (
                      <>
                        {d?.state === "error" ? <small className="status-error" title={d.error}>下载失败</small> : null}
                        {m.needsToken && !hasHfToken ? (
                          <button type="button" className="link-button" onClick={() => tokenRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}>
                            先填写令牌
                          </button>
                        ) : (
                          <button type="button" className="link-button" onClick={() => act(() => download(m.id))}>
                            {d?.doneBytes ? "继续下载" : "下载"}
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="settings-note">
          已安装模型共 {formatBytes(installedBytes)}。所有生成都在本机完成，不上传任何内容。
        </p>
      </div>

      <div className="settings-section" ref={aboutRef}>
        <h2>关于</h2>
        <div className="about-card">
          <img src={logo} alt="" width="56" height="56" />
          <div>
            <strong>TopLocal Studio · 本地创作台</strong>
            <span>版本 {version || "—"} · Apache-2.0 开源 · 非商业项目</span>
            <p>图片、视频、音乐、语音都在这台电脑上生成，不需要账号，也不上传任何内容。</p>
          </div>
          <button type="button" className="button button-secondary" onClick={() => openExternal(REPO_URL)}>
            <GithubLogo size={17} /> 开源主页
          </button>
        </div>
      </div>
    </section>
  );
}
