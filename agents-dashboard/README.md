# agents-dashboard —— AgentOps 本地看板

> **定位**：`agents/` 的图形化视图层——展示多子代理 runtime 账本（状态/自报上下文/估算成本）、浏览报告存档、在线编辑职能 spec（含 skill URL 配置）。文件为真相源，SQLite 仅为派生只读索引。
> 设计决策见 `docs/iteration/phases/agents-infra/architecture.MD`（仅 windows 分支）。

## 1. 技术栈

- Next.js 16（App Router）+ antd 6.6.2（AntdRegistry + zhCN）
- better-sqlite3（FTS5 全文检索；v13 起 N-API 预编译随包分发，安装无需本机编译工具链）
- chokidar（监听 `agents/` 文件变更 → SQLite 增量索引）
- 生产模式运行（`next build` + `next start`）

## 2. 启动步骤

**前置条件**：Node.js ≥ 22（npm 附带）；无需 Python/编译工具链。

**方式 A：Windows 一键脚本（推荐）**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-agents-dashboard.ps1
```

脚本自动完成：依赖安装（首次，`npm ci`）→ 生产构建 → 端口 8600 占用预检 → 启动（仅绑定 127.0.0.1 回环）。

**方式 B：手动（跨平台）**

```powershell
cd agents-dashboard
npm ci --ignore-scripts        # --ignore-scripts 为防御性开关（v13 无 install script，见 §6）
npm run build
npx next start -H 127.0.0.1 -p 8600
```

**访问与停止**：
- 浏览器打开 http://127.0.0.1:8600 （仅本机回环可访问）；
- 停止：终端 `Ctrl+C`；
- 端口被占用：一键脚本会给出占用 PID 提示；手动启动需先释放 8600 或换端口。

**数据源**：`AGENT_OPS_DIR` 环境变量指向账本目录（默认仓库根 `agents/`）；必须在 `agents-dashboard/` 目录下启动（或显式设置 `AGENT_OPS_DIR`），否则报错并给出提示。运行数据写入 `agents-dashboard/data/ledger.db`（gitignore，可随时删除重建）。

## 3. 目录结构

```
agents-dashboard/
├── app/
│   ├── page.tsx                    # 概览页：状态卡片 + 环形图 + 账本列表（检索/过滤）
│   ├── specs/page.tsx              # spec 编辑页（直写 agents/functions/*.md）
│   ├── costs/page.tsx              # 成本页（CNY 合计 + 各模型成本 + pending 标注 + 上下文占用）
│   ├── runs/[id]/page.tsx          # 单条 run 详情（元数据 + 报告全文）
│   ├── fanout/page.tsx             # fan-out 配置页（两条流水线可视化 + JSON 编辑器，直写 agents/fanout.json）
│   ├── components/DonutChart.tsx   # 零依赖 SVG 环形图（状态/职能分布）
│   ├── layout.tsx / globals.css    # AntdRegistry + ConfigProvider(zhCN) 根布局与最小全局样式
│   └── api/                        # health / runs / runs/[id] / aggregates / specs / specs/[name] / specs/validate / fanout
├── lib/db.ts                       # SQLite schema + FTS5 + chokidar 增量索引（文件→库）
├── docs/antd-reference.md          # antd 官方资料本地存档（changelog / migration-v6 / use-with-next）
├── scripts/test-spec-roundtrip.mjs # spec 保存往返测试（UTF-8 安全）
├── AGENTS.md / CLAUDE.md           # 见下
└── package.json / package-lock.json# 依赖与锁文件（resolved 全部为公共 npmjs registry）
```

**AGENTS.md 与 CLAUDE.md 是什么**：Next.js 16 脚手架自动生成的 AI 编码指引文件——`AGENTS.md` 提示"此版本 Next 与训练数据不同、改码前先读 `node_modules/next/dist/docs/`"；`CLAUDE.md` 仅一行 `@AGENTS.md` 引用它。二者由 `next dev` 自动写入/重建（来源：`node_modules/next/dist/server/lib/generate-agent-files.js`），**入库是为了保持工作树干净，删除会被 dev 重建，无需手动编辑**。

## 4. API 速查

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | `{ok, runs, indexed_at}`；调用前重索引（文件真相源优先） |
| `/api/runs?q=&role=&status=&limit=&offset=` | GET | FTS5 全文检索（短语查询，兼容 `code-review` 连字符）+ 过滤 |
| `/api/runs/:id` | GET | 单条 run + 报告全文（report_body） |
| `/api/aggregates` | GET | 汇总指标（总数/状态/职能/累计成本/pending_price） |
| `/api/specs` | GET/PUT | 列表 / 保存（直写文件，白名单校验 + 路径越界防护） |
| `/api/specs/:name` | GET | 读取 spec 内容（仅 *.md，无扩展名自动补） |
| `/api/specs/validate` | POST | 调 `scripts/agent-ops.py validate-spec` 校验所见内容 |
| `/api/fanout` | GET/PUT | 读取 / 保存 `agents/fanout.json`（结构校验：两条流水线 + 每步必备字段 + order 连续） |

## 5. 与项目其它部分的关系

| 对象 | 关系 |
|---|---|
| `agents/functions/*.md` | **真相源**：看板编辑 = 直写这些文件；spec 参数节即编辑点 |
| `agents/fanout.json` | fan-out 流程配置（planning 调研前置 + 关闭五步），`/fanout` 页直写；下一轮流程按保存后的配置执行 |
| `agents/runtime/registry.json` + `agents/runs/` | 账本源（gitignore 本地留证）；chokidar 监听变更 → SQLite 增量 upsert |
| `scripts/agent-ops.py` | 账本 CLI：看板的 validate 按钮复用其 `validate-spec` |
| `verify/gui_check_dashboard*.mjs` | 看板截图/验收脚本 |

## 6. 已知边界与故障排查

- **仅回环 + 无鉴权**：`next start` 固定 `-H 127.0.0.1`（一键脚本与手动命令一致），spec 与 fan-out 写端点不鉴权——本机信任模型，不对外网暴露；如需局域网访问请自行加反向代理鉴权。
- **端口 8600 被占**：一键脚本会提示占用 PID；先结束旧实例或手动换端口。
- **`AGENT_OPS_DIR 不存在` 报错**：说明未在 `agents-dashboard/` 目录下启动，或 `AGENT_OPS_DIR` 指向了不存在路径。
- **dev 模式静态 chunk 403**：Next 16 dev 长时间热更新后 `/_next/static/chunks` 可能 403 → 使用生产构建（本 README 两种方式均为生产模式）。
- **成本口径**：`pending_price` = 该模型无单价（deepseek/qwen/openrouter 待人工填 `agents/runtime/prices.json` manual 段）；成本单位 CNY（USD 单价 × `meta.fx_usd_cny`），自报+估算口径，精确账单以服务商后台为准。
- **防双写**：看板只写 spec 文件；账本记录只经 agent-ops CLI 追加（registry 带完整性校验）。
- **依赖锁文件**：`package-lock.json` 所有 `resolved` 均指向公共 npmjs registry，无内部源/凭证（评审检查项，见 `agents/functions/code-review.md`）；better-sqlite3 v13 无 install script、N-API 预编译随包分发（`prebuilds/`，ABI 无关、覆盖 win32/darwin/linux），安装无需编译工具链；CI 的 `--ignore-scripts` 为防御性空操作（选型调研见 3-LEARNED 1.31 与 `agents/runs/run-2026-08-31-tech-research-014/`）。
