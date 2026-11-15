# FDE-VAULT

Enterprise Forward Deployed Engineering Ledger. A Claude Code skill plus a local
command (`fde`) that gives every terminal AI tool in a project (Claude Code,
Antigravity, Cursor, Codex CLI) one shared, session-gated ledger of customer
accounts, scope boundaries, architectural rulings, and an engineering journal.
Files in `./.fde-vault/` are plaintext markdown documents protected by session-gated
account isolation and best-effort local secret and PII redaction.

Python 3 standard library only. macOS, Linux, and Windows.

## Installation from GitHub

Install the global `fde` CLI and skill definitions directly from GitHub across macOS, Linux, and Windows:

### macOS / Linux (One-Line Installer)
```bash
curl -fsSL https://raw.githubusercontent.com/fde-vault/fde-vault/main/install.sh | bash
```

### Windows PowerShell (One-Line Installer)
```powershell
irm https://raw.githubusercontent.com/fde-vault/fde-vault/main/install.ps1 | iex
```

### Python Pip / Pipx Install
```bash
pip install git+https://github.com/fde-vault/fde-vault.git
```
or via `pipx`:
```bash
pipx install git+https://github.com/fde-vault/fde-vault.git
```

### Scaffolding in Any Repository (`fde init`)
Once installed, run `fde init` in any engineering repository to scaffold the complete FDE governance environment without touching any existing live account folders:
```bash
cd /path/to/your/project
fde init
```
This generates `.fde-vault/_blueprint/`, `.fde-vault/index.json`, `.claude/skills/fde-vault/`, `.agent/skills/fde-vault/`, `.claude/settings.json`, and cross-agent discovery pointers (`AGENTS.md`, `GEMINI.md`, `CLAUDE.md`, `.cursorrules`, `.gitignore`).

## Local Setup

```
python3 .claude/skills/fde-vault/scripts/install_cli.py
```

On Windows use `py -3` in place of `python3`. The installer:

- adds an `fde` function between `# >>> fde-vault >>>` markers in `~/.zshrc` and
  `~/.bashrc` (macOS), `~/.bashrc` and `~/.profile` (Linux), or the PowerShell
  `$PROFILE` (Windows). Repeated runs replace the block; they never duplicate it.
- writes `~/.local/bin/fde` and, on Windows, `%USERPROFILE%\bin\fde.bat`
- mirrors the skill to `./.agent/skills/fde-vault/` and `~/.claude/skills/fde-vault/`

Preview with `--dry-run`. Remove everything it added with `--uninstall`.
`./fde-vault` and `fde-vault.bat` in this folder are local launchers that do the
same job without installing anything.

## Use

| Command | What it does |
| --- | --- |
| `fde` | Startup animation, cover page, passphrase prompt, unlock |
| `fde lock` | Seal the session immediately |
| `fde status` | Session, active account, index drift, portfolio |
| `fde ingest --clipboard` | Scrub the clipboard into the active inbox |
| `fde ingest --file PATH --wipe` | Scrub a file into the inbox, shred the source |

Then, in your AI tool, use `/switch <account>`, `/discover`, `/sync`, `/scope`,
`/preflight`, `/incident`, `/rfc`, `/brief`, `/handoff`, `/steps`, `/status`,
`/lock`, and `/open`. See `.claude/skills/fde-vault/SKILL.md` for the full suite.

First launch asks you to set a passphrase (minimum 10 characters). It is stored
only as a salted PBKDF2-HMAC-SHA256 hash (100,000 iterations) in
`.fde-vault/.vault.auth`. Sessions last 8 hours; set `FDE_SESSION_TTL_HOURS` to change that.

## Layout

```
.claude/settings.json                  hook wiring (prompt and tool firewalls)
.claude/skills/fde-vault/SKILL.md      skill definition
.claude/skills/fde-vault/references/   core-rules.md, playbooks.md
.claude/skills/fde-vault/scripts/      vault_guard.py, hooks, installer, tests
.agent/skills/fde-vault/               mirror of the skill
.fde-vault/                            the single canonical data store
  _blueprint/                          template cloned for each new account
  index.json                           portfolio index (empty at ship)
  <account>/brain.md timeline.md inbox.md outputs/
```

No demo accounts are shipped. `.fde-vault/` live data is git-ignored by default.

## Security model

Read this before trusting it with real client data.

- **Session-Gated Isolation:** Files in `.fde-vault/` are plaintext markdown documents gated by local session checks and firewall hooks. The passphrase gates sessions and hook decisions. It does **not** encrypt files on disk. Anything with local filesystem access can read `.fde-vault/`. Use full-disk encryption (FileVault, BitLocker, LUKS) for confidentiality at rest.
- **Best-Effort Redaction:** Redaction is best-effort pattern matching (cloud keys, tokens, private keys, JWTs, URL credentials, secret assignments, cards with Luhn check, SSNs, emails, phone numbers). Review `inbox.md` before `/sync` when stakes are high. Names, addresses, and free-text secrets are not detected.
- **Firewall Hooks:** The hooks block prompts and tool calls that contain credential formats, and block tool access to `.fde-vault/` while locked. They inspect command text and prompt payloads locally before egress. They are an engineering guardrail against accidents, not a kernel sandbox.
- **Firewall Modes:** Set `FDE_FIREWALL=credentials` to stop the prompt hook from blocking emails and phone numbers while keeping credential blocking strictly active.
- A wrong passphrase triggers an exponential backoff (capped at 5 minutes).

## Tests

```
python3 .claude/skills/fde-vault/scripts/test_fde_vault.py
```

Covers hashing, sessions, locking, redaction, ingest, hooks, installer
idempotency, the dashboard, the animation, and repo hygiene (no emojis, no demo
data, standard library only).

## Keeping mirrors in sync

The project copy is the source. After editing it, rerun the installer to refresh
the mirrors. Data never lives in a mirror, so they cannot drift on content.
