# 报价表多档（高峰／空闲）· 独立 spec — 2026-09-26

> **定位**：本文件是"**价表多档 + 按时段计价**"的**唯一设计真源**。
> 数据落点 = `agents/runtime/prices.json::scraped.deepseek`（同日改造完成）；
> 代码落点 = `scripts/agent-ops.py`（时段选档 + `prices-derive` 键白名单）、
> `scripts/fetch-prices.py`（deepseek 解析器）——**两者本轮都未改**（见 §7 与 §4 普查表）。
>
> **起因（用户原话，逐字）**：
> ① "本地模型档位是可以根据官网报价页面得到，这件事我提醒过你"
> ② "不能迭代报价表吗 没人规定报价表只能维护一种价格，这是设计上的偷懒"
>
> 改造前的缺陷：`scraped.deepseek` 每个模型**只有一组价格**，官方却是**高峰／空闲两档**
> （空闲 = 高峰的一半），于是夜间工作被按高峰价计费 ⇒ 成本**约 2 倍高估**。
>
> **同名姊妹**：`docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD` §6.3
> （G3 输入第 3 条，本 spec 是它的展开）。**引用纪律**：那份只留指针，正文以本文件为准。

---

## 1. 数据源与逐字读数

### 1.1 抓取命令（实测可复跑，本机 PowerShell）

`web_fetch` 工具打不开该域（工具侧限制，非站点问题），故走本机 HTTP：

```powershell
$out = Join-Path $env:TEMP 'ds-pricing-raw.html'
$r = Invoke-WebRequest -Uri 'https://api-docs.deepseek.com/quick_start/pricing' `
      -UseBasicParsing -TimeoutSec 60 `
      -Headers @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
[System.IO.File]::WriteAllBytes($out, $r.RawContentStream.ToArray())
# -> STATUS=200 BYTES=23982
```

同法取中文页（**CNY 口径的唯一来源**）：

```powershell
$r2 = Invoke-WebRequest -Uri 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing' `
       -UseBasicParsing -TimeoutSec 45 `
       -Headers @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
[System.IO.File]::WriteAllBytes((Join-Path $env:TEMP 'ds-pricing-zh.html'), $r2.RawContentStream.ToArray())
# -> ZH_STATUS=200 BYTES=24116
```

### 1.2 抓取时刻（UTC+8）

本机时区 **不是** UTC+8（`[System.TimeZoneInfo]::Local.Id` = `Tokyo Standard Time`，UTC+9），
故由抓取 mtime 的 UTC 值**显式换算**到 UTC+8：

| 页面 | 文件 | UTC（实测 mtime） | **UTC+8（本 spec 与 JSON 采用）** |
|---|---|---|---|
| 英文／USD 展示页 | `%TEMP%\ds-pricing-raw.html` | `2026-09-26T14:41:27Z` | `2026-09-26T22:41:27+08:00` |
| 中文／CNY 页 | `%TEMP%\ds-pricing-zh.html` | `2026-09-26T14:41:45Z` | `2026-09-26T22:41:45+08:00` |

JSON 里 `_fetched_at` = `2026-09-26T22:41:45+08:00`（取 CNY 页，它是数值来源），
`_fetched_at_usd_display_page` = `2026-09-26T22:41:27+08:00`。

### 1.3 逐字价格行（中文页原文，**未转述、未四舍五入**）

URL：`https://api-docs.deepseek.com/zh-cn/quick_start/pricing`
抓取：`2026-09-26T22:41:45+08:00`

表头（逐字）：`模型 | deepseek-flash(1) | deepseek-v4-pro`
表首句（逐字）：`下表所列模型价格以“百万 tokens”为单位。`

价格六行，按页面顺序**逐字**：

```text
价格(2)
  百万tokens输入（缓存命中）    空闲时段   0.02元   0.15元
                              高峰时段   0.04元   0.30元
  百万tokens输入（缓存未命中）  空闲时段   1元      4.5元
                              高峰时段   2元      9.0元
  百万tokens输出               空闲时段   4元      13.5元
                              高峰时段   8元      27.0元
```

> 注意：页面把高峰行写成**无标签格**（区间标签用 `rowspan="2"`），
> 所以"高峰时段"三个字是从上一行的区间标签继承的，**不是**我补的。
> 解析证据：按 `<tr>` 切分后第 15/17/19 行首格即 `高峰时段`。

脚注（**逐字**，关键两条）：

```text
(1) 模型名请使用 deepseek-flash。旧模型名 deepseek-v4-flash、deepseek-v4-flash-vision-exp
    仍可调用，但对应模型已下线，请求将由 DeepSeek-V4.1-Flash 模型提供服务，并按 Flash 价格计费。
(2) 空闲时段价格为高峰时段价格的一半。北京时间周一至周五（不含中国法定节假日）
    9:00 - 12:00、14:00 - 18:00 为高峰时段；其余时段，包括周末及中国法定节假日全天均为空闲时段。
```

### 1.4 英文页逐字价格行（USD 展示口径，仅作交叉核对）

URL：`https://api-docs.deepseek.com/quick_start/pricing`，抓取 `2026-09-26T22:41:27+08:00`

```text
PRICING(2)
  1M INPUT TOKENS (CACHE HIT)   OFF-PEAK  $0.003   $0.022
                                PEAK      $0.006   $0.044
  1M INPUT TOKENS (CACHE MISS)  OFF-PEAK  $0.15    $0.66
                                PEAK      $0.3     $1.32
  1M OUTPUT TOKENS              OFF-PEAK  $0.6     $1.98
                                PEAK      $1.2     $3.96
```

脚注 (2) 逐字：`Peak hours are 01:00 - 04:00 and 06:00 - 10:00 UTC, Monday through Friday,
excluding Chinese public holidays. All other hours are off-peak, including weekends and
Chinese public holidays in full.`

**两页时区等价性（实测换算，不是推断）**：UTC `01:00`→UTC+8 `09:00`、UTC `04:00`→`12:00`、
UTC `06:00`→`14:00`、UTC `10:00`→`18:00`（2026-09-28 为周一）。
⇒ 英文页的 UTC 窗口与中文页的北京时间窗口**是同一组窗口**；JSON 用 `Asia/Shanghai` 表达。

---

## 2. 换算过程（¥/M → USD/token，可复算）

