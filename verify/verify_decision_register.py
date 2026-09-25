#!/usr/bin/env python3
"""决策登记册机检（`TG-20` ③④⑤，2026-09-25 D6）。

## 为什么要这条闸门

`docs/6-DECISIONS.md` 是**用户裁决的唯一登记处**：任何其它文档引用裁决时只引条目号，
原文只存在那里。它此前是**纯人工维护**的——"字段填没填全、状态词合法不合法、
`path:line` 指针还指不指得着、§4.1 的逐字引文是否真的出自它标注的那一行"全靠人读。
2026-09-25 的实测：里面曾有 **6 处 `path:line` 指针漂移**（复核 `run-…-083` minor
发现），
而 §4.1 的 103 条逐字引文此前只被**人工抽查**过一次。

## 判据（`③ 机检判据`）

1. **章节在位**：`§1 字段定义` / `§2 提问纪律` / `§3` / `§4.1` / `§4.2` / `§4.3` / `§5`
/ `§6` 必须存在；
2. **条目字段齐全**：每个 `### <条目号>` 条目必须有全部 8 个字段标签（`§1`
的字段定义即契约）；
3. **状态词受控**：`生效状态` 的值必须以文件头的受控状态词开头
   （`生效`/`已被取代`/`失效`/`待裁定`/`进行中`/`已答复`/`待回填`）；
4. **被取代必须指向存在的条目**：`[已被 <条目号> 取代（日期）]` 里的 `<条目号>`
必须在本文件里真的存在
   （指向"别的文档/卡"时按具名引用处理，不要求是同文件条目，但要写得出文档名）；
5. **指针可核**：全文出现的 `path:line` 指针，路径必须存在、行号必须在文件行数内（`0 <
line <= N`）；
6. **引文 ↔ 出处（§4.1 专项）**：逐字引文必须能在它标注的 `path:line`**该行或相邻 ±2
行**里找到
   （规范化：去空白、去引号差异）——这是"引文可核"而不是"指针存在"；
7. **待回填可见**：`待回填`/`未验证（待补）`
的**条数与条目号**必须打印出来（**不是**问题项，
   但"没回填"必须看得见，且 §5/§6 必须与读数一致）。

## 反向对照（`--selftest`，4 条）

(a) 少一个字段 ⇒ FAIL；(b) 状态词不在受控表内 ⇒ FAIL；(c) 指针指向不存在的文件 ⇒ FAIL；
(d) §4.1 引文与出处行不符 ⇒ FAIL；外加 (e) 干净 fixture ⇒ 零问题（防假红）。
fixture 全部落在 `%TEMP%`（闸门自身不改仓库文件）。

## 用法

```
.venv\\Scripts\\python.exe verify\\verify_decision_register.py            # 真数据
.venv\\Scripts\\python.exe verify\\verify_decision_register.py --selftest # 只跑反向对照
```

rc: 0=通过（含"只有 WARN"）/ 1=有 FAIL / 2=用法或政策错误。
"""

from __future__ import annotations

VERIFY_META = {
    'features': '决策登记册机检（TG-20 ③④⑤）：章节在位 / 条目 8 字段齐全 / '
                '受控状态词 / 被取代指向存在的条目 / path:line 指针可核 / '
                '§4.1 引文↔出处逐条核对 / 待回填可见；含 9 条反向对照自检',
    'tier': 'offline', 'providers': [], 'est_cost_cny': 0, 'est_seconds': 5,
    'routes': [], 'requires': ['none'],
}

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.agent_policy import path_in_head  # noqa: E402

if not __debug__:  # noqa: SIM108 —— -O/PYTHONOPTIMIZE 会剥离 assert；守卫必须是普通语句，不能是 assert
    raise SystemExit("本闸门不得在 -O/PYTHONOPTIMIZE 下运行（`__debug__` 为 False ⇒ "
    "判据会被整体剥离）——见 3-LEARNED 1.65")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REGISTER_REL = "docs/6-DECISIONS.md"
SECTIONS = ("## 1. 字段定义", "## 2. 提问纪律", "## 3. ", "## 4. ", "## 4.1 ",
            "## 4.2 ", "## 4.3 ", "## 5.", "## 6.")
