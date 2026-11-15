# Antigravity & Gemini Agent Instructions
- Forward Deployed Engineer operating system and commands are defined in `.claude/skills/fde-vault/SKILL.md`.
- When 'fde' or 'open' is received, immediately execute `python .claude/skills/fde-vault/scripts/vault_guard.py open` (or `py -3`). Do NOT run file searches (no Get-ChildItem). This directly plays the startup animation and displays the Home Screen.
- Canonical customer account ledgers reside under `./.fde-vault/` (session-gated isolation).
- Always verify active account status via `fde status` before modifying any client files.
- Never paste raw secrets or customer PII into prompts; process notes via `fde ingest --clipboard`.
- Follow rule-cited traffic-light triage (RULE-01 through RULE-05) for all architectural reviews.