本仓现有口径：`meta.currency = "USD"`（**单价**货币）、`meta.fx_usd_cny = 7.2`、
成本输出 = CNY（`1-WORKFLOW`／`agents/README.md:46` 的用户决策）。
价表存 **USD/token**，故官网 **¥/百万 token** 必须换算：

```text
usd_per_token = cny_per_1m / fx_usd_cny / 1_000_000      (round 10 位，与 fetch-prices._per1m 同精度)
```

逐项（`fx = 7.2`）：

| 档位 | 字段（官方行名） | 模型 | 官网原值 | USD/token（算式） |
|---|---|---|---|---|
| peak | 输入（缓存未命中） | deepseek-flash | `2元` | `2/7.2/1e6` = `0.0000002778` |
| peak | 输入（缓存未命中） | deepseek-v4-pro | `9.0元` | `9/7.2/1e6` = `0.00000125` |
| peak | 输入（缓存命中） | deepseek-flash | `0.04元` | `0.04/7.2/1e6` = `0.0000000056` |
| peak | 输入（缓存命中） | deepseek-v4-pro | `0.30元` | `0.3/7.2/1e6` = `0.0000000417` |
| peak | 输出 | deepseek-flash | `8元` | `8/7.2/1e6` = `0.0000011111` |
| peak | 输出 | deepseek-v4-pro | `27.0元` | `27/7.2/1e6` = `0.00000375` |
| off_peak | 输入（缓存未命中） | deepseek-flash | `1元` | `1/7.2/1e6` = `0.0000001389` |
| off_peak | 输入（缓存未命中） | deepseek-v4-pro | `4.5元` | `4.5/7.2/1e6` = `0.000000625` |
| off_peak | 输入（缓存命中） | deepseek-flash | `0.02元` | `0.02/7.2/1e6` = `0.0000000028` |
| off_peak | 输入（缓存命中） | deepseek-v4-pro | `0.15元` | `0.15/7.2/1e6` = `0.0000000208` |
| off_peak | 输出 | deepseek-flash | `4元` | `4/7.2/1e6` = `0.0000005556` |
| off_peak | 输出 | deepseek-v4-pro | `13.5元` | `13.5/7.2/1e6` = `0.000001875` |

两条映射规则（都是**沿用本仓既有约定**，不是新发明）：

* `cache_creation_input_token_cost` := 同行 **cache-miss input** 单价
  （官方两表都**没有**"缓存写入"行，见 §6 未决点 2）；
* `max_input_tokens` 不属本次抓取值，deepseek 段沿用不设该键的现状（官方给的是上下文长度
  1M / 最大输出 384K，**未**写入本表，避免把"上下文长度"与"计费上限"混为一谈）。

**可复算性**：JSON 内 `_cny_verbatim` 保存了官网原字符串（带 `元`），
`_conversion` 保存算式，`fx_usd_cny` 在 `meta`。
任何人可 `json` 读 `_cny_verbatim` → 按上式 → 与 `models.<m>._tiers.<tier>.*` 逐位比对。
本轮已用独立脚本做过 49 项比对（含 round-trip、off_peak == peak/2、扁平镜像一致性），全通过。

**校验规则也实测过**：`off_peak × 2 == peak` 对每个 模型×字段 成立（官方"一半"规则的机器校验）。

---

## 3. 档位选择规则

### 3.1 用 run 自身的时间戳选档

`run` 的定义域 = `agents/runtime/registry.json` 的 `runs[]`，其中 `started_at` / `ended_at`
是 **UTC ISO-8601**（实测末条：`"started_at": "2026-09-26T05:11:18+00:00"`）。

规则：

1. `t_cst = datetime.fromisoformat(ts).astimezone(ZoneInfo("Asia/Shanghai"))`；
2. `is_peak(t_cst)` = 周一~周五 **且** 落在 `09:00 <= t < 12:00` 或 `14:00 <= t < 18:00`；
   **区间左闭右开**（09:00 整算高峰、12:00 整算空闲）；
3. 其余（含周末、含 12:00–14:00 午间、含 18:00–次日 09:00 夜间）⇒ 空闲。

**边界实测**（`2026-09-28` 周一）：

| UTC | UTC+8 | 判定 |
|---|---|---|
| `00:59` | 08:59 Mon | 空闲 |
| `01:00` | 09:00 Mon | **高峰** |
| `03:59` | 11:59 Mon | 高峰 |
| `04:00` | 12:00 Mon | **空闲** |
| `05:59` | 13:59 Mon | 空闲 |
| `06:00` | 14:00 Mon | **高峰** |
| `09:59` | 17:59 Mon | 高峰 |
| `10:00` | 18:00 Mon | **空闲** |

与英文页 UTC 窗口（01:00–04:00、06:00–10:00）一致 ⇒ 两页口径闭合。

### 3.2 时间戳缺失 ⇒ **按高峰计**并打 `tier_assumed`

`started_at` 或 `ended_at` 为 `null` 时，**不得静默挑一个便宜的档**：

* 计费档位取 `peak`（**保守上界**：宁可高估，不得低估——低估会让预算闸门放行超支）；
* 该 run 的成本对象必须带 `tier_assumed: true`（与既有 `estimated` / `pending_price`
  同层的**可见性标记**，不改变金额语义）；
* 理由（与 `2026-09-26-g2-close-retro.MD` §7 同源）：本仓有真实的"时间戳缺失"历史——
  `register` 漏 `--start`、`queued` 直接收尾、时钟退化。此时代理人**拿不到真值**，
  回填只能编一个像样的数（§7 场景 2/5 已判定 (a) 方案覆盖不了）。故此处**不猜时刻**，
  只声明"这个数按高峰算"，让读账的人知道它偏保守而不是偏乐观。

### 3.3 跨档 run 的计法（**推荐：时间加权分摊**）

`run` 只有**一个** `usage` 汇总（实测字段 `usage: {}`，键为
`input_tokens` / `output_tokens` / `cache_read_tokens` / `cache_write_tokens`），
**没有逐次调用的时间戳** ⇒ 无法知道"哪部分 token 花在哪个档"。

推荐规则（有界、可复算、方向保守）：

```text
peak_frac     = (与高峰窗口重叠的墙钟秒数) / (ended_at - started_at 总秒数)
off_peak_frac = 1 - peak_frac
cost_cny      = usage × [ peak_frac × peak_usd + off_peak_frac × off_peak_usd ] × fx
```

