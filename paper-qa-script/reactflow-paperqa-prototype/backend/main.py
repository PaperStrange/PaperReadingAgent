import os
import sys
import time
import uuid
import json
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aviary.core import Message
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from paperqa import Docs, Settings
from paperqa.agents.search import get_directory_index
from paperqa.settings import AgentSettings, IndexSettings, ParsingSettings

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_SCRIPT_DIR = _SCRIPT_DIR.parent.parent
if str(_ROOT_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_SCRIPT_DIR))

try:
    from runtime_trace import RuntimeTracer
except Exception:
    class RuntimeTracer:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.events: list[dict[str, Any]] = []

        def __enter__(self) -> "RuntimeTracer":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None


@dataclass
class SessionState:
    session_id: str
    settings: Settings | None = None
    search_index: Any | None = None
    candidate_paths: list[str] = field(default_factory=list)
    docs: Docs | None = None
    evidence_session: Any | None = None
    answer_session: Any | None = None
    run_records: list[dict[str, Any]] = field(default_factory=list)


SESSIONS: dict[str, SessionState] = {}


class RunEventBroker:
    def __init__(self) -> None:
        self._history: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._subscribers: dict[tuple[str, str], set[asyncio.Queue]] = {}

    def publish(self, key: tuple[str, str], event: dict[str, Any]) -> None:
        self._history.setdefault(key, []).append(event)
        for q in list(self._subscribers.get(key, set())):
            try:
                q.put_nowait(event)
            except Exception:
                pass

    def subscribe(self, key: tuple[str, str]) -> tuple[asyncio.Queue, list[dict[str, Any]]]:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(key, set()).add(q)
        return q, list(self._history.get(key, []))

    def unsubscribe(self, key: tuple[str, str], q: asyncio.Queue) -> None:
        if key not in self._subscribers:
            return
        self._subscribers[key].discard(q)
        if not self._subscribers[key]:
            self._subscribers.pop(key, None)


RUN_EVENT_BROKER = RunEventBroker()


class StepRequest(BaseModel):
    session_id: str | None = None
    run_id: str | None = None
    step: str
    params: dict[str, Any] = Field(default_factory=dict)
    upstream: dict[str, Any] = Field(default_factory=dict)


class StepResponse(BaseModel):
    session_id: str
    run_id: str
    step: str
    ok: bool
    duration_s: float
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    function_trace: list[dict[str, Any]] = Field(default_factory=list)


class TranslatePreviewRequest(BaseModel):
    session_id: str
    text: str


app = FastAPI(title="PaperQA ReactFlow Prototype API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_session(session_id: str | None) -> SessionState:
    sid = session_id or str(uuid.uuid4())
    if sid not in SESSIONS:
        SESSIONS[sid] = SessionState(session_id=sid)
    return SESSIONS[sid]


def build_settings(params: dict[str, Any]) -> Settings:
    api_key = params.get("api_key") or os.getenv("OPENAI_API_KEY", "")
    api_base = params.get("api_base", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = params.get("model", "openai/qwen-omni-turbo")
    embedding_model = params.get("embedding_model", "openai/text-embedding-v4")
    temperature = float(params.get("temperature", 0.1))
    paper_dir = str(Path(params.get("paper_directory", "./data/pdf")).expanduser())
    index_name = params.get("index_name", "debug_index")
    embedding_batch_size = int(params.get("embedding_batch_size", 10))
    chunk_chars = int(params.get("chunk_chars", 5000))
    chunk_overlap = int(params.get("chunk_overlap", 250))

    if not api_key:
        raise ValueError("api_key is required")

    os.environ["OPENAI_API_KEY"] = api_key

    llm_config = {
        "name": model,
        "model_list": [
            {
                "model_name": model,
                "litellm_params": {
                    "model": model,
                    "temperature": temperature,
                    "api_base": api_base,
                    "api_key": api_key,
                },
            }
        ],
    }
    embedding_config = {
        "name": embedding_model,
        "model_list": [
            {
                "model_name": embedding_model,
                "litellm_params": {
                    "model": embedding_model,
                    "api_base": api_base,
                    "api_key": api_key,
                },
            }
        ],
        "batch_size": embedding_batch_size,
    }

    return Settings(
        llm=model,
        llm_config=llm_config,
        summary_llm=model,
        summary_llm_config=llm_config,
        embedding=embedding_model,
        embedding_config=embedding_config,
        parsing=ParsingSettings(
            use_doc_details=bool(params.get("use_doc_details", False)),
            reader_config={
                "chunk_chars": max(200, chunk_chars),
                "overlap": max(0, chunk_overlap),
            },
            enrichment_llm=model,
            enrichment_llm_config=llm_config,
        ),
        agent=AgentSettings(
            rebuild_index=False,
            index=IndexSettings(
                paper_directory=str(Path(paper_dir).resolve()),
                files_filter=lambda f: f.suffix in {".pdf", ".txt", ".md", ".html"},
                name=index_name,
            ),
        ),
    )

def _safe_text_preview(text: str, max_len: int = 220) -> str:
    raw = (text or "").replace("\n", " ").strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 14] + "...[truncated]"


def _paperqa_trace(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if str(e.get("func", "")).startswith("paperqa.")]


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/translate_preview")
async def translate_preview(req: TranslatePreviewRequest) -> dict[str, str]:
    session = SESSIONS.get(req.session_id)
    if session is None or session.settings is None:
        raise HTTPException(status_code=400, detail="session/settings not ready")
    text = (req.text or "").strip()
    if not text:
        return {"text_zh": ""}
    model = session.settings.get_llm()
    prompt = (
        "Translate the following scientific text into concise Chinese.\n"
        "Keep proper nouns, formulas, and citations unchanged where appropriate.\n"
        "Return translation only.\n\n"
        f"Text:\n{text}"
    )
    try:
        result = await model.call_single(messages=[Message(content=prompt)])
        return {"text_zh": str(result.text or "")}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"translate failed: {exc}") from exc


