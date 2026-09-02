---
name: workspace-check
description: Workspace & functional-integrity verification handbook (executed by the main agent, never delegated): zero git residue, branch/port hygiene, pre-development cleanup, .gitignore coverage, regression suite all green.
version: "1.2.0"
model: ""
tools: []
metadata:
  tags: [review, workspace, manual]
  estimated_chars: 1200
  note: Executed by the main agent (decision D2: starting services / killing processes are high-risk operations, never delegated to a subagent)
---

# Role

You are the main agent's **environment-verification handbook** — not a subagent prompt. This function stays with the main agent (see trigger-tier decision D2).

# Trigger

- **Before starting a development round** (step 0 pre-development cleanup, added 2026-08-31 per user decision);
- Sprint close three-check (the "third check");
- Any "I'm done, wrap it up" moment.

# Task Input (provided by the orchestrator per run)

None — this function is executed by the main agent itself (decision D2), never dispatched to a subagent, so there is no run payload; the "task" is the current round's change list, read from `git status` and the sprint doc.

# Configurable Parameters (edit point: adjust only this section, never the body rules)

| Parameter | Current value | Meaning |
|---|---|---|
| Port list | 5173 (frontend), 8787 (backend), 8501 (Streamlit), 8600 (agents dashboard, phase 3) | ports checked in step 4 |
| Regression scripts (offline) | verify_smoke / verify_prune_callbacks / verify_agentops / verify_index_health | no API, no network |
| Regression scripts (online) | verify_provider_switch / verify_e2e / verify_e2e_openai / eval_retrieve | real key required (e2e_openai needs account balance) |
| Regression scripts (GUI) | gui_check*.mjs | requires frontend+backend running + Playwright |

# Steps (fixed order)

0. **Pre-development cleanup (added 2026-08-31, user decision)**: before touching code, run the port-hygiene check (step 4) and stop any leftover dev servers from previous rounds (PID + command-line verification only, per 3-LEARNED 1.11/1.20); re-check FREE. Stale servers cause spurious errors and locked files mid-development.
1. **Zero workspace residue**: check `git status --short` line by line — every changed file must belong to this round's change list; unexpected residue (temp files, artifacts, unregistered screenshots) is handled explicitly (commit or gitignore or delete).
2. **Branch hygiene (local)**: local branches are main/windows (+ the current sync branch); stale sync branches deleted; `git log --oneline -3` confirms HEAD matches the plan.
3. **Branch hygiene (remote; added 2026-08-30 after user found the blind spot)**: `git ls-remote --heads origin` must show `mac/main/windows` only — **every merged PR's `sync/*` head branch must be deleted** (`git push origin --delete <branch>`); if the repo "delete head branch on merge" setting is on, it happens automatically (async) — still re-check.
4. **Port hygiene**: `Get-NetTCPConnection -LocalPort 5173,8787,8501,8600 -State Listen` all FREE; if occupied → locate the PID per SOP + confirm the command line via `Get-CimInstance Win32_Process` is a project process → `Stop-Process` **only on confirmed PIDs** (never mass-kill by process name — see 3-LEARNED 1.11/1.20) → re-check FREE.
5. **.gitignore coverage**: `git status --porcelain --ignored` spot-checks that artifacts (__pycache__/.venv/node_modules/.next/agents-dashboard/data/data/remote/verify/*.log/*_result.json) are properly ignored.
6. **Regression suite** (select by change scope):
   - offline: `verify_smoke.py`, `verify_prune_callbacks.py`, `verify_index_health.py`, `verify_agentops.py`;
   - online: `verify_provider_switch.py`, `verify_e2e.py`, `eval_retrieve.py`, `verify_e2e_openai.py` (needs balance);
   - GUI (frontend+backend running): `gui_check*.mjs`;
   - frontend/dashboard: `npm run build` (agents-dashboard likewise).
   Record PASS/FAIL per script with an output summary.
7. **Wrap-up**: stop dev servers started this round and re-check ports; write the conclusion (change list + regression output) into the sprint doc §9.

# Output Template (report body in Chinese — project docs are Chinese; keep script names and PASS/FAIL verbatim)

```
# workspace-check report
- workspace: <change-list verification result>
- branches: <branch state>
- ports: <5173/8787/8501/8600 state>
- regression: <per-script PASS/FAIL summary>
- conclusion: <third-check passed or not>
```

# Forbidden

- Never mass-kill processes by name; stop services only by PID + command-line verification;
- Never skip the port re-check (after stopping any dev server, re-verify FREE);
- Never treat "output looks error-free" as PASS: regression conclusions must come from the script's own PASS output or assertions.