* **为什么用墙钟时间加权、而不是"按 ended_at 归档"**：`usage` 是整段 run 的累计量，
  它**物理上**分布在整段时长上；用结束时刻给整段贴一个标签，等价于假设全部 token
  都产生在最后一刻——对"22:00 起跑、次日 10:30 结束"的 run 会把大量夜间 token 按高峰算，
  正是本次要修的 2 倍高估的翻版。
* **为什么不用"多数时长所在档"**：它是时间加权的二值化，边界附近跳变，且丢掉"跨了多久"的信息。
* **为什么保守方向仍成立**：`peak_frac` 由真实时钟算出，不含乐观假设；
  且当 `usage` 为空（走 `chars/4` 兜底）时，兜底量同样按同一 `peak_frac` 分摊。
* **可复算**：输入只需 `started_at` / `ended_at` / `usage` / `fx`，全部已在 `registry.json` 内。

**现状读数（诚实报告，非估计）**：对 `registry.json` 现存 run 逐条套用该规则，
**窗口跨越档位边界的 run = 0 条**（全部落在单一档内；末条 run 为周六 13:11→13:27，
判定 `off_peak`，`peak_frac = 0.000`）。⇒ 3.3 是**面向以后**的规则，
现在无论取"整段归档"还是"时间加权"结果**相同**；这既是它尚未被真实案例压过的证据，
也是它可以先落规格、后落代码的理由。

### 3.4 未纳入本轮规则的（明确不做，不是遗漏）

* **中国法定节假日日历**：官方口径"不含中国法定节假日"⇒ 节假日全天算空闲。
  本 spec 与 JSON **都没有**编码节假日表（见 §6 未决点 1）。
  后果：在法定节假日的 09:00–12:00 / 14:00–18:00，本规则会判"高峰"而官方按空闲 ⇒ **高估**（保守侧）。
* **`manual` 段的档位语义**：`manual` 是"人工覆盖价、非 null 优先"，现有结构是单组价。
  本轮**未**给它加档（改了会让 5 个既有键的语义分叉），也未规定"manual 命中时档位怎么办"
  （见 §6 未决点 4）。

---

## 4. 受影响调用点普查表（硬规则：见案例 25）

### 4.1 证据命令（grep ＋ 命中行号）

```console
$ git grep -n "prices\.json" -- '*.py' '*.ts' '*.tsx' '*.json'
$ git grep -n "input_cost_per_token\|cache_read_input_token_cost\|cache_creation_input_token_cost" -- '*.py' '*.ts' '*.tsx'
$ git grep -n "cost_per_token\|fx_usd_cny\|scraped\|manual" -- 'agents-dashboard/**/*.ts' 'agents-dashboard/**/*.tsx'
```

### 4.2 普查表

"改档后该点行为是否变化"= 本轮 `prices.json` 改造（deepseek 加 `_tiers` / 扁平键改镜像高峰 /
旧值挪入 `_legacy_single_tier`）之后，**不配合任何代码改动**时的行为。

