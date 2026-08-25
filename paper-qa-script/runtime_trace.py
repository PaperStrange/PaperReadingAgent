from __future__ import annotations

import datetime as dt
import importlib
import inspect
import re
import time
import asyncio
import itertools
import contextvars
import base64
from pathlib import Path
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any


def _redact(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9]{16,}", "sk-***REDACTED***", text)


def _summarize_value(v: Any, max_len: int = 180) -> str:
    try:
        if v is None:
            return "None"
        if isinstance(v, (bool, int, float)):
            return repr(v)
        if isinstance(v, str):
            short = v if len(v) <= max_len else (v[: max_len - 20] + "...[truncated]")
            return _redact(repr(short))
        if isinstance(v, (list, tuple, set)):
            name = type(v).__name__
            return f"{name}(len={len(v)})"
        if isinstance(v, dict):
            keys = list(v.keys())[:8]
            return f"dict(len={len(v)}, keys={keys})"
        if hasattr(v, "question") and hasattr(v, "answer"):
            q = getattr(v, "question", "")
            a = getattr(v, "answer", "")
            return f"{type(v).__name__}(question={_summarize_value(q, 80)}, answer_chars={len(a or '')})"
        if hasattr(v, "status") and hasattr(v, "session"):
            return f"{type(v).__name__}(status={getattr(v, 'status', None)})"
        if hasattr(v, "__class__"):
            return type(v).__name__
    except Exception:
        return "<unserializable>"
    return "<unknown>"


def _summarize_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    arg_vals = list(args)
    if arg_vals and hasattr(arg_vals[0], "__class__"):
        # likely bound method self
        arg_vals = arg_vals[1:]
    return {
        "args": [_summarize_value(a) for a in arg_vals[:4]],
        "kwargs": {k: _summarize_value(v) for k, v in list(kwargs.items())[:10]},
    }


def _to_text_preview(text: str, max_len: int = 320) -> str:
    clean = (text or "").replace("\n", " ").strip()
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 14] + "...[truncated]"


def _to_text_full(text: str, max_len: int = 6000) -> str:
    raw = (text or "").strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 14] + "...[truncated]"


def _safe_image_url(media: Any, max_bytes: int = 200_000) -> str | None:
    try:
        data = getattr(media, "data", b"")
        if not isinstance(data, (bytes, bytearray)):
            return None
        if len(data) > max_bytes:
            return None
        if hasattr(media, "to_image_url") and callable(media.to_image_url):
            return media.to_image_url()
    except Exception:
        return None
    return None


def _extract_page_from_text_name(name: str) -> int | None:
    m = re.search(r"pages?\s+(\d+)(?:-(\d+))?", name or "", flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _render_pdf_page_preview(file_location: str, page_num_1_based: int) -> tuple[str | None, str]:
    try:
        import fitz  # pymupdf
    except Exception:
        return None, "no_fitz"
    try:
        path = Path(file_location)
        if not path.exists():
            return None, "file_not_found"
        if path.suffix.lower() != ".pdf":
            return None, "not_pdf"
        with fitz.open(path) as pdf:
            if len(pdf) == 0:
                return None, "empty_pdf"
            pidx = max(0, min(page_num_1_based - 1, len(pdf) - 1))
            page = pdf[pidx]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.45, 0.45), alpha=False)
            raw = pix.tobytes("png")
            if len(raw) > 400_000:
                return None, "image_too_large"
            b64 = base64.b64encode(raw).decode("ascii")
            return f"data:image/png;base64,{b64}", "ok"
    except Exception:
        return None, "render_error"
    return None, "unknown"


