"""远程源解析器（Sprint-3 US-3.2，主题 B 的网络/IO 部分）。

把 `url` / `arxiv_id` / `doi` 三类远程源统一解析为 PDF/HTML 文件并下载到
staging 目录（`data/remote/<index_name>/`），随后复用现有索引/解析管线。

设计约束：
- 幂等：同名文件已存在且非空 → 跳过（status="cached"）；
- 单个源失败不影响其它源（记录到 `RemoteResolveResult.error`）；
- 文件名净化（防路径穿越）；PDF/HTML 按内容嗅探补后缀；
- 安全（code review M1/M2）：下载前校验 URL（仅 http/https + 拒绝本机/内网地址，
  重定向逐跳复检）；下载大小上限 + 流式写临时文件，防止内存/磁盘被超大文件打爆；
- 全部失败时由调用方（编排层）抛出含明细的 ValueError。
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import socket
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from app.data_sources import RemoteSourceConfig, SourceKind, SourceSpec, remote_staging_dir

_ARXIV_API = "https://export.arxiv.org/api/query"
_UNPAYWALL_API = "https://api.unpaywall.org/v2"
_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
_SAFE_SUFFIXES = {".pdf", ".txt", ".md", ".html", ".htm"}
_TIMEOUT = 30.0
_MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024   # 单文件 200MB 上限
_MAX_REDIRECTS = 5


# 开发沙箱的透明代理把公网域名解析到 198.18.0.0/15（RFC 2544 基准段，公网不可路由，
# 仅本机代理可到达）：豁免该段，其余私有/回环/链路本地/保留地址一律拒绝（SSRF 防护）。
_BENCHMARK_PROXY_NET = ipaddress.ip_network("198.18.0.0/15")


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip in _BENCHMARK_PROXY_NET:
        return False
    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_reserved,
            ip.is_multicast,
            ip.is_unspecified,
        )
    )


def _host_allowed(host: str) -> bool:
    """拒绝本机/内网/链路本地/保留地址（SSRF 防护）；解析失败视为不允许。"""
    try:
        return not _is_blocked_ip(ipaddress.ip_address(host))
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    return all(
        not _is_blocked_ip(ipaddress.ip_address(info[4][0]))
        for info in infos
    )


def _validate_url(url: str) -> str:
    """校验下载 URL：仅 http/https 且主机为公网地址；返回原 URL。"""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的协议：{parsed.scheme or '(空)'}（仅允许 http/https）")
    host = parsed.hostname
    if not host:
        raise ValueError(f"URL 缺少主机名：{url!r}")
    if not _host_allowed(host):
        raise ValueError(f"拒绝访问本机/内网地址：{host}（出于安全仅允许公网源）")
    return url


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
    return _validate_url(pdf_url)


async def resolve_one(
    spec: SourceSpec, dest_dir: Path, client: httpx.AsyncClient
) -> RemoteResolveResult:
    """解析并下载单个远程源（幂等；失败仅记录）。

    下载安全：URL 经 `_validate_url`（公网 http/https），重定向逐跳复检；
    大小上限 `_MAX_DOWNLOAD_BYTES`，流式写临时文件后原子改名。
    """
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
            pdf_url = _validate_url(spec.value)
            digest = hashlib.sha1(spec.value.encode("utf-8")).hexdigest()[:10]
            filename = _safe_filename(spec.value, f"source-{digest}.pdf")

        target = dest_dir / filename
        result.pdf_url = pdf_url
        result.filename = filename
        if target.exists() and target.stat().st_size > 0:
            result.ok = True
            result.status = "cached"
            result.size_bytes = target.stat().st_size
            return result

        url = pdf_url
        for _hop in range(_MAX_REDIRECTS + 1):
            async with client.stream("GET", url) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        raise ValueError(f"重定向缺少 Location 头（{resp.status_code}）")
                    url = _validate_url(urljoin(url, location))
                    continue
                resp.raise_for_status()
                content_length = resp.headers.get("content-length")
                if content_length and int(content_length) > _MAX_DOWNLOAD_BYTES:
                    raise ValueError(
                        f"文件过大（{int(content_length) // 1024 // 1024}MB > {_MAX_DOWNLOAD_BYTES // 1024 // 1024}MB 上限）"
                    )
                head = b""
                total = 0
                tmp_path = dest_dir / f".{filename}.part"
                try:
                    with open(tmp_path, "wb") as tmp:
                        async for chunk in resp.aiter_bytes():
                            total += len(chunk)
                            if total > _MAX_DOWNLOAD_BYTES:
                                raise ValueError(
                                    f"下载超过大小上限（{_MAX_DOWNLOAD_BYTES // 1024 // 1024}MB），已中止"
                                )
                            if len(head) < 1024:
                                head += chunk[: 1024 - len(head)]
                            tmp.write(chunk)
                    if total == 0:
                        raise ValueError("下载内容为空")
                    suffix = _sniff_suffix(head, filename)
                    if Path(filename).suffix.lower() != suffix:
                        filename = f"{Path(filename).stem}{suffix}"
                        target = dest_dir / filename
                        result.filename = filename
                    os.replace(tmp_path, target)
                except Exception:
                    tmp_path.unlink(missing_ok=True)
                    raise
                break
        else:
            raise ValueError(f"重定向次数超过 {_MAX_REDIRECTS} 次，已中止")

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
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        results = [await resolve_one(s, staged_dir, client) for s in specs]
    report = RemoteResolveReport(staged_dir=str(staged_dir), results=results)
    if report.ok_count == 0:
        raise ValueError(
            "远程源全部解析失败：\n" + "\n".join(f"  - {f}" for f in report.failures)
        )
    return report