| # | 位点（证据 = grep 命中行） | 夹具／生产 | 读什么 | 改档后行为 |
|---|---|---|---|---|
| 1 | `scripts/agent-ops.py:88`（`PRICES_PATH = RUNTIME_DIR / "prices.json"`） | 生产 | 路径常量 | 不变（仅路径） |
| 2 | `scripts/agent-ops.py:441-443` `_load_prices()` | 生产 | 整份 JSON | 不变 |
| 3 | `scripts/agent-ops.py:447-461` `_prices_for()`：`:455` `for prov in p.get("scraped", {}).values()`、`:456` `model in prov.get("models", {})`、`:460` `prov["models"][model]` | 生产 | 模型级 dict | **不变**（按名字命中，返回整条含 `_tiers` 的 dict） |
| 4 | `scripts/agent-ops.py:481` `prices.get("input_cost_per_token")` | 生产 | 扁平键 | **不变**（扁平键 = 高峰镜像） |
| 5 | `scripts/agent-ops.py:483` `cache_read_input_token_cost` | 生产 | 扁平键 | **不变** |
| 6 | `scripts/agent-ops.py:484` `cache_creation_input_token_cost` | 生产 | 扁平键 | **不变** |
| 7 | `scripts/agent-ops.py:490-491`（`chars/4` 兜底同用扁平键） | 生产 | 扁平键 | **不变** |
| 8 | `scripts/agent-ops.py:1580-1584` `prices-derive` **键白名单**：`:1583-1584` 只收 `("max_input_tokens","input_cost_per_token","output_cost_per_token","cache_read_input_token_cost","cache_creation_input_token_cost")` | 生产 | auto 段重写 | **不变**（它只重写 `auto`；`scraped` 在 `:1588` 原样带过）——**但见 4.3 红字** |
| 9 | `scripts/agent-ops.py:1587-1589` `out = {"auto","manual","scraped","meta"}` | 生产 | 顶层键重建 | **变（若我加了顶层键的话）**：顶层只认这 4 个键 ⇒ 任何新增**顶层**键会被静默丢弃。故本轮**所有**新元数据都放在 `scraped.deepseek` **内部**（含 `_legacy_single_tier`），不放顶层 |
| 10 | `scripts/fetch-prices.py:33`（`PRICES_PATH`）、`:213-224` `merge()`（`:219` `merged["scraped"]=…` 整段覆盖）、`:260-265` `--apply` | 生产 | scraped 段 | 不变（`merge` 只按 provider 整段替换） |
| 11 | `scripts/fetch-prices.py:148-171` `parse_deepseek()` | 生产 | 官网 HTML | **不变（但已坏，见 4.3）** |
| 12 | `scripts/fetch-prices.py:152` `r"MODEL</td>(?:<td>(.*?)</td>){3}"` ＋ `:160` `if len(amounts) < 18 or len(models) != 3: return {}` | 生产 | 官网表形状 | **不变**：仍返回 `{}`（实测 0 模型），`--apply` 因此**不覆盖** deepseek 旧价（fail-safe，不写坏数据） |
| 13 | `paper-qa-script/app/usage.py:44`（`prices_path()`） | 生产 | 整份 JSON | 不变 |
| 14 | `paper-qa-script/app/usage.py:82-95` `price_for()`：`:85` `prices.get("scraped")`、`:89` `if name in models and models[name]`、`:91-94` auto 兜底 | 生产 | 模型级 dict | **不变**（命中即返回）；模型名候选由 `:65-78` `_model_candidates()` 归一化，`openai/deepseek-v4-flash` → `deepseek-v4-flash` 现仍在 `models` 内（以别名条目存在） |
| 15 | `paper-qa-script/app/usage.py:123` `price.get("input_cost_per_token")` | 生产 | 扁平键 | **不变** |
| 16 | `paper-qa-script/app/usage.py:98-102` `fx_usd_cny()` ← `meta.fx_usd_cny` | 生产 | meta | 不变（`meta` 逐字保留） |
| 17 | `agents-dashboard/lib/db.ts:320-324`（读 `prices.json` 的 `meta.fx_usd_cny`，兜底 7.2） | 生产 | 只读 `meta` | **不变** |
| 18 | `agents-dashboard/app/costs/page.tsx:76`、`:164`（文案：汇率来源／`pending_price` 释义） | 生产（文案） | 展示 | **不变**（但文案仍说"USD/token × fx"，未提两档 ⇒ 见 §6 未决点 6） |
| 19 | `verify/verify_agentops.py:152`（`AGENT_OPS_DIR=str(tmp)`）＋ `:173`、`:178`、`:270-272`、`:457` | **夹具** | 写/读 `%TEMP%` 的**合成** `prices.json` | **不变**（`AGENT_OPS_DIR` 把价表重定向到 `%TEMP%`，从不读仓库那份） |
| 20 | `verify/verify_agentops.py:386`（合成 HTML 表）、`:417-418`（断 `ds["deepseek-v4-flash"]["input_cost_per_token"] == 4.4e-7`） | **夹具** | 合成 HTML 内嵌旧表 | **不变**（本次未碰该文件）——**但它是旧表形状的冻结副本**，改 `parse_deepseek` 时必须同步，否则改完仍绿而解析器已换 |
| 21 | `verify/verify_usage.py:79-99`（`:80`、`:83`、`:95` 读 `input_cost_per_token`；**读仓库真实 `prices.json`**） | 半夹具：断言自己的算式，但**数据源是生产价表** | 真实 `scraped.deepseek.models["deepseek-v4-flash"]` | **实测不变**：`verify_usage.py` 改造后现跑 `rc=0`（全部断言通过）——这正是"扁平键镜像"存在的理由 |
| 22 | `verify/verify_ledger_measurement.py`（未直接读价表；读 `registry.json` 的 `cost_est`/时间戳） | 夹具 | 账本 | 不变（但 §3.2/§3.3 的标记与分摊若落代码，它会成为**新的**判据落点） |
| 23 | `verify/verify_artifact_paths.py:702`（docstring 举例 `agents/runtime/prices.json` 走 `!` 白名单） | 生产闸门 | **只看 `git status` 的 `??` 行**，不读价表内容 | **不变**。实测 `git check-ignore --no-index -q agents/runtime/prices.json` → `rc=1`（未忽略＝白名单生效）；改造后 `git status` 该文件仍是 ` M`（已跟踪被改），**不产生** `??` |
| 24 | `agents/policy.json:96`（`artifact_paths` 把 `prices.json` 列为入库数据文件） | 生产政策 | 路径声明 | 不变 |
| 25 | `docs/4-ALGORITHM.MD:627`（`:scraped.<provider>.models.<model>` → `auto` 兜底；汇率取 `meta.fx_usd_cny`） | 文档口径 | 描述 | **不变（但已不完整）**：未描述两档 ⇒ 见 §6 未决点 6 |
| 26 | `agents/README.md:45`（`scraped` 段优先级 `manual > scraped > auto`）、`:46`（单位 = CNY；价表单价 USD/token） | 文档口径 | 描述 | 不变；建议补一句"两档"（未改，避免与他人并发写冲突） |

### 4.3 两处**必须点名**的红字（不修则双档等于白做）

**红字 A —— `prices-derive` 的键白名单会**丢档**（且这是"重生成即丢"的形态）。**

`scripts/agent-ops.py:1580-1584` 的白名单只覆盖 `auto` 段的 5 个键；`scraped` 段虽在
`:1588` 原样带过，但 `:1587` 重建顶层 dict 的行为意味着：

* 若把档位元数据放在**顶层**（如 `tiers`、`scraped_at_cst`）⇒ 下次 `prices-derive` **静默丢弃**；
* 若把档位放在 `scraped.deepseek.models.<m>._tiers`（本轮选择）⇒ 因 `:1588` 整段带过而**幸存**，
  但**没有任何 `auto` 侧的白名单项**会保留档位 ⇒ 一旦把 deepseek 价移到 `auto` 段即丢档。

对照 `2026-09-25-gate-mechanism-failure-modes-case.MD:127`（"改源就要重生成；本地绿 ≠ 派生一致"）
与 `2026-09-21-a-m11-from-runs.MD`（并发写同文件静默丢段）：**双档的守卫必须是"派生后档位仍在"的断言**，
而不是"我这次写对了"。故 `prices-derive` 的键白名单同步**是双档生效的前置条件**，
本 spec 把它列为落代码时的第一判据（本轮该文件由另一写者负责，我未改）。

**红字 B —— `fetch-prices.py` 的 deepseek 解析器现在**完全解析不出**（实测）。**

非破坏性探针（`importlib` 加载模块、**不**跑 `--apply`）对两个页面分别调用 `parse_deepseek()`：

```console
$ .venv\Scripts\python.exe <probe>            # 见 §5 命令 4
parse_deepseek(en page (what SOURCES deepseek URL serves)) -> 0 models: {}
parse_deepseek(zh-cn page) -> 0 models: {}
```

原因（代码未改，形状已变）：`:152` 要求 `MODEL</td>` 后**恰好 3 个**模型名、
`:160` 要求 `$` 金额 **≥ 18 个**；而官网现行表是 **2 模型 / 12 金额**（且中文页用 `元` 而非 `$`，
无任何 `$`）。⇒ deepseek 抓取**已经失效**，且失效形态是"返回 `{}` ⇒ `--apply` 不覆盖旧价"
（**fail-safe，不写坏数据**，但价表会**静默停在 2026-09-20 的值**）。

⇒ **本轮 `prices.json` 的双档数据没有自动写入口**：下一次 `fetch-prices --apply` 不会重建它，
也不会毁掉它。这是"数据先行、代码随后"的已知窗口（见 §6 未决点 3）。

---

## 5. 复算与验证命令（本轮实际跑过的）

1. **JSON 合法性（本仓硬要求）**

