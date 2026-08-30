"""Embedding 默认推荐器（能力：选 provider 自动定 embedding，均可手动覆盖）。

分层设计（与需求方对齐的"混合分层"方案）：
- `EmbeddingRecommender` 接口：代码实现智能默认的接缝，未来 E3 可把"推荐"替换为
  agent workflow 步骤（agent 调同一组工具/数据源，输出建议+理由，经用户 review 写入配置）。
- `DefaultEmbeddingRecommender`（本实现）：
  1. provider 有 embedding API（`provider_config.has_embedding_api`）→ 用服务商**最新策展**模型；
  2. 无 API → 选 HuggingFace **下载量最高 + 兼容中文**的 SentenceTransformer 模型
     （在线查询 `huggingface.co/api/models?filter=sentence-transformers&sort=downloads`，
     按"multilingual / 已知中文模型"规则过滤取第一个；TTL 缓存 24h，离线/超时回落策展兜底）。
- 结果与理由通过 `config_notes.hints` 展示给前端，用户可随时用 `embedding_model` 手动覆盖。
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

import httpx
from pydantic import BaseModel

from provider_config import get_provider_config

_HF_API = "https://huggingface.co/api/models"
_CACHE_PATH = Path.home() / ".pqa" / "hf_embedding_top_cache.json"
_CACHE_TTL_S = 24 * 3600
_TIMEOUT = 6.0
# 已知"兼容中文"的 HF 模型名（含中文/多语言）；multilingual 为规则通配
_ZH_KNOWN_MODELS = {
    "BAAI/bge-m3", "BAAI/bge-small-zh-v1.5", "BAAI/bge-large-zh-v1.5",
    "shibing624/text2vec-base-chinese", "GanymedeNil/text2vec-large-chinese",
    "uer/sbert-base-chinese-nli",
}
# 兜底：多语言（含中文）、体积小、被广泛使用的模型
_FALLBACK_ST = "st-multi-qa-MiniLM-L6-cos-v1"


class EmbeddingRecommendation(BaseModel):
    """一次推荐结果（含理由，供 config_notes/前端展示与未来 agent 对齐）。"""

    model: str              # paperqa 完整名（st- 前缀或 API 名）
    source: str             # provider_curated | hf_top_multilingual | curated_fallback
    local: bool             # 是否本地 SentenceTransformer（st- 前缀）
    downloads: int | None = None
    reason: str = ""


class EmbeddingRecommender(ABC):
    """embedding 默认推荐接口。"""

    @abstractmethod
    async def recommend(self, provider: str | None) -> EmbeddingRecommendation:
        """按 provider 给出默认 embedding（不含用户显式指定场景）。"""


def _is_zh_compatible(model_id: str) -> bool:
    lowered = model_id.lower()
    return "multilingual" in lowered or model_id in _ZH_KNOWN_MODELS


def _read_cache() -> dict | None:
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        if time.time() - float(data.get("updated_at", 0)) < _CACHE_TTL_S:
            return data
    except Exception:
        pass
    return None


def _write_cache(model_id: str, downloads: int) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(
            json.dumps(
                {"model": model_id, "downloads": downloads, "updated_at": time.time()},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


async def _query_hf_top_multilingual() -> tuple[str, int] | None:
    """在线查询 HF 下载量最高的"兼容中文"ST 模型；失败返回 None（回落兜底）。"""
    if os.environ.get("PAPERQA_EMBED_RECOMMEND_LIVE", "1") == "0":
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = await client.get(
                _HF_API,
                params={"filter": "sentence-transformers", "sort": "downloads",
                        "direction": -1, "limit": 50},
            )
            r.raise_for_status()
            for item in r.json():
                model_id = str(item.get("id", ""))
                if _is_zh_compatible(model_id):
                    return model_id, int(item.get("downloads") or 0)
    except Exception:
        pass
    return None


class DefaultEmbeddingRecommender(EmbeddingRecommender):
    """默认实现：服务商策展 → HF 在线热门（带缓存）→ 策展兜底。"""

    async def recommend(self, provider: str | None) -> EmbeddingRecommendation:
        cfg = get_provider_config(provider)
        if cfg.get("has_embedding_api"):
            model = cfg["embedding"]
            return EmbeddingRecommendation(
                model=model,
                source="provider_curated",
                local=model.startswith("st-"),
                reason=(
                    f"服务商 {cfg['provider']} 提供 embedding API，"
                    f"自动使用其最新策展模型 {model}（可手动指定 embedding_model 覆盖）"
                ),
            )

        # 无 embedding API → HF 热门多语言（含中文）模型，TTL 缓存 + 离线回落
        cached = _read_cache()
        if cached:
            model_id = cached["model"]
            return EmbeddingRecommendation(
                model=f"st-{model_id}",
                source="hf_top_multilingual",
                local=True,
                downloads=cached.get("downloads"),
                reason=(
                    f"服务商 {cfg['provider']} 无 embedding API：自动选择 HuggingFace "
                    f"下载量最高的多语言（含中文）模型 {model_id}（缓存于 {_CACHE_PATH}，"
                    "首次自动下载；可手动指定 embedding_model 覆盖）"
                ),
            )

        found = await _query_hf_top_multilingual()
        if found:
            model_id, downloads = found
            _write_cache(model_id, downloads)
            return EmbeddingRecommendation(
                model=f"st-{model_id}",
                source="hf_top_multilingual",
                local=True,
                downloads=downloads,
                reason=(
                    f"服务商 {cfg['provider']} 无 embedding API：自动选择 HuggingFace "
                    f"下载量最高的多语言（含中文）模型 {model_id}（{downloads:,} 次下载，"
                    "首次自动下载；可手动指定 embedding_model 覆盖）"
                ),
            )

        return EmbeddingRecommendation(
            model=_FALLBACK_ST,
            source="curated_fallback",
            local=True,
            reason=(
                f"服务商 {cfg['provider']} 无 embedding API，且 HF 在线查询不可用："
                f"回落策展兜底模型 {_FALLBACK_ST}（多语言含中文；可手动指定 embedding_model 覆盖）"
            ),
        )


# 组合根：编排层使用的默认实例（E3 可替换为 agent 实现）
RECOMMENDER: EmbeddingRecommender = DefaultEmbeddingRecommender()
