# F-AC16 **checkpoint 可见性与可复现**：前端展示命中的 checkpoint 明细（`checkpoint_key

- `card`: F-AC16
- 索引: [../backlog.MD](../backlog.MD)

## 状态
**v1 ✅ 完成（2026-09-21）**；剩余增量待排期

## 规模
3

## 来源
**用户走查 2026-09-20（UTC+8）**：CK-1 存疑；**2026-09-21** 要求"第一版实现达到 Sprint-17 可做原型验证的可靠程度"

## Sprint
Sprint-16（走查追问 v1）

## 正文
`[用户插入]` **checkpoint 可见性与可复现**：前端展示命中的 checkpoint 明细（`checkpoint_key`/`manifest`/逐篇状态），支持按路径定位并用既有 checkpoint 复现——目的：pro 用户成本感知 + 单篇复现 + 幻觉核查

## 证据
**v1 证据**：`app/checkpoint_index.py`（只读，逐篇 `payload_path/payload_exists/payload_bytes`，坏件 fail-soft）+ `GET /api/checkpoints`（第 12 条路由）+ 前端 `CheckpointPanel.jsx`（工具按钮 → 命名空间 → 展开逐篇载荷路径可复制）；回归 `verify_checkpoint_index.py` **29 断言**（含路径穿越防护）+ `gui_check_fac16_checkpoint.mjs` **10 断言**（真实 15 命名空间、零成本）。**Sprint-17 原型候选（用户 2026-09-21：暂不动，待真实用户数据）**：① 一键"用该 checkpoint 重放"；② 按文献粒度成本展示