```console
$ .venv\Scripts\python.exe -c "import json,pathlib;json.loads(pathlib.Path('agents/runtime/prices.json').read_text(encoding='utf-8'))"
（无输出）EXIT=0
```

2. **档位数值 re-verify（独立脚本，读已落盘文件，不读生成器）**
   覆盖：`_cny_verbatim` → USD/token round-trip、`off_peak × 2 == peak`、
   扁平键 == `_tiers.peak`、`_legacy_single_tier` == `git show HEAD:…` 原值、
   别名与目标同价、`auto`/`manual`/`dashscope`/`openrouter` 未变、`meta` 未变、
   全文无科学计数法。结果 `PASS=49 FAIL=0`。

3. **抓取页逐字读数**：`%TEMP%\ds-pricing-raw.html`（英文）／`%TEMP%\ds-pricing-zh.html`（中文），
   解析用脚本按 `<tr>` 顺序走，断言恰好 6 个价格行、每行 2 个金额格。

4. **解析器现状探针**（红字 B 的命令）：

```console
$ .venv\Scripts\python.exe -c "<importlib load scripts/fetch-prices.py; parse_deepseek(zh_html)>"
parse_deepseek(zh-cn page) -> 0 models: {}
```

5. **档位规则边界 fixtures + 真实账本套用**：见 §3.1 表与 §3.3 读数（92 条 run，跨档 0 条）。

---

## 6. 未决点（**不确定就写不确定**）

1. **中国法定节假日日历未编码**。官方口径"不含中国法定节假日"，但**没有**机器可读的节假日表；
   我不知道本仓应否引入、从哪引入、由谁维护。现状影响：节假日白天判"高峰"⇒ **高估**（保守侧）。
   若哪天要精确，必须先解决"节假日表 = 谁的真源"（这是政策数据，按 `§6 政策数据化` 应进 `agents/policy.json`，
   但它的**内容**不适合手抄）。

2. **"缓存写入"单价的官方缺失**。官方两表都没有 cache-creation 行，我**沿用了本仓既有映射**
   （:= cache-miss input 单价）。这是**推断，不是读数**。若 deepseek 后台实际对缓存写入另有计价
   （或不计价），本表会错。我没有能找到的证据，也没查到官方说明。

3. **双档目前没有自动写入口**（红字 B）：`fetch-prices.parse_deepseek` 已解析不出新表。
   我不知道"先改代码还是先改数据"在本仓流程上哪个更合规（我按用户要求只改了数据侧）。
   风险窗口 = 下一次 `fetch-prices --apply` 之前，价表**停在** 2026-09-26 的快照。

4. **`manual` 段与档位的关系未定**。`manual.<model>` 现是"一组价、非 null 优先"。
   若某天要人工钉一个空闲价，是加 `_tiers` 还是加 `peak`/`off_peak` 两个键？
   我没有改，因为改它会分叉 5 个既有键的语义，且优先级 `manual > scraped` 会让"人工单档价"
   在时段计价里变成一个**新的**语义洞（人工价是否也按时段？）。
   本次 `manual` 全为 `null`（实测），故对当前成本结论**无影响**。

5. **换算用的是本仓 `fx_usd_cny = 7.2`，而官网两页自带的汇率不是 7.2**。实测隐含汇率：
   两个页面之间 `flash` 行恒为 `¥1 = $0.15` ⇒ 隐含 `6.6667`；`pro` 行恒为 `¥1 = $0.1467` ⇒ 隐含 `6.8182`。
   因此本表（官方 ¥ ÷ 7.2）与**官方 USD 展示值**存在 `+5.6%~+8%` 的系统差
   （例：`flash` 高峰输入 `2元` → `2.778e-7` USD/token，而英文页 `$0.3/1M` = `3.0e-7` USD/token）。
   我**选择**服从"单一 `fx_usd_cny` 口径"（换算式可复算、不引入第二个汇率），
   代价是相对官方 USD 值**高估**。若改为直接用英文页 USD 值，则 JSON 与官方 USD 完全一致、
   但与 `¥ × 1/7.2` 的复算不一致 ⇒ **两者不可兼得**。这个取舍得由用户裁（我倾向维持现状：
   偏差在保守侧、口径单一、可复算）。

   - **父代理裁定（2026-09-26，不再挂起）**：**维持 `¥ ÷ fx_usd_cny(7.2)`**。三条理由：
     ① **可复算**——任何人拿官网 ¥ 值和 JSON 里那一个汇率都能重算出本表的每个数，而"官网 USD 展示值"
       依赖对方页面当时的隐含汇率，我方**无法复算也无法复核**；
     ② **偏差在保守侧**——成本预估偏高 5.6%~8%，对"预算上限决策"是安全方向；
     ③ **单一汇率**——引入第二个汇率就等于本仓自己反复记录的"同一概念两处定义"（机制案例 23 的形态）。
     **代价已具名**：本表数值 **不等于** 官方英文页展示的 USD 值；引用本表时**不得**声称"与官网 USD 一致"。
     若将来要改成官方 USD 口径，须**同时**改 `meta.fx_usd_cny` 的语义说明与本条的复算式，不得只改数。

6. **口径文档尚未同步**：`docs/4-ALGORITHM.MD:627`、`agents/README.md:45-46`、
   `agents-dashboard/app/costs/page.tsx:164` 都还只描述"一组单价"。
   本轮**没有改这些文件**（用户只允许我写两个文件；且 `scripts/**`/`verify/**` 同切片只许一个写者）。
   双档落地时它们必须同步，否则就是"文档与数据分叉"。

7. **`_flat_key_policy` 的语义是过渡态，不是终态**。扁平键现在镜像**高峰**，
   于是"没有时段感知的消费方"会继续按高峰计费（保守，但对夜间仍是 2 倍高估）。
   **只有选档代码落地，本次改造才真正兑现"夜间不再按高峰计费"**。
   我把这条写在 JSON 里（`_flat_key_policy`）而不是只写在这里，就是为了让它跟着数据走。

8. **我不知道 `deepseek-flash` 与 `deepseek-v4-pro` 之外的模型是否也需要档位**。
   官方表现在只有这两个模型；`openrouter` 段里的 `deepseek/*` 是**第三方转售价**（另有自己的计价，
   实测值与官方不同），本 spec **未**假设它们也分档。

---

## 7. 本轮边界（我做了什么、没做什么）

