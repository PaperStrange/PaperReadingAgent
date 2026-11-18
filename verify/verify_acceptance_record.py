"""Read-only acceptance gate; classification data lives in agent policy.

The default command checks a committed delta. --selftest runs the same check()
against temporary Git objects and records; it does not accept the current work.
Record syntax and the human-signoff boundary are described in the record README.
Range semantics: use origin/main..HEAD for main landability; for a pre-PR batch
acceptance pass the windows-side commit window (last sync source..HEAD), otherwise
docs/iteration files that are merely absent from main are misclassified as changes.
"""
from __future__ import annotations

VERIFY_META = {
    "features": (
        "Acceptance record: classification, exact range, measured checklist, "
        "verdict consistency, fail-closed parsing; suite runs --selftest only; "
        "ALL PASS (N assertions)"
    ),
    "tier": "offline",
    "providers": [],
    "est_seconds": 8,
    "est_cost_cny": 0,
    "routes": [],
    "requires": ["git"],
}

import argparse
import fnmatch
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from verify.harness import finish, ok

if not __debug__:
    raise SystemExit("ACCEPTANCE FAIL: -O/PYTHONOPTIMIZE is forbidden")

POLICY_REL = "agents/policy.json"
SHA_RANGE = re.compile(r"[0-9a-f]{40}\.\.[0-9a-f]{40}")
ITEM = re.compile(
    r"- item:\s*(.*?)\s*\| reading:\s*(.*?)\s*\| verdict:\s*(\S+)\s*"
)


def git(root: Path, *args: str, stdin: str | None = None) -> str:
    """Run local Git and reject every nonzero exit instead of using partial data."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        input=stdin.encode("utf-8") if stdin is not None else None,
        capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(f"git {args[0]} rc={result.returncode}: {result.stderr}")
    return result.stdout.decode("utf-8")


def local_path(root: Path, value: str) -> Path:
    """Accept repository-relative paths only, including after symlink resolution."""
    if not value or "\\" in value or ":" in value:
        raise ValueError(f"unsafe relative path: {value!r}")
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes repository: {value!r}")
    return target


def matches(path: str, pattern: str) -> bool:
    """Match Windows paths case-insensitively; **/ also admits zero directories."""
    def walk(parts: list[str], patterns: list[str]) -> bool:
        """Only ** crosses directory separators; ordinary * stays in a segment."""
        if not patterns:
            return not parts
        if patterns[0] == "**":
            return walk(parts, patterns[1:]) or bool(
                parts and walk(parts[1:], patterns)
            )
        return bool(parts and fnmatch.fnmatchcase(parts[0], patterns[0])
                    and walk(parts[1:], patterns[1:]))

    return walk(path.casefold().split("/"), pattern.casefold().split("/"))


def load_config(root: Path) -> dict:
    """Validate classification data before inspecting any record."""
    data = json.loads((root / POLICY_REL).read_text(encoding="utf-8"))
    cfg = data["acceptance_review"]
    categories = cfg["categories"]
    if not isinstance(categories, dict) or not categories:
        raise ValueError("policy categories must be a nonempty object")
    verdicts = cfg["verdicts"]
    if not isinstance(verdicts, dict) or not all(verdicts.values()):
        raise ValueError("policy verdicts require semantic descriptions")
    priorities = []
    for name, rule in categories.items():
        for values in (cfg[rule["globs_key"]], rule["added_only_globs"]):
            if not isinstance(values, list) or any(
                not isinstance(v, str) or not v for v in values
            ):
                raise ValueError(f"policy {name}: invalid globs")
        if not cfg[rule["globs_key"]]:
            raise ValueError(f"policy {name}: empty globs")
        priority = rule["priority"]
        if type(priority) is not int or priority in priorities:
            raise ValueError(f"policy {name}: invalid/duplicate priority")
        priorities.append(priority)
        if type(rule["requires_walkthrough"]) is not bool:
            raise ValueError(f"policy {name}: requires_walkthrough must be bool")
        if rule["record_verdict"] not in verdicts:
            raise ValueError(f"policy {name}: unknown record_verdict")
    fallback = categories[cfg["default_category"]]
    if not fallback["requires_walkthrough"]:
        raise ValueError("policy default category must require human signoff")
    local_path(root, cfg["record_dir"])
    local_path(root, cfg["walkthrough_glob"])
    return cfg


def classify(cfg: dict, files: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Classify every changed path, then use the highest-priority category."""
    categories = cfg["categories"]
    order = sorted(categories, key=lambda k: categories[k]["priority"], reverse=True)
    chosen, readings = [], []
    for status, path in files:
        category = cfg["default_category"]
        for name in order:
            rule = categories[name]
            restricted = any(matches(path, g) for g in rule["added_only_globs"])
            if restricted and status != "A":
                continue
            if any(matches(path, g) for g in cfg[rule["globs_key"]]):
                category = name
                break
        chosen.append(category)
        readings.append(f"[1 classification] {status} {path} => {category}")
    category = max(
        chosen or [cfg["default_category"]],
        key=lambda k: categories[k]["priority"],
    )
    return category, readings


