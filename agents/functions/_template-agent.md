---
name: _template-agent
description: Template for authoring a new agent function spec. Copy to <function-name>.md, replace the placeholders, fill the five sections, bump version, run `agent-ops validate-spec`, then onboard. This file is the template itself — never register it as a runnable function.
version: "1.0.0"
model: ""
tools: []
metadata:
  tags: [template]
  estimated_chars: 1200
---

# Role

You are the **<function-name>** agent. State the single job in one or two sentences, then the hard boundary: what you do and — just as important — what you never do (review-only: never modify files; draft-only: main agent backfills).

# Trigger

- When the orchestrator dispatches <task type>;
- When the task input matches <detection rule, e.g. contains research-required keywords>;
- Manual invocation (user names this function).

# Task Input (provided by the orchestrator per run)

```json
{"<field>": "<type + example>", "<field2>": "..."}
```

# Configurable Parameters (edit point: adjust only this section and the corresponding lists, never the body rules)

| Parameter | Current value | Meaning |
|---|---|---|
| <param> | <default> | <what it controls, and the effect of changing it> |

# Steps (fixed order)

1. <step>
2. <step>

# Output Template (strict format; write the report in Chinese — project docs are Chinese — and keep fixed keywords such as critical/major/minor/nit, PASS/FAIL, file:line verbatim)

```
# <function-name> report (<task keys>)
## <section>
...
```

# Forbidden

- <rule>
