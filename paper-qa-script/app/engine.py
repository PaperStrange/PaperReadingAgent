"""引擎适配层（Sprint-2 US-2.5，refactor-analysis.MD 主题 E1/E2）。

- `EngineAdapter`：对 paperqa 引擎能力的抽象接口（config/index/query/add_doc/evidence/answer/run_agent/version）。
  上层编排只依赖本接口，不直接 import paperqa 内部实现 —— 为 vendor 切换、版本检查/回滚留出接缝。
- `LocalVendorAdapter`：包住现有 paperqa 调用的本地实现，**逐调用原样透传**（行为不变原则），
  包括 `make_settings`（即原 `main.build_settings` 的逐字迁移，含 provider_config 组合与环境变量副作用）。
- 默认实例 `ENGINE`：全局单例（只读使用），后续可改为 DI 注入（US-2.2 编排层决定注入方式）。
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import paperqa
from paperqa import Docs, Settings
from paperqa.agents.search import get_directory_index
from paperqa.settings import AgentSettings, IndexSettings, ParsingSettings

from provider_config import get_provider_config


class EngineAdapter(ABC):
    """paperqa 引擎能力抽象。方法签名与语义对齐 paperqa 调用（详见各方法 docstring）。"""

    @property
    @abstractmethod
    def version(self) -> str:
        """引擎（paperqa）版本号。"""
        ...

    @abstractmethod
    def make_settings(self, params: dict[str, Any]) -> Settings:
        """config：由前端参数 + provider 配置组合出 paperqa Settings（原 build_settings）。"""
        ...

    @abstractmethod
    async def get_directory_index(self, settings: Settings, build: bool) -> Any:
        """index：获取/构建目录索引（paperqa SearchIndex）。"""
        ...

    @abstractmethod
    async def query_index(self, search_index: Any, query: str, top_n: int) -> Any:
        """query：检索，返回 paperqa 原始结果（(score, path) 元组列表，keep_filenames=True）。"""
        ...

    @abstractmethod
    def new_docs(self) -> Docs:
        """新建空 Docs 容器。"""
        ...

    @abstractmethod
    async def add_doc(self, docs: Docs, path: str, settings: Settings) -> str:
        """add_doc：解析并向量化一个文件，返回 docname。"""
        ...

    @abstractmethod
    async def get_evidence(self, docs: Docs, question: str, settings: Settings) -> Any:
        """evidence：对 docs 做证据检索，返回 paperqa EvidenceResult。"""
        ...

    @abstractmethod
    async def query_answer(self, docs: Docs, evidence_session: Any, settings: Settings) -> Any:
        """answer：基于证据会话生成答案，返回 paperqa AnswerSession 对象。"""
        ...

    @abstractmethod
    async def run_agent(
        self,
        query: str,
        settings: Settings,
        docs: Docs | None = None,
        agent_type: Any = None,
        **kwargs: Any,
    ) -> Any:
        """run_agent：Agent 模式提问（当前后端未接线，接口预留）。"""
        ...


class LocalVendorAdapter(EngineAdapter):
    """本地 vendor（当前 paperqa 版本）实现：原样透传现有调用。"""

    @property
    def version(self) -> str:
        return paperqa.__version__

    def make_settings(self, params: dict[str, Any]) -> Settings:
        # 统一服务商切换：provider 参数 / PAPERQA_PROVIDER 环境变量；显式参数仍可覆盖
        provider_cfg = get_provider_config(params.get("provider"))

        api_key = params.get("api_key") or os.getenv("OPENAI_API_KEY") or provider_cfg["api_key"]
        api_base = params.get("api_base") or provider_cfg["api_base"]
        model = params.get("model") or provider_cfg["model"]
        vision_model = provider_cfg["vision_model"]
        embedding_model = params.get("embedding_model") or provider_cfg["embedding"]
        embedding_local = bool(provider_cfg["embedding_local"]) and embedding_model.startswith("st-")
        temperature = float(params.get("temperature", 0.1))
        paper_dir = str(Path(params.get("paper_directory", "./data/pdf")).expanduser())
        index_name = params.get("index_name", "debug_index")
        embedding_batch_size = int(params.get("embedding_batch_size", 10))
        chunk_chars = int(params.get("chunk_chars", 5000))
        chunk_overlap = int(params.get("chunk_overlap", 250))

        if not api_key:
            raise ValueError("api_key is required（请在 .env 或环境变量设置对应服务商的 Key）")

        os.environ["OPENAI_API_KEY"] = api_key

        def _litellm_params(model_name: str, temp: float | None = None) -> dict[str, Any]:
            p: dict[str, Any] = {"model": model_name, "api_key": api_key}
            if api_base:
                p["api_base"] = api_base
            if temp is not None:
                p["temperature"] = temp
            if provider_cfg.get("thinking_disabled"):
                # DeepSeek 思考模式需关闭以支持多轮工具调用（litellm 用 extra_body 透传）
                p["extra_body"] = {"thinking": {"type": "disabled"}}
            return p

        llm_config = {
            "name": model,
            "model_list": [
                {"model_name": model, "litellm_params": _litellm_params(model, temperature)}
            ],
        }
        vision_config = {
            "name": vision_model,
            "model_list": [
                {"model_name": vision_model, "litellm_params": _litellm_params(vision_model)}
            ],
        }
        embedding_config = {
            "name": embedding_model,
            "model_list": [
                {"model_name": embedding_model, "litellm_params": _litellm_params(embedding_model)}
            ],
            "batch_size": embedding_batch_size,
        }

        return Settings(
            llm=model,
            llm_config=llm_config,
            summary_llm=vision_model,
            summary_llm_config=vision_config,
            embedding=embedding_model,
            embedding_config=(
                {"batch_size": embedding_batch_size} if embedding_local else embedding_config
            ),
            parsing=ParsingSettings(
                use_doc_details=bool(params.get("use_doc_details", False)),
                reader_config={
                    "chunk_chars": max(200, chunk_chars),
                    "overlap": max(0, chunk_overlap),
                },
                enrichment_llm=vision_model,
                enrichment_llm_config=vision_config,
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

    async def get_directory_index(self, settings: Settings, build: bool) -> Any:
        return await get_directory_index(settings=settings, build=build)

    async def query_index(self, search_index: Any, query: str, top_n: int) -> Any:
        return await search_index.query(query, top_n=top_n, keep_filenames=True)

    def new_docs(self) -> Docs:
        return Docs()

    async def add_doc(self, docs: Docs, path: str, settings: Settings) -> str:
        return await docs.aadd(path=path, settings=settings)

    async def get_evidence(self, docs: Docs, question: str, settings: Settings) -> Any:
        return await docs.aget_evidence(question, settings=settings)

    async def query_answer(self, docs: Docs, evidence_session: Any, settings: Settings) -> Any:
        return await docs.aquery(evidence_session, settings=settings)

    async def run_agent(
        self,
        query: str,
        settings: Settings,
        docs: Docs | None = None,
        agent_type: Any = None,
        **kwargs: Any,
    ) -> Any:
        from paperqa.agents.main import agent_query

        if agent_type is not None:
            kwargs["agent_type"] = agent_type
        return await agent_query(query=query, settings=settings, docs=docs, **kwargs)


# 全局默认实例（后续编排层 DI 注入）
ENGINE: EngineAdapter = LocalVendorAdapter()
