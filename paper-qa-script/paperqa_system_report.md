# PaperQA System Inventory

> Generated from vendored paperqa `2026.1.6.dev10+g36348d0ca`（`paper-qa/src/paperqa`；本报告为静态分析产物，生成于 macOS 移植期）

- Source root（Windows）: `paper-qa/src/paperqa`（原 macOS 路径：`/Volumes/Extreme SSD/vscode_projects/PaperReading/paper-qa/src/paperqa`）
- Total functions: **371**
- Top-level: **121** | Class methods: **233** | Nested: **17** | Async: **133**

## Key Entry Functions
- `agents.main:agent_query` `(query: str | MultipleChoiceQuestion, settings: Settings, docs: Docs | None=None, agent_type: str | type=DEFAULT_AGENT_TYPE, **runner_kwargs) -> AnswerResponse`
- `agents.main:run_agent` `(docs: Docs, query: str | MultipleChoiceQuestion, settings: Settings, agent_type: str | type=DEFAULT_AGENT_TYPE, **runner_kwargs) -> AnswerResponse`
  - doc: Run an agent.
- `agents.search:get_directory_index` `(settings: MaybeSettings=None, build: bool=True) -> SearchIndex`
  - doc: Create a Tantivy index by reading from a directory of text files.
- `docs:Docs.aadd` `(self, path: str | os.PathLike, citation: str | None=None, docname: str | None=None, dockey: DocKey | None=None, title: str | None=None, doi: str | None=None, authors: list[str] | None=None, settings: MaybeSettings=None, llm_model: LLMModel | None=None, embedding_model: EmbeddingModel | None=None, **kwargs) -> str | None`
  - doc: Add a document to the collection.
- `docs:Docs.aget_evidence` `(self, query: PQASession | str, settings: MaybeSettings=None, callbacks: Sequence[Callable] | None=None, embedding_model: EmbeddingModel | None=None, summary_llm_model: LLMModel | None=None, partitioning_fn: Callable[[Embeddable], int] | None=None) -> PQASession`
- `docs:Docs.aquery` `(self, query: PQASession | str, settings: MaybeSettings=None, callbacks: Sequence[Callable] | None=None, llm_model: LLMModel | None=None, summary_llm_model: LLMModel | None=None, embedding_model: EmbeddingModel | None=None, partitioning_fn: Callable[[Embeddable], int] | None=None) -> PQASession`
- `settings:Settings.get_llm` `(self) -> LiteLLMModel`
- `settings:Settings.get_summary_llm` `(self) -> LiteLLMModel`
- `settings:Settings.get_embedding_model` `(self) -> EmbeddingModel`

## Approximate Call Paths
### `agents.main:agent_query`
- agents.main:agent_query -> agents.main:run_agent -> agents.main:run_aviary_agent -> agents.main:_run_with_timeout_failure
- agents.main:agent_query -> agents.main:run_agent -> agents.main:run_fake_agent -> agents.helpers:litellm_get_search_query -> agents.helpers:get_year
- agents.main:agent_query -> agents.main:run_agent -> agents.main:run_fake_agent -> agents.main:_run_with_timeout_failure
- agents.main:agent_query -> agents.main:run_agent -> agents.main:run_ldp_agent -> agents.main:_run_with_timeout_failure
- agents.main:agent_query -> agents.main:run_agent -> agents.search:get_directory_index -> agents.search:_make_progress_bar_update -> agents.__init__:is_running_under_cli
- agents.main:agent_query -> agents.main:run_agent -> agents.search:get_directory_index -> agents.search:maybe_get_manifest
- agents.main:agent_query -> agents.main:run_agent -> agents.search:get_directory_index -> settings:get_settings
### `agents.search:get_directory_index`
- agents.search:get_directory_index -> agents.search:_make_progress_bar_update -> agents.__init__:is_running_under_cli
- agents.search:get_directory_index -> agents.search:maybe_get_manifest
- agents.search:get_directory_index -> settings:get_settings
### `docs:Docs.aquery`
- docs:Docs.aquery -> docs:Docs.aget_evidence -> core:map_fxn_summary -> core:_map_fxn_summary -> utils:extract_score
- docs:Docs.aquery -> docs:Docs.aget_evidence -> core:map_fxn_summary -> core:_map_fxn_summary -> utils:strip_citations
- docs:Docs.aquery -> docs:Docs.aget_evidence -> docs:Docs.retrieve_texts -> docs:Docs._build_texts_index
- docs:Docs.aquery -> docs:Docs.aget_evidence -> docs:Docs.retrieve_texts -> settings:get_settings
- docs:Docs.aquery -> docs:Docs.aget_evidence -> settings:get_settings
- docs:Docs.aquery -> settings:get_settings

## Notes
- Call paths are static approximations from AST, not runtime traces.
- Dynamic dispatch / external library callbacks are intentionally not expanded.
