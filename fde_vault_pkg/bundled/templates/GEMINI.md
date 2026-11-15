# Antigravity & Gemini Agent Instructions
- Forward Deployed Engineer operating system and commands are defined in `.claude/skills/fde-vault/SKILL.md`.
- Typing 'fde' or '/open' launches the FDE-VAULT Home Screen and command directory.
- Canonical customer account ledgers reside under `./.fde-vault/` (session-gated isolation).
- Always verify active account status via `fde status` before modifying any client files.
- Never paste raw secrets or customer PII into prompts; process notes via `fde ingest --clipboard`.
- Follow rule-cited traffic-light triage (RULE-01 through RULE-05) for all architectural reviews.
