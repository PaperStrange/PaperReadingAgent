"""F-AC16 v1：checkpoint **只读索引**——把"本地已有哪些 checkpoint、含哪些文献、载荷在哪"暴露给前端/CLI。

动机（用户走查 CK-1）：pro 用户需要直接感知本次运行**复用了哪些本地 checkpoint**、按路径定位，
并能"用既有 checkpoint 单独复现结果"（也便于人工核查是否存在幻觉）。编排层的 step 输出已含
`checkpoint{reused/embedded/deduped/failed/checkpoint_key/manifest/reuse_misses}`，但缺少
① 逐篇**载荷路径**；② "全局有哪些命名空间"的视图。

设计约束：
- **只读**：不修改任何 checkpoint（写入仍归 `app/orchestration.py` 的 F-AC10 子系统）；
- 路径口径与编排层一致（`~/.pqa/embed_cache/checkpoints`），避免两套真相；
- **fail-soft**：单个坏 manifest 只跳过并记原因（只读视图不应因一个坏件整体不可用），
  但**逐篇状态如实回显**（ready/error/deduped 不美化）；
- 不暴露密钥（manifest 中本就没有）。
"""
from __future__ import annotations

import json
from pathlib import Path


def checkpoint_root() -> Path:
    """与 `app/orchestration.py::_embed_checkpoint_root()` 同一口径。"""
    return Path.home() / ".pqa" / "embed_cache" / "checkpoints"


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _doc_row(name: str, entry: dict, payload_dir: Path) -> dict:
    """把 manifest 里的一篇记录翻成前端可直接展示的行（含载荷路径与大小）。"""
    dockey = str(entry.get("dockey") or "")
    payload = payload_dir / f"{dockey}.json.gz" if dockey else None
    size = None
    exists = False
    if payload is not None:
        try:
            if payload.is_file():
                exists, size = True, payload.stat().st_size
        except OSError:
            exists = False
    return {
        "name": name,
        "docname": str(entry.get("docname") or ""),
        "dockey": dockey,
        "status": str(entry.get("status") or "unknown"),
        "texts_count": _safe_int(entry.get("texts_count")),
        "reused": bool(entry.get("reused", False)),
        "embedded_at": entry.get("embedded_at"),
        "error": str(entry.get("error") or ""),
        "payload_path": str(payload) if payload is not None else "",
        "payload_exists": exists,
        "payload_bytes": size,
    }


def _summarize(manifest_path: Path, data: dict) -> dict:
    key = str(data.get("checkpoint_key") or manifest_path.stem)
    payload_dir = manifest_path.parent / key
    docs_raw = data.get("docs") or {}
    rows = [_doc_row(str(name), (entry or {}), payload_dir) for name, entry in sorted(docs_raw.items())]
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    payload_bytes = sum(int(r["payload_bytes"] or 0) for r in rows)
    return {
        "checkpoint_key": key,
        "manifest_path": str(manifest_path),
        "payload_dir": str(payload_dir),
        "status": str(data.get("status") or "unknown"),
        "paper_dir": str(data.get("paper_dir") or ""),
        "index_name": str(data.get("index_name") or ""),
        "embedding_model": str(data.get("embedding_model") or ""),
        "chunk_chars": data.get("chunk_chars"),
        "chunk_overlap": data.get("chunk_overlap"),
        "updated_at": data.get("updated_at"),
        "docs_total": len(rows),
        "docs_by_status": by_status,
        "payload_bytes_total": payload_bytes,
        "readable": True,
        "docs": rows,
    }


def scan(root: Path | None = None, *, include_docs: bool = True) -> list[dict]:
    """列出全部命名空间（按 `updated_at` 倒序，缺失则按 mtime）。

    坏 manifest → 仍返回一条记录，带 `readable=False` 与 `error`，便于前端提示"该件损坏"。
    """
    base = Path(root) if root is not None else checkpoint_root()
    out: list[dict] = []
    if not base.is_dir():
        return out
    try:
        manifests = [p for p in base.glob("*.json") if p.is_file()]
    except OSError:
        return out
    for m in manifests:
        try:
            data = json.loads(m.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("manifest 顶层不是 JSON 对象")
            rec = _summarize(m, data)
        except Exception as exc:  # noqa: BLE001 —— 只读视图不因坏件整体失败
            try:
                mtime = m.stat().st_mtime
            except OSError:
                mtime = 0.0
            rec = {
                "checkpoint_key": m.stem,
                "manifest_path": str(m),
                "payload_dir": str(m.parent / m.stem),
                "status": "corrupt",
                "paper_dir": "",
                "index_name": "",
                "embedding_model": "",
                "chunk_chars": None,
                "chunk_overlap": None,
                "updated_at": mtime,
                "docs_total": 0,
                "docs_by_status": {},
                "payload_bytes_total": 0,
                "readable": False,
                "error": f"{type(exc).__name__}: {exc}",
                "docs": [],
            }
        if not include_docs:
            rec = {k: v for k, v in rec.items() if k != "docs"}
        out.append(rec)
    out.sort(key=lambda r: float(r.get("updated_at") or 0.0), reverse=True)
    return out


def namespace_detail(key: str, root: Path | None = None) -> dict | None:
    """取单个命名空间明细（含逐篇载荷路径）；不存在 → None。"""
    base = Path(root) if root is not None else checkpoint_root()
    manifest = base / f"{key}.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "checkpoint_key": key,
            "manifest_path": str(manifest),
            "payload_dir": str(base / key),
            "status": "corrupt",
            "readable": False,
            "error": f"{type(exc).__name__}: {exc}",
            "docs": [],
        }
    return _summarize(manifest, data)


def resolve_payload(key: str, dockey: str, root: Path | None = None) -> Path | None:
    """按 (key, dockey) 解析载荷路径（存在才返回）——供"用既有 checkpoint 复现"的 CLI/脚本使用。"""
    base = Path(root) if root is not None else checkpoint_root()
    p = base / key / f"{dockey}.json.gz"
    return p if p.is_file() else None
