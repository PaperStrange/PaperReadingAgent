"""编排层（Sprint-2 US-2.2）：六步流水线执行器。

分层（refactor-analysis.MD §3）：
- 本层只做**步骤编排**：拿到 StepRequest -> 逐步执行 config/load_index/retrieve/parse_chunk_embed/evidence/answer
  -> 返回 StepResponse；所有 paperqa 调用经 `EngineAdapter`（US-2.5），会话状态经 `SessionStore`（US-2.4）。
- 本层不 import FastAPI / 不碰 SSE 传输：实时事件通过 `on_event(dict)` 回调交给 API 层发布
  （US-2.3 的 SSE 接线：事件用 `app.events` 模型构造，字段与线上协议完全兼容）。
- 行为不变：六步的输入/输出/错误文案/事件字段与拆分前完全一致。
"""
from __future__ import annotations

import gzip
import json
import hashlib
import os
import re
import shutil
import time
import traceback
import uuid
import zlib
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.config_schema import validate_config
from app.data_sources import parse_remote_sources, validate_source_specs
from app.embedding_recommender import RECOMMENDER
from app.engine import ENGINE, EngineAdapter, prune_litellm_callbacks
from app.events import FunctionTraceEvent, StepEvent
from app.remote_resolver import resolve_remote_sources
from app.session_store import SessionState, SessionStore

try:
    from runtime_trace import RuntimeTracer
except Exception:
    class RuntimeTracer:  # type: ignore[no-redef]
        def __init__(self, on_event: Callable[[dict[str, Any]], None] | None = None) -> None:
            self.events: list[dict[str, Any]] = []

        def __enter__(self) -> "RuntimeTracer":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None


class StepRequest(BaseModel):
    """步骤请求（API 协议模型，编排层唯一入口）。"""

    session_id: str | None = None
    run_id: str | None = None
    step: str
    params: dict[str, Any] = Field(default_factory=dict)
    upstream: dict[str, Any] = Field(default_factory=dict)


class StepResponse(BaseModel):
    """步骤响应（API 协议模型）。"""

    session_id: str
    run_id: str
    step: str
    ok: bool
    duration_s: float
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    error_detail: str | None = None  # F-AC6：完整 traceback（主画布"摘要+可展开堆栈"）
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    output_snapshot: dict[str, Any] = Field(default_factory=dict)
    function_trace: list[dict[str, Any]] = Field(default_factory=list)


def _safe_text_preview(text: str, max_len: int = 220) -> str:
    raw = (text or "").replace("\n", " ").strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 14] + "...[truncated]"


def _paperqa_trace(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if str(e.get("func", "")).startswith("paperqa.")]


# code review M3：快照/记录中的敏感字段脱敏，避免 api_key 明文进入
# StepResponse.input_snapshot / run_records / session_records API
_SECRET_KEYS = {"api_key", "apikey", "password", "token", "secret", "authorization"}


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("***" if str(k).lower() in _SECRET_KEYS else _redact_secrets(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_secrets(v) for v in value]
    return value


# ---- parse_chunk_embed 的 Embedding 缓存（用于"载入最近一次 Embedding"） ----

def _embed_cache_dir() -> Path:
    d = Path.home() / ".pqa" / "embed_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# review 修正（Sprint-7）：embed 缓存 TTL（过期视为未命中，仍会被后续写入覆盖）
_EMBED_CACHE_TTL_S = 30 * 24 * 3600

# review 修正（Sprint-7）：run_records 上限（会话内存态防无界增长）
_MAX_RUN_RECORDS = 200


def _index_dir(settings: Any) -> Path:
    return Path(settings.agent.index.index_directory) / (settings.agent.index.name or "")


def _index_corrupt(settings: Any) -> bool:
    """索引完整性探针（US-4.2 + Sprint-5 关闭修正 + Sprint-7 M1 升级）：三重探测。

    1. files.zip：zlib 压缩对象存储（解压失败=损坏）；
    2. index/meta.json：Tantivy 段目录标记（缺失/不可解析=半成品状态）；
    3. tantivy Index.open + searcher()：真段损坏在此抛出（只读、懒加载，代价小）。

    仅做**只读校验**，删除动作由调用方（整目录重建）完成；
    避免"只删 files.zip"后 Tantivy 段与 docs/ 存储残留旧引用导致 query 崩溃。
    """
    index_dir = _index_dir(settings)
    zipf = index_dir / "files.zip"
    if zipf.exists():
        try:
            zlib.decompress(zipf.read_bytes())
        except zlib.error:
            return True
    # M1：Tantivy 段探测（meta.json 缺失即半成品；打开/建 searcher 失败即真段损坏）
    meta = index_dir / "index" / "meta.json"
    if not meta.exists():
        return True
    try:
        json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    try:
        from tantivy import Index

        Index.open(path=str(meta.parent)).searcher()  # 段读取器加载，真损坏在此抛出
    except Exception:
        return True
    return False


def _paper_dir_fingerprint(settings: Any) -> str:
    return hashlib.sha1(
        str(settings.agent.index.paper_directory).encode("utf-8")
    ).hexdigest()


def _write_index_marker(settings: Any) -> None:
    """记录本次构建所用的 paper_directory 指纹：目录切换时据此整目录重建。"""
    try:
        index_dir = _index_dir(settings)
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "paper_dir_marker.txt").write_text(
            _paper_dir_fingerprint(settings), encoding="utf-8"
        )
    except Exception:
        pass


