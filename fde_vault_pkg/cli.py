#!/usr/bin/env python3
"""CLI entrypoint for fde-vault global package."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

POINTER_AGENTS = """# Multi-Agent Operating Instructions
- Engagement governance and operational rules are defined in `.claude/skills/fde-vault/SKILL.md`.
- Typing 'fde' or 'open' launches the FDE-VAULT Home Screen and command directory.
- Account ledgers, charters, and deliverables reside in `./.fde-vault/` (session-gated isolation).
- Run `python3 .claude/skills/fde-vault/scripts/vault_guard.py status` before reading or editing account data.
- Sensitive credentials must never be written to chat; use local CPU ingestion (`fde ingest`).
- Format executive briefs and handoff runbooks using the printed-book hardcover layout.
"""

POINTER_GEMINI = """# Antigravity & Gemini Agent Instructions
- Forward Deployed Engineer operating system and commands are defined in `.claude/skills/fde-vault/SKILL.md`.
- Typing 'fde' or 'open' launches the FDE-VAULT Home Screen and command directory.
- Canonical customer account ledgers reside under `./.fde-vault/` (session-gated isolation).
- Always verify active account status via `fde status` before modifying any client files.
- Never paste raw secrets or customer PII into prompts; process notes via `fde ingest --clipboard`.
- Follow rule-cited traffic-light triage (RULE-01 through RULE-05) for all architectural reviews.
"""

POINTER_CLAUDE = """# Claude Code Agent Instructions
- Core FDE governance, workflow playbooks, and commands are defined in `.claude/skills/fde-vault/SKILL.md`.
- Typing 'fde' or 'open' launches the FDE-VAULT Home Screen and command directory.
- All client account data is stored in the canonical store `./.fde-vault/` (session-gated isolation).
- Verify session lock and active account with `fde status` before executing account actions.
- Do not output live credentials in chat; instruct users to run `fde ingest` for local CPU redaction.
- Adhere to the selective book formatting policy: keep everyday commands concise; use book layout for briefs/handoffs.
"""

POINTER_CURSOR = """# Cursor Rules for FDE-VAULT
- Refer to `.claude/skills/fde-vault/SKILL.md` for complete command definitions and core rules.
- Typing 'fde' or 'open' launches the FDE-VAULT Home Screen and command directory.
- Account data is located in `./.fde-vault/` and protected by session-gated isolation.
- Run `fde status` to check active account and repository lock before making changes.
- Never expose API keys or customer PII in editor chat; direct raw text to `fde ingest`.
- Respect multi-tenant invariants: reject core hacks (RULE-01 to RULE-05) and propose edge adapters.
"""

GITIGNORE_SNIPPET = """
# fde-vault live account data and session auth
.fde-vault/.vault.auth
.fde-vault/.session-unlocked
.fde-vault/.active-vault
.fde-vault/[!_]*
!.fde-vault/_blueprint/
!.fde-vault/index.json
"""

DEFAULT_SETTINGS = {
    "hooks": {
        "UserPromptSubmit": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 .claude/skills/fde-vault/scripts/prompt_hook.py || py -3 .claude/skills/fde-vault/scripts/prompt_hook.py || python .claude/skills/fde-vault/scripts/prompt_hook.py"
                    }
                ]
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Bash|Read|Write|Edit|MultiEdit|Glob|Grep",
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 .claude/skills/fde-vault/scripts/pre_tool_hook.py || py -3 .claude/skills/fde-vault/scripts/pre_tool_hook.py || python .claude/skills/fde-vault/scripts/pre_tool_hook.py"
                    }
                ]
            }
        ]
    }
}


def find_bundled_dir() -> Path:
    """Locates the bundled assets directory."""
    pkg_dir = Path(__file__).resolve().parent
    bundled = pkg_dir / "bundled"
    if bundled.is_dir() and (bundled / "skills" / "fde-vault" / "SKILL.md").is_file():
        return bundled

    # Fallback to source repo tree
    for parent in [pkg_dir] + list(pkg_dir.parents):
        if (parent / ".claude" / "skills" / "fde-vault").is_dir():
            return parent
    return pkg_dir


def cmd_init(target_path=None) -> int:
    """Scaffolds fde-vault into the target directory without touching live accounts."""
    target = Path(target_path).resolve() if target_path else Path.cwd().resolve()
    target.mkdir(parents=True, exist_ok=True)
    source_root = find_bundled_dir()

    print(f"[fde init] Scaffolding FDE-VAULT into {target}...")

    # 1. .fde-vault/_blueprint/
    blueprint_target = target / ".fde-vault" / "_blueprint"
    blueprint_target.mkdir(parents=True, exist_ok=True)
    blueprint_outputs = blueprint_target / "outputs"
    blueprint_outputs.mkdir(parents=True, exist_ok=True)
    gitkeep = blueprint_outputs / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

    # Determine blueprint source
    bp_source = source_root / "bundled" / "_blueprint"
    if not bp_source.is_dir():
        bp_source = source_root / "_blueprint"
    if not bp_source.is_dir():
        bp_source = source_root / ".fde-vault" / "_blueprint"

    if bp_source.is_dir():
        for item in bp_source.glob("*"):
            if item.is_file():
                dest = blueprint_target / item.name
                shutil.copy2(str(item), str(dest))
    else:
        # Fallback inline creation
        (blueprint_target / "brain.md").write_text("# Account Charter\n", encoding="utf-8")
        (blueprint_target / "timeline.md").write_text("# Operational Timeline\n", encoding="utf-8")
        (blueprint_target / "inbox.md").write_text("# Ingestion Queue\n", encoding="utf-8")

    # 2. .fde-vault/index.json (do NOT overwrite existing)
    index_file = target / ".fde-vault" / "index.json"
    if not index_file.exists():
        index_file.write_text(json.dumps({"generated_at": "", "vaults": {}}, indent=2), encoding="utf-8")
        print("  - Created .fde-vault/index.json")
    else:
        print("  - Preserved existing .fde-vault/index.json")

    # 3. .claude/skills/fde-vault/ and .agent/skills/fde-vault/
    skill_source = source_root / "bundled" / "skills" / "fde-vault"
    if not skill_source.is_dir():
        skill_source = source_root / "skills" / "fde-vault"
    if not skill_source.is_dir():
        skill_source = source_root / ".claude" / "skills" / "fde-vault"

    for dest_dir in [target / ".claude" / "skills" / "fde-vault", target / ".agent" / "skills" / "fde-vault"]:
        dest_dir.mkdir(parents=True, exist_ok=True)
        if skill_source.is_dir():
            for root_p, dirs, files in os.walk(str(skill_source)):
                if "__pycache__" in root_p:
                    continue
                rel = Path(root_p).relative_to(skill_source)
                cur_dest = dest_dir / rel
                cur_dest.mkdir(parents=True, exist_ok=True)
                for f in files:
                    shutil.copy2(os.path.join(root_p, f), str(cur_dest / f))

    print("  - Scaffolding .claude/skills/fde-vault/ and .agent/skills/fde-vault/")

    # 4. .claude/settings.json
    settings_file = target / ".claude" / "settings.json"
    if not settings_file.exists():
        settings_file.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
        print("  - Created .claude/settings.json")
    else:
        try:
            curr = json.loads(settings_file.read_text(encoding="utf-8"))
            if "hooks" not in curr:
                curr["hooks"] = DEFAULT_SETTINGS["hooks"]
                settings_file.write_text(json.dumps(curr, indent=2), encoding="utf-8")
        except Exception:
            pass

    # 5. Root discovery pointers
    pointers = [
        ("AGENTS.md", POINTER_AGENTS),
        ("GEMINI.md", POINTER_GEMINI),
        ("CLAUDE.md", POINTER_CLAUDE),
        (".cursorrules", POINTER_CURSOR),
    ]
    for fname, content in pointers:
        p_path = target / fname
        if not p_path.exists():
            p_path.write_text(content, encoding="utf-8")
            print(f"  - Created {fname}")

    # 6. .gitignore
    gi_path = target / ".gitignore"
    if not gi_path.exists():
        gi_path.write_text(GITIGNORE_SNIPPET.strip() + "\n", encoding="utf-8")
        print("  - Created .gitignore")
    else:
        existing = gi_path.read_text(encoding="utf-8")
        if ".fde-vault" not in existing:
            gi_path.write_text(existing.rstrip() + "\n" + GITIGNORE_SNIPPET + "\n", encoding="utf-8")
            print("  - Updated .gitignore with fde-vault rules")

    print("[fde init] Initialization complete.")
    print("Installed FDE-VAULT. Type 'fde' in your terminal or inside Claude Code / Antigravity to launch.")
    return 0


def find_vault_guard(cwd=None) -> Path:
    """Resolves vault_guard.py from cwd, parents, user home, or bundled package."""
    curr = Path(cwd).resolve() if cwd else Path.cwd().resolve()

    # Search current directory and parents
    for d in [curr] + list(curr.parents):
        p = d / ".claude" / "skills" / "fde-vault" / "scripts" / "vault_guard.py"
        if p.is_file():
            return p
        p_agent = d / ".agent" / "skills" / "fde-vault" / "scripts" / "vault_guard.py"
        if p_agent.is_file():
            return p_agent

    # Search user home
    home = Path.home()
    for d in [home / ".claude", home / ".agent"]:
        p = d / "skills" / "fde-vault" / "scripts" / "vault_guard.py"
        if p.is_file():
            return p

    # Search bundled package
    bundled = find_bundled_dir()
    for candidate in [
        bundled / "bundled" / "skills" / "fde-vault" / "scripts" / "vault_guard.py",
        bundled / "skills" / "fde-vault" / "scripts" / "vault_guard.py",
        bundled / ".claude" / "skills" / "fde-vault" / "scripts" / "vault_guard.py"
    ]:
        if candidate.is_file():
            return candidate

    return None


def main(argv=None) -> int:
    """CLI dispatcher."""
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] == "init":
        target = argv[1] if len(argv) > 1 else None
        return cmd_init(target)

    guard = find_vault_guard()
    if not guard or not guard.is_file():
        sys.stderr.write("fde: vault_guard.py not found in project, ~/.claude/skills/fde-vault, or package.\n")
        sys.stderr.write("Run 'fde init' in your repository to scaffold fde-vault.\n")
        return 1

    cmd_args = list(argv) if argv else ["open"]
    res = subprocess.run([sys.executable, str(guard)] + cmd_args)
    return res.returncode


if __name__ == "__main__":
    sys.exit(main())