def _structured_value_payload(
    v: Any,
    func_id: str = "",
    docname_to_path: dict[str, str] | None = None,
    current_source_path: str | None = None,
) -> dict[str, Any] | None:
    try:
        if v is None:
            return None
        if isinstance(v, list):
            first = v[0] if v else None
            if first is not None and hasattr(first, "text") and hasattr(first, "name"):
                items = []
                for t in v[:5]:
                    item = _structured_value_payload(
                        t,
                        func_id=func_id,
                        docname_to_path=docname_to_path,
                        current_source_path=current_source_path,
                    )
                    if item:
                        items.append(item)
                return {"kind": "TextList", "count": len(v), "items": items}
            return {"kind": "List", "count": len(v)}
        if hasattr(v, "text") and hasattr(v, "name"):
            media = getattr(v, "media", []) or []
            first_media_url = None
            if media:
                first_media_url = _safe_image_url(media[0])
            doc = getattr(v, "doc", None)
            docname = getattr(doc, "docname", "") if doc is not None else ""
            file_location = getattr(doc, "file_location", None) if doc is not None else None
            if not file_location and docname and docname_to_path:
                file_location = docname_to_path.get(docname)
            if not file_location and current_source_path:
                file_location = current_source_path
            page_preview_url = None
            preview_reason = None
            page_num = _extract_page_from_text_name(getattr(v, "name", ""))
            if (
                page_num is not None
                and isinstance(file_location, str | Path)
                and str(file_location)
                and func_id.endswith("paperqa.readers._make_chunk")
            ):
                page_preview_url, preview_reason = _render_pdf_page_preview(
                    str(file_location), page_num
                )
            elif func_id.endswith("paperqa.readers._make_chunk"):
                if page_num is None:
                    preview_reason = "no_page_num"
                elif not file_location:
                    preview_reason = "no_file_location"
                else:
                    preview_reason = "not_string_file_location"
            return {
                "kind": "Text",
                "name": getattr(v, "name", ""),
                "docname": docname,
                "text_preview": _to_text_preview(getattr(v, "text", "")),
                "text_full": _to_text_full(getattr(v, "text", "")),
                "media_count": len(media),
                "first_media_url": first_media_url,
                "file_location": str(file_location) if file_location else None,
                "page_num": page_num,
                "page_preview_url": page_preview_url,
                "preview_reason": preview_reason,
            }
        if hasattr(v, "content") and hasattr(v, "metadata"):
            md = getattr(v, "metadata", None)
            return {
                "kind": "ParsedText",
                "content_type": type(getattr(v, "content", None)).__name__,
                "parsed_len": getattr(md, "total_parsed_text_length", None),
                "count_parsed_media": getattr(md, "count_parsed_media", None),
            }
        if isinstance(v, dict):
            return {"kind": "Dict", "keys": list(v.keys())[:12], "size": len(v)}
    except Exception:
        return None
    return None


def _structured_args_payload(func_id: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any] | None:
    try:
        arg_vals = list(args)
        if arg_vals and hasattr(arg_vals[0], "__class__"):
            arg_vals = arg_vals[1:]
        payload: dict[str, Any] = {}
        if func_id.endswith("paperqa.readers._make_chunk"):
            if len(arg_vals) >= 5:
                payload = {
                    "chunk_text_preview": _to_text_preview(str(arg_vals[2])),
                    "page_range": f"{arg_vals[3]}-{arg_vals[4]}",
                }
        elif func_id.endswith("paperqa.readers.chunk_pdf"):
            chunk_chars = arg_vals[2] if len(arg_vals) >= 3 else kwargs.get("chunk_chars")
            overlap = arg_vals[3] if len(arg_vals) >= 4 else kwargs.get("overlap")
            payload = {"chunk_chars": chunk_chars, "overlap": overlap}
        elif func_id.endswith("paperqa.docs.Docs.aadd_texts"):
            payload = {
                "texts_arg": _summarize_value(arg_vals[0]) if arg_vals else None,
            }
        if payload:
            return payload
    except Exception:
        return None
    return None


@dataclass
class _Patch:
    obj: Any
    attr: str
    original: Any


