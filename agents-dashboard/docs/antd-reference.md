# Ant Design 设计规范与集成参考（本地留档）

> 用途：agents-dashboard 的 UI 规范与组件使用依据（用户决策：2026-08-30 采用 Ant Design 设计规范和组件样式，US-9.7）。
> 版本锁定：**antd 6.6.2**（2026-08 官网最新 6.x）+ `@ant-design/nextjs-registry 1.3.0` + `@ant-design/icons`。

## 1. 官方来源（联网核实于 2026-08-30）

| 主题 | 链接 |
|---|---|
| antd 官网（组件/设计语言） | https://ant.design |
| 更新日志（6.x 最新版本） | https://ant.design/changelog |
| v5 → v6 迁移指南（breaking changes 依据） | https://ant.design/docs/react/migration-v6 |
| Next.js App Router 集成（SSR registry） | https://ant.design/docs/react/use-with-next |
| v6 与 Tailwind v4 样式冲突问题 | https://github.com/ant-design/ant-design/issues/56015 |

## 2. 设计规范要点（本项目采用）

- **设计语言**：Ant Design 设计体系——统一 8 栅格间距、圆角 6、中性色阶（#f0f0f0 边框 / #fff 卡片底 / 主色 #1677ff v6 默认）。
- **布局**：`Layout(Header+Sider+Content)` 管理壳；内容区 `Row/Col` 栅格（gutter 16）+ `Card` 承载指标与表格。
- **组件规范**：指标用 `Statistic`；数据表一律 `Table`（size=small、分页 showTotal、`rowKey` 必须显式）；状态徽标用 `Tag`（succeeded=success / failed=error / running=processing / queued=default / cancelled=warning）；筛选用 `Input.Search` + `Select`(allowClear)；反馈用 `Alert`/`App.useApp().message`。
- **字体与文案**：中文优先（`ConfigProvider locale=zh_CN`）；代码/ID 类用 `Typography.Text code`；辅助说明 `Typography.Text type=secondary`。
- **主题定制**：走 `ConfigProvider theme.token`（本项目暂用默认 token，后续如需品牌色在此统一改，不散落写死）。

## 3. Next.js 16 集成要点（本项目实操）

1. 依赖：`antd`、`@ant-design/nextjs-registry`、`@ant-design/icons`（icons 独立包）。
2. `app/layout.tsx`：`<AntdRegistry><ConfigProvider locale={zhCN}><App>{children}</App></ConfigProvider></AntdRegistry>`——SSR 样式注入靠 registry；`App` 包裹后才能用 `App.useApp()` 的 message/modal。
3. **与 Tailwind v4 不共存（本项目的取舍）**：antd v6 走 CSS variables，与 Tailwind v4 preflight 有样式冲突（issue #56015）；本看板已**移除 Tailwind**（删除 `@import "tailwindcss"`、`postcss.config.mjs` 与依赖），globals.css 仅留 reset 兜底——全站组件一律 antd，无 utility class。
4. 类型：antd v6 自带 TS 类型；`Table<RowType>` 泛型列定义。

## 4. 组件速查（本看板已用）

| 组件 | 用途 | 位置 |
|---|---|---|
| Layout / Header / Sider / Content | 页面壳 | app/page.tsx、app/specs/page.tsx |
| Statistic / Card / Row / Col | 概览指标卡 | app/page.tsx |
| Table + Tag + Input.Search + Select | 账本列表与过滤 | app/page.tsx |
| List / List.Item.Meta | spec 选择列表 | app/specs/page.tsx |
| Input.TextArea / Button / Alert / message | spec 编辑与校验反馈 | app/specs/page.tsx |

## 5. 升级注意

- 升级 antd 时先读 [migration 文档](https://ant.design/docs/react/migration-v6)；样式回归用 `verify/gui_check_dashboard*.mjs` 截图比对（本地留证）。
