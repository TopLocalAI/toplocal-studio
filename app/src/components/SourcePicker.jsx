import { useEffect, useRef, useState } from "react";
import { ImageSquare, UploadSimple, X } from "@phosphor-icons/react";
import { api, fileUrl, uploadFile, uploadUrl } from "../api";

// Pick an input file: drag-and-drop / browse to upload, or reuse an earlier result.
// `value` is a job-param reference: {upload, preview} or {library, file, preview}.
export function SourcePicker({ kind = "image", value, onChange, label = "选择图片" }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [recent, setRecent] = useState([]);

  useEffect(() => {
    if (kind !== "image") return;
    api
      .library("image")
      .then(({ items }) => setRecent(items.slice(0, 6)))
      .catch(() => setRecent([]));
  }, [kind]);

  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const info = await uploadFile(file);
      onChange({ upload: info.id, preview: uploadUrl(info.file), name: file.name });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const accept = kind === "image" ? "image/*" : "audio/*,video/*";

  if (value) {
    return (
      <div className="source-chosen">
        {kind === "image" ? (
          <img src={value.preview} alt="已选择的图片" />
        ) : (
          <span className="source-name">{value.name}</span>
        )}
        <button type="button" className="icon-button" onClick={() => onChange(null)} title="移除">
          <X size={16} />
        </button>
      </div>
    );
  }

  return (
    <div>
      <button
        type="button"
        className={dragging ? "dropzone is-dragging" : "dropzone"}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files?.[0]);
        }}
        disabled={busy}
      >
        <UploadSimple size={22} />
        <strong>{busy ? "正在上传…" : label}</strong>
        <small>拖到这里，或点击选择文件</small>
      </button>
      <input
        ref={input}
        type="file"
        accept={accept}
        hidden
        onChange={(e) => {
          upload(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {recent.length ? (
        <div className="source-recent">
          <span>
            <ImageSquare size={14} /> 或从作品中选择
          </span>
          <div>
            {recent.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() =>
                  onChange({ library: item.id, file: item.result.image, preview: fileUrl(item.id, item.result.image) })
                }
                title={item.title}
              >
                <img src={fileUrl(item.id, item.result.image)} alt={item.title} />
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {error ? <p className="form-error">{error}</p> : null}
    </div>
  );
}