def _embed_cache_path(paper_dir: str, index_name: str, paths: list[str]) -> Path:
    key = hashlib.sha1("|".join([paper_dir, index_name, *paths]).encode("utf-8")).hexdigest()[:16]
    return _embed_cache_dir() / f"{key}.json"


def _read_embed_cache(p: Path) -> dict[str, Any] | None:
    """读缓存（review 修正 Sprint-7：过期 TTL 30 天，防 ~/.pqa/embed_cache 无界增长）。"""
    try:
        if p.exists():
            if time.time() - p.stat().st_mtime > _EMBED_CACHE_TTL_S:
                return None
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _write_embed_cache(p: Path, data: dict[str, Any]) -> None:
    try:
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ---------- F-AC10：文献级 embedding checkpoint（每篇完成即落盘，失败只补缺口） ----------
# 设计依据（Sprint-16 调研 run-2026-09-12-tech-research-047）：
# - 逐篇原子落盘 + 内容指纹/模型校验 + 只复用通过校验的条目 + 就绪判定 fail-closed；
# - 复用走 paperqa `aadd_texts`（texts 已带向量 → 不再调用嵌入模型，零嵌入成本）。

_EMBED_CHECKPOINT_SCHEMA = 1
# checkpoint 无 TTL（重建代价高，不能像 embed 缓存那样过期），改为**按命名空间数量收敛**防无界增长
_CHECKPOINT_NAMESPACE_KEEP = 20


def _prune_checkpoints(
    root: Path, keep: int = _CHECKPOINT_NAMESPACE_KEEP, protect: str = "", grace_s: float = 86400.0
) -> list[str]:
    """按 mtime 保留最近 keep 个命名空间（manifest + 载荷目录），删除更旧的。

    - `protect`：本轮在用的 key，永不删；
    - `grace_s`：宽限期——只清理 **updated_at 早于 now-grace_s** 的命名空间，
      避免并发运行（另一命名空间正在写入）时被误删而丢掉已花的嵌入成本（code-review 050 minor）。
    """
    try:
        manifests = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []
    cutoff = time.time() - grace_s
    removed: list[str] = []
    for m in manifests[keep:]:
        key = m.stem
        if key == protect:
            continue
        try:
            if m.stat().st_mtime > cutoff:
                continue  # 宽限期内（可能正在被另一轮使用）
            m.unlink()
            payload_dir = root / key
            if payload_dir.is_dir():
                shutil.rmtree(payload_dir, ignore_errors=True)
            removed.append(key)
        except OSError:
            continue
    return removed


