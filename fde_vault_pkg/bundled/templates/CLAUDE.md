# Claude Code Agent Instructions
- Core FDE governance, workflow playbooks, and commands are defined in `.claude/skills/fde-vault/SKILL.md`.
- When the user sends 'fde' or 'open', immediately execute `python .claude/skills/fde-vault/scripts/vault_guard.py open` (or `py -3` / `~/.claude/skills/fde-vault/scripts/vault_guard.py open`). In your chat response, ALWAYS output the emblem logo code block verbatim at the very top so the logo is visible to the user.
- All client account data is stored in the canonical store `./.fde-vault/` (session-gated isolation).
- Verify session lock and active account with `fde status` before executing account actions.
- Do not output live credentials in chat; instruct users to run `fde ingest` for local CPU redaction.
- Adhere to the selective book formatting policy: keep everyday commands concise; use book layout for briefs/handoffs.
