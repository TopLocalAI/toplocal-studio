import { useEffect, useState } from "react";
import { ArrowClockwise, CheckCircle, Moon, Sun } from "@phosphor-icons/react";
import { api } from "../api";
import { MODULES, TIER_LABEL } from "../data";
import { formatBytes, isDownloading, useModels } from "../hooks/useModels";

const MODULE_LABEL = { ...Object.fromEntries(MODULES.map((m) => [m.id, m.label])), shared: "通用" };

export function SettingsPage({ system, theme, onThemeChange, onRefresh }) {
  const { models, download, cancel, remove } = useModels(onRefresh);
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
          <dl className="device-grid">
            <dt>芯片</dt>
            <dd>{system.chip}</dd>
            <dt>内存</dt>
            <dd>
              {system.memoryGb} GB（{TIER_LABEL[system.tier]}）
            </dd>
            <dt>系统</dt>
            <dd>
              {system.os} {system.osVersion} · {system.arch}
            </dd>
            <dt>可用空间</dt>
            <dd>{system.diskFreeGb} GB</dd>
            <dt>加速</dt>
            <dd>{system.backend === "metal" ? "Apple Metal" : system.backend.toUpperCase()}</dd>
          </dl>
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
            <label>
              <span>Hugging Face 访问令牌（部分模型需要）</span>
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
                  <td>{m.name}</td>
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
                        <button type="button" className="link-button" onClick={() => act(() => download(m.id))}>
                          {d?.doneBytes ? "继续下载" : "下载"}
                        </button>
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
    </section>
  );
}