FIELDS = ("原文", "出处", "时点", "主代理归纳", "生效状态", "证据", "验证时间戳",
          "违背事故")
STATUS_WORDS = ("生效", "已被取代", "失效", "待裁定", "进行中", "已答复", "待回填")
ENTRY_RE = re.compile(r"^### (?P<id>D-\d{6}-\d+|V-\d+)\b(?P<title>.*)$", re.MULTILINE)
FIELD_RE = re.compile(r"^[-*]\s*(?P<name>[^:：]+?)\s*[:：]\s*(?P<value>.*)$")
# `path:line` 指针（只认仓库里的真实目录前缀，避免把 `2026-09-25 15:52` 之类当指针）
POINTER_RE = re.compile(
    r"`?((?:docs|agents|scripts|verify|src|paper-qa-script|\.github)/[^\s`：:，,）)]+?)"
    r":(\d+)(?:-\d+)?`?")
QUOTED_RE = re.compile(r"[「『\"“](?P<body>[^」』\"”]{2,})[」』\"”]")
SUPERSEDE_RE = re.compile(r"\[已被\s*(?P<who>[^\]\s]+)\s*取代")
PASSED = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    """自检断言：通过则计数并打印，失败则抛错
    （**不用裸 `assert`**——`-O` 会把它整体剥离）。"""
    global PASSED
    if cond:
        PASSED += 1
        print(f"PASS: {name} {detail}")
        return
    print(f"FAIL: {name} {detail}")
    raise AssertionError(f"{name} FAIL: {detail}")


def _norm(text: str) -> str:
    """规范化用于引文比对：去空白、统一引号、去 `**` 强调符。"""
    text = text.replace("**", "").replace("`", "")
    text = re.sub(r"[\s\u3000]+", "", text)
    return text


def _canon_field(name: str) -> str:
    """字段名归一：去掉**所有** `（…）` 限定语（`原文（逐字，选项式）` → `原文`）。

    2026-09-25 D6 实测两次：① 按**字面**比 ⇒ 把 4 条合法条目（`原文（逐字，选项式）`、
    `主代理归纳（拆两条）`、`原文（逐字，本会话消息片段）`）误判成"缺字段"；
    ② 只剥**末尾**一层括号 ⇒ 连规范写法 `原文（逐字）` 也被剥成
    `原文`，**全部条目**一起误报。
    误报与漏报一样是缺陷——归一化的判据必须对"带不带限定语"都成立，故这里剥到底、
    并把契约表也按同一口径归一（`FIELDS` 写基名）。
    """
    return re.sub(r"（[^（）]*）", "", name).strip()


def _lines_of(path: Path) -> list[str]:
    """读文件的行列表（UTF-8、容错解码；比对用，失败即空表由调用方处理）。"""
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _pointers(src: str) -> list[tuple[str, int]]:
    """`出处` 里可能有**多个**指针（`；` 分隔）⇒ 全部取出来逐个试。"""
    out: list[tuple[str, int]] = []
    for m in re.finditer(
            r"((?:docs|agents|scripts|verify|src|paper-qa-script|\.github)/[^\s:；;，,）)]+)"
                         r":(\d+)", src):
        item = (m.group(1), int(m.group(2)))
        if item not in out:
            out.append(item)
    return out


def _quote_fragments(body: str) -> list[str]:
    """逐字引文可能用 `｜｜` 分段（登记册自带说明）⇒ 取够长的片段逐个核。"""
    parts = [p for p in re.split(r"｜｜", body)]
    return [p for p in parts if len(_norm(p)) >= 4]


def parse_entries(text: str) -> list[dict]:
    """把登记册切成条目：`[{id, title, pos, block, fields}]`
    （`fields` = 字段基名 → 值）。"""
    marks = [(m.start(), m.group("id"), m.group("title").strip())
             for m in ENTRY_RE.finditer(text)]
    out: list[dict] = []
    for i, (pos, rid, title) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        block = text[pos:end]
        fields: dict[str, str] = {}
        for line in block.splitlines()[1:]:
            m = FIELD_RE.match(line.strip())
            if m:
                name = _canon_field(m.group("name"))
                fields.setdefault(name, m.group("value").strip())
        out.append({"id": rid, "title": title, "pos": pos, "block": block,
                    "fields": fields})
    return out


