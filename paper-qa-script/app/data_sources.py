"""数据源领域模型（Sprint-3 US-3.1，refactor-analysis.MD 主题 B）。

目标：把"数据源"从单一 `paper_directory` 假设解耦为多源描述：
- `local_dir`：本地论文目录（现状，默认）；
- `url` / `arxiv_id` / `doi`：远程源，由解析器（US-3.2）统一下载到 staging 目录后复用现有索引/解析管线。

本模块只含模型与纯校验（无网络/IO），供：
- `app/config_schema.py`（SSOT 扩展）引用类型定义；
- 编排层 load_index 步骤解析远程源前校验输入；
- 前端文档生成引用。
"""
from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$", re.IGNORECASE)
_DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$")
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


class SourceKind(StrEnum):
    """数据源类别。"""

    LOCAL_DIR = "local_dir"
    URL = "url"
    ARXIV_ID = "arxiv_id"
    DOI = "doi"


class SourceSpec(BaseModel):
    """单条数据源描述（解析器的最小输入单元）。"""

    kind: SourceKind
    value: str
    label: str | None = None  # 可选展示名（如 arXiv ID、文件名）


class RemoteSourceConfig(BaseModel):
    """远程源集合（前端表单逐行列表 → 结构化）。"""

    urls: list[str] = Field(default_factory=list)
    arxiv_ids: list[str] = Field(default_factory=list)
    dois: list[str] = Field(default_factory=list)

    def to_specs(self) -> list[SourceSpec]:
        specs: list[SourceSpec] = []
        specs.extend(SourceSpec(kind=SourceKind.URL, value=u) for u in self.urls)
        specs.extend(SourceSpec(kind=SourceKind.ARXIV_ID, value=a) for a in self.arxiv_ids)
        specs.extend(SourceSpec(kind=SourceKind.DOI, value=d) for d in self.dois)
        return specs

    def is_empty(self) -> bool:
        return not (self.urls or self.arxiv_ids or self.dois)


def parse_remote_sources(params: dict) -> RemoteSourceConfig:
    """从配置参数解析远程源（兼容 str/list 输入；空字符串视为空）。"""
    def _as_list(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            # 换行/逗号/分号分隔均可
            parts = re.split(r"[\n,;]+", value)
        elif isinstance(value, (list, tuple)):
            parts = [str(v) for v in value]
        else:
            return []
        return [p.strip() for p in parts if p and p.strip()]

    return RemoteSourceConfig(
        urls=_as_list(params.get("source_urls")),
        arxiv_ids=_as_list(params.get("source_arxiv_ids")),
        dois=_as_list(params.get("source_dois")),
    )


def validate_source_specs(specs: list[SourceSpec]) -> list[str]:
    """返回用户友好的中文错误列表（空列表 = 全部合法）。"""
    errors: list[str] = []
    for spec in specs:
        value = spec.value.strip()
        if spec.kind == SourceKind.URL:
            if not _URL_RE.match(value):
                errors.append(f"URL 非法（需 http/https 开头）：{value!r}")
        elif spec.kind == SourceKind.ARXIV_ID:
            if not _ARXIV_ID_RE.match(value):
                errors.append(
                    f"arXiv ID 非法（形如 2409.13740 或 2409.13740v2）：{value!r}"
                )
        elif spec.kind == SourceKind.DOI:
            if not _DOI_RE.match(value):
                errors.append(f"DOI 非法（形如 10.xxxx/yyyy）：{value!r}")
    return errors


def remote_staging_dir(index_name: str, base_dir: Path | None = None) -> Path:
    """远程源下载目录：默认 `<后端工作目录>/data/remote/<index_name>/`。"""
    if not index_name:
        index_name = "debug_index"
    # 索引名只作路径段：净化防穿越
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", index_name).strip("._") or "debug_index"
    return (base_dir or Path("data") / "remote") / safe_name
