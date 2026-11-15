# TE-2026-11-15-anchor-scope：A-PTR 是否扩展迁移到 iteration 指针

- stage: design
- trigger: MM-3 首跑；A-PTR 后续迁移范围的翻案评估。
- question: 是否已有足够证据推翻 A-PTR 的“不批量迁移”基线，把指向 `docs/iteration/**` 的存量行号指针整体改为锚点？
- baseline: [A-PTR 的共存期策略](../../agents-infra/cards/A-PTR.md#与旧-pathline-的共存期策略)明确保留旧形态，只处理实测漂移或正在改动的条目；[剩余分布与不迁理由](../../agents-infra/cards/A-PTR.md#剩余旧形态指针的分布与不迁理由)及文末完成范围明确 iteration 未迁。本记录是**翻案建议的证据评估**，不静默重议或改变生效基线（F5）。
- freeze: 2026-11-15 23:55 UTC+8；`python scripts/now-network.py` 返回“2026-11-15 23:55 UTC+8（来源 https://www.baidu.com/ 的 HTTP Date 头）”；windows HEAD `5b22be5217597d510d223dc3fce4e74da8603178`；本地 main `bc3121992a723f57abc5a3cd4b53090b97cbcafb`；run `run-2026-11-15-implementation-149`。main 指的是本地冻结引用，未 fetch，不代表远端最新值。
- material: `docs/6-DECISIONS.md` 的围栏外指针；`verify/verify_decision_register.py::POINTER_RE/ANCHOR_RE/_strip_fences/check_register`；`scripts/anchor-resolve.py::resolve`；[MM-6 定义与骨架](../mindset-v0.1.MD#2-思维实验的操作定义)。复现命令见“只读探针”；存量规模以探针现跑输出为准，不把卡片历史读数当现值。
- constraints: 只写 MM-3 本轮允许的草案、记录、卡和报告；不改登记册、目标文档、脚本、闸门、政策、其它卡或父索引；不提交。插入、重复、删锚和形态替换均只发生在内存。没有运行任何迁移。
- 定题说明: 原候选题 B 在核实时已发生变化：账本中 MM-4 的 `run-2026-11-15-implementation-150` 已 succeeded、卡已完成；继续把它当尚待排期会失真。因此使用仍未执行的 A-PTR 扩围问题。当前用户只授权评估，不授权翻案执行。

## 路径

### 路径 A：立即整体迁移存量 iteration 指针

- 动作集: 若获另行批准，逐目标生成锚点并整体替换登记册中的 iteration 行号指针；本轮仅模拟形态变化与缺席计数。
- 选择点: 迁移范围为全部存量；现在启动；改变登记册表示，但不改变 main 的文件树。
- 依赖事实: fact: A-PTR 文末仍标 iteration 未迁；P-A 实读 main 树与登记册解析器。inference: 整体迁移须逐目标确认唯一性、语义等价与分支计数；改动面越大，复核对象越多，当前没有覆盖全部目标的等价证据。
- 推演: 替换表示 → 围栏外同一目标路径多重集保持不变 → main 缺席路径仍然缺席。把“降未核棘轮”作为扩围收益会在此暴露错误；windows 的抗插入收益可能存在，但不能由单目标样本外推到全部存量。
- falsifier: 执行 P-A；若 main 的 iteration 子树缺席、替换前后被指路径多重集相同，则“仅换锚点能降低 main 未核条数”的收益主张被推翻。P-A 在内存使用占位锚文本只验证缺席分类与计数，不把这些文本当可发布锚。
- verdict: FAIL（以降低 main 未核量为理由立即全量扩围的主张）；全量锚点语义等价性未验证。
- 判决证据: 系统＝本地 git＋登记册解析器；对象＝冻结 main、windows HEAD 与 P-A；探针进程 rc=0，P-A verdict=FAIL。rc=0 表示取得并验证了反例，不能被当成路径通过。

### 路径 B：只为正在改动的真实目标做逐条试点

- 动作集: 另行申请一个登记册条目的迁移；以真实的 MM-3 来源指针为样本，先核目标等价、插入稳定、重复锚与删锚拒绝，再决定是否发布该条。
- 选择点: 范围收为具名目标；启动条件是实测漂移或正在改动；新增逐条核验动作，不调整 main 缺席口径或棘轮。
- 依赖事实: fact: `docs/6-DECISIONS.md` 的 A-191 指向 MM-3 来源行，P-B 先由真实指针枚举确认样本存在，再调用现有解析器。inference: 一条可核样本使语义复核可控；它仅证明局部能力，不证明整批收益。
- 推演: 从真实目标行构造直接锚 → 在内存目标正文前插入测试行 → 锚解析移动但仍命中原文本，旧行号已不是原目标 → 重复同锚或删除目标时解析器拒绝。省略偏移，避免把段内行号依赖带回来。
- falsifier: 执行 P-B；只要原锚非唯一、插入后目标文本改变、重复锚未报 ambiguous、删锚未报 not-found，或源文件字节变化，就推翻该样本可安全试点的判断；探针断言失败返回非零。
- verdict: PASS（真实单目标的内存模拟）；登记册实际改写、引文语义复核及两个分支完整验收未验证。
- 判决证据: 系统＝Python＋现有 anchor-resolve.resolve；对象＝P-B 中真实 MM-3 来源目标；rc=0，P-B verdict=PASS；原始输出见下。本轮只验证方法，不执行试点迁移。

### 路径 C（维持现状）：保留旧指针，继续由现有闸门暴露漂移

- 动作集: 不迁存量、不改政策；运行现有登记册闸门，保留 WARN；出现具名漂移或新证据时，再把相应条目送入路径 B 的单条评估。
- 选择点: 本轮不改变登记册；由事实事件触发后续动作，不预先展开全量清理。
- 依赖事实: fact: P-C 真跑当前 windows 登记册闸门，返回 PASS，同时报告已有引文漂移 WARN。inference: 现有判据允许的漂移仍是维护成本，PASS 只说明未越现行拒绝条件；不能解释为零风险或无需再处理。
- 推演: 保持已接受基线 → 取登记册判决与 WARN → 当前没有必须靠全量迁移解除的 FAIL；保留小步处理通道，避免为没有证据的全局收益启动大改。
- falsifier: 运行 `.venv\Scripts\python.exe verify\verify_decision_register.py`；若出现具名坏指针、引文不符或越过现行允许窗口导致 FAIL，立即推翻“这份快照可继续保持”的判断，定位该条并交父代理裁决修复；不能用历史 PASS 兜底。
- verdict: PASS（当前 windows 快照符合现行闸门）；长期漂移成本、main 完整验收和未来目标变化未验证。
- 判决证据: 系统＝verify_decision_register；对象＝本次 windows 工作树；rc=0，DECISION-REGISTER PASS；存在 WARN，关键输出见下。

## 只读探针与现跑证据

在仓库根目录 PowerShell 执行。P-A 的占位替换只检验计数与分支缺席逻辑；
P-B 调用生产解析器，使用真实文件内容的内存副本；两者都不落盘。
代码中数字是探针输入或现算结果，输出是本次进程原样采集。

```powershell
@'
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import importlib.util,json,subprocess
from verify.verify_decision_register import POINTER_RE, ANCHOR_RE, _strip_fences

root=Path.cwd()
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
main=subprocess.check_output(['git','rev-parse','main'],text=True).strip()
tree=subprocess.check_output(['git','ls-tree','-r','--name-only',main,'--','docs/iteration'],text=True)
print('HEAD='+head)
print('MAIN='+main)
print('P-A main_iteration_present='+str(bool(tree.strip())))
body='\n'.join(_strip_fences(Path('docs/6-DECISIONS.md').read_text(encoding='utf-8').splitlines())[0])
refs=[m for m in POINTER_RE.finditer(body) if m.group(1).startswith('docs/iteration/')]
converted=POINTER_RE.sub(lambda m: m.group(1)+'#<TE-absence-probe>' if m.group(1).startswith('docs/iteration/') else m.group(0),body)
before=Counter(m.group(1) for m in refs)
after=Counter(m.group('path') for m in ANCHOR_RE.finditer(converted) if m.group('path').startswith('docs/iteration/'))
existing=Counter(m.group('path') for m in ANCHOR_RE.finditer(body) if m.group('path').startswith('docs/iteration/'))
assert after==before+existing
print('P-A old_iteration_pointers='+str(sum(before.values())))
print('P-A counted_paths_preserved='+str(after==before+existing))
print('P-A absent_reduction_from_syntax_only=0' if not tree.strip() else 'P-A absence claim requires re-evaluation')
spec=importlib.util.spec_from_file_location('mm3_anchor','scripts/anchor-resolve.py')
anchor=importlib.util.module_from_spec(spec)
spec.loader.exec_module(anchor)
rel='docs/iteration/phases/mental-models/cards/MM-3.md'
ptr=rel+'#<用户 2026-09-07>'
original=(root/rel).read_text(encoding='utf-8')
a=anchor.resolve(root,ptr)
assert a['status']=='ok'
matching=[m for m in refs if m.group(1)==rel and int(m.group(2))==a['line']]
assert matching, 'not a real existing registry pointer'
read_text=Path.read_text
def resolve_text(value):
    def redirected(p,*args,**kwargs):
        return value if p.resolve()==(root/rel).resolve() else read_text(p,*args,**kwargs)
    with patch.object(Path,'read_text',redirected):
        return anchor.resolve(root,ptr)
inserted=original.splitlines()
inserted[1:1]=['<!-- TE insertion probe -->']*5
b=resolve_text('\n'.join(inserted))
assert b['status']=='ok' and b['line']==a['line']+5
assert inserted[b['line']-1]==original.splitlines()[a['line']-1]
old_same=inserted[a['line']-1]==original.splitlines()[a['line']-1]
assert not old_same
ambiguous=resolve_text(original+'\n用户 2026-09-07\n')
deleted=resolve_text(original.replace('用户 2026-09-07','TE removed source'))
assert ambiguous['status']=='ambiguous' and deleted['status']=='not-found'
assert (root/rel).read_text(encoding='utf-8')==original
print('P-B pointer='+ptr)
print('P-B before_line='+str(a['line'])+' inserted_line='+str(b['line'])+' same_target=True old_line_same_target='+str(old_same))
print('P-B duplicate='+ambiguous['status']+' removed='+deleted['status']+' source_unchanged=True')
print('P-A verdict=FAIL (syntax change cannot lower branch absence)')
print('P-B verdict=PASS (one real target, in-memory insertion and rejection controls only)')
'@ | .venv\Scripts\python.exe -
```

本次 rc=0，原样输出：

```text
HEAD=5b22be5217597d510d223dc3fce4e74da8603178
MAIN=bc3121992a723f57abc5a3cd4b53090b97cbcafb
P-A main_iteration_present=False
P-A old_iteration_pointers=1106
P-A counted_paths_preserved=True
P-A absent_reduction_from_syntax_only=0
P-B pointer=docs/iteration/phases/mental-models/cards/MM-3.md#<用户 2026-09-07>
P-B before_line=13 inserted_line=18 same_target=True old_line_same_target=False
P-B duplicate=ambiguous removed=not-found source_unchanged=True
P-A verdict=FAIL (syntax change cannot lower branch absence)
P-B verdict=PASS (one real target, in-memory insertion and rejection controls only)
```

P-C 命令：`.venv\Scripts\python.exe verify\verify_decision_register.py`，rc=0。
以下为进程自动采集的判决行；EVIDENCE 机器证据行不抄入文档，详细 WARN 与断言读数以现跑为准：

```text
DECISION-REGISTER PASS：124 条条目（§3 21 / §4.1 103）；指针 1248 处（其中本分支不存在 0 处未核，行 39 棘轮上限 0 条〔分支判据 `docs/iteration` 在树里=True〕）；§4.1 引文-出处逐条核对 97 条、0 条不符（另 0 条因路径不在本分支未核；±2 内漂移 10 条，见 WARN）；待回填 0 条（见 WARN）
```

## 收敛

- 排序键: 当前收益看能否解除实际拒绝条件；变更代价看登记册需改的范围；可逆性看能否按具名条目复核回退；证据强度看真仓判决、单目标模拟或尚未执行。范围是动作集的性质，不把未测量工时写成数字。
- 排序: 当前执行 C；有具名漂移或获准小切片时评估 B；A 暂不采纳。P-B 的局部成功与 P-C 的漂移 WARN 说明锚点有局部价值，P-A 则否证了以 main 未核下降为理由的全量收益。没有把“全量一定失败”或“保持现状永远最优”当事实。
- 建议: **本轮不扩展到 iteration 存量的整体迁移；维持 C，后续仅对实测漂移或正在改动的具名条目另行提审 B。**
- 采纳条件: 若新证据能证明局部条目的维护收益、锚点唯一性、原目标等价、两分支计数不变且获得父代理/用户批准，则采用 B；否则维持 C。A 还须补全量逐目标等价与收益证据，不能用本记录代替。
- 若结论错误会先在哪一步暴露: C 的下一次登记册判决最先暴露具名坏指针或引文不符；B 在“原目标 → 唯一锚”的预检就会因重复/删锚失败；若 main 已新增 iteration 文件，P-A 的树检查先翻转，本记录的分支缺席论据立即失效，必须重跑而非沿用。
- 未验证项: 未 fetch 远端；未在 main checkout 跑完整登记册闸门；未迁真实指针；未验证所有目标的锚点与引文等价；未测量长期维护耗时。P-A 的全路径计数模拟不等于 main 完整闸门，P-B 单样本也不代表全量证明（F6）。
- adoption: **本轮维持既定 C，否决本轮执行迁移**；裁决依据＝用户本卡派单明确只做 MM-3、禁止改登记册，日期＝2026-11-15（上述网络时间）。执行者只提出翻案评估，**新增政策采纳与 B 的执行批准均未裁决，裁决人待父代理/用户回填**；不冒称已获新的政策决定。

## 记录自检

F1：选择点同时改变范围、启动条件和核验动作，含维持现状；F2：事实均有源文件或探针；
F3：逐路径 falsifier 可执行；F4：区分探针 rc 与路径判决；F5：显式翻案评估并保留生效基线；
F6：声明 main 与全量未验证。形式机检复用 MM-6 §6.2：

```powershell
$f = 'docs/iteration/phases/mental-models/experiments/2026-11-15-TE-001.md'
$paths = @(Select-String -Path $f -Pattern '^### 路径' -Encoding utf8).Count
$fals = @(Select-String -Path $f -Pattern '^- falsifier:' -Encoding utf8).Count
$naked = @(Select-String -Path $f -Pattern '^- falsifier:\s*(理论|可能|也许|待补|TODO|不可执行)' -Encoding utf8).Count
"paths=$paths falsifiers=$fals naked=$naked"
if ($paths -ne $fals -or $naked -ne 0) { '无效'; exit 1 } else { 'PASS' }
```

读数以现跑为准，自动采集结果回填 MM-3 落地节与 run 报告；
MM-3 卡对本记录的引用是交付消费者，不声称父代理已采纳政策建议。


## 补充证据与裁决规范化（lead，2026-11-15）

执行者记录（本文件上半部）未在 main checkout 跑完整登记册闸门，并把部分"未验证"折叠进 PASS/FAIL 括号里；
本节补上缺的证据，并按 MM-6 §2.4 把 verdict 规范化为三态之一（未验证部分单列）。

### 补充证据：main 形态的真判决

- 系统：`verify/verify_decision_register.py`，运行于 `git worktree add --detach %TEMP%\mainshape origin/main`（main `945286a`）
- 时点读数（带 sha，main `945286a`，2026-11-15 现跑）：`quotes_checked=9`、`quotes_drift=0`、`pointers=1248`、`rc=0`；字段名与格式以 `verify/verify_decision_register.py` 的现跑末行为准。
- 判决：main 形态下 `pointers=1248` 仍全量计数，但可核引文从 windows 的 97 降到 **9**（其余指向缺席的 `docs/iteration/**`）；`quotes_drift=0` 不是"没有漂移"，而是**漂移不可测**。rc=0 ⇒ 闸门在 main 形态保持绿。
- 指针分实现跑（windows `5b22be5`）：`docs/6-DECISIONS.md` 的 `path:line` 指针共 **1191** 处，其中 `docs/iteration/**` **1106**、非 iteration **85**。

### verdict 规范化（三态，不折叠）

| 路径 | 原写法 | 规范化 |
|---|---|---|
| A 全量迁移 | `FAIL（…）；全量锚点语义等价性未验证。` | **FAIL**（"以降低 main 未核量为理由全量扩围"被 main 形态读数直接否证）；语义等价性未验证 → 移入未验证项 |
| B 局部试点 | `PASS（…）；真实改写未验证。` | **PASS**（单目标内存模拟）；真实改写与两分支验收未验证 → 移入未验证项 |
| C 维持现状 | `PASS（…）；长期漂移未验证。` | **PASS**（现行快照过闸门）；长期漂移成本未验证 → 移入未验证项 |

### lead 裁决

- 同意主建议：**维持 C**（不整体迁移 iteration 存量指针）；A 以 main 未核下降为理由被否证。
- B 的**局部试点**不在本记录授权内：它需要改 `docs/6-DECISIONS.md` 条目，属用户/父代理批准范围（与本轮"禁止改登记册"一致）。
- 本记录的 adoption 记在"收敛"节；本节只补证据与规范化，不改变原结论。