def _embed_checkpoint_root() -> Path:
    d = _embed_cache_dir() / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _embed_checkpoint_key(paper_dir: str, index_name: str, embedding_model: str) -> str:
    """checkpoint 命名空间 = (论文目录, 索引名, 嵌入模型)——任一变化即整体失效（fail-closed，不静默复用）。"""
    return hashlib.sha1(
        "|".join([paper_dir, index_name, embedding_model or ""]).encode("utf-8")
    ).hexdigest()[:16]


def _atomic_write_json(p: Path, data: dict[str, Any], *, gz: bool = False) -> None:
    """原子写（tmp + os.replace）：中断/崩溃不会留下半截 checkpoint。"""
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    if gz:
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
    else:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def _file_fingerprint(path: str) -> str:
    """内容指纹（弱口径）：size + mtime_ns——调研标注为弱证据，误判再升级全文 sha256。"""
    try:
        st = os.stat(path)
        return f"{st.st_size}:{st.st_mtime_ns}"
    except OSError:
        return "missing"


def _read_checkpoint_json(p: Path, *, gz: bool = False) -> dict[str, Any] | None:
    try:
        if not p.exists():
            return None
        if gz:
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                return json.load(fh)
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None  # 坏件视为未命中（fail-closed 到"重跑该篇"，而不是沿用不可信数据）


