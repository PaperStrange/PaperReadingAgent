# A-M9 better-sqlite3 选型（Sprint-10 US-10.4，tech-research 调研定论）：**维持

- `card`: A-M9
- 索引: [../backlog.MD](../backlog.MD)

## 状态
✅ 完成

## 规模
1

## 来源
—

## Sprint
Sprint-10（2026-08-31；调研报告 agents/runs/run-2026-08-31-tech-research-014/）

## 正文
better-sqlite3 选型（Sprint-10 US-10.4，tech-research 调研定论）：**维持 v13.0.3**——v13 无 install script、N-API 预编译随包分发（ABI 无关，覆盖 win32/darwin/linux），安装零工具链；`--ignore-scripts` 为防御性空操作保留；翻案条件（迁 node:sqlite 需 Node≥22.16/≥24 LTS + Stability 2.0 + FTS5 等价实测三条件齐备；降级 v12 永不）