class RuntimeTracer(AbstractContextManager):
    TARGETS = [
        "paperqa.agents.main.agent_query",
        "paperqa.agents.main.run_agent",
        "paperqa.agents.main.run_fake_agent",
        "paperqa.agents.main.run_aviary_agent",
        "paperqa.agents.main.run_ldp_agent",
        "paperqa.agents.main._run_with_timeout_failure",
        "paperqa.agents.search.get_directory_index",
        "paperqa.agents.search.SearchIndex.query",
        "paperqa.docs.Docs.aadd",
        "paperqa.docs.Docs.aadd_texts",
        "paperqa.docs.Docs.retrieve_texts",
        "paperqa.docs.Docs.aget_evidence",
        "paperqa.docs.Docs.aquery",
        "paperqa.readers.read_doc",
        "paperqa.core.map_fxn_summary",
        "paperqa.settings.Settings.get_llm",
        "paperqa.settings.Settings.get_summary_llm",
        "paperqa.settings.Settings.get_embedding_model",
        "paperqa.settings.Settings.get_enrichment_llm",
    ]

    OPTIONAL_TARGETS = [
        "lmi.embeddings.LiteLLMEmbeddingModel.embed_documents",
    ]
    MODULE_TARGETS = [
        "paperqa.docs",
        "paperqa.agents.main",
        "paperqa.agents.search",
        "paperqa.agents.tools",
        "paperqa.llms",
        "paperqa.core",
        "paperqa.readers",
        "paperqa.settings",
    ]

    def __init__(self, on_event: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.events: list[dict[str, Any]] = []
        self._patches: list[_Patch] = []
        self._active = False
        self._call_counter = itertools.count(1)
        self._call_stack_var: contextvars.ContextVar[list[int]] = contextvars.ContextVar(
            "runtime_trace_call_stack",
            default=[],
        )
        self._installed_keys: set[tuple[int, str]] = set()
        self._on_event = on_event
        self._docname_to_path: dict[str, str] = {}
        self._source_path_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
            "runtime_trace_source_path",
            default=None,
        )

    def _resolve_target(self, dotted: str) -> tuple[Any, str]:
        parts = dotted.split(".")
        for i in range(len(parts), 0, -1):
            module_name = ".".join(parts[:i])
            try:
                module = importlib.import_module(module_name)
                attrs = parts[i:]
                obj: Any = module
                for a in attrs[:-1]:
                    obj = getattr(obj, a)
                return obj, attrs[-1]
            except Exception:
                continue
        raise ImportError(f"Cannot resolve target: {dotted}")

    def _record(
        self,
        func_id: str,
        call_id: int,
        parent_call_id: int | None,
        depth: int,
        task_id: str | None,
        started_at: str,
        args_summary: dict[str, Any],
        status: str,
        duration_s: float,
        result_summary: str | None = None,
        result_payload: dict[str, Any] | None = None,
        args_payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        event = {
            "call_id": call_id,
            "parent_call_id": parent_call_id,
            "depth": depth,
            "task_id": task_id,
            "func": func_id,
            "started_at": started_at,
            "args": args_summary,
            "status": status,
            "duration_s": round(duration_s, 6),
            "result": result_summary,
            "result_payload": result_payload,
            "args_payload": args_payload,
            "error": _redact(error or ""),
        }
        self.events.append(event)
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass

    def _wrap(self, func: Callable, func_id: str) -> Callable:
        if inspect.iscoroutinefunction(func):

            async def aw(*args: Any, **kwargs: Any) -> Any:
                call_id = next(self._call_counter)
                stack = self._call_stack_var.get()
                parent_call_id = stack[-1] if stack else None
                depth = len(stack)
                token = self._call_stack_var.set([*stack, call_id])
                task = asyncio.current_task()
                task_id = f"task-{id(task)}" if task else None
                started_at = dt.datetime.now().isoformat(timespec="seconds")
                args_summary = _summarize_args(args, kwargs)
                args_payload = _structured_args_payload(func_id, args, kwargs)
                path_token: contextvars.Token[str | None] | None = None
                if func_id.endswith("paperqa.docs.Docs.aadd"):
                    path_val = kwargs.get("path")
                    if not path_val:
                        arg_vals = list(args)
                        if len(arg_vals) >= 2:
                            path_val = arg_vals[1]
                    path_token = self._source_path_var.set(
                        str(path_val) if path_val else self._source_path_var.get()
                    )
                t0 = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    if func_id.endswith("paperqa.docs.Docs.aadd") and isinstance(result, str):
                        path_val = kwargs.get("path")
                        if not path_val:
                            arg_vals = list(args)
                            if len(arg_vals) >= 2:
                                path_val = arg_vals[1]
                        if path_val:
                            self._docname_to_path[result] = str(path_val)
                    self._record(
                        func_id,
                        call_id,
                        parent_call_id,
                        depth,
                        task_id,
                        started_at,
                        args_summary,
                        "ok",
                        time.perf_counter() - t0,
                        result_summary=_summarize_value(result),
                        result_payload=_structured_value_payload(
                            result,
                            func_id=func_id,
                            docname_to_path=self._docname_to_path,
                            current_source_path=self._source_path_var.get(),
                        ),
                        args_payload=args_payload,
                    )
                    return result
                except Exception as exc:
                    self._record(
                        func_id,
                        call_id,
                        parent_call_id,
                        depth,
                        task_id,
                        started_at,
                        args_summary,
                        "error",
                        time.perf_counter() - t0,
                        args_payload=args_payload,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    raise
                finally:
                    if path_token is not None:
                        self._source_path_var.reset(path_token)
                    self._call_stack_var.reset(token)

            return aw

        def sw(*args: Any, **kwargs: Any) -> Any:
            call_id = next(self._call_counter)
            stack = self._call_stack_var.get()
            parent_call_id = stack[-1] if stack else None
            depth = len(stack)
            token = self._call_stack_var.set([*stack, call_id])
            try:
                task = asyncio.current_task()
                task_id = f"task-{id(task)}" if task else None
            except RuntimeError:
                task_id = None
            started_at = dt.datetime.now().isoformat(timespec="seconds")
            args_summary = _summarize_args(args, kwargs)
            args_payload = _structured_args_payload(func_id, args, kwargs)
            path_token: contextvars.Token[str | None] | None = None
            if func_id.endswith("paperqa.docs.Docs.aadd"):
                path_val = kwargs.get("path")
                if not path_val:
                    arg_vals = list(args)
                    if len(arg_vals) >= 2:
                        path_val = arg_vals[1]
                path_token = self._source_path_var.set(
                    str(path_val) if path_val else self._source_path_var.get()
                )
            t0 = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                if func_id.endswith("paperqa.docs.Docs.aadd") and isinstance(result, str):
                    path_val = kwargs.get("path")
                    if not path_val:
                        arg_vals = list(args)
                        if len(arg_vals) >= 2:
                            path_val = arg_vals[1]
                    if path_val:
                        self._docname_to_path[result] = str(path_val)
                self._record(
                    func_id,
                    call_id,
                    parent_call_id,
                    depth,
                    task_id,
                    started_at,
                    args_summary,
                    "ok",
                    time.perf_counter() - t0,
                    result_summary=_summarize_value(result),
                    result_payload=_structured_value_payload(
                        result,
                        func_id=func_id,
                        docname_to_path=self._docname_to_path,
                        current_source_path=self._source_path_var.get(),
                    ),
                    args_payload=args_payload,
                )
                return result
            except Exception as exc:
                self._record(
                    func_id,
                    call_id,
                    parent_call_id,
                    depth,
                    task_id,
                    started_at,
                    args_summary,
                    "error",
                    time.perf_counter() - t0,
                    args_payload=args_payload,
                    error=f"{type(exc).__name__}: {exc}",
                )
                raise
            finally:
                if path_token is not None:
                    self._source_path_var.reset(path_token)
                self._call_stack_var.reset(token)

        return sw

    def _install(self, target: str, required: bool) -> None:
        try:
            obj, attr = self._resolve_target(target)
            key = (id(obj), attr)
            if key in self._installed_keys:
                return
            # FIX(原文件 bug): staticmethod/classmethod 不能被替换成普通函数，
            # 否则经实例调用时会多传 self/cls，导致 TypeError（例如 SearchIndex.filehash）。
            # 用 inspect.getattr_static 拿到原始描述符，保持其绑定语义；还原时也还原描述符本身。
            original_descriptor = inspect.getattr_static(obj, attr, None)
            if isinstance(original_descriptor, staticmethod):
                original = original_descriptor.__func__
                restore = original_descriptor
            elif isinstance(original_descriptor, classmethod):
                original = original_descriptor.__func__
                restore = original_descriptor
            else:
                original = getattr(obj, attr)
                restore = original
            if not callable(original):
                return
            wrapped = self._wrap(original, target)
            if isinstance(original_descriptor, staticmethod):
                setattr(obj, attr, staticmethod(wrapped))
            elif isinstance(original_descriptor, classmethod):
                setattr(obj, attr, classmethod(wrapped))
            else:
                setattr(obj, attr, wrapped)
            self._patches.append(_Patch(obj=obj, attr=attr, original=restore))
            self._installed_keys.add(key)
        except Exception:
            if required:
                raise

    def _install_module_targets(self, module_name: str) -> None:
        module = importlib.import_module(module_name)

        for attr, value in vars(module).items():
            if attr.startswith("__"):
                continue

            if inspect.isfunction(value) and getattr(value, "__module__", "").startswith(module_name):
                self._install(f"{module_name}.{attr}", required=False)
                continue

            if inspect.isclass(value) and getattr(value, "__module__", "").startswith(module_name):
                for meth_name, meth in vars(value).items():
                    if meth_name.startswith("__"):
                        continue
                    target = None
                    if inspect.iscoroutinefunction(meth) or inspect.isfunction(meth):
                        target = f"{module_name}.{value.__name__}.{meth_name}"
                    elif isinstance(meth, staticmethod):
                        fn = meth.__func__
                        if inspect.iscoroutinefunction(fn) or inspect.isfunction(fn):
                            target = f"{module_name}.{value.__name__}.{meth_name}"
                    elif isinstance(meth, classmethod):
                        fn = meth.__func__
                        if inspect.iscoroutinefunction(fn) or inspect.isfunction(fn):
                            target = f"{module_name}.{value.__name__}.{meth_name}"
                    if target:
                        self._install(target, required=False)

    def __enter__(self) -> "RuntimeTracer":
        if self._active:
            return self
        self._active = True
        self.events.clear()
        self._docname_to_path.clear()
        self._call_counter = itertools.count(1)
        self._installed_keys.clear()
        for target in self.TARGETS:
            self._install(target, required=True)
        for module_name in self.MODULE_TARGETS:
            self._install_module_targets(module_name)
        for target in self.OPTIONAL_TARGETS:
            self._install(target, required=False)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for patch in reversed(self._patches):
            setattr(patch.obj, patch.attr, patch.original)
        self._patches.clear()
        self._installed_keys.clear()
        self._active = False
