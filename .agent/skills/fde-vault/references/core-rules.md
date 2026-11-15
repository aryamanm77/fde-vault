# FDE-VAULT Core Rules

Load this file before classifying any request or running `/preflight`. Every
classification must cite the rule ID that decided it. Cite the strictest rule
that applies; cite more than one when several apply.

## Rules

### RULE-01 — Core Immutability
Never modify, patch, fork, or vendor-copy the supplier's core product source to
satisfy one customer. Customer needs are met through configuration, supported
extension points, and edge code that sits outside the core.

### RULE-02 — Adapter Isolation
Customer-specific logic lives in a separate edge adapter with a documented
interface, its own tests, and a named owner. It may call public surfaces of the
core. It must not reach into core internals, private tables, or undocumented
behavior.

### RULE-03 — Upstream First
A gap that other customers are likely to hit is raised as an upstream RFC
(`/rfc`) before a long-lived local workaround is built. A local workaround
that outlives its RFC needs an expiry date recorded in the journal.

### RULE-04 — Secrets and PII Boundary
Credentials, tokens, keys, and personal data never enter chat, the repository,
logs, or the ledger. They move only through local `ingest`, are scrubbed on the
way in, and live in the customer's own secret manager.

### RULE-05 — Scope and Reversibility
Work outside the written scope in `brain.md` needs stakeholder approval before
it starts. Every change must have a rollback path, and every deviation is
recorded in the timeline with its tier and rule ID.

## Traffic-Light Criteria

### CRITERIA-GREEN — Safe
All of the following hold:
- The change is configuration, a supported extension setting, or documentation.
- It is within the `IN SCOPE` list.
- It touches no core source and creates no new long-lived code.
- It is reversible in a single step.

Journal tag: `GREEN [CONFIG-TWEAK]`.

### CRITERIA-YELLOW — Caution
Any of the following hold, and none of the RED conditions do:
- New edge code or an adapter is required (RULE-02 applies).
- The request sits on the boundary of scope, or expands it modestly (RULE-05).
- A temporary workaround exists for a gap that belongs upstream (RULE-03).
- Rollback is possible but takes more than one step.

Required before proceeding: a named owner, a rollback plan, and a journal entry.
Journal tag: `YELLOW [EDGE-ADAPTER]`.

### CRITERIA-RED — Stop
Any of the following hold:
- The change modifies or forks core source (RULE-01).
- It couples to core internals or undocumented behavior (RULE-02).
- It involves raw credentials or personal data in chat, repo, or logs (RULE-04).
- It is explicitly `OUT OF SCOPE`, or irreversible without data loss (RULE-05).

Required: do not proceed. Offer the compliant alternatives in the ruling.
Journal tag: `RED [CORE-HACK]`.

## Mapping to Scope Verdicts

| Scope check result | Meaning | Typical tier |
| --- | --- | --- |
| WITHIN SCOPE | Matches an `IN SCOPE` item | GREEN |
| SCOPE EXPANSION | Adjacent to scope, needs approval | YELLOW |
| OUT OF SCOPE | Matches `OUT OF SCOPE` or is unrelated | RED |

## Citation Format

State the classification and the rule in the ruling block:

> **Architectural Ruling — YELLOW (EDGE-ADAPTER, RULE-02 / CRITERIA-YELLOW)**
> One paragraph explaining why, and the compliant path.