def parse_record(text: str) -> tuple[dict, list[tuple[str, str, str]], list[str]]:
    """Parse a small, strict Markdown record without a YAML dependency."""
    fields, items, problems = {}, [], []
    checklist = False
    in_checklist = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower() == "## checklist":
            if checklist:
                problems.append("[5 parse] duplicate checklist")
            checklist = in_checklist = True
            continue
        if stripped.startswith("#"):
            in_checklist = False
        if in_checklist and stripped:
            match = ITEM.fullmatch(stripped)
            if match:
                items.append(match.groups())
            else:
                problems.append(f"[3 checklist] malformed item: {stripped}")
            continue
        match = re.fullmatch(
            r"(range|classification|verdict|walkthrough):\s*(.*)", stripped
        )
        if match:
            key, value = match.groups()
            if key in fields:
                problems.append(f"[5 parse] duplicate {key}")
            fields[key] = value
    for key in ("range", "classification", "verdict"):
        if not fields.get(key):
            problems.append(f"[5 parse] missing {key}")
    if not checklist or not items:
        problems.append("[5 parse] missing/empty checklist")
    return fields, items, problems


def record_checks(root: Path, cfg: dict, text: str, expected: str,
                  category: str, delta_date: str) -> tuple[list[str], list[str]]:
    """Apply record matching, measured-item and human-reference predicates."""
    fields, items, problems = parse_record(text)
    readings = []
    actual = fields.get("range", "")
    if not SHA_RANGE.fullmatch(actual) or actual != expected:
        problems.append(f"[2 range] record={actual!r}; expected={expected}")
    if fields.get("classification") != category:
        problems.append(f"[2 classification] expected {category}")
    verdict = fields.get("verdict")
    rule = cfg["categories"][category]
    if verdict not in cfg["verdicts"]:
        problems.append(f"[4 verdict] unknown verdict={verdict!r}")
    if verdict != rule["record_verdict"]:
        problems.append(
            f"[4 verdict] {category} requires {rule['record_verdict']}; "
            f"record verdict={verdict}"
        )
    names = set()
    for name, reading, item_verdict in items:
        readings.append(f"[3 checklist] {name}: {reading} => {item_verdict}")
        if not name or name in names:
            problems.append(f"[3 checklist] empty/duplicate item={name!r}")
        names.add(name)
        normalized = reading.strip().casefold().rstrip(".。!")
        if normalized in (
            "", "pass", "fail", "ok", "done", "checked", "verified", "n/a",
            "none", "i checked it", "all checks passed", "我检查过了",
            "已检查", "已验证", "通过", "无", "待填",
        ) or re.search(r"未验证|未执行|not (?:verified|run)", normalized):
            problems.append(f"[3 reading] {name}: missing measured reading")
        if item_verdict not in ("PASS", "FAIL"):
            problems.append(f"[3 checklist] {name}: unverified/invalid verdict")
        if item_verdict == "FAIL":
            problems.append(f"[4 item FAIL] {name}: cannot authorize PR")
            if verdict == "PASS":
                problems.append(f"[4 verdict] item {name} FAIL but record PASS")
    if rule["requires_walkthrough"]:
        reference = fields.get("walkthrough", "")
        if not matches(reference, cfg["walkthrough_glob"]):
            problems.append(f"[2 walkthrough] glob mismatch: {reference!r}")
        else:
            try:
                signed = local_path(root, reference).read_text(encoding="utf-8")
                head = expected.split("..")[1]
                stamp = rf"(?<!\d){re.escape(delta_date)}(?!\d)"
                if head not in signed and not re.search(stamp, signed):
                    problems.append("[2 walkthrough] missing delta SHA/date")
                if not re.search(r"\u2611\s*通过|签收[:：]\s*\S", signed):
                    problems.append(
                        "[2 walkthrough] unsigned: "
                        f"{reference} lacks the ☑通过 / 签收 marker")
            except (OSError, ValueError) as exc:
                problems.append(f"[2 walkthrough] {reference}: {exc}")
    return problems, readings


