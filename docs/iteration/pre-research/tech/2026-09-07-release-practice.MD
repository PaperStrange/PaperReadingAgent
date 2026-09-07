# 预研笔记：GitHub Releases 发版实践（release-practice）

> 状态：**探讨中，未开卡**（2026-09-07）。本笔记是未来「首次发版 v1.0.0」工作项的强制上下文输入（planning 时按 §4.4 注入）。
> 归属：`docs/iteration/pre-research/tech/`（仅 windows 分支维护）。

## 1. 背景与用户关切

- 用户（2026-09-07）：下一步排期按"验收修复 → 数据+成本 → 发版"推进；希望先讨论发版内容。
- 参考案例（用户提供）：[Hoshi-Reader-Android](https://github.com/HuangAntimony/Hoshi-Reader-Android)——GitHub 上每个版本都有打包文件与详细版本说明，值得调研参考。

## 2. 参考案例观察（2026-09-07 实测其 Releases）

| 维度 | Hoshi Reader 做法 |
|---|---|
| Tag | 纯语义化 `v1.3.3`（无日期前缀） |
| Release 标题 | `Hoshi Reader v1.3.3` |
| 产物（assets） | 按 ABI 命名的 APK（`Hoshi-Reader-v1.3.3-arm64-v8a.apk` 等）+ LICENSE 文件——**用户直接下载即用** |
| 版本说明 | 英文、`### Added / Changed / Fixed` 三组、逐条具体（每条说明改了什么、为什么用户在意），800~2300 字 |
| 节奏 | 小步高频发版（v1.3.1→v1.3.3 间隔短），无 pre-release 标记 |

## 3. 业界最佳实践对照（来源见 §6）

- **语义化版本**：`vX.Y.Z`（major.breaking / minor.feature / patch.fix）——业界主流（[SemVer](https://semver.org/)；Hoshi/绝大多数项目采用）。
- **版本说明结构**：Keep a Changelog 六组（Added/Changed/Deprecated/Removed/Fixed/Security）+ 顶部「Unreleased」段（[keepachangelog.com](https://keepachangelog.com/)）；Hoshi 简化为三组，适合发布节奏快的项目。
- **自动化**：release-please（conventional commits → 自动 changelog + 版本号，[caddy-labels 案例](https://github.com/cpritchett/caddy-labels/pull/37)）；tag 触发构建 workflow 自动产出打包文件（[localsend release.yml](https://github.com/localsend/localsend/blob/6279d3e3/.github/workflows/release.yml)）。
- **产物形态**：直接可运行的二进制/安装包优先于源码包（用户零门槛）。

## 4. 我们项目的决策点（待用户拍板）

### D1 版本号格式（冲突点）
- 现状（`docs/5-VERSIONS.MD`）：`年.月.日-vR.R.R`（日期前缀，如 `2026.08.30-v1.0.0`）——与按 sprint 日期的节奏贴合，但**非主流**（SemVer 无日期段，工具链兼容差）。
- 选项：A=保留现状；B=改纯 `v1.0.0` 语义化（与 Hoshi/主流一致，日期信息放 Release 说明里）。

### D2 发布产物形态（最大决策点）
- 现状：项目 = 前端 npm build + FastAPI 后端 + .venv 依赖 + 数据目录，**无打包管线**。
- 选项：
  - ① 源码包（zip/tar.gz 自动生成）+ 部署脚本 + 详细安装说明（务实起点，门槛高）；
  - ② Windows 免安装包（PyInstaller 打后端 + 前端静态文件 + 启动器 .bat → zip）——用户解压即用；
  - ③ 安装器（Inno Setup/NSIS）——体验最好，工程量最大；
  - 建议：首发 ①+② 组合（源码包保底 + 免安装包给 Windows 用户），③ 作为后续优化。

### D3 版本说明模板
- 建议：**中文**、五组（新增/修复/优化/已知限制/验证记录），逐条具体 + 底部引用 `5-VERSIONS.MD` 对应行与三查结论；比 Hoshi 多「验证记录」一组（呼应我们"结论来自可复现证据"文化）。

### D4 首发形态与节奏
- 建议：首个版本发 **pre-release（如 v1.0.0-rc1）** 收集你的验收反馈 → 稳定后转正式 v1.0.0；此后小步高频（每次 sprint 关闭后若有用户可见变化即发 patch/minor）。

### D5 tag 与自动化
- 现状约定：tag 打在 windows 同步进 main 的合并提交上（5-VERSIONS §1）。✓ 保持。
- 自动化：手动 `gh release create`（或扩展 github-pr.ps1 加 release 子命令）+ 可选 tag 触发构建 workflow 自动打产物（D2 选 ②/③ 时值得做）。

## 5. 用户决策记录（chronological）

| 时间 | 决策 |
|---|---|
| 2026-09-07 | 排期定稿：Sprint-15（验收修复交互类+TG-3）→ Sprint-16（数据+成本）→ 发版讨论 |
| 2026-09-07 | 提出发版参考案例（Hoshi-Reader-Android），要求调研最佳实践一起探讨 |

## 6. 来源

- [Hoshi-Reader-Android Releases（API 实测）](https://github.com/HuangAntimony/Hoshi-Reader-Android/releases)
- [SemVer](https://semver.org/) / [Keep a Changelog](https://keepachangelog.com/)
- [release-please 自动化案例](https://github.com/cpritchett/caddy-labels/pull/37)
- [localsend 自动发布 workflow](https://github.com/localsend/localsend/blob/6279d3e3/.github/workflows/release.yml)
- [VERSIONING_POLICY 范例](https://github.com/RedRing2020/RedRing/blob/develop/VERSIONING_POLICY.md)

## 7. 注入指引（供 planning_pipeline / tech-research）

- 命中关键词：发版 / GitHub Releases / 版本号规范 / 产物打包 / release notes / v1.0.0
- 开卡时本笔记为基线：D1~D5 已拍板项不得重议（翻案建议除外）；未拍板项由开卡后的 tech-research 深化（如 D2 打包方案选型对比）。
