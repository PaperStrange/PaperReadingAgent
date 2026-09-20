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
import re
from pathlib import Path

# checkpoint key = `sha1(...)[:16]`（编排层生成，实测 16 位）→ 接受 6~64 位十六进制。
# 下限放宽到 6 是为了兼容历史键与测试键；**安全性来自"仅十六进制 + 锚定匹配"**（长度不是安全属性），
# `?key=` 来自 HTTP 查询串，若直接拼进路径可被 `../` 穿越到 checkpoint 根之外，故按 key 的接口都必须过本函数。
_KEY_RE = re.compile(r"^[0-9a-f]{6,64}$")


def _safe_key(key: str) -> str:
    """校验并归一化 checkpoint key（小写十六进制）；非法 → ValueError（调用方转 400）。"""
    k = (key or "").strip().lower()
    if not _KEY_RE.match(k):
        raise ValueError("checkpoint key 非法：应为 6~64 位十六进制字符串")
    return k


def checkpoint_root() -> Path:
    """与 `app/orchestration.py::_embed_checkpoint_root()` 同一口径。"""
    return Path.home() / ".pqa" / "embed_cache" / "checkpoints"


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _doc_row(name: str, entry: dict, payload_dir: Path | None) -> dict:
    """把 manifest 里的一篇记录翻成前端可直接展示的行（含载荷路径与大小）。

    **dockey 取 basename**（复核 Round 5 minor）：manifest 是磁盘文件，可能被手工改坏；
    不归一化就会把 `..\\..` 拼进路径、探到命名空间之外（只读探测，但仍是越界读取面）。

    `payload_dir=None`（2026-09-21 关闭三查·二查 major）：命名空间 key 非法时**不回显任何载荷路径**，
    也就不再对外部文件做存在性/大小探测。
    """
    raw_dockey = Path(str(entry.get("dockey") or "")).name
    dockey = "" if raw_dockey in (".", "..") else raw_dockey
    payload = payload_dir / f"{dockey}.json.gz" if (payload_dir is not None and dockey) else None
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
    """汇总一个命名空间；**key 必须过 `_safe_key`**（2026-09-21 关闭三查·二查 major，教训 1.61）。

    `checkpoint_key` 与 dockey 同源（都来自磁盘 manifest、都可能被手工改坏），上一轮只归一化了 dockey，
    于是 key 直接拼进 `payload_dir` → 绝对路径或 `../..` 可逃出 checkpoint 根，再经
    `GET /api/checkpoints` 回显 `payload_exists`/`payload_bytes` = 任意文件存在性与大小探测。
    这里改为：非法 key 先回退到目录名；目录名也不合法 → **完全不回显/不探测载荷路径**，并记 `key_warning`。
    """
    raw_key = str(data.get("checkpoint_key") or manifest_path.stem)
    key_warning = ""
    safe_key = ""
    try:
        safe_key = _safe_key(raw_key)
    except ValueError:
        key_warning = f"checkpoint_key 非法（{raw_key[:60]!r}）→ 忽略，按目录名回退"
        try:
            safe_key = _safe_key(manifest_path.stem)
        except ValueError:
            safe_key = ""
            key_warning += "；目录名亦非合法 key → 载荷路径不回显（防越界探测）"
    key = safe_key or raw_key
    payload_dir = (manifest_path.parent / safe_key) if safe_key else None
    docs_raw = data.get("docs") or {}
    rows = [_doc_row(str(name), (entry or {}), payload_dir) for name, entry in sorted(docs_raw.items())]
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    payload_bytes = sum(int(r["payload_bytes"] or 0) for r in rows)
    return {
        "checkpoint_key": key,
        "manifest_path": str(manifest_path),
        "payload_dir": str(payload_dir) if payload_dir is not None else "",
        "key_warning": key_warning,
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
    """取单个命名空间明细（含逐篇载荷路径）；不存在 → None；key 非法 → ValueError。"""
    base = Path(root) if root is not None else checkpoint_root()
    k = _safe_key(key)
    manifest = base / f"{k}.json"
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
    """按 (key, dockey) 解析载荷路径（存在才返回）——供"用既有 checkpoint 复现"的 CLI/脚本使用。

    key 非法 → ValueError；dockey 只取 basename（防 `../` 拼接）。
    """
    base = Path(root) if root is not None else checkpoint_root()
    k = _safe_key(key)
    name = Path(str(dockey or "")).name
    if not name or name in (".", ".."):
        return None
    p = base / k / f"{name}.json.gz"
    return p if p.is_file() else None