def check(root: Path, rev_range: str,
          record: str | None = None) -> tuple[list[str], list[str]]:
    """Check the real delta and records; never write or recover parsing errors."""
    readings = []
    try:
        cfg = load_config(root)
        ends = rev_range.split("..")
        if len(ends) != 2 or not all(ends) or "..." in rev_range:
            raise ValueError("range must be A..B")
        shas = [git(root, "rev-parse", "--verify", "--end-of-options",
                    f"{ref}^{{commit}}").strip() for ref in ends]
        expected = "..".join(shas)
        if not SHA_RANGE.fullmatch(expected):
            raise ValueError("range endpoints must resolve to full SHA-1 commits")
        raw = git(root, "diff", "--name-status", "-z", "--no-renames", *shas, "--")
        parts = raw.rstrip("\0").split("\0") if raw else []
        if len(parts) % 2:
            raise ValueError("cannot parse git diff --name-status -z")
        files = list(zip(parts[::2], parts[1::2]))
        excluded = [
            item for item in files
            if (item[0] == "D" and item[1] in cfg.get("ignored_deletions", []))
            or any(matches(item[1], g) for g in cfg.get("ignore_globs", []))
        ]
        files = [item for item in files if item not in excluded]
        category, readings = classify(cfg, files)
        readings.insert(0, f"range: {expected}")
        readings.insert(1, f"delta scope: ignored {len(excluded)} retained mac "
                          "launcher deletion(s)")
        readings.append(f"classification: {category}; files={len(files)}")
        stamp = git(root, "show", "-s", "--format=%cI", shas[1]).strip()
        delta_date = datetime.fromisoformat(stamp).astimezone(
            timezone(timedelta(hours=8))
        ).date().isoformat()
        if record is None:
            directory = local_path(root, cfg["record_dir"])
            candidates, errors = [], []
            for path in sorted(directory.glob("AC-*.MD")):
                rel = path.relative_to(Path(root).resolve()).as_posix()
                body = local_path(root, rel).read_text(encoding="utf-8")
                fields, _, issues = parse_record(body)
                if fields.get("range") == expected:
                    candidates.append(rel)
                errors.extend(f"{rel}: {issue}" for issue in issues)
            if len(candidates) != 1:
                return [f"[2 record] expected one matching AC record; "
                        f"found {len(candidates)}", *errors], readings
            record = candidates[0]
        readings.append(f"record: {record}")
        body = local_path(root, record).read_text(encoding="utf-8")
        problems, measured = record_checks(
            root, cfg, body, expected, category, delta_date
        )
        return problems, readings + measured
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [f"[5 input/parse] {type(exc).__name__}: {exc}"], readings