def check_register(root: Path, rel: str = REGISTER_REL, *,
                   doc: Path | None = None) -> dict:
    """真数据判据：返回 `{"problems": [...], "warns": [...], "stats": {...}}`。

    `doc` 用于自检（把 fixture 登记册指到 `%TEMP%` 的字面量落点）；真数据走 `root /
    rel`。
    指针/引文的**解析根**始终是 `root`（自检打真仓库文件，夹具自身不造"假源文件"）。
    """
    problems: list[str] = []
    warns: list[str] = []
    path = Path(doc) if doc is not None else root / rel
    if not path.is_file():
        # 两种"不存在"必须分开（修复验证复核 `run-…-089` major 1d(b) 的实测）：
        #   * **在 HEAD 的树里存在、工作区没有** ⇒ **被删** ⇒ FAIL（与同批的指针判据、
        #     与 `md_tables` 的条件根口径一致——旧码在这里走 SKIP rc=0，方向反了）；
        #   * HEAD 里也没有（`main`/同步分支按设计没有这份 windows-only 治理文档）
        #     ⇒ **具名 SKIP**（判决行不得打 PASS、不得打印 `EVIDENCE:`）。
        if doc is None and path_in_head(root, rel):
            return {"problems": [f"{rel} 在 `HEAD` 的提交树里存在、工作区却不存在 "
                                 f"⇒ **被删**"
                                 f"（不是分支差异）——决策登记册是裁决的唯一登记处，"
                                 f"删除即 fail-closed"],
                    "skipped": False, "stats": {}, "warns": []}
        return {"problems": [], "skipped": True, "stats": {},
                "warns": [f"{rel} 不在本分支（windows-only 治理文档）⇒ "
                          f"本次机检**未执行**"
                          f"（**不是通过**；windows 上必须存在并按全部判据核）"]}
    text = path.read_text(encoding="utf-8", errors="replace")
    _lines = text.splitlines()
    for section in SECTIONS:
        # 章节必须在**行首**出现（二查 `run-…-087` minor 5：子串测试能被正文/围栏里的
        # 同名字样满足 ⇒ "章节在位"这条判据形同虚设）
        if not any(line.startswith(section) for line in _lines):
            problems.append(f"[章节] 缺 {section!r}（登记册的结构契约；"
                            f"删章节等于删判据；只认**行首**标题，正文提及不算）")
    entries = parse_entries(text)
    if not entries:
        problems.append("[条目] 一个条目都没解析出来（解析口径或文件结构变了 ⇒ "
        "fail-closed）")
    ids = {e["id"] for e in entries}
    # 归纳标记词（`TG-20` ③(v)：原文块里**不得**混排主代理的归纳）
    induction_marks = ("我认为", "这意味着", "结论是", "主代理归纳", "我判断", "即：")
    for e in entries:
        # ② 字段**标签在场**还不够，值必须**非空**（二查 `run-…-087` major 4：8
        # 个空值标签
        # 也能 PASS ⇒ "空值条目既不算已核也不算待回填"，等于把登记册变成一张空表）。
        # 允许的"空"是**显式占位**（`待回填` / `未验证（待补）` / `无`），它们非空。
        missing = [f for f in FIELDS
                   if f not in e["fields"] or not e["fields"][f].strip()]
        if missing:
            problems.append(f"[字段] {e['id']} 缺字段或值为空：{'、'.join(missing)}"
                            f"（§1 的字段定义即契约；无值请写 "
                            f"`待回填`/`未验证（待补）`）")
        quote = e["fields"].get("原文", "")
        src = e["fields"].get("出处", "")
        # ③(iv)：出处必须是**可定位的指针**，或显式的"会话"形态（§1 只认这两种）
        if src and not _pointers(src) and "会话" not in src and "待回填" not in src:
            problems.append(f"[出处] {e['id']} 的出处既不是 `path:line` "
            f"指针、也不是显式的『会话』形态："
                            f"{src[:40]!r}（§1 只认这两种；出处不可核 = 引文不可核）")
        # ③(v)：原文块与归纳区**不得同段混排**
        hit_marks = [m for m in induction_marks if m in quote]
        if hit_marks:
            problems.append(f"[原文纯洁性] {e['id']} 的 `原文` 里出现归纳标记词 "
            f"{hit_marks}"
                            f"——原文区只放逐字引用，归类/影响判断一律写到独立的 "
                            f"`主代理归纳` 行")
        status = e["fields"].get("生效状态", "")
        status_norm = _norm(status)
        if status_norm and not any(status_norm.startswith(w) for w in STATUS_WORDS):
            problems.append(f"[状态词] {e['id']} 的生效状态={status[:30]!r} "
            f"不在受控状态词表内"
                            f"（{list(STATUS_WORDS)}）——状态词是机检的唯一入口，不许自创")
        # **必须用归一化后的状态词**（二查 `run-…-087` major 2 的实测）：真条目
        # `docs/6-DECISIONS.md:84` 写的是 `**已被取代** [已被 … 取代（…）]`，
        # 未归一时 `status.startswith("已被取代")` 为假 ⇒ **整段取代判据根本不执行**
        # （raw=1 条 vs 归一后 2 条）。同族：只用"去掉 `**`"就够，但要用**同一处**归一。
        if status_norm.startswith("已被取代"):
            m = SUPERSEDE_RE.search(status)
            if not m:
                problems.append(f"[取代] {e['id']} 标了『已被取代』却没有 "
                                f"`[已被 <条目号> 取代（日期）]` 标注")
            else:
                who = m.group("who")
                if re.fullmatch(r"(D-\d{6}-\d+|V-\d+)", who) and who not in ids:
                    problems.append(f"[取代] {e['id']} 的取代方 {who} 在本文件里不存在"
                                    f"（指向不存在的条目 = 悬空取代）")
    # 指针可核（全文）。**分支差异 ≠ 漂移**（二查 `run-…-088` critical 1）：
    # 登记册里大量指针指向 `docs/iteration/**`（windows-only）⇒ 在没有该子树的分支上
    # 不能判 FAIL，只能**具名跳过**（否则 G2 的同步 PR 会让 main 的 CI 变红，650 项）。
    # 但"未核"必须**收窄到真正不存在的子树**（修复验证复核 `run-…-089` major 1d(a)
    # 的实测：
    # 首版把**打错/改名的路径**也算成未核 ⇒ 旧码 FAIL、新码 PASS，判据被自己放宽了）。
    # 三层判据（证据都是 git）：
    #   * 该路径在 `HEAD` 树里存在 ⇒ **被删** ⇒ FAIL；
    #   * 该路径**父目录**在 `HEAD` 树里存在 ⇒ 同级目录里没有这个名字 =
    #     **打错/改名/漂移** ⇒ FAIL；
    #   * 父目录也不在树里（如 `docs/iteration/**` 在 main）⇒ 真·分支差异 ⇒ 记未核。
    pointers: list[tuple[str, int, str]] = []
    for m in POINTER_RE.finditer(text):
        pointers.append((m.group(1), int(m.group(2)), m.group(0)))
    bad_ptr = 0
    absent_ptr = 0
    for relp, line, raw in pointers:
        target = root / relp
        if not target.is_file():
            if path_in_head(root, relp):
                problems.append(f"[指针] {raw} 在 `HEAD` 的提交树里存在、"
                                f"工作区却不存在 ⇒ "
                                f"被删（不是分支差异）")
                bad_ptr += 1
            elif path_in_head(root, str(Path(relp).parent).replace("\\", "/")):
                problems.append(f"[指针] {raw} 指向的文件不存在，"
                                f"而它的目录在 `HEAD` 里存在 ⇒ "
                                f"**打错或改名**（同级目录里没有这个名字）→ "
                                f"fail-closed，"
                                f"不得当成分支差异放行")
                bad_ptr += 1
            else:
                absent_ptr += 1        # 本分支没有这条路径 ⇒ 未核（计数可见，不当通过）
            continue
        total = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
        if line < 1 or line > total:
            problems.append(f"[指针] {raw} 的行号越界（该文件只有 {total} 行）")
            bad_ptr += 1
    # §4.1 引文 ↔ 出处：出处可给**多个**指针（`；` 分隔），引文可用 `｜｜` 分段
    # ⇒ 逐段核对"该段能否在**任一**指针的邻域里找到"（首版只取第一个指针、不拆段 ⇒ 16
    # 条误报）。
    v_entries = [e for e in entries if e["id"].startswith("V-")]
    checked = 0
    unverifiable = 0
    mismatch: list[str] = []
    for e in v_entries:
        # 字段名一律用**基名**（见 `_canon_field`）
        quote = e["fields"].get("原文", "")
        src = e["fields"].get("出处", "")
        m_q = QUOTED_RE.search(quote)
        ptrs = _pointers(src)
        if not m_q or not ptrs:
            continue                     # 非仓内出处（会话/待回填）不在此判据内
        # **本分支没有的路径**（如 main 上的 `docs/iteration/**`）⇒
        # 这条引文本次**核不了**：
        # 计入 `unverifiable`（可见），不计入"已核 0 条"的空转守卫，也不判 FAIL。
        if not any((root / relp).is_file() for relp, _ln in ptrs):
            unverifiable += 1
            continue
        fragments = _quote_fragments(m_q.group("body"))
        if not fragments:
            # 片段太短（如"现在修"）⇒ 核它没有意义，跳过并不算通过
            continue
        checked += 1
        for frag in fragments:
            want = _norm(frag)
            hit = ""
            for relp, ln in ptrs:
                target = root / relp
                if not target.is_file():
                    continue             # 文件不存在由指针判据点名，这里不重复计
                lines = _lines_of(target)
                window = lines[max(0, ln - 3):ln + 2]
                if any(want in _norm(x) for x in window):
                    hit = f"{relp}:{ln}"
                    break
            if not hit:
                tried = "、".join(f"{p}:{n}" for p, n in ptrs[:3])
                # **漂移提示**：指针没命中时，顺手在**整个文件**里找一次
                # ——找到就报出当前行号，
                # 让"指针漂移"变成一条可执行修复（本仓实测：我在 §6 插入新规则后，
                # 后面所有 `1-WORKFLOW.MD:NNN`
                # 指针整体下移，登记册里两条逐字引文当场失配）。
                where = ""
                for relp, _ln in ptrs:
                    target = root / relp
                    if not target.is_file():
                        continue
                    for idx, text_line in enumerate(_lines_of(target), 1):
                        if want in _norm(text_line):
                            where = f"（现位于 {relp}:{idx} ⇒ 建议改指针）"
                            break
                    if where:
                        break
                mismatch.append(f"{e['id']}：引文片段 {frag[:24]!r} 不在任何标注位置"
                                f"（{tried}）的 ±2 行内{where}")
    if mismatch:
        problems.append(f"[引文↔出处] {len(mismatch)} 条逐字引文在标注位置找不到："
                        + "；".join(mismatch[:5])
                        + ("…" if len(mismatch) > 5 else ""))
    # **空转守卫**（2026-09-25 D6 实测踩到）：字段名归一化改了以后，取值用的还是旧键名
    # ⇒ `quote` 恒为空 ⇒ 一条都没核，而判决行照样打印"核对 0 条、0 条不符"=
    # **看起来通过**。
    # "应核 0 条"与"该核的都没核"必须能区分：有仓内出处的 §4.1 条目 > 0 而 checked == 0
    # ⇒ FAIL。
    in_repo = [e for e in v_entries
               if any((root / p).is_file()
                      for p, _ln in _pointers(e["fields"].get("出处", "")))]
    if in_repo and checked == 0:
        problems.append(f"[引文↔出处] {len(in_repo)} 条 §4.1 "
        f"条目带**本分支可核**的出处、"
                        f"却**一条都没被核对**（判据空转：取值键名/解析口径被改坏时会出现"
                        f"这种『看起来通过』）")
    pending = [e["id"] for e in entries
               if e["fields"].get("生效状态", "").startswith("待回填")
               or e["fields"].get("验证时间戳", "").startswith("待回填")
               or "未验证" in e["fields"].get("验证时间戳", "")]
    if pending:
        warns.append(f"{len(pending)} 条条目仍是待回填/未验证（前 8 条：{pending[:8]}）"
                     f"——回填前不得引用为已核生效裁决")
    if absent_ptr or unverifiable:
        warns.append(f"本分支不存在的路径：指针 {absent_ptr} 处未核、引文 "
        f"{unverifiable} 条未核"
                     f"（分支差异；windows 上这些**全部**要核，见 `summary` 的 0/0）")
    stats = {"entries": len(entries),
             "section3": sum(1 for e in entries if e["id"].startswith("D-")),
             "section41": len(v_entries), "pointers": len(pointers),
             "bad_pointers": bad_ptr, "pointers_branch_absent": absent_ptr,
             "quotes_checked": checked, "quotes_unverifiable": unverifiable,
             "quotes_mismatch": len(mismatch), "pending": len(pending)}
    return {"problems": problems, "warns": warns, "stats": stats, "skipped": False}


