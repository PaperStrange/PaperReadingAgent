import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import FlowNode from "./FlowNode";
import FunctionTraceNode from "./FunctionTraceNode";
import { newSession, resetSession, runStep } from "./api";

const nodeTypes = { stepNode: FlowNode, functionNode: FunctionTraceNode };

function safeParseJson(text) {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

function makeRunId() {
  const ts = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const rnd = Math.random().toString(36).slice(2, 8);
  return `run-${ts}-${rnd}`;
}

function makeNode(id, title, step, x, y, params) {
  return {
    id,
    type: "stepNode",
    position: { x, y },
    data: {
      title,
      step,
      params,
      status: "idle",
      duration: null,
      output: {},
      error: null,
      lastSnapshot: null,
    },
  };
}

function mergeFunctionTrace(prevTrace, nextTrace) {
  const merged = new Map();
  const keyOf = (e) =>
    `${e?.call_id ?? "na"}|${e?.func ?? ""}|${e?.parent_call_id ?? "root"}|${e?.task_id ?? "task-main"}`;
  for (const e of prevTrace || []) {
    merged.set(keyOf(e), e);
  }
  for (const e of nextTrace || []) {
    merged.set(keyOf(e), { ...(merged.get(keyOf(e)) || {}), ...e });
  }
  return [...merged.values()].sort((a, b) => (a.call_id || 0) - (b.call_id || 0));
}

const initialNodesRaw = [
  makeNode("n1", "1) Config", "config", 20, 40, {
    api_key: "",
    api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    model: "openai/qwen-omni-turbo",
    embedding_model: "openai/text-embedding-v4",
    paper_directory: "/Volumes/Extreme SSD/vscode_projects/PaperReading/data/pdf",
    index_name: "debug_index",
    embedding_batch_size: 10,
    chunk_chars: 5000,
    chunk_overlap: 250,
    temperature: 0.1,
  }),
  makeNode("n2", "2) Load Index", "load_index", 480, 40, {
    build: true,
  }),
  makeNode("n3", "3) Retrieve", "retrieve", 940, 40, {
    query: "什么是PaperQA？",
    top_n: 5,
  }),
  makeNode("n4", "4) Parse Chunk Embed", "parse_chunk_embed", 1380, 40, {
    candidate_paths: [],
  }),
  makeNode("n5", "5) Gather Evidence", "evidence", 1820, 40, {
    question: "什么是PaperQA？",
  }),
  makeNode("n6", "6) Generate Answer", "answer", 2260, 40, {}),
];

const initialEdges = [
  { id: "e1-2", source: "n1", target: "n2" },
  { id: "e2-3", source: "n2", target: "n3" },
  { id: "e3-4", source: "n3", target: "n4" },
  { id: "e4-5", source: "n4", target: "n5" },
  { id: "e5-6", source: "n5", target: "n6" },
];
const STEP_NODE_IDS = new Set(initialNodesRaw.map((n) => n.id));

function buildFunctionSubgraphForStep(stepNode) {
  const trace = stepNode?.data?.lastSnapshot?.function_trace || [];
  const ordered = [...trace]
    .sort((a, b) => (a.call_id || 0) - (b.call_id || 0))
    .slice(0, 140);

  if (!ordered.length) return { nodes: [], edges: [] };

  const byCallId = new Map();
  ordered.forEach((evt) => {
    if (evt.call_id != null) byCallId.set(evt.call_id, evt);
  });

  const children = new Map();
  const roots = [];
  ordered.forEach((evt) => {
    const cid = evt.call_id;
    const pid = evt.parent_call_id;
    if (cid == null) return;
    if (pid == null || !byCallId.has(pid)) {
      roots.push(cid);
      return;
    }
    if (!children.has(pid)) children.set(pid, []);
    children.get(pid).push(cid);
  });
  for (const arr of children.values()) arr.sort((a, b) => a - b);
  roots.sort((a, b) => a - b);

  const layoutX = new Map();
  const layoutDepth = new Map();
  let cursor = 0;
  const visited = new Set();

  const place = (cid, depth) => {
    if (visited.has(cid)) return layoutX.get(cid) ?? 0;
    visited.add(cid);
    layoutDepth.set(cid, depth);
    const kids = children.get(cid) || [];
    if (!kids.length) {
      layoutX.set(cid, cursor);
      cursor += 1;
      return layoutX.get(cid);
    }
    const kidXs = kids.map((k) => place(k, depth + 1));
    const x = kidXs.reduce((s, v) => s + v, 0) / kidXs.length;
    layoutX.set(cid, x);
    return x;
  };

  roots.forEach((r) => place(r, 0));
  ordered.forEach((evt) => {
    const cid = evt.call_id;
    if (cid != null && !layoutX.has(cid)) place(cid, 0);
  });

  const PAD_X = 24;
  const PAD_Y = 24;
  // Keep layout constants aligned with .fn-node-card width in styles.css
  const NODE_W = 340;
  const NODE_H = 210;
  const GAP_X = 24;
  const GAP_Y = 22;
  const DEPTH_GAP = 34;
  const MAX_CANVAS_WIDTH = 860;
  const cols = Math.max(
    1,
    Math.floor((MAX_CANVAS_WIDTH - PAD_X * 2 + GAP_X) / (NODE_W + GAP_X))
  );

  const depthGroups = new Map();
  ordered.forEach((evt, idx) => {
    const callId = evt.call_id ?? idx + 1;
    const depth = layoutDepth.get(callId) ?? Math.max(evt.depth || 0, 0);
    const xOrder = layoutX.get(callId) ?? idx;
    if (!depthGroups.has(depth)) depthGroups.set(depth, []);
    depthGroups.get(depth).push({ callId, evt, xOrder });
  });
  for (const arr of depthGroups.values()) {
    arr.sort((a, b) => a.xOrder - b.xOrder || a.callId - b.callId);
  }

  const posByCallId = new Map();
  const orderedDepths = [...depthGroups.keys()].sort((a, b) => a - b);
  let depthStartY = PAD_Y;
  let maxRowWidth = 0;
  for (const depth of orderedDepths) {
    const arr = depthGroups.get(depth) || [];
    const rows = Math.max(1, Math.ceil(arr.length / cols));
    const rowWidth = Math.min(arr.length, cols) * (NODE_W + GAP_X) - GAP_X;
    maxRowWidth = Math.max(maxRowWidth, rowWidth);

    arr.forEach((item, i) => {
      const row = Math.floor(i / cols);
      const col = i % cols;
      posByCallId.set(item.callId, {
        x: PAD_X + col * (NODE_W + GAP_X),
        y: depthStartY + row * (NODE_H + GAP_Y),
        depth,
      });
    });
    depthStartY += rows * (NODE_H + GAP_Y) + DEPTH_GAP;
  }

  // Soft collision pass to handle tall cards (expanded payloads) and keep minimal spacing.
  const placed = [];
  for (const depth of orderedDepths) {
    const arr = depthGroups.get(depth) || [];
    for (const item of arr) {
      const base = posByCallId.get(item.callId);
      if (!base) continue;
      let x = base.x;
      let y = base.y;
      for (const p of placed) {
        const overlapY = Math.abs(y - p.y) < NODE_H;
        const overlapX = Math.abs(x - p.x) < NODE_W;
        if (overlapY && overlapX) {
          x = p.x + NODE_W + GAP_X;
        }
      }
      posByCallId.set(item.callId, { x, y, depth });
      placed.push({ x, y });
      maxRowWidth = Math.max(maxRowWidth, x + NODE_W - PAD_X);
    }
  }

  const nodes = [];
  ordered.forEach((evt, idx) => {
    const callId = evt.call_id ?? idx + 1;
    const pos = posByCallId.get(callId) || {
      x: PAD_X,
      y: PAD_Y,
      depth: layoutDepth.get(callId) ?? Math.max(evt.depth || 0, 0),
    };
    const nodeId = `${stepNode.id}__fn__${callId}`;
    nodes.push({
      id: nodeId,
      type: "functionNode",
      position: {
        x: pos.x,
        y: pos.y,
      },
      draggable: true,
      data: {
        call_id: callId,
        func: evt.func || "",
        status: evt.status || "ok",
        duration_s: evt.duration_s || 0,
        depth: pos.depth,
        parent_call_id: evt.parent_call_id ?? null,
        task_id: evt.task_id || "task-main",
        result: evt.result || "",
        args_payload: evt.args_payload || null,
        result_payload: evt.result_payload || null,
        error: evt.error || "",
      },
    });
  });

  const idByCallId = new Map(nodes.map((n) => [Number(n.data.call_id), n.id]));
  const edges = [];
  ordered.forEach((evt, idx) => {
    const callId = evt.call_id ?? idx + 1;
    const curId = idByCallId.get(Number(callId));
    if (!curId) return;
    if (evt.parent_call_id != null && idByCallId.has(Number(evt.parent_call_id))) {
      const parentId = idByCallId.get(Number(evt.parent_call_id));
      edges.push({
        id: `fn-edge-parent-${parentId}-${curId}`,
        source: parentId,
        target: curId,
      });
    }
  });

  return {
    nodes,
    edges,
    meta: {
      width: Math.max(820, PAD_X * 2 + maxRowWidth),
      height: Math.max(420, depthStartY + PAD_Y),
    },
  };
}

export default function App() {
  const [apiBase, setApiBase] = useState("http://127.0.0.1:8787");
  const [sessionId, setSessionId] = useState("");
  const [runId, setRunId] = useState(makeRunId());
  const [globalLog, setGlobalLog] = useState([]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodesRaw);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const [fnNodes, setFnNodes, onFnNodesChange] = useNodesState([]);
  const [fnEdges, setFnEdges, onFnEdgesChange] = useEdgesState([]);
  const [activeStepId, setActiveStepId] = useState("n1");
  const [fnCanvasMeta, setFnCanvasMeta] = useState({ width: 820, height: 420 });
  const [fnFlowRevision, setFnFlowRevision] = useState(0);

  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  const fnNodesRef = useRef(fnNodes);
  const fnEdgesRef = useRef(fnEdges);

  const sessionIdRef = useRef(sessionId);
  const runIdRef = useRef(runId);
  const activeStepIdRef = useRef(activeStepId);
  const lastRenderedStepRef = useRef(null);

  const refreshScheduledRef = useRef(false);
  const pendingFnNodesRef = useRef([]);
  const revealTimerRef = useRef(null);
  const desiredFnEdgesRef = useRef([]);

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);
  useEffect(() => {
    edgesRef.current = edges;
  }, [edges]);
  useEffect(() => {
    fnNodesRef.current = fnNodes;
  }, [fnNodes]);
  useEffect(() => {
    fnEdgesRef.current = fnEdges;
  }, [fnEdges]);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);
  useEffect(() => {
    runIdRef.current = runId;
  }, [runId]);
  useEffect(() => {
    activeStepIdRef.current = activeStepId;
  }, [activeStepId]);

  const applyNodesUpdate = useCallback(
    (updater) => {
      setNodes((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        nodesRef.current = next;
        return next;
      });
    },
    [setNodes]
  );

  const applyEdgesUpdate = useCallback(
    (updater) => {
      setEdges((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        edgesRef.current = next;
        return next;
      });
    },
    [setEdges]
  );

  const applyFnNodesUpdate = useCallback(
    (updater) => {
      setFnNodes((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        fnNodesRef.current = next;
        return next;
      });
    },
    [setFnNodes]
  );

  const applyFnEdgesUpdate = useCallback(
    (updater) => {
      setFnEdges((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        fnEdgesRef.current = next;
        return next;
      });
    },
    [setFnEdges]
  );

  const logLine = useCallback((line) => {
    setGlobalLog((logs) => [...logs, `[${new Date().toLocaleTimeString()}] ${line}`]);
  }, []);

  const stopRevealTimer = useCallback(() => {
    if (revealTimerRef.current) {
      clearInterval(revealTimerRef.current);
      revealTimerRef.current = null;
    }
    pendingFnNodesRef.current = [];
  }, []);

  const syncFnEdges = useCallback(() => {
    const visibleIds = new Set(fnNodesRef.current.map((n) => n.id));
    const kept = (desiredFnEdgesRef.current || []).filter(
      (e) => visibleIds.has(e.source) && visibleIds.has(e.target)
    );
    applyFnEdgesUpdate(kept);
  }, [applyFnEdgesUpdate]);

  const startRevealTimer = useCallback(() => {
    if (revealTimerRef.current) {
      clearInterval(revealTimerRef.current);
      revealTimerRef.current = null;
    }

    if (!pendingFnNodesRef.current.length) {
      syncFnEdges();
      return;
    }

    revealTimerRef.current = setInterval(() => {
      if (!pendingFnNodesRef.current.length) {
        stopRevealTimer();
        syncFnEdges();
        return;
      }
      const nextNode = pendingFnNodesRef.current.shift();
      applyFnNodesUpdate((prev) => {
        if (prev.some((n) => n.id === nextNode.id)) return prev;
        return [...prev, nextNode];
      });
      syncFnEdges();
    }, 45);
  }, [applyFnNodesUpdate, stopRevealTimer, syncFnEdges]);

  const refreshFunctionPanel = useCallback(() => {
    const stepNode = nodesRef.current.find((n) => n.id === activeStepIdRef.current);
    if (!stepNode) {
      lastRenderedStepRef.current = null;
      applyFnNodesUpdate([]);
      applyFnEdgesUpdate([]);
      setFnCanvasMeta({ width: 820, height: 420 });
      return;
    }
    const stepId = stepNode.id;
    const switchedStep = lastRenderedStepRef.current !== stepId;
    if (switchedStep) {
      stopRevealTimer();
      pendingFnNodesRef.current = [];
      desiredFnEdgesRef.current = [];
      fnNodesRef.current = [];
      fnEdgesRef.current = [];
      applyFnNodesUpdate([]);
      applyFnEdgesUpdate([]);
      setFnFlowRevision((v) => v + 1);
      lastRenderedStepRef.current = stepId;
    }

    const built = buildFunctionSubgraphForStep(stepNode);
    setFnCanvasMeta(built.meta || { width: 820, height: 420 });
    let nextNodes = built.nodes || [];
    let nextEdges = built.edges || [];

    // Avoid mid-run disappearing nodes caused by temporary trace shrinkage.
    if (stepNode.data?.status === "running" && !switchedStep) {
      const builtIds = new Set(nextNodes.map((n) => n.id));
      const prevNodesSameStep = fnNodesRef.current.filter((n) =>
        String(n.id).startsWith(`${stepId}__fn__`)
      );
      const keepOld = prevNodesSameStep.filter((n) => !builtIds.has(n.id));
      if (keepOld.length) {
        nextNodes = [...nextNodes, ...keepOld];
        const keepIds = new Set(nextNodes.map((n) => n.id));
        const keepOldEdges = fnEdgesRef.current.filter(
          (e) => keepIds.has(e.source) && keepIds.has(e.target)
        );
        const edgeIds = new Set(nextEdges.map((e) => e.id));
        for (const e of keepOldEdges) {
          if (!edgeIds.has(e.id)) {
            nextEdges.push(e);
            edgeIds.add(e.id);
          }
        }
      }
    }
    desiredFnEdgesRef.current = nextEdges;

    // Do not pin old coordinates; recompute every refresh to keep collision-free layout.
    const stabilized = nextNodes.map((n) => ({
      ...n,
      data: {
        ...n.data,
        api_base: apiBase,
        session_id: sessionIdRef.current || null,
      },
    }));

    const existingIds = new Set(fnNodesRef.current.map((n) => n.id));
    const keepNow = stabilized.filter((n) => existingIds.has(n.id));
    const queued = stabilized
      .filter((n) => !existingIds.has(n.id))
      .sort((a, b) => Number(a.data?.call_id || 0) - Number(b.data?.call_id || 0));

    pendingFnNodesRef.current = queued;
    applyFnNodesUpdate(keepNow);
    if (!keepNow.length) {
      applyFnEdgesUpdate([]);
    } else {
      syncFnEdges();
    }
    startRevealTimer();
  }, [apiBase, applyFnEdgesUpdate, applyFnNodesUpdate, startRevealTimer, stopRevealTimer, syncFnEdges]);

  const scheduleFnRefresh = useCallback(() => {
    if (refreshScheduledRef.current) return;
    refreshScheduledRef.current = true;
    requestAnimationFrame(() => {
      refreshScheduledRef.current = false;
      refreshFunctionPanel();
    });
  }, [refreshFunctionPanel]);

  useEffect(() => {
    refreshFunctionPanel();
  }, [activeStepId, refreshFunctionPanel]);

  useEffect(() => () => stopRevealTimer(), [stopRevealTimer]);

  const sortedByX = useCallback((ids) => {
    const posMap = new Map(nodesRef.current.map((n) => [n.id, n.position.x]));
    return [...ids].sort((a, b) => (posMap.get(a) ?? 0) - (posMap.get(b) ?? 0));
  }, []);

  const getUpstreamIds = useCallback(
    (nodeId) => {
      const rev = new Map();
      for (const e of edgesRef.current) {
        if (!rev.has(e.target)) rev.set(e.target, new Set());
        rev.get(e.target).add(e.source);
      }
      const seen = new Set();
      const stack = [...(rev.get(nodeId) ?? [])];
      while (stack.length) {
        const cur = stack.pop();
        if (seen.has(cur)) continue;
        seen.add(cur);
        for (const p of rev.get(cur) ?? []) stack.push(p);
      }
      return sortedByX([...seen]);
    },
    [sortedByX]
  );

  const getDownstreamIds = useCallback(
    (nodeId) => {
      const fwd = new Map();
      for (const e of edgesRef.current) {
        if (!fwd.has(e.source)) fwd.set(e.source, new Set());
        fwd.get(e.source).add(e.target);
      }
      const seen = new Set();
      const stack = [...(fwd.get(nodeId) ?? [])];
      while (stack.length) {
        const cur = stack.pop();
        if (seen.has(cur)) continue;
        seen.add(cur);
        for (const p of fwd.get(cur) ?? []) stack.push(p);
      }
      return sortedByX([...seen]);
    },
    [sortedByX]
  );

  const markDownstreamStale = useCallback(
    (nodeId) => {
      const staleIds = new Set(getDownstreamIds(nodeId));
      if (!staleIds.size) return;
      applyNodesUpdate((nds) =>
        nds.map((n) => {
          if (!staleIds.has(n.id) || n.data.status === "running") return n;
          return {
            ...n,
            data: {
              ...n.data,
              status: "stale",
              duration: null,
              error: null,
            },
          };
        })
      );
    },
    [applyNodesUpdate, getDownstreamIds]
  );

  const runSingleNode = useCallback(
    async (id, opts = { markDependents: true }) => {
      const currentNode = nodesRef.current.find((n) => n.id === id);
      if (!currentNode) return null;

      let sid = sessionIdRef.current;
      if (!sid) {
        const created = await newSession(apiBase);
        sid = created.session_id;
        setSessionId(sid);
      }

      const incoming = edgesRef.current
        .filter((e) => e.target === id)
        .map((e) => nodesRef.current.find((n) => n.id === e.source))
        .filter(Boolean);

      const upstream = {
        upstream_node_ids: incoming.map((n) => n.id),
        outputs: incoming.map((n) => ({
          node_id: n.id,
          step: n.data.step,
          output: n.data.output,
          status: n.data.status,
        })),
      };

      const activeRunId = runIdRef.current || makeRunId();
      if (!runIdRef.current) setRunId(activeRunId);

      const inputSnapshot = {
        step: currentNode.data.step,
        params: currentNode.data.params || {},
        upstream,
        session_id: sid,
      };

      let evtSource = null;
      try {
        const streamUrl = `${apiBase}/api/stream/${sid}/${activeRunId}`;
        evtSource = new EventSource(streamUrl);
        evtSource.onmessage = (ev) => {
          try {
            const payload = JSON.parse(ev.data || "{}");
            if (payload.kind !== "function_trace") return;

            applyNodesUpdate((nds) =>
              nds.map((n) => {
                if (n.id !== id) return n;
                const prev = n.data?.lastSnapshot?.function_trace || [];
                if (prev.some((x) => x.call_id === payload.call_id && x.func === payload.func)) {
                  const nextTrace = prev.map((x) =>
                    x.call_id === payload.call_id && x.func === payload.func
                      ? { ...x, ...payload }
                      : x
                  );
                  return {
                    ...n,
                    data: {
                      ...n.data,
                      lastSnapshot: {
                        run_id: activeRunId,
                        timestamp: new Date().toISOString(),
                        input: inputSnapshot,
                        output: n.data?.lastSnapshot?.output || {},
                        function_trace: nextTrace,
                        error: n.data?.lastSnapshot?.error || null,
                      },
                    },
                  };
                }
                const nextTrace = [...prev, payload].sort(
                  (a, b) => (a.call_id || 0) - (b.call_id || 0)
                );
                return {
                  ...n,
                  data: {
                    ...n.data,
                    lastSnapshot: {
                      run_id: activeRunId,
                      timestamp: new Date().toISOString(),
                      input: inputSnapshot,
                      output: n.data?.lastSnapshot?.output || {},
                      function_trace: nextTrace,
                      error: n.data?.lastSnapshot?.error || null,
                    },
                  },
                };
              })
            );

            if (activeStepIdRef.current === id) {
              scheduleFnRefresh();
            }
          } catch {
            // ignore malformed events
          }
        };
      } catch {
        evtSource = null;
      }

      applyNodesUpdate((nds) =>
        nds.map((n) =>
          n.id === id ? { ...n, data: { ...n.data, status: "running", error: null } } : n
        )
      );

      try {
        const resp = await runStep(apiBase, {
          session_id: sid,
          run_id: activeRunId,
          step: currentNode.data.step,
          params: currentNode.data.params || {},
          upstream,
        });

        if (!sessionIdRef.current && resp.session_id) {
          setSessionId(resp.session_id);
        }

        applyNodesUpdate((nds) =>
          nds.map((n) =>
            n.id === id
              ? {
                  ...n,
                  data: {
                    ...n.data,
                    status: resp.ok ? "success" : "failed",
                    duration: resp.duration_s,
                    output: resp.output,
                    error: resp.error,
                    lastSnapshot: {
                      run_id: resp.run_id || activeRunId,
                      timestamp: new Date().toISOString(),
                      input: resp.input_snapshot || inputSnapshot,
                      output: resp.output_snapshot || resp.output || {},
                      function_trace: mergeFunctionTrace(
                        n.data?.lastSnapshot?.function_trace || [],
                        resp.function_trace || []
                      ),
                      error: resp.error || null,
                    },
                  },
                }
              : n
          )
        );

        if (activeStepIdRef.current === id) {
          scheduleFnRefresh();
        }

        logLine(
          `${resp.run_id || activeRunId} | ${currentNode.data.step} -> ${
            resp.ok ? "OK" : "FAIL"
          } | funcs=${(resp.function_trace || []).length}`
        );

        if (resp.ok && opts.markDependents) markDownstreamStale(id);
        if (evtSource) evtSource.close();
        return resp;
      } catch (e) {
        applyNodesUpdate((nds) =>
          nds.map((n) =>
            n.id === id
              ? {
                  ...n,
                  data: {
                    ...n.data,
                    status: "failed",
                    error: String(e),
                    lastSnapshot: {
                      run_id: activeRunId,
                      timestamp: new Date().toISOString(),
                      input: inputSnapshot,
                      output: {},
                      function_trace: [],
                      error: String(e),
                    },
                  },
                }
              : n
          )
        );

        if (activeStepIdRef.current === id) scheduleFnRefresh();
        logLine(`${activeRunId} | ${currentNode.data.step} -> ERROR ${e}`);
        if (evtSource) evtSource.close();
        return null;
      }
    },
    [apiBase, applyNodesUpdate, logLine, markDownstreamStale, scheduleFnRefresh]
  );

  const runUpstreamOnly = useCallback(
    async (id) => {
      const upstreamIds = getUpstreamIds(id);
      for (const uid of upstreamIds) {
        const r = await runSingleNode(uid, { markDependents: false });
        if (!r || !r.ok) break;
      }
      applyNodesUpdate((nds) =>
        nds.map((n) =>
          n.id === id && n.data.status !== "running"
            ? { ...n, data: { ...n.data, status: "stale" } }
            : n
        )
      );
    },
    [applyNodesUpdate, getUpstreamIds, runSingleNode]
  );

  const runFromHere = useCallback(
    async (id) => {
      const sequence = [id, ...getDownstreamIds(id)];
      for (const nid of sequence) {
        const r = await runSingleNode(nid, { markDependents: false });
        if (!r || !r.ok) break;
      }
    },
    [getDownstreamIds, runSingleNode]
  );

  const withHandlers = useCallback(
    (node) => ({
      ...node,
      data: {
        ...node.data,
        onChangeParams: (id, text) => {
          const parsed = safeParseJson(text);
          if (!parsed.ok) {
            applyNodesUpdate((nds) =>
              nds.map((n) =>
                n.id === id
                  ? { ...n, data: { ...n.data, error: `Invalid JSON: ${parsed.error}` } }
                  : n
              )
            );
            return;
          }
          applyNodesUpdate((nds) =>
            nds.map((n) =>
              n.id === id
                ? {
                    ...n,
                    data: {
                      ...n.data,
                      params: parsed.value,
                      status: "stale",
                      error: null,
                    },
                  }
                : n
            )
          );
          markDownstreamStale(id);
        },
        onRun: (id) => runSingleNode(id, { markDependents: true }),
        onRunUpstream: (id) => runUpstreamOnly(id),
        onRunFromHere: (id) => runFromHere(id),
      },
    }),
    [applyNodesUpdate, markDownstreamStale, runFromHere, runSingleNode, runUpstreamOnly]
  );

  const onMainConnect = useCallback(
    (params) => applyEdgesUpdate((eds) => addEdge({ ...params, animated: true }, eds)),
    [applyEdgesUpdate]
  );

  const hydratedNodes = useMemo(() => nodes.map((n) => withHandlers(n)), [nodes, withHandlers]);

  const runAllSequential = useCallback(async () => {
    const ordered = [...nodesRef.current].sort((a, b) => a.position.x - b.position.x);
    for (const n of ordered) {
      const r = await runSingleNode(n.id, { markDependents: false });
      if (!r || !r.ok) break;
    }
  }, [runSingleNode]);

  const clearFunctionPanel = useCallback(() => {
    stopRevealTimer();
    lastRenderedStepRef.current = null;
    desiredFnEdgesRef.current = [];
    applyFnNodesUpdate([]);
    applyFnEdgesUpdate([]);
    setFnFlowRevision((v) => v + 1);
    logLine("function panel cleared");
  }, [applyFnEdgesUpdate, applyFnNodesUpdate, logLine, stopRevealTimer]);

  const expandSelectedStepOnly = useCallback(() => {
    const selected = nodesRef.current.find((n) => STEP_NODE_IDS.has(n.id) && n.selected);
    if (!selected) {
      logLine("expand selected skipped: select one step node first");
      return;
    }
    setActiveStepId(selected.id);
    logLine(`function panel switched to ${selected.id}`);
  }, [logLine]);

  const refreshActiveStepPanel = useCallback(() => {
    refreshFunctionPanel();
    logLine(`function panel refreshed: ${activeStepIdRef.current}`);
  }, [logLine, refreshFunctionPanel]);

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="title">PaperQA ReactFlow Prototype</div>
        <div className="controls-row">
          <input
            className="inline-input"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            placeholder="API Base"
          />
          <input
            className="inline-input"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="Session ID"
          />
          <input
            className="inline-input"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            placeholder="Run ID"
          />
          <button onClick={() => setRunId(makeRunId())}>New Run ID</button>
          <button
            onClick={async () => {
              const r = await newSession(apiBase);
              setSessionId(r.session_id);
            }}
          >
            New Session
          </button>
          <button
            onClick={async () => {
              if (!sessionId) return;
              await resetSession(apiBase, sessionId);
              logLine(`reset session ${sessionId}`);
            }}
          >
            Reset Session
          </button>
          <button onClick={runAllSequential}>Run All (Left-to-Right)</button>
          <button onClick={expandSelectedStepOnly}>Expand Selected Step Only</button>
          <button onClick={refreshActiveStepPanel}>Refresh Active Function Panel</button>
          <button onClick={clearFunctionPanel}>Clear Function Panel</button>
        </div>
      </div>

      <div className="canvas-split">
        <div className="canvas-pane">
          <div className="pane-title">Main Pipeline Canvas</div>
          <div className="pane-flow">
            <ReactFlow
              nodes={hydratedNodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onMainConnect}
              onNodeClick={(_, node) => {
                if (STEP_NODE_IDS.has(node.id)) {
                  setActiveStepId(node.id);
                }
              }}
              fitView
            >
              <MiniMap />
              <Controls />
              <Background gap={20} />
            </ReactFlow>
          </div>
        </div>

        <div className="canvas-pane fn-pane">
          <div className="pane-title-row">
            <div className="pane-title">Function Subcanvas (by step)</div>
            <div className="step-switch-row">
              {initialNodesRaw.map((s) => (
                <button
                  key={s.id}
                  className={`step-switch-btn ${activeStepId === s.id ? "active" : ""}`}
                  onClick={() => setActiveStepId(s.id)}
                >
                  {s.data.title}
                </button>
              ))}
            </div>
          </div>
          <div className="pane-flow" style={{ minHeight: `${Math.min(760, fnCanvasMeta.height + 80)}px` }}>
            <ReactFlow
              key={`fn-${activeStepId}-${fnFlowRevision}`}
              nodes={fnNodes}
              edges={fnEdges}
              nodeTypes={nodeTypes}
              onNodesChange={onFnNodesChange}
              onEdgesChange={onFnEdgesChange}
              fitView
            >
              <Controls />
              <Background gap={16} />
            </ReactFlow>
          </div>
        </div>
      </div>

      <div className="log-panel">
        <div className="log-title">Execution Log</div>
        <pre>{globalLog.join("\n")}</pre>
      </div>
    </div>
  );
}
