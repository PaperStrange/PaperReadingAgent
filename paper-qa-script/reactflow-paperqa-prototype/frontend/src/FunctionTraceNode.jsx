import React, { useMemo, useState } from "react";
import { Handle, Position } from "reactflow";
import JsonTree from "./JsonTree";
import { translatePreview } from "./api";

function short(text, maxLen = 180) {
  const s = String(text ?? "");
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen - 14) + "...[truncated]";
}

function formatDuration(sec) {
  const s = Number(sec || 0);
  if (s <= 0) return "0s";
  if (s < 0.001) return `${Math.max(1, Math.round(s * 1_000_000))}us`;
  if (s < 1) return `${Math.round(s * 1_000)}ms`;
  return `${s.toFixed(3)}s`;
}

export default function FunctionTraceNode({ data }) {
  const [zhText, setZhText] = useState("");
  const [translating, setTranslating] = useState(false);
  const [translateErr, setTranslateErr] = useState("");

  const rp = data?.result_payload || null;
  const ap = data?.args_payload || null;
  const showMedia = rp && typeof rp === "object" && (rp.page_preview_url || rp.first_media_url);
  const previewReason = rp && typeof rp === "object" ? rp.preview_reason : null;
  const previewState = (() => {
    if (!rp || typeof rp !== "object") return null;
    if (previewReason === "ok" || rp.page_preview_url || rp.first_media_url) return "ok";
    if (!previewReason) return "none";
    if (previewReason === "no_fitz" || previewReason === "render_error") return "error";
    return "warn";
  })();
  const textFull = useMemo(() => {
    if (!rp || typeof rp !== "object") return "";
    return String(rp.text_full || rp.text_preview || "");
  }, [rp]);

  const onTranslate = async () => {
    if (!textFull) return;
    setTranslateErr("");
    setTranslating(true);
    try {
      if (!data?.api_base || !data?.session_id) {
        throw new Error("missing api_base or session_id");
      }
      const r = await translatePreview(data.api_base, {
        session_id: data.session_id,
        text: textFull,
      });
      setZhText(String(r.text_zh || ""));
    } catch (e) {
      setTranslateErr(String(e));
    } finally {
      setTranslating(false);
    }
  };

  return (
    <div className={`fn-node-card ${data?.status === "error" ? "fn-error" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="fn-title">#{data?.call_id} {data?.func || "function"}</div>
      <div className="fn-meta">
        {data?.status || "ok"} | {formatDuration(data?.duration_s)}
      </div>
      <div className="fn-meta">
        depth={data?.depth ?? 0} | parent={data?.parent_call_id ?? "root"} | task={data?.task_id || "task-main"}
      </div>
      {previewState ? (
        <div className={`fn-preview-chip fn-preview-${previewState}`}>
          preview {previewState}
          {previewReason ? `: ${previewReason}` : ""}
        </div>
      ) : null}
      {data?.result ? <div className="fn-result">result: {short(data.result)}</div> : null}
      {ap ? (
        <details className="fn-detail" open>
          <summary>args payload</summary>
          <JsonTree value={ap} />
        </details>
      ) : null}
      {rp ? (
        <details className="fn-detail" open>
          <summary>result payload</summary>
          <JsonTree value={rp} />
          {textFull ? (
            <details className="fn-text-block" open>
              <summary>Text (English, full)</summary>
              <pre>{textFull}</pre>
              <button className="run-btn" onClick={onTranslate} disabled={translating}>
                {translating ? "Translating..." : "Translate to 中文"}
              </button>
              {zhText ? (
                <details className="fn-text-block" open>
                  <summary>中文翻译</summary>
                  <pre>{zhText}</pre>
                </details>
              ) : null}
              {translateErr ? <div className="fn-error-text">translate error: {translateErr}</div> : null}
            </details>
          ) : null}
          {showMedia ? (
            <img
              className="fn-media"
              src={rp.page_preview_url || rp.first_media_url}
              alt="chunk media preview"
            />
          ) : null}
          {!showMedia && previewReason ? (
            <div className="fn-preview-reason">preview: {String(previewReason)}</div>
          ) : null}
        </details>
      ) : null}
      {data?.error ? <div className="fn-error-text">error: {data.error}</div> : null}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