def selftest() -> int:
    """9 条反向对照（fixture 写在 `%TEMP%` 的**字面量落点**上，不动仓库文件）。

    落点一律写成"`Path(tempfile.gettempdir())` +
    字面量"的**单一表达式**（不经变量中转），
    满足 `verify_artifact_paths.py` 对新脚本写盘目标的静态可判定要求——第一版用
    `tmp / REGISTER_REL` 与 `src.parent.mkdir()`，被该闸门当场判 FAIL 2 处。
    引文/指针的**读**仍打真仓库文件（`docs/6-DECISIONS.md:1`：标题行稳定、内容可核）。
    """
    # 引文与出处的对照源：用**真仓库文件**里稳定存在的一行（标题行），避免夹具自身漂移
    quote_src = "docs/6-DECISIONS.md:1"

    def build(fields: dict[str, str], src: str = quote_src) -> str:
        body = [f"## {n}" for n in ("1. 字段定义", "2. 提问纪律", "3. x", "4. x",
                                    "4.1 x", "4.2 x", "4.3 x", "5. x", "6. x")]
        body.append("## 4.1 逐字原话")
        body.append("### V-001 夹具")
        rows = {"原文": '"决策登记册"', "出处": src, "时点": "2026-01-01",
                "主代理归纳": "夹具（归纳只写在这一行）",
                "生效状态": "生效", "证据": src,
                "验证时间戳": "2026-01-01", "违背事故": "无"}
        rows.update(fields)
        for name in FIELDS:
            # `None` = **整条字段不写**（模拟漏字段）
            if name in rows and rows[name] is not None:
                body.append(f"- {name}: {rows[name]}")
        body.append("## 4.2 x")
        return "\n".join(body) + "\n"

    def run(text: str) -> dict:
        (Path(tempfile.gettempdir())
         / "decision-register-selftest.md").write_text(text, encoding="utf-8")
        return check_register(
            ROOT, doc=Path(tempfile.gettempdir()) / "decision-register-selftest.md")

    clean = run(build({}))
    ok("反向对照 e 干净 fixture（8 字段齐 + 引文与出处相符）→ 零 problem（防假红）",
       clean["problems"] == [], f"problems={clean['problems'][:1]}")
    ok("反向对照 e' 引文↔出处**真的核过**（quotes_checked ≥ 1，不是空转）",
       clean["stats"].get("quotes_checked", 0) >= 1, f"stats={clean['stats']}")
    missing = run(build({"时点": None}))
    ok("反向对照 a 少一个字段 ⇒ FAIL 且点名条目与字段",
       any("缺字段" in p and "V-001" in p for p in missing["problems"]),
       f"problems={missing['problems'][:1]}")
    bogus = run(build({"生效状态": "大概生效吧"}))
    ok("反向对照 b 状态词不在受控表内 ⇒ FAIL（状态词是机检入口，不许自创）",
       any("状态词" in p for p in bogus["problems"]),
       f"problems={bogus['problems'][:1]}")
    dangling = run(build({"出处": "docs/no-such-tree-xyz/a.md:3",
                          "证据": "docs/no-such-tree-xyz/a.md:3"}))
    ok("反向对照 c1 指针指向**本分支与 `HEAD` 都没有**的子树 ⇒ 记『未核』"
       "（`pointers_branch_absent`），不误判成漂移"
       "（二查 run-…-088 critical 1：登记册大量指针指向 windows-only 子树）",
       dangling["problems"] == []
       and dangling["stats"].get("pointers_branch_absent", 0) >= 1,
       f"problems={dangling['problems'][:1]} stats={dangling['stats']}")
    # 反向对照 c1′（**修复验证复核 `run-…-089` major 1d(a) 的原始形态**）：
    # 路径在**存在的
    # 同级目录**里查无此名 = 打错/改名 ⇒ 必须 FAIL（首版把所有"文件不存在"都算成未核
    # ⇒ 旧码 FAIL、新码 PASS，判据被自己放宽了）。
    typo = run(build({"出处": "docs/does-not-exist.md:3",
                      "证据": "docs/does-not-exist.md:3"}))
    ok("反向对照 c1′ 名字打错/改名（同级目录在 `HEAD` 里存在）⇒ FAIL，"
       "**不得**混进『未核』",
       any("打错或改名" in p for p in typo["problems"])
       and typo["stats"].get("pointers_branch_absent", 0) == 0,
       f"problems={typo['problems'][:1]}")
    # 反向对照 c2（**被删**才是 FAIL）：在 `%TEMP%` 的**真 git
    # 仓库**里提交一份文件再删掉
    # ⇒ `path_in_head()` 为真、工作区没有 ⇒ 必须 FAIL（真入口、真
    # git，不注入中间变量）。
    import subprocess as _sp
    repo = str(Path(tempfile.gettempdir()) / "decision-register-selftest-repo")
    _sp.run(["git", "init", "-q", repo], capture_output=True)
    (Path(tempfile.gettempdir()) / "decision-register-selftest-repo" / "docs").mkdir(
        parents=True, exist_ok=True)
    (Path(tempfile.gettempdir()) / "decision-register-selftest-repo" / "docs"
     / "gone.md").write_text("line 1\nline 2\n", encoding="utf-8")
    # 登记册**自身**也要有一份被提交过（供 c3 测"登记册被删"）
    (Path(tempfile.gettempdir()) / "decision-register-selftest-repo"
     / "register.md").write_text(build({}), encoding="utf-8")
    _sp.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    _sp.run(["git", "-C", repo, "-c", "user.name=t",
             "-c", "user.email=t@example.invalid",
             "commit", "-q", "-m", "fixture"], capture_output=True)
    (Path(tempfile.gettempdir()) / "decision-register-selftest-repo" / "docs"
     / "gone.md").unlink()
    (Path(tempfile.gettempdir()) / "decision-register-selftest.md").write_text(
        build({"原文": '"line 1"', "出处": "docs/gone.md:1", "证据": "docs/gone.md:1"}),
        encoding="utf-8")
    deleted = check_register(
        Path(repo), doc=Path(tempfile.gettempdir()) / "decision-register-selftest.md")
    ok("反向对照 c2 路径在 `HEAD` 里存在、工作区被删 ⇒ FAIL（『被删』与『分支差异』"
       "必须分开）",
       any("被删" in p for p in deleted["problems"]),
       f"problems={deleted['problems'][:1]}")
    # 反向对照 c3（**修复验证复核 `run-…-089` major 1d(b)**）：登记册**自身**在 HEAD 里
    # 存在、工作区被删 ⇒ 必须 FAIL（首版对此走"具名 SKIP rc=0"，
    # 方向与同批指针判据相反）。
    (Path(tempfile.gettempdir()) / "decision-register-selftest-repo"
     / "register.md").unlink()
    reg_deleted = check_register(Path(repo), rel="register.md")
    ok("反向对照 c3 登记册自身被删（HEAD 里有）⇒ FAIL，而不是 SKIP",
       any("被删" in p for p in reg_deleted["problems"])
       and not reg_deleted.get("skipped"),
       f"problems={reg_deleted['problems'][:1]} skipped={reg_deleted.get('skipped')}")
    wrong_quote = run(build({"原文": '"这句话在源文件里根本没有"'}))
    ok("反向对照 d §4.1 引文与出处行不符 ⇒ FAIL（引文可核 ≠ 指针存在）",
       any("引文↔出处" in p for p in wrong_quote["problems"]),
       f"problems={wrong_quote['problems'][:1]}")
    superseded = run(build({"生效状态": "已被取代 [已被 D-250925-99 "
    "取代（2026-01-01）]"}))
    ok("反向对照 f 『已被取代』指向不存在的条目 ⇒ FAIL（悬空取代）",
       any("取代方" in p for p in superseded["problems"]),
       f"problems={superseded['problems'][:1]}")
    # 二查 run-…-087 major 2 的**真实排版**：状态词带 `**` 加粗 ⇒
    # 必须走同一条归一化后再判
    bold = run(build({"生效状态": "**已被取代** [已被 D-250925-99 "
    "取代（2026-01-01）]"}))
    ok("反向对照 f′ 加粗形态 `**已被取代**` 也必须触发取代判据（未归一化会整段跳过）",
       any("取代方" in p for p in bold["problems"]),
       f"problems={bold['problems'][:1]}")
    # 二查 run-…-087 major 4：8 个标签齐全但**值全空** ⇒ 必须 FAIL（空表不是登记册）
    empty = run(build({k: "" for k in FIELDS}))
    ok("反向对照 i 8 个字段标签齐全但值全空 ⇒ FAIL（标签在场 ≠ 有内容）",
       any("值为空" in p for p in empty["problems"]),
       f"problems={empty['problems'][:1]}")
    bad_src = run(build({"出处": "我记得是在某份文档里"}))
    ok("反向对照 g 出处既非 `path:line` 也非『会话』形态 ⇒ FAIL（出处不可核 = "
    "引文不可核）",
       any("出处" in p for p in bad_src["problems"]),
       f"problems={bad_src['problems'][:1]}")
    mixed = run(build({"原文": '"请继续阶段 B"（我认为这句就是批准）'}))
    ok("反向对照 h `原文` 里混排归纳标记词 ⇒ FAIL（原文区与归纳区必须分离）",
       any("原文纯洁性" in p for p in mixed["problems"]),
       f"problems={mixed['problems'][:1]}")
    print(f"\nALL PASS ({PASSED} assertions)")
    return 0