* **做了**：① `agents/runtime/prices.json` 的 `scraped.deepseek` 两档结构化改造
  （`_tiers.peak` / `_tiers.off_peak`，`_fetched_at`，官网 URL，换算过程，`_cny_verbatim`，
  `_legacy_single_tier`，别名，扁平键镜像）；② 本 spec 文件。
* **没做（明确）**：未改 `scripts/agent-ops.py`（时段选档、`prices-derive` 键白名单）、
  未改 `scripts/fetch-prices.py`（deepseek 解析器）、未改 `verify/**`、
  未改 `paper-qa-script/**`、未改 `agents-dashboard/**`、未改任何 `docs/**` 既有文件、
  未 `git add` / `commit` / `push`。
* **因此**：§3.2 的 `tier_assumed`、§3.3 的时间加权分摊、红字 A 的白名单同步、红字 B 的解析器修复
  **都还是设计，不是实现**——本 spec 是它们的落点，不是它们已完成的证据。

---

## 8. 实现记录（2026-09-27，行 15 ＋ 行 16 同批落地）

> 本节由**实现批**追加，**不改写**上面任何既有章节。上表仍是"改造前的诊断"，
> 本节是"改造后的事实"。台账
> `docs/iteration/phases/testing-governance/2026-09-26-g2-closure-ledger.MD` 的 **E9**
> 要求行 15 与行 16 同批——本批同时改了 `scripts/fetch-prices.py`、
> `scripts/agent-ops.py`、`verify/verify_agentops.py`。

### 8.1 落地清单（按文件）

| 文件 | 落地的规格条款 | 关键实现 |
|---|---|---|
| `scripts/agent-ops.py` | §3.1／§3.2／§3.3、§4 红字 A | `peak_windows_from_prices`（窗口**从价表读**，不写死在代码里）、`is_peak_at`、`peak_frac_for`、`_tier_prices`、`_estimate_cost` 选档；`prices-derive` 白名单加 `_tiers`/`_tier_scheme` + 顶层多档键转发 + 未入册顶层键 WARN |
| `scripts/fetch-prices.py` | §4 红字 B、§6 未决点 3 | `parse_deepseek` 按 `<tr>` 平铺重写：模型数从表头读出（不再要求 3）、金额同时认 `$` 与 `元`、**同页抓两档**；`_provider_meta()` 随抓取写回 `_peak_windows`/`_tier_timezone`；`merge()` 并回解析器不产出的元数据键；`judge_scrape()` 把"抓空／价表过旧"变成出声的 WARN（`--check` 下 FAIL） |
| `verify/verify_agentops.py` | 台账 E9 | `:386` 那份**旧表形状冻结副本**换成现行表形状并改断言；新增 `price_shape_problems()` 形状契约、E9 反向对照、"派生后档位仍在"判据 |
| `agents/runtime/prices.json` | — | **未改**（本批一行都没动它；下节"改前 vs 改后"用的是 HEAD 版脚本，不是旧价表） |

### 8.2 复现命令（每条都已现跑，读数以命令输出为准）

```console
# 解析器：两个官方页都能解析出 2 模型 × 2 档（英文页 $ / 中文页 元）
$ .venv\Scripts\python.exe scripts\fetch-prices.py --check

# 选档规则边界 + 反证（在闸门内，离线，固定时刻夹具）
$ .venv\Scripts\python.exe verify\verify_agentops.py

# 改前 vs 改后：同一 run 行喂给 HEAD 版与被改版 `_estimate_cost`
$ git show HEAD:scripts/agent-ops.py   # 改前实现
$ .venv\Scripts\python.exe scripts\agent-ops.py finish <run_id> --status succeeded --usage-in 4000 --usage-out 500
```

### 8.3 改前 vs 改后（真入口：真 CLI ＋ 真账本行）

同一 usage（`input=4000, output=500, cache_read=2000`）、同一时间戳
（`2026-09-26T16:30:35+00:00` ＝ UTC+8 `2026-09-27 Sun 00:30:35`，**周末 ⇒ 空闲档**），
分别喂给 HEAD 版与被改版 `_estimate_cost`：

| 实现 | `total`（CNY） | `tier` |
|---|---|---|
| 改前（`git show HEAD:scripts/agent-ops.py`） | `0.01208124` | （无该字段） |
| 改后（worktree） | `0.0060408` | `off_peak` |

⇒ 夜间 run 的成本估算**减半**，正是本卡要修的那个 2 倍偏差。

**真 CLI 验收（`register --start` → `finish`）**：`run-2026-09-27-impact-assessment-098`
的 `cost_est.tier = "off_peak"`、`total = 0.0060408`；同一 usage 的
`run-2026-09-27-impact-assessment-097`（改后代码遇到"同秒收尾"时的中间态）为
`tier="peak"` + `tier_assumed=true`。两条 run 的 `started_at` 都**确实落在空闲窗口内**
（闸门里有这条前置断言）。

### 8.4 规格含糊／待补（**实现时未自作主张的部分**）

1. **§3.2 的"时间戳缺失"不等于"时长为 0"。** 本仓 `register --start` 后同秒收尾很常见
   （`_now()` 秒级截断 ⇒ `started_at == ended_at`）。若把这种 run 也按 §3.2 当"缺失"，
   夜间 run 会被重新算成 2 倍——与 §3.1"按 run 自身时间戳选档"冲突。
   实现取**起点那一刻判档**（零长度 run 落在哪一档），只在端点**真的缺失/不可解析**
   或末态早于起点（时钟退化）时才 `tier_assumed`。**这条是规格没写、必须由人确认的口径**。
2. **跨档 run 的 `cost_est.tier` 取值未定。** §3.3 只给了金额算式，没说标签写什么。
   实现写 `"mixed"` 并附 `peak_frac`（可复算），但**规格未授权该取值**。
3. **没有档位数据的模型标 `tier: "flat"`**（dashscope/openrouter 段仍是单档）。
   规格未规定这种 run 的标签；不标的话"用没用档位"在账本里看不出来。
4. **红字 A 的作用域比原文更窄（实测）**：`_AUTO_KEY_WHITELIST` 决定 `auto` 段**有哪些键**，
   而**值是 litellm 表给的**——litellm 没有 `_tiers` ⇒ `auto` 里的 `_tiers` 只能是 `null`。
   白名单同步只能保证"将来 litellm 若给出档位，派生不会丢"；**真正让档位活着的是
   `scraped` 段整段带过**。`auto` 段要承载档位，需要另给它一个真源（未做，未定由谁供）。