class PipelineOrchestrator:
    """六步流水线编排器：DI 注入 engine 与 store（路由层组装）。"""

    def __init__(self, engine: EngineAdapter, store: SessionStore) -> None:
        self._engine = engine
        self._store = store

    # ---------- F-AC10：文献级 embedding checkpoint ----------

    @staticmethod
    def _checkpoint_manifest(
        paper_dir: Path,
        settings: Any,
        model: str,
        entries: dict[str, Any],
        status: str,
        checkpoint_key: str = "",
    ) -> dict[str, Any]:
        reader_cfg = getattr(getattr(settings, "parsing", None), "reader_config", None) or {}
        return {
            "schema": _EMBED_CHECKPOINT_SCHEMA,
            "checkpoint_key": checkpoint_key,  # 契约字段（code-review 050 major：manifest 自述 key，测试/巡检不再靠猜测）
            "paper_dir": str(paper_dir),
            "index_name": str(getattr(getattr(settings, "agent", None).index, "name", "") or ""),
            "embedding_model": model,
            # 切块口径（code-review 050 minor）：变更即判为不可复用，防"旧分块静默沿用"
            "chunk_chars": reader_cfg.get("chunk_chars"),
            "chunk_overlap": reader_cfg.get("overlap"),
            "parse_schema": _EMBED_CHECKPOINT_SCHEMA,
            "status": status,  # ready=本轮全部就绪；partial=有失败/未完成（fail-closed）
            "updated_at": time.time(),
            "docs": entries,
        }

    async def _add_docs_with_checkpoint(
        self,
        docs: Any,
        paths: list[str],
        paper_dir: Path,
        session: SessionState,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """逐篇 `add_doc` + 文献级 checkpoint：每篇完成即原子落盘；命中校验直接复用（零嵌入成本）。

        - 命名空间 = (论文目录, 索引名, 嵌入模型)：任一变化 → 整份 checkpoint 失效（不静默复用旧向量）；
        - 命中条件 = status=ready + 内容指纹一致 + 载荷可读 + 还原成功；任一不满足 → 该篇重跑；
        - 单篇失败：写入 status=error 后抛出（保持既有错误文案与"中止整步"语义）；
        - 全部走完无异常才把 manifest 置 ready。
        """
        settings = session.settings
        model = str(getattr(settings, "embedding", "") or "")
        index_name = str(getattr(getattr(settings, "agent", None).index, "name", "") or "")
        ckpt_key = _embed_checkpoint_key(str(paper_dir), index_name, model)
        root = _embed_checkpoint_root()
        manifest_path = root / f"{ckpt_key}.json"
        payload_dir = root / ckpt_key
        _prune_checkpoints(root, protect=ckpt_key)  # 防无界增长（保留最近 N 个命名空间，绝不删本轮用的）

        manifest = _read_checkpoint_json(manifest_path) or {}
        _reader_cfg = getattr(getattr(settings, "parsing", None), "reader_config", None) or {}
        _cur_chunk = _reader_cfg.get("chunk_chars")
        _cur_overlap = _reader_cfg.get("overlap")
        # 复用前提（fail-closed）：schema + 嵌入模型 + **切块口径** 全部一致（code-review 050 minor：
        # 否则改了 chunk_chars/overlap 仍会静默沿用旧分块向量）
        model_match = (
            manifest.get("schema") == _EMBED_CHECKPOINT_SCHEMA
            and manifest.get("embedding_model") == model
            and manifest.get("chunk_chars") == _cur_chunk
            and manifest.get("chunk_overlap") == _cur_overlap
        )
        entries: dict[str, Any] = dict(manifest.get("docs") or {}) if model_match else {}
        stats: dict[str, Any] = {
            "reused": 0,
            "embedded": 0,
            "deduped": 0,
            "failed": 0,
            "model_match": bool(model_match),
            "chunk_chars": _cur_chunk,
            "chunk_overlap": _cur_overlap,
            "checkpoint_key": ckpt_key,
            "manifest": str(manifest_path),
        }
        per_file: list[dict[str, Any]] = []

        for p in paths:
            # paper_dir 已是绝对路径（Windows 含 \\?\ 长路径前缀），直接拼接避免 re-resolve 丢失前缀
            abs_path = p if Path(p).is_absolute() else str(paper_dir / p)
            fingerprint = _file_fingerprint(abs_path)
            entry = entries.get(p) or {}
            reused = False
            reuse_reason = ""

            if entry.get("status") == "ready" and entry.get("fingerprint") == fingerprint:
                payload = _read_checkpoint_json(
                    payload_dir / f"{entry.get('dockey', '')}.json.gz", gz=True
                )
                if not payload or not payload.get("doc"):
                    reuse_reason = "payload_missing_or_corrupt"
                else:
                    p0 = time.perf_counter()
                    try:
                        ok_restore, n_texts = await self._engine.restore_doc(docs, payload, settings)
                    except Exception as exc:  # noqa: BLE001 —— 还原失败即回落重跑（不沿用不可信数据）
                        ok_restore, n_texts = False, 0
                        reuse_reason = f"restore_error:{type(exc).__name__}:{exc}"
                    if ok_restore:
                        reused = True
                        stats["reused"] += 1
                        per_file.append(
                            {
                                "file": p,
                                "docname": str(payload["doc"].get("docname") or entry.get("docname") or ""),
                                "added_chunks": n_texts,
                                "duration_s": round(time.perf_counter() - p0, 3),
                                "reused": True,
                                "deduped": False,
                            }
                        )
                    elif not reuse_reason:
                        reuse_reason = "restore_returned_false"
            elif entry:
                reuse_reason = f"stale:{entry.get('status')}:" + (
                    "fingerprint_changed" if entry.get("fingerprint") != fingerprint else "status_not_ready"
                )
            else:
                reuse_reason = "no_entry"
            if not reused:
                stats.setdefault("reuse_misses", {})[p] = reuse_reason
            if reused:
                continue

            before = len(docs.texts)
            p0 = time.perf_counter()
            try:
                docname = await self._engine.add_doc(docs, abs_path, settings)
            except Exception as exc:  # noqa: BLE001
                stats["failed"] += 1
                entries[p] = {
                    **entry,
                    "fingerprint": fingerprint,
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "updated_at": time.time(),
                }
                _atomic_write_json(
                    manifest_path,
                    self._checkpoint_manifest(paper_dir, settings, model, entries, "partial", ckpt_key),
                )
                # US-5.1：单文件失败给出上下文；文件缺失多半是索引与目录不一致
                raise ValueError(
                    f"解析文件失败：{p}（{str(exc) or repr(exc)}）。"
                    "若为文件不存在：请核对 Config 节点的论文目录，"
                    "并重新运行 Config → load_index 使索引与目录一致"
                ) from exc

            payload = self._engine.export_doc(docs, docname or "") or {}
            if not payload:
                # 内容去重：paperqa 以文件 content_hash 作 dockey，同内容文件的第二次添加是 no-op
                # （本轮已由另一篇同内容文档覆盖）→ 记 deduped（非错误、非 ready：无独立载荷可复用）
                stats["deduped"] += 1
                entries[p] = {
                    "fingerprint": fingerprint,
                    "dockey": "",
                    "docname": docname or "",
                    "texts_count": 0,
                    "status": "deduped",
                    "embedded_at": time.time(),
                    "error": "",
                }
                _atomic_write_json(
                    manifest_path,
                    self._checkpoint_manifest(paper_dir, settings, model, entries, "partial", ckpt_key),
                )
                per_file.append(
                    {
                        "file": p,
                        "docname": docname or "",
                        "added_chunks": 0,
                        "duration_s": round(time.perf_counter() - p0, 3),
                        "reused": False,
                        "deduped": True,
                    }
                )
                continue

            stats["embedded"] += 1
            dockey = str((payload.get("doc") or {}).get("dockey") or docname)
            _atomic_write_json(payload_dir / f"{dockey}.json.gz", payload, gz=True)
            # 清理该篇的旧版本载荷（指纹变化 → 新 dockey）：防载荷目录按历史内容版本无界增长
            old_dockey = str(entry.get("dockey") or "")
            if old_dockey and old_dockey != dockey:
                try:
                    (payload_dir / f"{old_dockey}.json.gz").unlink(missing_ok=True)
                except OSError:
                    pass
            entries[p] = {
                "fingerprint": fingerprint,
                "dockey": dockey,
                "docname": docname or "",
                "texts_count": len(docs.texts) - before,
                "status": "ready",
                "embedded_at": time.time(),
                "error": "",
            }
            _atomic_write_json(
                manifest_path,
                self._checkpoint_manifest(paper_dir, settings, model, entries, "partial"),
            )
            per_file.append(
                {
                    "file": p,
                    "docname": docname or "",
                    "added_chunks": len(docs.texts) - before,
                    "duration_s": round(time.perf_counter() - p0, 3),
                    "reused": False,
                    "deduped": False,
                }
            )

        _atomic_write_json(
            manifest_path,
            self._checkpoint_manifest(paper_dir, settings, model, entries, "ready", ckpt_key),
        )
        return per_file, stats

    async def run_step(
        self,
        req: StepRequest,
        *,
        on_event: Callable[[dict[str, Any]], None],
    ) -> StepResponse:
        """执行一个步骤，返回 StepResponse；过程事件经 on_event 发布（SSE 接线由 API 层完成）。"""
        prune_litellm_callbacks()  # US-5.4（引擎层生命周期维护，见 app/engine.py）
        session: SessionState = self._store.get_or_create(req.session_id)
        run_id = req.run_id or f"run-{uuid.uuid4().hex[:10]}"
        step = req.step
        t0 = time.perf_counter()
        input_snapshot = _redact_secrets(
            {
                "step": step,
                "params": req.params,
                "upstream": req.upstream,
            }
        )

        def on_trace_event(evt: dict[str, Any]) -> None:
            func_name = str(evt.get("func", ""))
            if not func_name.startswith("paperqa."):
                return
            # US-2.3 接线：函数追踪经事件模型序列化（字段与线上协议一致）
            on_event(
                FunctionTraceEvent(
                    kind="function_trace",
                    session_id=session.session_id,
                    run_id=run_id,
                    step=step,
                    **evt,
                ).model_dump(exclude={"ts", "trace_id"})
            )

        tracer = RuntimeTracer(on_event=on_trace_event)
        try:
            with tracer:
                if step == "config":
                    # embedding 智能默认（未显式指定时按 provider 自动选择；均可手动覆盖）
                    settings_params = dict(req.params)
                    embedding_rec = None
                    if not settings_params.get("embedding_model"):
                        embedding_rec = await RECOMMENDER.recommend(
                            settings_params.get("provider")
                        )
                        settings_params["embedding_model"] = embedding_rec.model

                    session.settings = self._engine.make_settings(settings_params)
                    # 二查修正（Sprint-5 关闭）：配置重跑 = 下游状态全部失效，
                    # 避免"改目录后 load_index 绿成功但用旧索引/旧 docs"的陈旧误导
                    session.search_index = None
                    session.candidate_paths = []
                    session.docs = None
                    session.evidence_session = None
                    session.answer_session = None
                    # US-3.3：数据源参数存入会话（load_index 步骤读取；Run All 时各节点参数独立）
                    session.data_source_params = {
                        k: req.params.get(k)
                        for k in ("data_source", "source_urls", "source_arxiv_ids", "source_dois")
                    }
                    config_notes = validate_config(settings_params)
                    if embedding_rec is not None:
                        config_notes["hints"].insert(
                            0, f"[Embedding 自动选择] {embedding_rec.reason}"
                        )
                    output = {
                        "paper_directory": session.settings.agent.index.paper_directory,
                        "index_name": session.settings.agent.index.name,
                        "llm": session.settings.llm,
                        "embedding": session.settings.embedding,
                        # 追加：配置唯一真源校验/提示（US-2.1，只增不减，行为不变）
                        "config_notes": config_notes,
                    }
                    if embedding_rec is not None:
                        # 追加：自动解析结果（含理由），前端可直接展示
                        output["embedding_resolved"] = embedding_rec.model_dump()

                elif step == "load_index":
                    if session.settings is None:
                        raise ValueError("Run config step first")
                    # US-3.3：remote 模式先解析下载远程源（staging 目录在 make_settings 已指向）。
                    # 数据源参数以会话内 config 步骤的值为唯一来源（与 make_settings 决策一致，防覆盖漂移）。
                    ds_params: dict[str, Any] = session.data_source_params
                    remote_cfg = parse_remote_sources(ds_params)
                    data_source = (ds_params.get("data_source") or "local").lower()
                    remote_report = None
                    if data_source == "remote":
                        if remote_cfg.is_empty():
                            raise ValueError(
                                "remote 模式需要至少一个数据源：source_urls / source_arxiv_ids / source_dois"
                            )
                        spec_errors = validate_source_specs(remote_cfg.to_specs())
                        if spec_errors:
                            raise ValueError("远程源校验失败：\n" + "\n".join(f"  - {e}" for e in spec_errors))
                        remote_report = await resolve_remote_sources(
                            remote_cfg,
                            session.settings.agent.index.name or "",
                        )
                    build = bool(req.params.get("build", True))
                    # US-4.2：目录不存在 → 友好报错（避免静默建空索引）
                    paper_dir_str = session.settings.agent.index.paper_directory
                    if build and paper_dir_str and not Path(paper_dir_str).exists():
                        raise ValueError(
                            f"论文目录不存在：{paper_dir_str}（请检查 paper_directory 参数；"
                            "remote 模式请先在 config 节点配置数据源）"
                        )
                    # Sprint-5 关闭二查修正：目录指纹不一致或 files.zip 损坏 → 整目录重建。
                    # 仅删 files.zip 会让 Tantivy 段/docs 存储残留旧引用（query 报 No such file）；
                    # 同目录同指纹时保持增量（行为不变）。
                    if build:
                        index_dir = _index_dir(session.settings)
                        marker = index_dir / "paper_dir_marker.txt"
                        current_fp = ""
                        try:
                            current_fp = marker.read_text(encoding="utf-8").strip()
                        except Exception:
                            pass
                        fingerprint = _paper_dir_fingerprint(session.settings)
                        if current_fp != fingerprint or _index_corrupt(session.settings):
                            import shutil

                            shutil.rmtree(index_dir, ignore_errors=True)
                    session.search_index = await self._engine.get_directory_index(
                        settings=session.settings, build=build
                    )
                    if build:
                        _write_index_marker(session.settings)
                    index_files = await session.search_index.index_files
                    output = {
                        "index_name": session.search_index.index_name,
                        "indexed_files": len(index_files),
                        "files": list(index_files.keys()),
                    }
                    if remote_report is not None:
                        # 追加：远程源解析明细（只增不减）
                        output["remote_sources"] = remote_report.model_dump()

                elif step == "retrieve":
                    if session.search_index is None:
                        raise ValueError("Run load_index step first")
                    query = req.params.get("query")
                    if not query:
                        query = req.upstream.get("question") or "PaperQA"
                    top_n = int(req.params.get("top_n", 5))

                    def _dedupe(results: Any) -> list[str]:
                        seen_local: set[str] = set()
                        out: list[str] = []
                        for r in results:
                            if isinstance(r, tuple) and len(r) == 2 and r[1] not in seen_local:
                                seen_local.add(r[1])
                                out.append(r[1])
                        return out

                    # US-5.2：按命中顺序去重（chunk 级结果可能重复文件）
                    query_used = query
                    strategy = "direct"
                    results = await self._engine.query_index(session.search_index, query, top_n)
                    deduped = _dedupe(results)

                    # US-6.1：多语检索 v1——含 CJK 的 query 零命中时提取英文关键词重试
                    # （确定性、零 LLM 成本；如"什么是PaperQA？"→"PaperQA"）
                    if not deduped and re.search(r"[\u4e00-\u9fff]", query):
                        keywords = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", query)
                        if keywords:
                            query_used = " ".join(keywords)
                            strategy = "keyword_retry"
                            results = await self._engine.query_index(
                                session.search_index, query_used, top_n
                            )
                            deduped = _dedupe(results)

                    if not deduped:
                        deduped = list((await session.search_index.index_files).keys())[:top_n]
                        result_mode = "fallback_first_n"
                        strategy = "fallback_first_n"  # 三查修正：策略枚举与结果对齐，hit_note 不再误报
                    else:
                        result_mode = "ranked"

                    hit_note = {
                        "direct": "直接命中：query 与索引分块 BM25 匹配",
                        "keyword_retry": (
                            "中文 query 直接检索零命中，已提取英文关键词重试（多语检索 v1）；"
                            "若仍不满意可改用英文 query"
                        ),
                        "fallback_first_n": (
                            "零命中：query 未匹配到任何分块（中文 query 且无英文关键词，"
                            "或索引内容与 query 语言不一致）；已回退取索引前 N 个文件"
                        ),
                    }[strategy]

                    session.candidate_paths = deduped
                    output = {
                        "query": query,
                        "query_used": query_used,
                        "query_strategy": strategy,  # direct / keyword_retry / fallback_first_n
                        "candidate_count": len(deduped),
                        "candidate_paths": deduped,
                        "result": result_mode,  # ranked=命中排名；fallback_first_n=零命中回退
                        "hit_note": hit_note,   # US-6.2：命中理由（前端 JsonTree 直接可见）
                    }

                elif step == "parse_chunk_embed":
                    if session.settings is None:
                        raise ValueError("Run config step first")
                    if session.search_index is None:
                        raise ValueError("Run load_index step first")
                    embed_mode = (req.params.get("embed_mode") or "run").lower()
                    paper_dir = Path(session.settings.agent.index.paper_directory)
                    paths = req.params.get("candidate_paths") or session.candidate_paths
                    if not paths:
                        paths = list((await session.search_index.index_files).keys())[:5]
                    cache_path = _embed_cache_path(
                        str(paper_dir),
                        session.settings.agent.index.name or "",
                        sorted(paths),
                    )

                    # "载入最近一次 Embedding"：能复用本会话 docs 则最快；否则用缓存（仅还原展示）
                    if embed_mode == "load":
                        if session.docs is not None:
                            docs = session.docs
                            sample_texts = [
                                {
                                    "name": getattr(t, "name", ""),
                                    "docname": getattr(getattr(t, "doc", None), "docname", ""),
                                    "text_preview": _safe_text_preview(getattr(t, "text", "")),
                                }
                                for t in list(docs.texts)[:8]
                            ]
                            output = {
                                "docs_count": len(docs.docs),
                                "texts_count": len(docs.texts),
                                "per_file": [],
                                "sample_texts": sample_texts,
                                "loaded": True,
                                "source": "session",
                            }
                        else:
                            cached = _read_embed_cache(cache_path)
                            if cached is not None:
                                output = {**cached, "loaded": True, "source": "cache"}
                                # docs 未在内存（跨会话）：evidence/answer 直接用它会缺 docs，
                                # 前端此时会提示"重新生成"以重建 docs。
                            else:
                                # 无缓存 -> 按原逻辑执行（F-AC10：逐篇 checkpoint，命中即零成本复用）
                                docs = self._engine.new_docs()
                                per_file, ckpt = await self._add_docs_with_checkpoint(
                                    docs, paths, paper_dir, session
                                )
                                session.docs = docs
                                sample_texts = [
                                    {
                                        "name": getattr(t, "name", ""),
                                        "docname": getattr(getattr(t, "doc", None), "docname", ""),
                                        "text_preview": _safe_text_preview(getattr(t, "text", "")),
                                    }
                                    for t in list(docs.texts)[:8]
                                ]
                                output = {
                                    "docs_count": len(docs.docs),
                                    "texts_count": len(docs.texts),
                                    "per_file": per_file,
                                    "sample_texts": sample_texts,
                                    "loaded": False,
                                    "checkpoint": ckpt,
                                }
                                _write_embed_cache(cache_path, output)
                    else:
                        # "重新生成"（regen）或默认（run）：总是重跑并覆盖缓存
                        # F-AC10：重跑逐篇走 checkpoint——已就绪且指纹/模型一致的文献直接复用（不再调用嵌入模型）
                        docs = self._engine.new_docs()
                        per_file, ckpt = await self._add_docs_with_checkpoint(
                            docs, paths, paper_dir, session
                        )
                        session.docs = docs
                        sample_texts = [
                            {
                                "name": getattr(t, "name", ""),
                                "docname": getattr(getattr(t, "doc", None), "docname", ""),
                                "text_preview": _safe_text_preview(getattr(t, "text", "")),
                            }
                            for t in list(docs.texts)[:8]
                        ]
                        output = {
                            "docs_count": len(docs.docs),
                            "texts_count": len(docs.texts),
                            "per_file": per_file,
                            "sample_texts": sample_texts,
                            "loaded": False,
                            "regen": embed_mode == "regen",
                            "checkpoint": ckpt,
                        }
                        _write_embed_cache(cache_path, output)

                elif step == "evidence":
                    if session.docs is None:
                        raise ValueError("Run parse_chunk_embed step first")
                    if session.settings is None:
                        raise ValueError("Run config step first")
                    question = req.params.get("question")
                    if not question:
                        question = req.upstream.get("question") or "什么是PaperQA？"
                    session.evidence_session = await self._engine.get_evidence(
                        session.docs, question, session.settings
                    )
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
                    session.answer_session = await self._engine.query_answer(
                        session.docs, session.evidence_session, session.settings
                    )
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
            del session.run_records[: max(0, len(session.run_records) - _MAX_RUN_RECORDS)]
            on_event(
                StepEvent(
                    kind="step_done",
                    session_id=session.session_id,
                    run_id=run_id,
                    step=step,
                    ok=True,
                    duration_s=ok_resp.duration_s,
                    function_count=len(ok_resp.function_trace),
                ).model_dump(exclude={"ts", "trace_id", "output", "error"})
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
                error_detail=traceback.format_exc(),  # F-AC6：完整堆栈供前端展开
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
                    "error_detail": err_resp.error_detail,  # F-AC6
                    "function_trace": _paperqa_trace(tracer.events),
                    "timestamp": time.time(),
                }
            )
            del session.run_records[: max(0, len(session.run_records) - _MAX_RUN_RECORDS)]
            on_event(
                StepEvent(
                    kind="step_done",
                    session_id=session.session_id,
                    run_id=run_id,
                    step=step,
                    ok=False,
                    error=str(exc),
                    duration_s=err_resp.duration_s,
                    function_count=len(err_resp.function_trace),
                ).model_dump(exclude={"ts", "trace_id", "output"})
            )
            return err_resp


# 组合根：全局编排器实例（engine + store 由 API 层注入）
ORCHESTRATOR: PipelineOrchestrator | None = None


def make_orchestrator(
    store: SessionStore,
    engine: EngineAdapter = ENGINE,
) -> PipelineOrchestrator:
    """组合根工厂：API 层启动时调用并绑定全局 ORCHESTRATOR。"""
    global ORCHESTRATOR
    ORCHESTRATOR = PipelineOrchestrator(engine=engine, store=store)
    return ORCHESTRATOR
