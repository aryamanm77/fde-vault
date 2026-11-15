---
description: Instantly display the Portfolio Index of all accounts and active vault status
---

1. Check active session: If `./.fde-vault/.session-unlocked` exists, the vault is UNLOCKED; otherwise LOCKED.
2. Read `./.fde-vault/index.json` to inspect all registered accounts, stages, and health.
3. Display the Portfolio Index table in the printed hardcover journal page format with zero emojis.
4. If index drift is detected between directories and index.json, synchronize with `python3 .claude/skills/fde-vault/scripts/vault_guard.py reindex`.
