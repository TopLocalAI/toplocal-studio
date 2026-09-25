import { useState } from "react";
import { Check, Copy } from "@phosphor-icons/react";
import { api } from "../api";
import { t } from "../i18n";

// A generation error, with a button that copies the full details (engine logs of the last
// failed job, system info) for a bug report.
export function ErrorMessage({ text }) {
  const [copied, setCopied] = useState(false);
  if (!text) return null;
  const copy = async () => {
    try {
      const { report } = await api.errorReport();
      await navigator.clipboard.writeText(report || text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard or service unavailable */
    }
  };
  return (
    <div className="form-error" role="alert">
      <p>{text}</p>
      <button type="button" className="link-button error-copy" onClick={copy}>
        {copied ? <Check size={13} weight="bold" /> : <Copy size={13} />} {copied ? t("已复制") : t("复制错误详情")}
      </button>
    </div>
  );
}
