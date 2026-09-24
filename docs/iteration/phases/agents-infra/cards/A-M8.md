# A-M8 **main 补齐 windows 历史分叉**（Sprint-9 二查 011 发现）：`paper-qa-scrip

- `card`: A-M8
- 索引: [../backlog.MD](../backlog.MD)

## 状态
✅ 完成

## 规模
3

## 来源
Sprint-9 三查（2026-08-30）

## Sprint
Sprint-10（US-10.2，2026-08-31）：双向差分核查（三点差分为合并基假象）→ 真实分叉仅 5 文件 → PR #35 合并 602e855 后仅余 4 个 mac .sh（有意分叉）

## 正文
**main 补齐 windows 历史分叉**（Sprint-9 二查 011 发现）：`paper-qa-script/app/*.py`、`provider_config.py`、`verify/verify_remote_e2e.py` 等核心代码在 windows↔main 存在既存分叉（历史工作项同步遗漏，非 Sprint-9 引入），需专项 PR 按工作项补齐（mac 分支以 main 为源）
