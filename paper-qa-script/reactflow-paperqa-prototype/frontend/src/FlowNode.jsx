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
    error_detail: errorDetail,
    lastSnapshot,
    onChangeParams,
    onRun,
    onRunUpstream,
    onRunFromHere,
    onLoadEmbedding,
  } = data;

  const isParseStep = step === "parse_chunk_embed";
  const isConfigStep = step === "config";
  const isAnswerStep = step === "answer"; // F-AC11：answer 节点答案全文展示

  // F-AC14（用户走查 2026-09-20 新增问题②）：三个复制按钮**各自独立**的暂态反馈。
  // 原实现共用单一 `copied` state（HEAD e1c6cdb 的 :42）→ 点"复制答案"时"复制 output"
  // 也变"已复制 ✓"（串台）。现每类一个 state + 一个 timer，互不覆盖。
  // 写法对齐同仓 FunctionTraceNode 的 `errCopied`（每按钮独立 state）。
  const COPY_FEEDBACK_MS = 1500;
  const [copiedOutput, setCopiedOutput] = useState(false);
  const [copiedError, setCopiedError] = useState(false);
  const [copiedAnswer, setCopiedAnswer] = useState(false);
  const copiedTimersRef = useRef({});
  useEffect(
    () => () => {
      Object.values(copiedTimersRef.current).forEach((t) => {
        if (t) clearTimeout(t);
      });
    },
    []
  );
  const copiedSetters = {
    output: setCopiedOutput,
    error: setCopiedError,
    answer: setCopiedAnswer,
  };
  const flashCopied = (kind) => {
    const setCopied = copiedSetters[kind];
    if (!setCopied) return;
    setCopied(true);
    const timers = copiedTimersRef.current;
    if (timers[kind]) clearTimeout(timers[kind]);
    timers[kind] = setTimeout(() => setCopied(false), COPY_FEEDBACK_MS);
  };
  const copyText = async (text, kind) => {
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
      flashCopied(kind);
    } catch {
      /* 剪贴板不可用时忽略 */
    }
  };

  // US-4.1 + 走查 2026-09-10：JSON 编辑区改**非受控**（defaultValue + ref）——
  // 受控 textarea 每次击键经 params 回写触发 React 重设 value → 光标跳末尾；
  // 非受控下 React 不触碰 DOM value，光标天然保留；外部 params 变化在未聚焦时手动同步。
  const paramsJson = JSON.stringify(params || {}, null, 2);
  const textareaRef = useRef(null);
  const focusedRef = useRef(false);
  useEffect(() => {
    const next = JSON.stringify(params || {}, null, 2);
    if (!focusedRef.current && textareaRef.current && textareaRef.current.value !== next) {
      textareaRef.current.value = next;
    }
  }, [params]);

  // F-AC4（验收②）：节点运行完成（running → success/failed）时自动收起所有展开项，
  // 仅 output_snapshot 保持展开；用户重新展开后不重复收起，直到下一次运行完成。
  const prevStatusRef = useRef(status);
  const [collapseSignal, setCollapseSignal] = useState(0);
  useEffect(() => {
    const prev = prevStatusRef.current;
    if (prev === "running" && (status === "success" || status === "failed")) {
      setCollapseSignal((s) => s + 1);
    }
    prevStatusRef.current = status;
  }, [status]);
  const collapsed = collapseSignal > 0;

  return (
    <div className={`node-card status-${status || "idle"}`}>
      <Handle type="target" position={Position.Left} />

      <div className="node-header">
        <div className="node-title">{title}</div>
        <div className="node-step">{step}</div>
      </div>

      {isConfigStep ? (
        <SchemaForm
          params={params}
          apiBase={data.apiBase}
          collapsed={collapsed}
          onChange={(text) => onChangeParams(id, text)}
        />
      ) : null}

      <textarea
        ref={textareaRef}
        className="node-textarea nodrag nopan"
        defaultValue={paramsJson}
        onFocus={() => {
          focusedRef.current = true;
        }}
        onBlur={() => {
          focusedRef.current = false;
        }}
        onChange={(e) => {
          onChangeParams(id, e.target.value);
        }}
      />

      {/* F-AC13：运行按钮行必须 nodrag nopan（与 :120 textarea、:177 output 一致）——
          否则 ReactFlow 把 mousedown 判为节点拖拽起点，首次 click 被吃掉（要点 1~2 次才生效）。
          判据在 @reactflow/core 的 useDrag：hasSelector(target, ".nodrag", nodeRef)。 */}
      <div className="node-actions nodrag nopan" data-testid="node-actions-main">
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
        <div className="node-actions embed-actions nodrag nopan" data-testid="node-actions-embed">
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

      <div className="node-output nodrag nopan">
        <div className="node-block-title">
          output_snapshot
          {/* F-AC11（走查 N1）：output 完整查看——一键复制全文 JSON；标题 hover 出全文 tooltip */}
          {!error && (
            <button
              className="run-btn copy-output-btn"
              data-copy-kind="output"
              data-copied={copiedOutput ? "true" : "false"}
              title="复制 output 完整内容"
              onClick={() => copyText(JSON.stringify(output || {}, null, 2), "output")}
            >
              {copiedOutput ? "已复制 ✓" : "复制 output"}
            </button>
          )}
        </div>
        {error ? (
          <div>
            <div className="node-actions err-actions">
              <button
                className="run-btn copy-err-btn"
                data-copy-kind="error"
                data-copied={copiedError ? "true" : "false"}
                title="复制完整错误信息，便于二次调试"
                onClick={() =>
                  copyText(
                    errorDetail ? `${error}\n\n===== 完整堆栈 =====\n${errorDetail}` : error,
                    "error"
                  )
                }
              >
                {copiedError ? "已复制 ✓" : "复制报错"}
              </button>
            </div>
            {/* F-AC6（验收④）：主画布报错 = 摘要 + 可展开完整堆栈（Q5 口径） */}
            <pre className="error-text">{error}</pre>
            {errorDetail ? (
              <details className="error-detail">
                <summary>完整堆栈（traceback）</summary>
                <pre className="error-text">{errorDetail}</pre>
              </details>
            ) : null}
          </div>
        ) : isAnswerStep && output?.answer ? (
          /* F-AC11：answer 节点直接展示答案全文（不再埋在截断的 JsonTree 里） */
          <div className="node-answer">
            <div className="node-block-title">
              答案全文
              <button
                className="run-btn copy-output-btn"
                data-copy-kind="answer"
                data-copied={copiedAnswer ? "true" : "false"}
                onClick={() =>
                  copyText(
                    `答案：\n${output.answer || ""}\n\n参考文献：\n${output.references || ""}`,
                    "answer"
                  )
                }
              >
                {copiedAnswer ? "已复制 ✓" : "复制答案"}
              </button>
            </div>
            <pre className="answer-text">{output.answer}</pre>
            {output.references ? (
              <details className="answer-refs-detail" open>
                <summary>参考文献</summary>
                <pre className="answer-refs">{output.references}</pre>
              </details>
            ) : null}
          </div>
        ) : (
          /* F-AC4：output_snapshot 不参与收起（仅此块在完成后保持展开） */
          <JsonTree value={output || {}} collapsed={false} />
        )}
      </div>

      {lastSnapshot ? (
        <div className="node-output nodrag nopan">
          <div className="node-block-title">input_snapshot</div>
          <JsonTree value={{ input_snapshot: lastSnapshot.input || {} }} collapsed={collapsed} />
        </div>
      ) : null}

      {lastSnapshot ? (
        <div className="node-output nodrag nopan">
          <div className="node-block-title">function_trace (time ordered)</div>
          <JsonTree value={functionTraceList(lastSnapshot.function_trace || [])} collapsed={collapsed} />
        </div>
      ) : null}

      <Handle type="source" position={Position.Right} />
    </div>
  );
}
