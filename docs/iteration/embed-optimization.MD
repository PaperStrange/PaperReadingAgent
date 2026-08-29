# parse_chunk_embed 提速分析（③C 探索项）

> 归属：`docs/iteration/`（迭代中的增量项目文档）。本文档**只做分析，不落地实现**，
> 供后续 sprint 评估「预分割 文本/图片/表格/公式」加速方案。

## 现状：parse_chunk_embed 为什么慢

实测（单篇 PaperQA2.pdf，25 页，DeepSeek 供应商，`multimodal` 默认 `ON_WITH_ENRICHMENT`）：**约 27s / 23 个 text**。

耗时构成（按成本从大到小）：

| 环节 | 说明 | 是否大头 |
|---|---|---|
| **图片增强 enrichment** | 每张从 PDF 提取的图片都会发给 DeepSeek 视觉模型 `deepseek-v4-flash-vision-exp` 生成描述；该模型是**推理模型**，单次调用较慢且并行度受限 | ✅ 主导 |
| PDF 解析 | PyMuPDF 解析 + 切分文本，快 | 否 |
| Citation 推测 | `Docs.aadd` 先 peek 首块 + 1 次 LLM 调用生成引用 | 少量 |
| 向量化 | 本地 `st-multi-qa-MiniLM-L6-cos-v1`，本地推理，快 | 否 |

> 结论：慢在**图片增强的视觉模型串行调用**，而非解析或向量化。

## 预分割（区分 文本/图片/表格/公式）能否加速——可行性分析

**能，且方向是对的。** 理由：

1. **媒体已经可分离**：paperqa readers（pypdf/pymupdf）在切块时已把图片作为 `media` 列表挂到对应 chunk（`runtime_trace` 的 `_make_chunk` 载荷里的 `media_count`、`first_media_url` 可见）。所以「图片与其他内容区分」这一步**已有基础设施**。

2. **表格/公式的识别**：pymupdf 提供页面布局；`pymupdf_layout` 可改善排版分析。表格/公式通常以「图片或排版块」形式存在，可在解析阶段做启发式分类。

**可落地的加速方向（按性价比）**：

| 方向 | 收益 | 成本/风险 |
|---|---|---|
| ① `parsing.multimodal=False`（跳过图片增强） | 最大，几乎消除视觉调用，可能从 27s 降到几秒 | 丢失图片/图表语义描述，回答「看图」类问题变弱 |
| ② 预分割后**只对图片/表格调用视觉模型**，文本纯本地 | 中，去掉无关视觉调用 | 需自实现「chunk→media 归类」，复用已有 `media` 列表即可 |
| ③ 改用**非推理**视觉模型 / 降低图片分辨率 / 批量化 | 中 | 依赖服务商可用模型（DashScope qwen-omni 已支持图片） |
| ④ **懒增强**：先按文本建立索引，问答命中某 chunk 的图片时才增强 | 中-高（只增强被用到的图） | 需改 paperqa 的 enrichment 触发时机，改动较大 |
| ⑤ 缓存增强结果（按图片 hash） | 中，重复解析/问答时不重复增强 | 需按图片内容 hash 建缓存 |

> 建议：本轮**先落地 ①/②/③ 的可配置开关**（例如在 `ParsingSettings` 暴露 `multimodal` 与增强模型选择），
> 并把「增强结果缓存（按图片 hash）」作为下个 sprint 的候选 Backlog 项。

## 是否影响功能

- 关闭/预分割只影响「图片内容参与回答」的丰富度，**不破坏**文字问答主流程（离线冒烟 8/8、全链路问答均通过）。
- 若需保留图片语义，优先选 **③（换更快的视觉模型/降分辨率）+ ⑤（缓存）**，而非完全关闭。

## 相关
- `docs/2-ARCHITECTURE.MD`（multimodal / enrichment 配置在 `app/engine.py::make_settings`——即原 `main.build_settings`；parse_chunk_embed 步骤与 embed 缓存在 `app/orchestration.py`，Sprint-2 解耦后迁移）
- Sprint 记录：`docs/iteration/sprint/2026-08-26-sprint-1.md`
