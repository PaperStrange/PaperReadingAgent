import React, { useEffect, useRef, useState } from "react";
import { Handle, Position } from "reactflow";
import JsonTree from "./JsonTree";
import SchemaForm from "./SchemaForm";

function functionTraceList(trace) {
  const ordered = [...(trace || [])].sort(
    (a, b) => (a.call_id || 0) - (b.call_id || 0)
  );
  return ordered.slice(0, 40).map((e) => ({
    call_id: e.call_id,
    func: e.func,
    status: e.status,
    duration_s: e.duration_s,
    result: e.result,
  }));
}

export default function FlowNode({ id, data }) {
  const {
    title,
    step,
    params,
    status,
    duration,
    output,
    error,
    lastSnapshot,
    onChangeParams,
    onRun,
    onRunUpstream,
    onRunFromHere,
    onLoadEmbedding,
  } = data;

  const isParseStep = step === "parse_chunk_embed";
  const isConfigStep = step === "config";

  // US-5.3：复制报错按钮的暂态反馈（含降级路径与 unmount 清理，Sprint-5 关闭二查修正）
  const [copied, setCopied] = useState(false);
  const copiedTimerRef = useRef(null);
  useEffect(
    () => () => {
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    },
    []
  );
  const flashCopied = () => {
    setCopied(true);
    if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    copiedTimerRef.current = setTimeout(() => setCopied(false), 1500);
  };
  const copyErrorText = async (text) => {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text || "");
      } else {
        // 非安全上下文/旧浏览器降级：临时 textarea + execCommand
        const ta = document.createElement("textarea");
        ta.value = text || "";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      flashCopied();
    } catch {
      /* 剪贴板不可用时忽略 */
    }
  };

  // US-4.1：JSON 编辑区用本地草稿态，避免父组件回写格式化 JSON 导致光标跳末尾/无法连续编辑。
  // 聚焦期间外部 params 变化不覆盖草稿；失焦后恢复跟随。
  const paramsJson = JSON.stringify(params || {}, null, 2);
  const [draft, setDraft] = useState(paramsJson);
  const focusedRef = useRef(false);
  useEffect(() => {
    if (!focusedRef.current) {
      setDraft(JSON.stringify(params || {}, null, 2));
    }
  }, [params]);

  return (
    <div className={`node-card status-${status || "idle"}`}>
      <Handle type="target" position={Position.Left} />

      <div className="node-header">
        <div className="node-title">{title}</div>
        <div className="node-step">{step}</div>
      </div>

      {isConfigStep ? (
        <SchemaForm params={params} apiBase={data.apiBase} onChange={(text) => onChangeParams(id, text)} />
      ) : null}

      <textarea
        className="node-textarea"
        value={draft}
        onFocus={() => {
          focusedRef.current = true;
        }}
        onBlur={() => {
          focusedRef.current = false;
        }}
        onChange={(e) => {
          setDraft(e.target.value);
          onChangeParams(id, e.target.value);
        }}
      />

      <div className="node-actions">
        <button className="run-btn" onClick={() => onRunUpstream(id)}>
          Run Upstream
        </button>
        <button className="run-btn" onClick={() => onRun(id)}>
          Run Node
        </button>
        <button className="run-btn" onClick={() => onRunFromHere(id)}>
          Run From Here
        </button>
      </div>

      {isParseStep && onLoadEmbedding ? (
        <div className="node-actions embed-actions">
          <button
            className="run-btn"
            title="载入最近一次 Embedding 结果；若无则按原逻辑执行"
            onClick={() => onLoadEmbedding(id, "load")}
          >
            载入 Embedding
          </button>
          <button
            className="run-btn"
            title="即使已有 Embedding，也强制重新执行 parse_chunk_embed"
            onClick={() => onLoadEmbedding(id, "regen")}
          >
            重新生成
          </button>
        </div>
      ) : null}

      <div className="node-actions">
        <span className="node-status">
          {status || "idle"}
          {duration ? ` (${duration}s)` : ""}
        </span>
      </div>

      {lastSnapshot?.run_id ? (
        <div className="node-run-meta">
          run_id: <code>{lastSnapshot.run_id}</code>
        </div>
      ) : null}

      <div className="node-output">
        <div className="node-block-title">output_snapshot</div>
        {error ? (
          <div>
            <div className="node-actions err-actions">
              <button
                className="run-btn copy-err-btn"
                title="复制完整错误信息，便于二次调试"
                onClick={() => copyErrorText(error)}
              >
                {copied ? "已复制 ✓" : "复制报错"}
              </button>
            </div>
            <pre className="error-text">{error}</pre>
          </div>
        ) : (
          <JsonTree value={output || {}} />
        )}
      </div>

      {lastSnapshot ? (
        <div className="node-output">
          <div className="node-block-title">input_snapshot</div>
          <JsonTree value={{ input_snapshot: lastSnapshot.input || {} }} />
        </div>
      ) : null}

      {lastSnapshot ? (
        <div className="node-output">
          <div className="node-block-title">function_trace (time ordered)</div>
          <JsonTree value={functionTraceList(lastSnapshot.function_trace || [])} />
        </div>
      ) : null}

      <Handle type="source" position={Position.Right} />
    </div>
  );
}