5. **§6 未决点 5 的换算口径未改**：中文页 `元` 仍按 `meta.fx_usd_cny`（`_DS_CNY` 缺省 7.2）
   换算，**没有**改用官方英文页的 USD 展示值。
6. **`fetch-prices --apply` 现在会写回档位元数据**（`_provider_meta`）。这是本批新增的写盘面：
   它把 §1 里"数据先行、代码随后"的窗口关闭了，但也意味着**下一次 `--apply` 会重写
   `scraped.deepseek` 的元数据块**（官网脚注逐字串以代码为真源）。这一点本 spec 原文未预见。

### 8.5 明确**未做**（越界声明）

* 未改 `paper-qa-script/app/usage.py`：它的 `cost_cny()` 仍读扁平键（= 高峰镜像）。
  litellm 回调**不带 run 时间戳**，那里"按 run 选档"没有输入；夜间批次的成本在那条链路上
  仍偏保守（高估）。**这是已知的、具名的缺口**，不是本批能靠改价表解决的。
* 未编码中国法定节假日（§6 未决点 1 原样保留）：节假日白天仍判高峰 ⇒ 高估（保守侧）。
* 未改 `agents-dashboard/**`（文案仍只说一组单价）、未改 `docs/4-ALGORITHM.MD`／
  `agents/README.md` 的口径段（他人并发写的文件）。
* 未 `git add`／`commit`／`push`。

## 附录 R｜§8.4 三处口径空白的裁定（父代理 2026-09-27，**裁定即规格**）

实现批把三处规格没写的地方交回裁定。以下为裁定结论，**实现批的处置全部采纳**：

1. **"时间戳缺失" ≠ "时长为 0"**：`register --start` 后同秒收尾在本仓极常见（`_now()` 秒级截断 ⇒
   `started_at == ended_at`）。**裁定：零时长不是"缺失"**，取**起点那一刻**判档（起点是真实观测），
   `tier_assumed` **只在端点真的缺失/不可解析、或末态早于起点时才置位**。
   **理由**：若按 §3.2 字面把同秒当"缺失"，夜间 run 会被重新按高峰计 ⇒ **与 §3.1 冲突并重新引入约 2 倍高估**，
   即本次要修的那个 bug。**该裁定优先于 §3.2 的字面读法。**
2. **跨档 run 的标签**：**采纳 `tier: "mixed"` ＋ `peak_frac`（0~1，可复算）**。
   **理由**：跨档必须可审计——只给金额无法回答"用了多少高峰"，而 `peak_frac` 让金额可复算
   （验收实测 `peak_frac == 0.5` 且金额 = 0.5×高峰＋0.5×空闲，逐位一致）。
3. **无档位数据的模型标 `tier: "flat"`**：**采纳**。
   **理由**：不标则"这条 run 到底用没用档位"在账本里看不出；标了才能在下游区分"单档供应商"与"漏了档位数据"。

**其余三处（红字 A 作用域、`--apply` 写 `_provider_meta`、换算口径未改）不当场改规格**：
前两处是实测事实与新增写盘面，已由实现批写入 §8 实现记录；第三处维持 `¥ ÷ meta.fx_usd_cny`（见未决点 5 的父代理裁定）。

---

## 9. 行 20 实现记录（2026-09-27）

> 本节由**行 20 批**追加，**不改写**上面任何既有章节。§6 未决点 7 与 §8.5 都把
> "`app/usage.py` 的 `cost_cny()` 仍读扁平键（= 高峰镜像）"列为**具名缺口**；
> 本节是它的关闭记录。关闭标准 = **零未闭环项**（`docs/6-DECISIONS.md::D-250926-06`），
> 被关闭项 = `docs/iteration/phases/testing-governance/2026-09-26-g2-close-retro.MD` §5 行 20。

### 9.1 可行性判定：回调**确实**能拿到"该次调用自己"的时刻（行 20 的"没有选档输入"已被实测推翻）

行 20 原文说"litellm 回调**不带 run 时间戳** ⇒ 该链路没有选档输入"。前半句仍然成立
（**run** 时间戳确实没有），后半句**不成立**：

| 问题 | 结论（2026-09-27 实测） | 证据 |
|---|---|---|
| 回调能拿到该次调用自己的时刻吗 | **能**，而且是**两个端点**（起 ＋ 止） | `litellm` 1.76.1：`litellm/integrations/custom_logger.py::log_event` 以 `callback_func(kwargs, response_obj, start_time, end_time)` **按位置**调自定义回调；调用点在 `litellm_core_utils/litellm_logging.py`（同步 `success_handler` 与异步 `async_success_handler` 各一处） |
| 时刻的形态是什么 | `datetime.now()` 的**朴素本地时间**（`tzinfo is None`） | 探针（`acompletion` ＋ `mock_response`，离线）：回调收到 `datetime(2026, 9, 27, 2, 1, 50, 58794)`，同刻本机墙钟 02:01（本机 UTC+9）、UTC 17:01 |
| 一次调用会触发几次回调 | **一次**（`acompletion` 只走异步列表；同步可调用回调在 `acompletion=True` 时被跳过）⇒ 不会双计 | 同上探针 `CALLBACK_COUNT=1`；`verify_usage.py` ⑫1 把这条做成判据 |
| 只用 `now()`（结束时刻）够不够判档 | **不够**。那等于"给整段贴一个结束时刻的标签"，正是 §3.3 具名否掉的算法（会把跨档 token 全按末刻那一档算） | §3.3 的两条理由；实现取 §3.3 的时间加权（下面 §9.2） |
| 跨档（高峰↔空闲）怎么计价 | **墙钟时间加权**，与 §3.3 同式、与 `scripts/agent-ops.py::peak_frac_for` 同边界/同缺失方向 | `verify_usage.py` ⑪4（`peak_frac == 0.5` → 金额 = 0.5×高峰 ＋ 0.5×空闲）；⑪14 与参考实现逐条同值 |
| 时间戳缺失/不可得怎么办 | **按高峰计 ＋ 打 `tier_assumed`**（§3.2 原样，不静默挑便宜的档） | `verify_usage.py` ⑪5/⑪6/⑪8 |