def fixture_tree(root: Path, contents: dict[str, str]) -> str:
    """Create temporary Git objects without touching any index or real branch."""
    tree = {}
    for path, body in contents.items():
        branch = tree
        parts = path.split("/")
        for part in parts[:-1]:
            branch = branch.setdefault(part, {})
        blob = git(root, "hash-object", "-w", "--stdin", stdin=body).strip()
        branch[parts[-1]] = blob

    def build(node: dict) -> str:
        """Recursively serialize Git trees for the fixture only."""
        rows = []
        for name, value in sorted(node.items()):
            if isinstance(value, dict):
                rows.append(f"040000 tree {build(value)}\t{name}\n")
            else:
                rows.append(f"100644 blob {value}\t{name}\n")
        return git(root, "mktree", stdin="".join(rows)).strip()

    return build(tree)


def fixture_commit(root: Path, contents: dict[str, str], parent: str = "") -> str:
    """Create a synthetic commit object, with no refs, hooks, add or commit CLI."""
    args = ["-c", "user.name=AC fixture", "-c", "user.email=ac@example.invalid",
            "commit-tree", fixture_tree(root, contents)]
    if parent:
        args += ["-p", parent]
    return git(root, *args, stdin="acceptance fixture\n").strip()


def selftest() -> int:
    """Run positive and negative controls through check() in temporary copies."""
    source = load_config(ROOT)

    def example(pattern: str) -> str:
        """Materialize a policy glob, avoiding a duplicate classification table."""
        return pattern.replace("**/", "sample/").replace("*", "sample")

    human = source["default_category"]
    auto = next(k for k, v in source["categories"].items()
                if not v["requires_walkthrough"])
    prod = example(source[source["categories"][human]["globs_key"]][0])
    added = example(source["categories"][auto]["added_only_globs"][0])
    with tempfile.TemporaryDirectory(prefix="acceptance-record-") as td:
        base = Path(td)
        git(base, "init", "--quiet")
        # Fixed temporary sink names keep the artifact-path gate statically exact.
        # Only fixture output locations differ; classification globs are copied.
        cfg = json.loads(json.dumps(source))
        cfg["record_dir"] = "records"
        cfg["walkthrough_glob"] = "signed-*.MD"
        (base / "agents").mkdir()
        (base / POLICY_REL).write_text(
            json.dumps({"acceptance_review": cfg}), encoding="utf-8", newline="\n"
        )
        (base / "records").mkdir()
        record = base / "records" / "AC-fixture.MD"
        a = fixture_commit(base, {prod: "old\n"})
        p = fixture_commit(base, {prod: "new\n"}, a)
        n = fixture_commit(base, {prod: "old\n", added: "new\n"}, a)
        prange, nrange = f"{a}..{p}", f"{a}..{n}"

        def body(delta: str, category: str, verdict: str) -> str:
            """Build an AC record with a measured fixture-command excerpt."""
            return (f"range: {delta}\nclassification: {category}\n"
                    f"verdict: {verdict}\nwalkthrough: signed-fixture.MD\n\n"
                    "## checklist\n"
                    "- item: smoke | reading: rc=0; cases=1 | verdict: PASS\n")

        def probe(label: str, delta: str, content: str, needle: str = "") -> None:
            """Write a temporary record, then assert check()'s named result."""
            (base / "records" / "AC-fixture.MD").write_text(
                content, encoding="utf-8", newline="\n"
            )
            problems, readings = check(base, delta, "records/AC-fixture.MD")
            print(f"CONTROL {label}: gate_rc={int(bool(problems))}")
            for line in readings + problems:
                print(f"  {line}")
            expected = any(needle in e for e in problems) if needle else not problems
            ok(label, expected, "; ".join(problems) or "check() PASS")

        probe("1 production + PASS", prange, body(prange, human, "PASS"),
              "requires NEEDS-HUMAN")
        (base / "signed-fixture.MD").write_text(
            f"结论：\u2611 通过\n签收：fixture-user\nSynthetic signoff: {p}\n",
            encoding="utf-8", newline="\n"
        )
        clean_human = body(prange, human, "NEEDS-HUMAN")
        clean_auto = body(nrange, auto, "PASS")
        probe("2 production + human reference", prange, clean_human)
        probe("3 non-production + measured PASS", nrange, clean_auto)
        probe("4 missing reading", nrange,
              clean_auto.replace("rc=0; cases=1", ""), "missing measured reading")
        probe("5 range mismatch", nrange, body(prange, auto, "PASS"), "[2 range]")
        (base / "records" / "AC-fixture.MD").write_text(
            clean_auto, encoding="utf-8", newline="\n"
        )
        shutil.copytree(base, base / "copy", ignore=shutil.ignore_patterns("copy"))
        problems, readings = check(base / "copy", nrange)
        if problems:
            print("  COPY PROBE problems: " + "; ".join(problems)[:800])
            print("  COPY PROBE readings: " + " | ".join(readings)[:800])
        ok("6 clean copy", not problems, f"gate_rc={int(bool(problems))}")
        problems, _ = check(base / "copy" / ".", nrange)
        ok("6b non-canonical root", not problems, f"gate_rc={int(bool(problems))}")
        snapshot = {p.relative_to(base): p.read_bytes()
                    for p in base.rglob("*") if p.is_file()}
        check(base, nrange)
        after = {p.relative_to(base): p.read_bytes()
                 for p in base.rglob("*") if p.is_file()}
        ok("check is read-only", snapshot == after)
        for field in ("range", "classification"):
            content = re.sub(rf"(?m)^{field}:.*\n", "", clean_auto)
            probe(f"missing {field}", nrange, content, f"missing {field}")
        probe("missing checklist", nrange, clean_auto.split("## checklist")[0],
              "missing/empty checklist")
        probe("declaration only", nrange,
              clean_auto.replace("rc=0; cases=1", "我检查过了"), "[3 reading]")
        probe("item FAIL + PASS", nrange,
              clean_auto.replace("| verdict: PASS", "| verdict: FAIL"),
              "FAIL but record PASS")
        probe("item FAIL + FAIL", nrange,
              clean_auto.replace("verdict: PASS", "verdict: FAIL"), "[4 item FAIL]")
        probe("unverified dependency", nrange,
              clean_auto.replace("rc=0; cases=1", "未验证: dependency missing"),
              "[3 reading]")
        probe("duplicate range", nrange, f"range: {nrange}\n" + clean_auto,
              "duplicate range")
        probe("malformed checklist", nrange, clean_auto + "- checked\n",
              "malformed item")
        probe("wrong classification", nrange, clean_auto.replace(auto, human),
              "[2 classification]")
        probe("wrong signoff glob", prange,
              clean_human.replace("signed-fixture.MD", "unrelated.MD"),
              "glob mismatch")
        probe("nested signoff not matched by star", prange,
              clean_human.replace("signed-fixture.MD", "signed-dir/nested.MD"),
              "glob mismatch")
        (base / "signed-fixture.MD").write_text(
            "Unrelated signoff\n", encoding="utf-8", newline="\n"
        )
        probe("signoff lacks delta", prange, clean_human, "missing delta SHA/date")
        date = git(base, "show", "-s", "--format=%cI", p).strip()
        date = datetime.fromisoformat(date).astimezone(
            timezone(timedelta(hours=8))
        ).date().isoformat()
        (base / "signed-fixture.MD").write_text(
            f"结论：\u2611 通过\n签收：fixture-user\n{date}\n",
            encoding="utf-8", newline="\n"
        )
        probe("signoff delta date", prange, clean_human)
        (base / "signed-fixture.MD").write_text(
            f"Synthetic signoff without a signature marker: {p}\n",
            encoding="utf-8", newline="\n"
        )
        probe("unsigned walkthrough rejected", prange, clean_human, "[2 walkthrough] unsigned")
        (base / "signed-fixture.MD").write_text(
            f"结论：\u2611 通过\n签收：fixture-user\nSynthetic signoff: {p}\n",
            encoding="utf-8", newline="\n"
        )
        modified = fixture_commit(base, {prod: "old\n", added: "modified\n"}, n)
        delta = f"{n}..{modified}"
        probe("existing script modified", delta, body(delta, auto, "PASS"),
              "requires NEEDS-HUMAN")
        deleted = fixture_commit(base, {prod: "old\n"}, n)
        delta = f"{n}..{deleted}"
        probe("existing script deleted", delta, body(delta, auto, "PASS"),
              "requires NEEDS-HUMAN")
        # Scope controls: excluded sync paths and retained mac deletions
        # must not classify.
        mac = next(iter(source.get("ignored_deletions") or []), "scripts/setup-env.sh")
        mgmt = "docs/iteration/sprint/sample/sample.MD"
        with_mgmt = fixture_commit(
            base, {prod: "old\n", added: "new\n", mgmt: "x\n"}, a)
        d1 = f"{a}..{with_mgmt}"
        probe("management doc counts as production", d1, body(d1, auto, "PASS"),
              "requires NEEDS-HUMAN")
        ignored_path = example(next(iter(source.get("ignore_globs") or []), ""))
        if ignored_path:
            with_ignored = fixture_commit(
                base, {prod: "old\n", added: "new\n", ignored_path: "x\n"}, a)
            d3 = f"{a}..{with_ignored}"
            probe("acceptance artifact ignored", d3, body(d3, auto, "PASS"))
        keep = fixture_commit(base, {prod: "old\n", mac: "kept\n"}, a)
        drop = fixture_commit(base, {prod: "old\n", added: "new\n"}, keep)
        d2 = f"{keep}..{drop}"
        probe("retained mac deletion ignored", d2, body(d2, auto, "PASS"))

        overlap = next(g for g in source[source["categories"][auto]["globs_key"]]
                       if classify(source, [("A", example(g))])[0] == human)
        category, _ = classify(source, [("A", example(overlap))])
        ok("production wins overlapping globs", category == human, overlap)
        category, _ = classify(source, [("A", "unknown-file")])
        ok("unmatched defaults to human", category == human)
        extra = auto + "-extra"
        cfg["categories"][extra] = dict(cfg["categories"][auto])
        cfg["categories"][extra]["priority"] += 1
        (base / POLICY_REL).write_text(
            json.dumps({"acceptance_review": cfg}), encoding="utf-8", newline="\n"
        )
        probe("additional category from data", nrange, body(nrange, extra, "PASS"))
        del cfg["categories"][extra]
        (base / POLICY_REL).write_text(
            json.dumps({"acceptance_review": cfg}), encoding="utf-8", newline="\n"
        )
        problems, _ = check(base, nrange, "../outside.MD")
        ok("record path escape rejected", any("unsafe" in e for e in problems))
        record.unlink()
        problems, _ = check(base, nrange)
        ok("missing record rejected", any("[2 record]" in e for e in problems))
        problems, _ = check(base, "bad-range")
        ok("bad range fails closed", any("[5 input/parse]" in e for e in problems))
    return finish("verify_acceptance_record.py", " mode=selftest")


def main() -> int:
    """Report all failed predicates; success applies only to the checked range."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--range", default="origin/main..HEAD", dest="rev_range")
    parser.add_argument("--record")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    problems, readings = check(ROOT, args.rev_range, args.record)
    for line in readings:
        print(line)
    for problem in problems:
        print(f"FAIL: {problem}")
    if problems:
        print(f"ACCEPTANCE FAIL ({len(problems)} problems)")
        return 1
    for name in ("classification", "record/range/signoff", "measured checklist",
                 "verdict consistency", "fail-closed parsing"):
        ok(name, True, "check() completed without predicate failures")
    finish("verify_acceptance_record.py", " mode=range")
    print("ACCEPTANCE PASS: record permits PR for this committed range")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
