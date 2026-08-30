# agents-dashboard —— AgentOps 本地看板（阶段 3 交付物）

> **定位**：`agents/` 的图形化视图层——展示多子代理 runtime 账本（状态/自报上下文/估算成本）、浏览报告存档、在线编辑职能 spec（含 skill URL 配置）。文件为真相源，SQLite 仅为派生只读索引。
> 设计决策见 `docs/iteration/phases/agents-infra/architecture.MD`（仅 windows 分支，§2.2 技术栈、§3.2 账本模型、§6 阶段 3 验收）。

## 1. 技术栈与运行

- **栈**：Next.js 16（App Router）+ antd 6.6.2（Ant Design，AntdRegistry + zhCN，简约风）+ better-sqlite3（FTS5）+ chokidar。Tailwind/shadcn 未采用的原因见 `docs/antd-reference.md`（antd v6 与 Tailwind v4 CSS 变量冲突，issue #56015）。
- **启动**（生产模式，演示/验收推荐；仅绑定 127.0.0.1 回环）：
  ```powershell
  .\scripts\start-agents-dashboard.ps1        # Windows 一键（npm ci → build → next start -H 127.0.0.1 -p 8600）
  # 跨平台等价：
  cd agents-dashboard; npm run build; npx next start -H 127.0.0.1 -p 8600
  ```
- **数据源**：`AGENT_OPS_DIR` 环境变量（默认仓库根 `agents/`）指向账本目录；运行数据写入 `agents-dashboard/data/ledger.db`（gitignore，可随时删除重建）。

## 2. 目录结构

```
agents-dashboard/
├── app/
│   ├── page.tsx                    # 概览页：状态卡片 + 账本列表（检索/过滤）
│   ├── specs/page.tsx              # spec 编辑页（直写 agents/functions/*.md）
│   ├── costs/page.tsx              # 成本页（CNY 合计 + 各模型 cost + pending 标注 + 上下文占用）
│   ├── runs/[id]/page.tsx          # 单条 run 详情（描述 + 报告全文，表格行点击进入）
│   ├── components/DonutChart.tsx   # 零依赖 SVG 环形图（状态/职能分布）
│   ├── layout.tsx                  # AntdRegistry + ConfigProvider(zhCN) + App 根布局
│   ├── globals.css                 # 最小全局样式（antd reset 由 registry 接管）
│   └── api/                        # 只读为主；spec 写入走 PUT
│       ├── health/                 # GET 健康 + 触发重索引
│       ├── runs/  runs/[id]/       # 账本列表（q/role/status/limit/offset）+ 单条详情
│       ├── aggregates/             # 汇总（总数/状态/职能/累计成本/pending_price）
│       └── specs/  specs/[name]/  specs/validate/   # 列表 / 读取 / 保存 / CLI 校验
├── lib/db.ts                       # SQLite schema + FTS5 + chokidar 增量索引（文件→库）
├── docs/antd-reference.md          # antd 官方资料本地存档（changelog/migration/use-with-next）
└── scripts/test-spec-roundtrip.mjs # spec 保存往返测试（UTF-8 安全）
```

## 3. API 速查

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/health` | GET | `{ok, runs, indexed_at}`；每次调用前重索引（文件真相源优先） |
| `/api/runs?q=&role=&status=&limit=&offset=` | GET | FTS5 全文检索（短语查询，兼容 `code-review` 连字符）+ 过滤 |
| `/api/runs/:id` | GET | 单条 run + 报告全文（report_body） |
| `/api/aggregates` | GET | 汇总指标（成本含 `pending_price` 提示） |
| `/api/specs` | GET/PUT | 列表 / **保存（直写文件，白名单校验 + 路径越界防护）** |
| `/api/specs/:name` | GET | 读取 spec 内容（仅 *.md，无扩展名自动补） |
| `/api/specs/validate` | POST | 调 `scripts/agent-ops.py validate-spec` 校验所见内容 |

## 4. 与项目其它部分的关系

| 对象 | 关系 |
|---|---|
| `agents/functions/*.md` | **真相源**：看板编辑 = 直写这些文件；spec 参数节即编辑点 |
| `agents/runtime/registry.json` + `agents/runs/` | 账本源（gitignore 本地留证）；chokidar 监听变更 → SQLite 增量 upsert（≤30s） |
| `scripts/agent-ops.py` | 账本 CLI：看板的 validate 按钮复用其 `validate-spec` |
| `verify/gui_check_dashboard*.mjs` | 看板截图/验收脚本（playwright 取 reactflow frontend 的 node_modules） |

## 5. 已知边界（如实记录）

- **仅回环 + 无鉴权**：`next start` 固定 `-H 127.0.0.1`（start 脚本与跨平台命令均如此），spec 写端点不鉴权——本机信任模型，与后端/前端同约定，不对外网暴露。若需局域网访问，请自行加反向代理鉴权。
- **dev 模式静态 chunk 403**：Next 16 dev 长时间热更新后 `/_next/static/chunks` 可能 403（客户端 JS 加载失败）→ 重启 dev 或改用**生产构建**（演示/验收已切换生产）。
- **成本为自报+估算口径**：`pending_price` 表示该模型无单价（deepseek/qwen/openrouter 待人工填 `agents/runtime/prices.json` manual 段）；成本单位 CNY（USD 单价 × `meta.fx_usd_cny`），精确账单以服务商后台为准。
- **防双写边界**：看板只写 spec 文件；账本记录只经 agent-ops CLI 追加（registry 带完整性校验）。
