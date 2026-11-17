# 验收记录（AC）

建 PR 前，由独立于实现者的 acceptance-review 执行者按增量走查清单逐项跑机检，
返回 AC 正文，由主代理落盘。分类、记录目录、判决语义、人工签收档匹配规则的
唯一真源是 `agents/policy.json::acceptance_review`；职能见
`agents/functions/acceptance-review.md`，建 PR 规则见 `docs/1-WORKFLOW.MD` §3。

文件命名为 `AC-<网络日期>-<slug>.MD`。日期用 `python scripts/now-network.py` 现取。
同一完整 range 默认只能匹配一份记录；需要选定修订记录时显式传 `--record`。

```text
range: <A 的完整 40 位 sha>..<B 的完整 40 位 sha>
classification: <闸门输出的分类>
verdict: <PASS 或 FAIL 或 NEEDS-HUMAN>
walkthrough: <production 必填的既有用户签收档相对路径>

## checklist
- item: <清单项名称> | reading: <执行命令；rc；实测输出摘录> | verdict: PASS
```

每项必须有实测读数；空值、单独写 PASS、写“我检查过了”均不成立。任何失败项都
阻止建 PR，整份记录不得 PASS。依赖缺失属于“未验证”，保留清单项及原因，写
`reading: 未验证: <原因> | verdict: 未验证`，整份用 NEEDS-HUMAN；此记录会被闸门
阻断，待环境补齐后重跑，不能把未验证伪装成实测 FAIL 或 PASS。

production 命中优先，未匹配文件默认 production。新增脚本白名单只认状态 A，
修改或删除既有脚本仍属 production；改名按删除与新增分别分类。政策中
`docs/iteration/phases/**` 覆盖 mental-models 三个子目录的 non-production 声明，
因此它们当前仍属 production。新增类别在政策 `categories` 增加一个 category 键、
对应 globs 和执行参数，闸门按数据读取。

```powershell
python verify/verify_acceptance_record.py --range <A..B> --record <AC记录相对路径>
python verify/verify_acceptance_record.py --selftest
```

不带参数时检查 `origin/main..HEAD`；不传 `--record` 时在政策目录内查找匹配 range
的 AC 文件。两端都会解析为完整 sha，记录必须逐字一致。production 的记录仍为
NEEDS-HUMAN，并引用命中 `walkthrough_glob` 的既有签收档，档内须含 B 的完整 sha
或 B 提交时间折算 UTC+8 的日期。机器检查引用和标识，签收真实性由用户承担；
代理不得新增或改写用户签名。闸门成功只说明该记录满足建 PR 条件。

闸门只读已提交 delta 和磁盘记录，不纳入工作树未提交变更。AC 可以在被验收提交
之后落盘，避免“提交 sha 必须包含引用自己的记录”的循环；将 AC 文件本身纳入后续
delta 时照常按政策分类，无特殊豁免。套件只执行 `--selftest`，其 PASS 不等于当前
delta 已验收；建 PR 前必须另外执行真实 range 检查。

机检能验证记录结构、读数缺失、分类及引用一致性，不能证明任意自由文本读数为真，
也不读取派单外的清单来推断是否漏项；执行者须完整保留 `checklist_path` 和命令日志，
便于独立抽检。断言数与反向对照读数以自测命令当次输出为准。
