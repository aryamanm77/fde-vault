---
name: fde-vault
description: Enterprise Forward Deployed Engineer (FDE) application and command center. Triggered by 'fde', '/open', '/fde', or vault requests. Enforces passphrase-locked vault sessions, session-gated account isolation, best-effort local secret/PII redaction, pre-implementation architecture guardrails, scope governance, incident triage, upstream RFC drafting, atomic multi-account indexing, and printed-book engineering diary artifacts.
---

# FDE-VAULT

Enterprise Forward Deployed Engineering Ledger. One canonical, passphrase-locked
store at `./.fde-vault/` is shared by every terminal AI tool in this project.
Files in `./.fde-vault/` are plaintext markdown documents gated by session checks
and firewall hooks.

Throughout this file, `GUARD` means:

```
python3 .claude/skills/fde-vault/scripts/vault_guard.py
```

Fall back to `python` or `py -3` when `python3` is unavailable, and to
`~/.claude/skills/fde-vault/scripts/vault_guard.py` when the project copy is absent.
Do NOT run file search commands (such as Get-ChildItem, find, or glob scans) to locate `vault_guard.py`.

## AI Chat Entry Triggers (fde, open)

Activate and launch the **FDE-VAULT Home Screen & Animation** whenever the user inputs:
- `fde` (case-insensitive standalone word)
- `open` (case-insensitive word)
- Or explicitly asks to launch, open, or view the vault directory.

### PROCEDURE FOR AI ASSISTANTS (Claude Code & Antigravity):
When the user inputs `fde` or `open`:
1. **DO NOT RUN ANY TOOLS OR COMMANDS:**
   - Do NOT run `py`, `python`, `bash`, `Get-ChildItem`, or any shell commands.
   - Do NOT ask user permission for any commands.
   - Immediately output the Home Screen and logo directly in your chat response in under 1 second.
2. **Render the Home Screen in Chat:**
   Your chat response MUST start with the official FDE-VAULT emblem logo code block verbatim so it is visible to the user:

```text
                    ▄████████▄        
                  ▄██▀  ██  ▀██▄      ██████   █████▄   ██████
                 ██▀   ▄██▄   ▀██     ██▄▄     ██  ██   ██▄▄  
                 ██▄▄▄██████▄▄▄██     ██▀▀     ██  ██   ██▀▀  
                 ██▀▀▀██████▀▀▀██     ██       █████▀   ██████
                 ██▄   ▀██▀   ▄██     
                  ▀██▄  ██  ▄██▀      V A U L T               
                    ▀████████▀        

                       ● Ready.                        
```

## F D E · V A U L T
   Followed by the live session/account status blockquote:
   - If unlocked:
     `> **STATUS: UNLOCKED** — Active Account: \`<account>\` (Session active)`
   - If locked or uninitialised:
     `> **STATUS: LOCKED** — Run 'fde' in your terminal (or '!fde' in Claude Code) to unlock.`
   
   Followed by the exact 1-line-per-command Home Screen directory table (plain words only):

| Command | Everyday Meaning |
| :--- | :--- |
| `home` (or `open`) | Cover page, live status, and full command directory |
| `lock` | Seal the vault session immediately |
| `accounts` (or `status`, `vaults`) | View all customer accounts and active session status |
| `select <account>` (or `switch`, `start`) | Select or create a customer account |
| `setup` (or `discover`) | Day-1 technical kickoff and requirements setup |
| `notes [text]` (or `sync`, `log`) | Save and organize scrubbed notes into account ledger |
| `check-request "<request>"` (or `scope`) | Check if a customer request is within project scope |
| `check-code "<proposal>"` (or `preflight`, `guard`) | Check architectural proposal against core rules |
| `issue "<problem>"` (or `incident`) | Log a live production issue and fix runbook |
| `proposal "<feature>"` (or `rfc`) | Draft an engineering design proposal document |
| `summary` (or `brief`, `report`) | One-page executive status summary for leadership |
| `finish` (or `handoff`, `done`) | Complete engagement, transition runbook, and hardcover book |
| `roadmap` (or `steps`) | Engagement milestone roadmap and task checklist |

| Terminal Command | Operational Purpose |
| :--- | :--- |
| `fde` (or `fde open`) | Unlock vault with passphrase and display Home Screen |
| `fde lock` | Seal the vault session immediately |
| `fde ingest --clipboard` | Scrub host clipboard directly into active inbox |
| `fde ingest --file <path> --wipe` | Scrub local file into inbox, then shred source |
| `fde render-dashboard` | Compile active engagement into interactive hardcover book |

   **Security Protocol:** Never ask the user to type their passphrase into AI chat. If locked, display the single terminal unlock instruction. If unlocked, show the running next step footer.