@app.post("/api/new_session")
async def new_session() -> dict[str, str]:
    s = get_or_create_session(None)
    return {"session_id": s.session_id}


@app.post("/api/reset_session")
async def reset_session(payload: dict[str, str]) -> dict[str, str]:
    sid = payload.get("session_id")
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    SESSIONS[sid] = SessionState(session_id=sid)
    return {"session_id": sid, "status": "reset"}


@app.get("/api/session_records/{session_id}")
async def session_records(session_id: str) -> dict[str, Any]:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "session_id": session_id,
        "count": len(session.run_records),
        "records": session.run_records,
    }


@app.get("/api/stream/{session_id}/{run_id}")
async def stream_run_events(session_id: str, run_id: str) -> StreamingResponse:
    key = (session_id, run_id)
    q, history = RUN_EVENT_BROKER.subscribe(key)

    async def gen():
        try:
            for evt in history:
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            RUN_EVENT_BROKER.unsubscribe(key, q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/run_step", response_model=StepResponse)
async def run_step(req: StepRequest) -> StepResponse:
    session = get_or_create_session(req.session_id)
    run_id = req.run_id or f"run-{uuid.uuid4().hex[:10]}"
    event_key = (session.session_id, run_id)
    step = req.step
    t0 = time.perf_counter()
    input_snapshot = {
        "step": step,
        "params": req.params,
        "upstream": req.upstream,
    }

    def on_trace_event(evt: dict[str, Any]) -> None:
        func_name = str(evt.get("func", ""))
        if not func_name.startswith("paperqa."):
            return
        RUN_EVENT_BROKER.publish(
            event_key,
            {
                "kind": "function_trace",
                "session_id": session.session_id,
                "run_id": run_id,
                "step": step,
                **evt,
            },
        )

    tracer = RuntimeTracer(on_event=on_trace_event)
    try:
        with tracer:
            if step == "config":
                session.settings = build_settings(req.params)
                output = {
                    "paper_directory": session.settings.agent.index.paper_directory,
                    "index_name": session.settings.agent.index.name,
                    "llm": session.settings.llm,
                    "embedding": session.settings.embedding,
                }

            elif step == "load_index":
                if session.settings is None:
                    raise ValueError("Run config step first")
                build = bool(req.params.get("build", True))
                session.search_index = await get_directory_index(settings=session.settings, build=build)
                index_files = await session.search_index.index_files
                output = {
                    "index_name": session.search_index.index_name,
                    "indexed_files": len(index_files),
                    "files": list(index_files.keys()),
                }

            elif step == "retrieve":
                if session.search_index is None:
                    raise ValueError("Run load_index step first")
                query = req.params.get("query")
                if not query:
                    query = req.upstream.get("question") or "PaperQA"
                top_n = int(req.params.get("top_n", 5))
                results = await session.search_index.query(query, top_n=top_n, keep_filenames=True)
                paths = [r[1] for r in results if isinstance(r, tuple) and len(r) == 2]
                if not paths:
                    paths = list((await session.search_index.index_files).keys())[:top_n]
                session.candidate_paths = paths
                output = {
                    "query": query,
                    "candidate_count": len(paths),
                    "candidate_paths": paths,
                }

            elif step == "parse_chunk_embed":
                if session.settings is None:
                    raise ValueError("Run config step first")
                if session.search_index is None:
                    raise ValueError("Run load_index step first")
                docs = Docs()
                paper_dir = Path(session.settings.agent.index.paper_directory)
                paths = req.params.get("candidate_paths") or session.candidate_paths
                if not paths:
                    paths = list((await session.search_index.index_files).keys())[:5]
                per_file = []
                for p in paths:
                    before = len(docs.texts)
                    p0 = time.perf_counter()
                    abs_path = str((paper_dir / p).resolve()) if not Path(p).is_absolute() else p
                    docname = await docs.aadd(path=abs_path, settings=session.settings)
                    per_file.append(
                        {
                            "file": p,
                            "docname": docname,
                            "added_chunks": len(docs.texts) - before,
                            "duration_s": round(time.perf_counter() - p0, 3),
                        }
                    )
                session.docs = docs
                sample_texts: list[dict[str, Any]] = []
                for t in list(docs.texts)[:8]:
                    sample_texts.append(
                        {
                            "name": getattr(t, "name", ""),
                            "docname": getattr(getattr(t, "doc", None), "docname", ""),
                            "text_preview": _safe_text_preview(getattr(t, "text", "")),
                        }
                    )
                output = {
                    "docs_count": len(docs.docs),
                    "texts_count": len(docs.texts),
                    "per_file": per_file,
                    "sample_texts": sample_texts,
                }

            elif step == "evidence":
                if session.docs is None:
                    raise ValueError("Run parse_chunk_embed step first")
                if session.settings is None:
                    raise ValueError("Run config step first")
                question = req.params.get("question")
                if not question:
                    question = req.upstream.get("question") or "什么是PaperQA？"
                session.evidence_session = await session.docs.aget_evidence(question, settings=session.settings)
                output = {
                    "question": question,
                    "contexts_count": len(session.evidence_session.contexts or []),
                    "context_ids": [c.id for c in (session.evidence_session.contexts or [])],
                }

            elif step == "answer":
                if session.docs is None:
                    raise ValueError("Run parse_chunk_embed step first")
                if session.settings is None:
                    raise ValueError("Run config step first")
                if session.evidence_session is None:
                    raise ValueError("Run evidence step first")
                session.answer_session = await session.docs.aquery(session.evidence_session, settings=session.settings)
                ans_obj = session.answer_session
                answer_text = (
                    getattr(ans_obj, "answer", None)
                    or getattr(ans_obj, "formatted_answer", None)
                    or getattr(ans_obj, "raw_answer", None)
                    or ""
                )
                references_text = getattr(ans_obj, "references", "") or ""
                used_contexts = sorted(
                    list(getattr(ans_obj, "used_contexts", None) or [])
                )
                output = {
                    "answer": answer_text,
                    "references": references_text,
                    "used_contexts": used_contexts,
                    "answer_available_fields": [
                        k
                        for k in ("answer", "formatted_answer", "raw_answer", "references", "used_contexts")
                        if hasattr(ans_obj, k)
                    ],
                }

            else:
                raise ValueError(f"Unknown step: {step}")

        ok_resp = StepResponse(
            session_id=session.session_id,
            run_id=run_id,
            step=step,
            ok=True,
            duration_s=round(time.perf_counter() - t0, 3),
            output=output,
            input_snapshot=input_snapshot,
            output_snapshot=output,
            function_trace=_paperqa_trace(tracer.events),
        )
        session.run_records.append(
            {
                "session_id": session.session_id,
                "run_id": run_id,
                "step": step,
                "ok": True,
                "duration_s": ok_resp.duration_s,
                "input_snapshot": input_snapshot,
                "output_snapshot": output,
                "error": None,
                "function_trace": _paperqa_trace(tracer.events),
                "timestamp": time.time(),
            }
        )
        RUN_EVENT_BROKER.publish(
            event_key,
            {
                "kind": "step_done",
                "session_id": session.session_id,
                "run_id": run_id,
                "step": step,
                "ok": True,
                "duration_s": ok_resp.duration_s,
                "function_count": len(ok_resp.function_trace),
            },
        )
        return ok_resp

    except Exception as exc:
        err_resp = StepResponse(
            session_id=session.session_id,
            run_id=run_id,
            step=step,
            ok=False,
            duration_s=round(time.perf_counter() - t0, 3),
            output={},
            error=str(exc),
            input_snapshot=input_snapshot,
            output_snapshot={},
            function_trace=_paperqa_trace(tracer.events),
        )
        session.run_records.append(
            {
                "session_id": session.session_id,
                "run_id": run_id,
                "step": step,
                "ok": False,
                "duration_s": err_resp.duration_s,
                "input_snapshot": input_snapshot,
                "output_snapshot": {},
                "error": str(exc),
                "function_trace": _paperqa_trace(tracer.events),
                "timestamp": time.time(),
            }
        )
        RUN_EVENT_BROKER.publish(
            event_key,
            {
                "kind": "step_done",
                "session_id": session.session_id,
                "run_id": run_id,
                "step": step,
                "ok": False,
                "error": str(exc),
                "duration_s": err_resp.duration_s,
                "function_count": len(err_resp.function_trace),
            },
        )
        return err_resp

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8787)
