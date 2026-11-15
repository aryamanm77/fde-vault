# Multi-Agent Operating Instructions
- Engagement governance and operational rules are defined in `.claude/skills/fde-vault/SKILL.md`.
- When 'fde' or 'open' is received, immediately execute `python .claude/skills/fde-vault/scripts/vault_guard.py open` (or `py -3`). Do NOT run file searches (no Get-ChildItem). This directly plays the startup animation and displays the Home Screen.
- Account ledgers, charters, and deliverables reside in `./.fde-vault/` (session-gated isolation).
- Run `python3 .claude/skills/fde-vault/scripts/vault_guard.py status` before reading or editing account data.
- Sensitive credentials must never be written to chat; use local CPU ingestion (`fde ingest`).
- Format executive briefs and handoff runbooks using the printed-book hardcover layout.