## Core Operating Rules

1. **Verify unlocked session and active account first.** Run `GUARD status`
   before reading or writing any account data. If it reports `locked` or
   `uninitialised`, instruct the user to run `fde` in their local terminal and
   enter the passphrase there. Never ask the user to type the passphrase into AI
   chat, and never try to read `.vault.auth` or `.session-unlocked`.
2. **Best-effort local secret and PII protection.** Never ask the user to paste
   live credentials or raw personal data into chat. Direct sensitive notes
   through `fde ingest --clipboard` or `fde ingest --file <path>` locally, then
   process `./.fde-vault/<active>/inbox.md`. Redaction is best-effort pattern matching.
   If a user pastes something sensitive anyway, do not repeat it; advise rotating it
   and continue with a redacted form. Set `FDE_FIREWALL=credentials` to relax personal
   data blocking while retaining credential blocking.
3. **Rule-cited traffic-light triage.** Load `references/core-rules.md` before
   classifying requests or running `preflight`. Every `GREEN`, `YELLOW`, or
   `RED` classification must cite the exact rule ID (`RULE-01` to `RULE-05`) and
   the matching criteria (`CRITERIA-GREEN`, `CRITERIA-YELLOW`, `CRITERIA-RED`).
4. **Progressive playbooks.** Load `references/playbooks.md` when running
   `discover` or `rfc`, onboarding a new account (`switch <new-account>`), or
   compiling a `handoff`.
5. **Use the guard for writes it owns.** Append journal entries with `GUARD log`,
   change phase or status with `GUARD set`, and refresh the index with
   `GUARD reindex`. Edit `brain.md` sections directly, then run `GUARD reindex`.
   Never write credentials or personal data into any ledger file.

## Complete Command Suite

- `home` (or `open`) — Show the **FDE-VAULT** Cover Page and full Command Directory
  (`GUARD open` prints it in a terminal).
- `lock` — Run `GUARD lock`. The vault is sealed immediately.
- `accounts` (or `status`, `vaults`) — Run `GUARD reindex --check`, then `GUARD status`.
  Report any drift and show the Portfolio Index of all accounts.
- `select <account>` (or `switch`, `start`) — Run `GUARD switch <account>`. It
  sanitizes the name to `[a-z0-9-]`, clones `./.fde-vault/_blueprint/` if the
  account is new, binds the working directory in `brain.md`, writes
  `.active-vault`, and updates `index.json` atomically. For a new account follow
  Playbook A, then present the opening Chapter leaf.
- `setup` (or `discover`) — Generate a tailored Day-1 Technical Discovery charter from
  Playbook B and record each answer into `brain.md` under `Discovery Answers`.
- `notes [text]` (or `sync`, `log`) — Read the scrubbed `inbox.md`. If the user gave
  inline notes, pass them through `GUARD redact --text` first and use only the
  scrubbed output. Update `brain.md`, then append a dated diary entry with
  `GUARD log --tier GREEN|YELLOW|RED`, using `[CONFIG-TWEAK]`,
  `[EDGE-ADAPTER]`, or `[CORE-HACK]` respectively. Then run `GUARD inbox-clear`
  and `GUARD reindex`.
- `check-request "<request>"` (or `scope`) — Compare the request with `IN SCOPE` and `OUT OF SCOPE`
  in `brain.md`. Return `WITHIN SCOPE`, `SCOPE EXPANSION`, or `OUT OF SCOPE`
  with the matching rule ID, and draft a diplomatic stakeholder response.
- `check-code "<proposal>"` (or `preflight`, `guard`) — Validate the proposal against
  `references/core-rules.md`. Return `SAFE (GREEN)`, `CAUTION (YELLOW)`, or
  `STOP (RED)` with rule citations and compliant alternatives.
- `issue "<problem>"` (or `incident`) — Follow Playbook F: log with a UTC timestamp, list
  `YELLOW` and `RED` deviations as candidate root causes, give containment and
  permanent mitigation steps, and elevate status to `RED` with `GUARD set status RED`.
- `proposal "<feature>"` (or `rfc`) — Draft a formal upstream RFC with Playbook C, saved to
  `./.fde-vault/<active>/outputs/rfc-<slug>.md`.
