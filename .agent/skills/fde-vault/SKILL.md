---
name: fde-vault
description: Enterprise Forward Deployed Engineer (FDE) application and command center. Enforces passphrase-locked vault sessions, session-gated account isolation, best-effort local secret/PII redaction, pre-implementation architecture guardrails, scope governance, incident triage, upstream RFC drafting, atomic multi-account indexing, and printed-book engineering diary artifacts.
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
   classifying requests or running `/preflight`. Every `GREEN`, `YELLOW`, or
   `RED` classification must cite the exact rule ID (`RULE-01` to `RULE-05`) and
   the matching criteria (`CRITERIA-GREEN`, `CRITERIA-YELLOW`, `CRITERIA-RED`).
4. **Progressive playbooks.** Load `references/playbooks.md` when running
   `/discover` or `/rfc`, onboarding a new account (`/switch <new-account>`), or
   compiling a `/handoff`.
5. **Use the guard for writes it owns.** Append journal entries with `GUARD log`,
   change phase or status with `GUARD set`, and refresh the index with
   `GUARD reindex`. Edit `brain.md` sections directly, then run `GUARD reindex`.
   Never write credentials or personal data into any ledger file.

## Complete Command Suite

- `/open` — Show the **FDE-VAULT** Cover Page and full Command Directory
  (`GUARD open` prints it in a terminal). Remind the user to launch with `fde` locally.
- `/lock` — Run `GUARD lock`. The vault is sealed immediately.
- `/status` (alias `/vaults`) — Run `GUARD reindex --check`, then `GUARD status`.
  Report any drift and show the Portfolio Index of all accounts.
- `/switch <account>` (alias `/start`) — Run `GUARD switch <account>`. It
  sanitizes the name to `[a-z0-9-]`, clones `./.fde-vault/_blueprint/` if the
  account is new, binds the working directory in `brain.md`, writes
  `.active-vault`, and updates `index.json` atomically. For a new account follow
  Playbook A, then present the opening Chapter leaf.
- `/discover` — Generate a tailored Day-1 Technical Discovery charter from
  Playbook B and record each answer into `brain.md` under `Discovery Answers`.
- `/sync [notes]` (alias `/log`) — Read the scrubbed `inbox.md`. If the user gave
  inline notes, pass them through `GUARD redact --text` first and use only the
  scrubbed output. Update `brain.md`, then append a dated diary entry with
  `GUARD log --tier GREEN|YELLOW|RED`, using `[CONFIG-TWEAK]`,
  `[EDGE-ADAPTER]`, or `[CORE-HACK]` respectively. Then run `GUARD inbox-clear`
  and `GUARD reindex`.
- `/scope "<request>"` — Compare the request with `IN SCOPE` and `OUT OF SCOPE`
  in `brain.md`. Return `WITHIN SCOPE`, `SCOPE EXPANSION`, or `OUT OF SCOPE`
  with the matching rule ID, and draft a diplomatic stakeholder response.
- `/preflight "<proposal>"` (alias `/guard`) — Validate the proposal against
  `references/core-rules.md`. Return `SAFE (GREEN)`, `CAUTION (YELLOW)`, or
  `STOP (RED)` with rule citations and compliant alternatives.
- `/incident "<issue>"` — Follow Playbook F: log with a UTC timestamp, list
  `YELLOW` and `RED` deviations as candidate root causes, give containment and
  permanent mitigation steps, and elevate status to `RED` with `GUARD set status RED`.
- `/rfc "<title>"` — Draft a formal upstream RFC with Playbook C, saved to
  `./.fde-vault/<active>/outputs/rfc-<slug>.md`.
- `/brief` (alias `/report`) — Generate a one-page Executive Status Brief (Playbook E),
  save it to `./.fde-vault/<active>/outputs/manager-brief.md`, and present it in
  book-page format.
- `/handoff` (alias `/done`) — Follow Playbook D: compile
  `outputs/handoff-runbook.md` and `outputs/core-feature-pitch.md`, then run
  `GUARD render-dashboard` to produce the interactive page-turning hardcover
  book at `outputs/dashboard.html`.
- `/steps` — Run `GUARD steps` and present the **Engagement Table of Contents**
  with `[Current Chapter]` aligned to the active account's `phase` and `status`.

## Selective Book Formatting Policy

Keep everyday operational commands (`/status`, `/switch`, `/sync`, `/scope`, `/preflight`, `/incident`, `/steps`) crisp, concise, and direct in authoritative operational prose, ending with an indented blockquote ruling (when classifying architecture or scope) and a single italic running footer:
*Next Step: Run `<command>` to <reason> — or `/steps` to view the full engagement table of contents.*

Reserve the full **printed hardcover book-chapter layout** (Roman-numeral chapter heading `## Chapter <Roman-Numeral> — <Account-Title>`, folio metadata header, drop-cap style narrative entry, and ruling blockquote) for milestone deliverables:
- `/brief` (One-page Executive Status Brief)
- `/handoff` (Operational transition runbook and feature pitches)
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