def main() -> int:
    """真数据档：核对 `docs/6-DECISIONS.md`，随后跑自检（`--selftest` 只跑自检）。"""
    if "--selftest" in sys.argv:
        return selftest()
    report = check_register(ROOT)
    for w in report["warns"]:
        print(f"WARN: {w}")
    if report["problems"]:
        print(f"DECISION-REGISTER FAIL（{len(report['problems'])} 项）：")
        for p in report["problems"][:40]:
            print(f"  - {p}")
        if len(report["problems"]) > 40:
            print(f"  … 另有 {len(report['problems']) - 40} 项")
        return 1
    if report.get("skipped"):
        # M-B 口径：**没查**不许打印 PASS/`EVIDENCE:`（判决行自己说明原因）
        print("DECISION-REGISTER SKIP（本分支没有 `docs/6-DECISIONS.md`；"
              "真数据判据**未执行**——**不是通过**）")
        return 0
    s = report["stats"]
    print(f"DECISION-REGISTER PASS：{s.get('entries')} 条条目（§3 {s.get('section3')} "
    f"/ §4.1 "
          f"{s.get('section41')}）；指针 {s.get('pointers')} 处（其中本分支不存在 "
          f"{s.get('pointers_branch_absent')} 处未核）；§4.1 引文-出处逐条核对 "
          f"{s.get('quotes_checked')} 条、{s.get('quotes_mismatch')} 条不符"
          f"（另 {s.get('quotes_unverifiable')} 条因路径不在本分支未核）；"
          f"待回填 {s.get('pending')} 条（见 WARN）")
    rc = selftest()
    if rc == 0:
        print(f"EVIDENCE: verify_decision_register.py assertions={PASSED} rc=0 "
              f"entries={s.get('entries')} quotes_checked={s.get('quotes_checked')}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