- `summary` (or `brief`, `report`) — Generate a one-page Executive Status Brief (Playbook E),
  save it to `./.fde-vault/<active>/outputs/manager-brief.md`, and present it in
  book-page format.
- `finish` (or `handoff`, `done`) — Follow Playbook D: compile
  `outputs/handoff-runbook.md` and `outputs/core-feature-pitch.md`, then run
  `GUARD render-dashboard` to produce the interactive page-turning hardcover
  book at `outputs/dashboard.html`.
- `roadmap` (or `steps`) — Engagement table of contents and milestone roadmap.
- `steps` (or `/steps`) — Run `GUARD steps` and present the **Engagement Table of Contents**
  with `[Current Chapter]` aligned to the active account's `phase` and `status`.

## Selective Book Formatting Policy

Keep everyday operational commands (`status`, `switch`, `sync`, `scope`, `preflight`, `incident`, `steps`) crisp, concise, and direct in authoritative operational prose, ending with an indented blockquote ruling (when classifying architecture or scope) and a single italic running footer:
*Next Step: Run 'switch <account>' to mount an account ledger, or 'status' to view portfolio — or 'steps' to view the full engagement table of contents.*

Reserve the full **printed hardcover book-chapter layout** (Roman-numeral chapter heading `## Chapter <Roman-Numeral> — <Account-Title>`, folio metadata header, drop-cap style narrative entry, and ruling blockquote) for milestone deliverables:
- `brief` (One-page Executive Status Brief)
- `handoff` (Operational transition runbook and feature pitches)
- `outputs/dashboard.html` (Interactive page-turning hardcover HTML book)
- `outputs/dashboard.html` (Interactive page-turning hardcover HTML book)

Standard Layout Template for Full Chapter Milestones:

```markdown
## Chapter <Roman-Numeral> — <Account-Title>
**Account:** <Account>  |  **Stage:** <Phase>  |  **Date:** <YYYY-MM-DD>

---

### Entry <NN> — <HH:MM> UTC
<Concise narrative paragraph in a calm, authoritative operational voice,
summarizing the update, check, review, or status.>

> **Architectural Ruling — <GREEN / YELLOW / RED> (<Classification>, <Rule-ID>)**
> <Clear engineering explanation of the recommended, compliant path.>

---
*Next Step: Run `<command>` to <reason> — or `/steps` to view the full engagement table of contents.*
```

Rulings appear whenever an architectural classification is made (`CRITERIA-GREEN`, `CRITERIA-YELLOW`, `CRITERIA-RED`, or `RULE-01` through `RULE-05`). Omit the blockquote when none applies. When the vault is locked, the response contains only the unlock instruction and the running footer.

## Guard Reference

| Subcommand | Purpose | Needs unlocked session |
| --- | --- | --- |
| `open` | Animation, cover page, passphrase prompt (local terminal only) | No |
| `lock` | Seal the session | No |
| `redact [--text T]` | Scrub text locally | No |
| `status [--json]` | Session, active account, drift, portfolio | Yes |
| `steps` | Engagement table of contents | Yes |
| `switch <account>` | Create or activate an account | Yes |
| `reindex [--check]` | Rebuild or verify `index.json` | Yes |
| `log --tier T [--tag X] [--title T] text` | Append a journal entry | Yes |
| `set phase\|status <value>` | Update phase or status | Yes |
| `ingest --clipboard \| --file P [--wipe]` | Scrub into the inbox | Yes |
| `inbox-clear` | Reset the active inbox | Yes |
| `render-dashboard` | Build `outputs/dashboard.html` | Yes |
| `passwd` | Change the passphrase | Yes |

Phases: `Discovery`, `Build`, `Deploy`, `Stabilize`, `Handoff`.
Statuses: `GREEN`, `YELLOW`, `RED`.

## Security Notes

- **Session-Gated Isolation:** The passphrase gates sessions and tool access through hooks. Files in `./.fde-vault/` are plaintext markdown documents gated by session checks and firewall hooks; they are not encrypted at rest. Treat the vault as access-controlled and session-gated, not encrypted.
- **Best-Effort Redaction:** Redaction is best-effort pattern matching (API keys, tokens, private keys, JWTs, card numbers, phone numbers). Review `inbox.md` before `/sync` when material is sensitive.
- **Firewall Modes:** Hooks in `.claude/settings.json` block prompts and tool calls that contain credentials or personal data before they reach the model. By default (`FDE_FIREWALL=strict`), credentials and personal data are blocked; set `FDE_FIREWALL=credentials` to block credentials only. Tool access to `./.fde-vault/` is blocked while locked.
