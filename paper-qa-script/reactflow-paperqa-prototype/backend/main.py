"""PaperQA ReactFlow Prototype API —— 路由层（Sprint-2 US-2.2 解耦后）。

分层职责（refactor-analysis.MD §3）：
- 本文件只保留：FastAPI app、CORS、SSE 传输（RunEventBroker）、会话组合根（MemorySessionStore）。
- 六步流水线编排 → `app.orchestration.PipelineOrchestrator`；
- paperqa 引擎调用 → `app.engine.EngineAdapter`；
- 事件模型 → `app.events`；配置 SSOT → `app.config_schema`。
- 10 条 API 路由（Sprint-4 新增 /api/providers；Sprint-11 新增 /api/config_schema、/api/config/validate）与线上协议（run_step 请求/响应、SSE 消息字段）与拆分前完全一致。
"""
import sys
import uuid
import json
import asyncio
from pathlib import Path
from typing import Any

from aviary.core import Message
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from paperqa import Settings

_SCRIPT_DIR = Path(__file__).resolve().parent
_ROOT_SCRIPT_DIR = _SCRIPT_DIR.parent.parent
if str(_ROOT_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_SCRIPT_DIR))

from app.engine import ENGINE  # noqa: E402
from app.orchestration import StepRequest, StepResponse, make_orchestrator  # noqa: E402
from app.session_store import MemorySessionStore, SessionState  # noqa: E402
from app.config_schema import get_config_schema, validate_config  # noqa: E402
from provider_config import list_providers_safe  # noqa: E402


class RunEventBroker:
    """SSE 传输层：内存 pub/sub + 事件历史（订阅者先拿历史再收实时）。"""

    _MAX_HISTORY = 500  # 每个 (session_id, run_id) 的历史上限（review m8：防无界增长）
    _MAX_KEYS = 200     # review 修正（Sprint-7）：历史键总数上限（旧会话/旧 run 不再有人订阅时淘汰）

    def __init__(self) -> None:
        self._history: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self._subscribers: dict[tuple[str, str], set[asyncio.Queue]] = {}

    def publish(self, key: tuple[str, str], event: dict[str, Any]) -> None:
        if key not in self._history and len(self._history) >= self._MAX_KEYS:
            self._history.pop(next(iter(self._history)), None)
        history = self._history.setdefault(key, [])
        history.append(event)
        del history[: max(0, len(history) - self._MAX_HISTORY)]
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


# 组合根：会话存储（US-2.4）、事件传输、编排器（US-2.2）
SESSIONS = MemorySessionStore()
RUN_EVENT_BROKER = RunEventBroker()
ORCHESTRATOR = make_orchestrator(store=SESSIONS)


class TranslatePreviewRequest(BaseModel):
    session_id: str
    text: str


app = FastAPI(title="PaperQA ReactFlow Prototype API")

app.add_middleware(
    CORSMiddleware,
    # 安全加固：只允许本地前端来源跨域访问，避免公网任意页面调用本地后端
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_session(session_id: str | None) -> SessionState:
    return SESSIONS.get_or_create(session_id)


def build_settings(params: dict[str, Any]) -> Settings:
    # US-2.5：经 EngineAdapter 透传（LocalVendorAdapter 实现与原先完全一致，行为不变）
    return ENGINE.make_settings(params)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/providers")
async def providers() -> dict[str, Any]:
    # Sprint-4 US-4.3：provider 注册表（内置 + 自定义），供前端下拉；绝不包含密钥
    return {"providers": list_providers_safe()}


@app.get("/api/config_schema")
async def config_schema() -> dict[str, Any]:
    # Sprint-11 US-11.1（F2 阶段 A）：配置唯一真源（app.config_schema）的对外形态——前端由它驱动表单
    return get_config_schema()


class ConfigValidateRequest(BaseModel):
    params: dict[str, Any]


@app.post("/api/config/validate")
async def config_validate(req: ConfigValidateRequest) -> dict[str, list[str]]:
    # Sprint-11 US-11.1：提示性校验（errors/warnings/hints，不改变 build_settings 行为）
    return validate_config(req.params or {})


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
    SESSIONS.reset(sid)
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
async def stream_run_events(request: Request, session_id: str, run_id: str) -> StreamingResponse:
    key = (session_id, run_id)
    q, history = RUN_EVENT_BROKER.subscribe(key)

    async def gen():
        try:
            for evt in history:
                # US-5.5：客户端断连后停止发送（避免 socket.send() raised exception 噪音）
                if await request.is_disconnected():
                    return
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                    if await request.is_disconnected():
                        return
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        return
                    yield ": keepalive\n\n"
        finally:
            RUN_EVENT_BROKER.unsubscribe(key, q)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/run_step", response_model=StepResponse)
async def run_step(req: StepRequest) -> StepResponse:
    # 路由层职责：解析 run_id、绑定 SSE 事件通道；六步逻辑在编排层
    session = get_or_create_session(req.session_id)
    run_id = req.run_id or f"run-{uuid.uuid4().hex[:10]}"
    event_key = (session.session_id, run_id)
    req_ready = req.model_copy(update={"session_id": session.session_id, "run_id": run_id})
    return await ORCHESTRATOR.run_step(
        req_ready,
        on_event=lambda evt: RUN_EVENT_BROKER.publish(event_key, evt),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8787)
