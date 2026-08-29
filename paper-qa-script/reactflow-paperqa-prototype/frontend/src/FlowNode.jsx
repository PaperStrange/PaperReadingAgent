import React from "react";
import { Handle, Position } from "reactflow";
import DataSourcePanel from "./DataSourcePanel";
import JsonTree from "./JsonTree";

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

  return (
    <div className={`node-card status-${status || "idle"}`}>
      <Handle type="target" position={Position.Left} />

      <div className="node-header">
        <div className="node-title">{title}</div>
        <div className="node-step">{step}</div>
      </div>

      {isConfigStep ? (
        <DataSourcePanel
          params={params}
          onChange={(text) => onChangeParams(id, text)}
        />
      ) : null}

      <textarea
        className="node-textarea"
        value={JSON.stringify(params || {}, null, 2)}
        onChange={(e) => onChangeParams(id, e.target.value)}
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
          <pre className="error-text">{error}</pre>
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
