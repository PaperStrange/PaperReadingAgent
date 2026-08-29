"""远程源解析器（Sprint-3 US-3.2，主题 B 的网络/IO 部分）。

把 `url` / `arxiv_id` / `doi` 三类远程源统一解析为 PDF/HTML 文件并下载到
staging 目录（`data/remote/<index_name>/`），随后复用现有索引/解析管线。

设计约束：
- 幂等：同名文件已存在且非空 → 跳过（status="cached"）；
- 单个源失败不影响其它源（记录到 `RemoteResolveResult.error`）；
- 文件名净化（防路径穿越）；PDF/HTML 按内容嗅探补后缀；
- 全部失败时由调用方（编排层）抛出含明细的 ValueError。
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from app.data_sources import RemoteSourceConfig, SourceKind, SourceSpec, remote_staging_dir

_ARXIV_API = "https://export.arxiv.org/api/query"
_UNPAYWALL_API = "https://api.unpaywall.org/v2"
_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
_SAFE_SUFFIXES = {".pdf", ".txt", ".md", ".html", ".htm"}
_TIMEOUT = 30.0


class RemoteResolveResult(BaseModel):
    """单个远程源的解析/下载结果。"""

    kind: SourceKind
    value: str
    ok: bool
    status: str = ""          # downloaded | cached | failed
    filename: str | None = None
    pdf_url: str | None = None   # 实际使用的下载链接（arXiv/DOI 解析后的）
    size_bytes: int | None = None
    error: str | None = None


class RemoteResolveReport(BaseModel):
    """一次解析的整体报告（追加进 load_index 输出，前端可展示）。"""

    staged_dir: str
    results: list[RemoteResolveResult] = Field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def fail_count(self) -> int:
        return len(self.results) - self.ok_count

    @property
    def failures(self) -> list[str]:
        return [f"{r.kind.value}: {r.value} -> {r.error}" for r in self.results if not r.ok]


def _safe_filename(raw: str, fallback: str) -> str:
    """净化文件名：取 basename、剔除路径/控制字符、防穿越。"""
    name = Path(urlparse(raw).path if "://" in raw else raw).name or fallback
    name = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "_", name).strip(" .")
    return name or fallback


def _sniff_suffix(head: bytes, current: str) -> str:
    """按内容嗅探修正后缀（PDF/HTML），无法判断时保留原后缀（无后缀则 .pdf）。"""
    lower = current.lower()
    if lower.endswith(tuple(_SAFE_SUFFIXES)):
        return lower[lower.rfind("."):]
    if head[:5] == b"%PDF-":
        return ".pdf"
    stripped = head.lstrip()[:512].lower()
    if b"<!doctype html" in stripped or b"<html" in stripped:
        return ".html"
    return ".pdf"


async def resolve_arxiv_pdf_url(arxiv_id: str, client: httpx.AsyncClient) -> str:
    """export.arxiv.org 公开 API（免 key）：arXiv ID → PDF 链接（失败重试一次）。"""
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            r = await client.get(_ARXIV_API, params={"id_list": arxiv_id, "max_results": 1})
            r.raise_for_status()
            root = ET.fromstring(r.text)
            entries = root.findall("a:entry", _ATOM_NS)
            if not entries:
                raise ValueError(f"arXiv 未找到 {arxiv_id!r}")
            title = (entries[0].findtext("a:title", default="", namespaces=_ATOM_NS) or "").strip()
            if title.lower().startswith("error"):
                raise ValueError(f"arXiv 返回错误：{title}")
            return f"https://arxiv.org/pdf/{arxiv_id}"
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt == 0:
                import asyncio

                await asyncio.sleep(1.0)
    raise last_exc  # type: ignore[misc]


async def resolve_doi_pdf_url(doi: str, client: httpx.AsyncClient) -> str:
    """Unpaywall：DOI → 开放获取 PDF 链接。

    要求真实邮箱（`UNPAYWALL_EMAIL` 环境变量，与 paperqa 客户端同约定）；
    未设置时给出清晰指引，避免示例邮箱被 API 拒绝后的迷惑报错。
    """
    import os

    email = os.environ.get("UNPAYWALL_EMAIL", "").strip()
    if not email:
        raise ValueError(
            "Unpaywall 要求真实邮箱：请设置环境变量 UNPAYWALL_EMAIL=你的邮箱 后重试（DOI 源暂不可用）"
        )
    r = await client.get(f"{_UNPAYWALL_API}/{doi}", params={"email": email})
    if r.status_code == 404:
        raise ValueError(f"Unpaywall 未找到该 DOI（{doi}）")
    if r.status_code == 422:
        raise ValueError(f"Unpaywall 拒绝请求：{r.text[:200]}（请确认 UNPAYWALL_EMAIL 为真实邮箱）")
    r.raise_for_status()
    data = r.json()
    best = data.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf") or best.get("url")
    if not pdf_url:
        raise ValueError(f"该 DOI 无开放获取全文（Unpaywall 未返回 PDF 链接，OA 状态：{data.get('oa_status')}）")
    return pdf_url


async def resolve_one(
    spec: SourceSpec, dest_dir: Path, client: httpx.AsyncClient
) -> RemoteResolveResult:
    """解析并下载单个远程源（幂等；失败仅记录）。"""
    result = RemoteResolveResult(kind=spec.kind, value=spec.value, ok=False)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        if spec.kind == SourceKind.ARXIV_ID:
            pdf_url = await resolve_arxiv_pdf_url(spec.value, client)
            filename = _safe_filename(f"{spec.value}.pdf", f"{spec.value}.pdf")
        elif spec.kind == SourceKind.DOI:
            pdf_url = await resolve_doi_pdf_url(spec.value, client)
            filename = _safe_filename(f"{spec.value.replace('/', '_')}.pdf", "paper.pdf")
        else:  # URL
            pdf_url = spec.value
            filename = _safe_filename(spec.value, f"source-{abs(hash(spec.value)) % 100000}.pdf")

        target = dest_dir / filename
        result.pdf_url = pdf_url
        result.filename = filename
        if target.exists() and target.stat().st_size > 0:
            result.ok = True
            result.status = "cached"
            result.size_bytes = target.stat().st_size
            return result

        async with client.stream("GET", pdf_url, follow_redirects=True) as resp:
            resp.raise_for_status()
            head = b""
            chunks: list[bytes] = []
            total = 0
            async for chunk in resp.aiter_bytes():
                chunks.append(chunk)
                total += len(chunk)
                if len(head) < 1024:
                    head += chunk[: 1024 - len(head)]
            if total == 0:
                raise ValueError("下载内容为空")

        suffix = _sniff_suffix(head, filename)
        if Path(filename).suffix.lower() != suffix:
            filename = f"{Path(filename).stem}{suffix}"
            target = dest_dir / filename
            result.filename = filename
        target.write_bytes(b"".join(chunks))
        result.ok = True
        result.status = "downloaded"
        result.size_bytes = target.stat().st_size
    except httpx.TimeoutException:
        result.status = "failed"
        result.error = f"网络超时（{_TIMEOUT}s），请重试或检查网络"
    except Exception as exc:  # noqa: BLE001 单个源失败仅记录
        result.status = "failed"
        # httpx 等异常 str() 可能为空 -> repr 兜底，保证错误明细可读
        result.error = str(exc) or repr(exc) or type(exc).__name__
    return result


async def resolve_remote_sources(
    config: RemoteSourceConfig,
    index_name: str,
    base_dir: Path | None = None,
) -> RemoteResolveReport:
    """解析全部远程源 → staging 目录；全失败时抛 ValueError（带明细）。"""
    staged_dir = remote_staging_dir(index_name, base_dir)
    specs = config.to_specs()
    if not specs:
        return RemoteResolveReport(staged_dir=str(staged_dir), results=[])
    timeout = httpx.Timeout(_TIMEOUT, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        results = [await resolve_one(s, staged_dir, client) for s in specs]
    report = RemoteResolveReport(staged_dir=str(staged_dir), results=results)
    if report.ok_count == 0:
        raise ValueError(
            "远程源全部解析失败：\n" + "\n".join(f"  - {f}" for f in report.failures)
        )
    return report
