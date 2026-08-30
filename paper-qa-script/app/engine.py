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

        def _as_float(key: str, default: float) -> float:
            try:
                return float(params.get(key, default))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"参数 {key} 应为数字，收到 {params.get(key)!r}") from exc

        def _as_int(key: str, default: int) -> int:
            try:
                return int(params.get(key, default))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"参数 {key} 应为整数，收到 {params.get(key)!r}") from exc

        api_key = params.get("api_key") or os.getenv("OPENAI_API_KEY") or provider_cfg["api_key"]
        api_base = params.get("api_base") or provider_cfg["api_base"]
        model = params.get("model") or provider_cfg["model"]
        # 视觉/增强模型可显式覆盖（默认随 provider；provider 未定义时回落 model）
        vision_model = (
            params.get("vision_model")
            or provider_cfg.get("vision_model")
            or model
        )
        embedding_model = params.get("embedding_model") or provider_cfg["embedding"]
        # st- 前缀 = 本地/远程 HuggingFace SentenceTransformer 模型（首次自动下载），
        # 不依赖 provider 是否有 embedding API；其它名走 litellm API（paperqa 约定）
        embedding_local = embedding_model.startswith("st-")
        temperature = _as_float("temperature", 0.1)
        index_name = params.get("index_name", "debug_index")
        data_source = (params.get("data_source") or "local").lower()
        if data_source == "remote":
            # US-3.3：remote 模式 -> 论文目录指向统一下载的 staging 目录（data/remote/<index_name>/）
            from app.data_sources import remote_staging_dir

            paper_dir = str(remote_staging_dir(index_name))
        else:
            paper_dir = str(Path(params.get("paper_directory", "./data/pdf")).expanduser())
        recurse_subdirectories = bool(params.get("recurse_subdirectories", True))
        manifest_file = params.get("manifest_file") or None
        embedding_batch_size = _as_int("embedding_batch_size", 10)
        chunk_chars = _as_int("chunk_chars", 5000)
        chunk_overlap = _as_int("chunk_overlap", 250)

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

        def _win_ready_path(p: Path) -> str:
            """Windows 长路径（>260 字符）需要 \\\\?\\ 前缀才能被 open 正常访问（Sprint-4 US-4.2）。"""
            resolved = str(p.resolve())
            if os.name == "nt" and not resolved.startswith("\\\\?\\"):
                resolved = "\\\\?\\" + resolved
            return resolved

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
                    paper_directory=_win_ready_path(Path(paper_dir)),
                    files_filter=lambda f: (
                        f.suffix in {".pdf", ".txt", ".md", ".html"}
                        # 跳过隐藏目录（如 .qoder/.git），避免索引无关文件
                        and not any(part.startswith(".") for part in f.parts)
                    ),
                    name=index_name,
                    manifest_file=manifest_file,
                    recurse_subdirectories=recurse_subdirectories,
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