**朴素时间戳按什么时区解释**：按**本机墙钟**（`datetime.now()` 的语义），**不是** UTC。
这一条与 `agent-ops._parse_ts`（朴素 ⇒ UTC）**刻意不同**，理由是两条链路的输入来源不同：
registry.json 里的 ISO 串本身带 `+00:00`（朴素值是退化形态），而 litellm 给的是本机墙钟。
代价已实测：本机 UTC+9 时，若把 02:01 的调用当 UTC，`02:01Z` 换算成 CST 是 10:01 ⇒ 判**高峰**；
真实时刻 `01:01 CST` ⇒ 判**空闲**。**照抄 agent-ops 的朴素分支会让档位整体错一个小时**。
`verify_usage.py` ⑪14 把这条差异做成**具名判据**（两边各按自己的来源解释，差额 = 本机偏移）。

### 9.2 落地清单（按文件）

| 文件 | 落地的规格条款 | 关键实现 |
|---|---|---|
| `paper-qa-script/app/usage.py` | §3.1／§3.2／§3.3（**镜像**行 16 的参考实现） | `peak_windows()`（窗口**从价表读**）、`is_peak_at`、`peak_frac`、`tier_prices`、`_tier_plan`；`cost_cny(by_model, tiered=None)` 新增 `by_tier` / `tier_by_model` / `tier_assumed_calls` 三个**可审计**键；`snapshot()`/`delta()` 都带档位增量 |
| `verify/verify_usage.py` | 判据 | ⑪0~⑪14（真入口对照 ＋ 前置断言 ＋ 反证 ＋ 与参考实现逐条同值）、⑫1~⑫3（真派发把该次调用的时刻交给回调）；`cost` 键白名单相应扩展 |
| 本文件 | 本节 | — |

**"改前"取自哪里**：钉住 revision ``1ed6f937396eb81e7fc6a9e40d87fbdd139fa926``（本批开工时的 HEAD），
**不取 `HEAD`**——本批提交之后 `git show HEAD:` 会拿到改后版本，那条对照会自我作废。
价表两边钉成**同一份**（`%TEMP%` 里加载的旧实现，`prices_path()` 的 `parents[2]` 指不到仓库，
不钉就会退化成"无价 vs 有价"）。

### 9.3 真入口前后对照（同一 usage、同一入口、只差代码版本）

夹具时刻均为 **2026-09-28 周一（CST）**，usage = `prompt 1000`；金额单位 CNY。
"改前" = 钉住 revision 的 `hook_success`（litellm 实际调用的那个函数），"改后" = worktree。

| 场景 | 前置断言（确实发生） | 改前 | 改后 | 档位标签 |
|---|---|---|---|---|
| 夜间 `22:30→22:31` | `peak_frac == 0.0`、CST `Mon 22:30` 非高峰 | `0.002` | `0.001` | `off_peak` |
| 高峰 `10:00→10:01` | `peak_frac == 1.0` | `0.002` | `0.002` | `peak` |
| 跨档 `11:00→13:00` | `peak_frac == 0.5`（高峰 1h ＋ 空闲 1h） | `0.002` | `0.0015` | `mixed` |
| 缺两端时间戳 | 判据要求"不得被算成空闲" | `0.002` | `0.002` ＋ `tier_assumed` | `peak` |
| 零长度夜间 `22:30→22:30` | `peak_frac == 0.0`（§8.4 裁定 1） | `0.002` | `0.001`，**不**打 `tier_assumed` | `off_peak` |
| 时钟退化 `10:01→10:00` | `end < start` | `0.002` | `0.002` ＋ `tier_assumed` | `peak` |

⇒ **夜间精确 2.0×**（`0.002 == 2 × 0.001`）；**高峰与改前同值**（没有反向算错）。
另有**真派发**一条：`acompletion` ＋ `mock_response`（离线、不付费）经 litellm 真回调路径记录，
记录的档位 = 用**捕获到的时刻**独立算出的档位（2026-09-27 现跑为 `off_peak`，与当时 CST 落在空闲窗口一致）。

**一处必须说清的数值细节**：真实价表里 `deepseek-v4-flash` 的 `off_peak` **输出**单价是
`5.556e-07`，而"高峰的一半"是 `5.5555e-07`（表内 10 位四舍五入）。故当 usage 同时含输入与输出时，
未取整的比值是 `1.99982…` 而不是 `2.0`（输入键逐位满足 `off × 2 == peak`，故纯输入 usage 是精确 2.0×）。
判据因此写成"金额 == 由价表现值推出的该档金额"（逐位），而不是写死 2.0。

### 9.4 本次判据在哪些时候会红（不是恒真）

- 改前实现在同一输入下**不满足**夜间判据（`verify_usage.py` ⑪2 反证）——判据咬得住；
- 把窗口数据换成"周一全天高峰" ⇒ 同一次夜间调用改判高峰（⑪13 反证①）；
- 窗口形状非法 ⇒ fail-closed 判高峰，不许静默变便宜（⑪13 反证②）；
- 真派发若未触发回调（异步派发超时）⇒ ⑫1 直接 FAIL，**不**静默跳过。

### 9.5 行 20 未做／未决（**不确定就写不确定**）

1. **未编码中国法定节假日**（§6 未决点 1 原样保留）：节假日白天仍判高峰 ⇒ 高估（保守侧）。
2. **未改 `manual` 段的档位语义**（§6 未决点 4 原样保留）：`manual` 命中时仍按扁平键计价。
3. **`auto` 段没有档位真源**（§8.4 第 4 条原样保留）：`auto`/`litellm` 来源的模型只有在
   **价表带 `_tiers` 且带 `_peak_windows`** 时才分档，否则如实标 `flat`。
4. **文档口径尚未同步**：`docs/4-ALGORITHM.MD` §13、`agents/README.md:45-46`、
   `agents-dashboard/app/costs/page.tsx` 仍只描述"一组单价"。本批的写入集只有
   `paper-qa-script/app/usage.py`、`verify/verify_usage.py` 与本文件 ⇒ **未改**它们
   （与 §6 未决点 6 同因）。
5. **`verify_usage.py` 现在需要 `git`**（`VERIFY_META.requires` 已如实声明）：它要取钉住
   revision 的**改前**实现来对照。取不到 ⇒ FAIL（fail-closed），不静默降级成"只跑改后"。
6. **进程级累计的既有口径未动**：`delta()` 仍是**进程级时间窗**（`scope` 字段标注），
   多会话并发时逐步用量仍会把他人调用算进来——这与行 20 无关，是既有的独立缺口。
