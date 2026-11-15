# Claude Code Agent Instructions
- Core FDE governance, workflow playbooks, and commands are defined in `.claude/skills/fde-vault/SKILL.md`.
- When the user sends 'fde' or 'open', DO NOT run any bash tools, shell commands, or python processes. NEVER ask user permission. Immediately output the official FDE-VAULT emblem logo code block verbatim at the very top of your reply, followed by the Home Screen directory table.
- All client account data is stored in the canonical store `./.fde-vault/` (session-gated isolation).
- Verify session lock and active account with `fde status` before executing account actions.
- Do not output live credentials in chat; instruct users to run `fde ingest` for local CPU redaction.
- Adhere to the selective book formatting policy: keep everyday commands concise; use book layout for briefs/handoffs.
