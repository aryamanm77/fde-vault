# FDE-VAULT Playbooks

Load this file for `/discover`, `/rfc`, onboarding a new account
(`/switch <new-account>`), and compiling a `/handoff`.

## Playbook A — Onboarding a New Account

1. After `vault_guard.py switch <account>` reports `created: yes`, open
   `brain.md` and confirm `Working Directory` is bound.
2. Ask the user for the mission in one sentence, then draft `Mission`,
   `IN SCOPE`, and `OUT OF SCOPE` from the answer. Read the drafts back for
   confirmation before saving.
3. Offer `/discover` to complete the rest of the charter.
4. Remind the user that credentials and personal data go through
   `fde ingest --clipboard`, never through chat.

## Playbook B — Day-1 Technical Discovery (`/discover`)

Tailor the questions to the mission. Ask in groups of three or four, record each
answer into the `Discovery Answers` section of `brain.md` as it arrives, and
never ask for secrets.

**Outcome and users**
- What business outcome defines success, and by when?
- Who are the primary users, and how many?
- What happens today when the process fails?

**Systems and data**
- Which systems of record are involved, and who owns each?
- Which integration surfaces are supported (API, webhooks, files, events)?
- What data classes are involved, and which are regulated?

**Environment and operations**
- Where does this run, and who deploys to it?
- What are the availability, latency, and audit requirements?
- How are secrets stored today? (Ask where, never for the values.)

**Constraints and governance**
- Which change-approval gates exist?
- Which behaviors of the core product are non-negotiable for the customer?
- Who can approve scope changes, and how quickly?

Close by proposing updates to `IN SCOPE` and `OUT OF SCOPE`, a first list of
risks for `Open Risks`, and a phase recommendation.

## Playbook C — Upstream RFC (`/rfc "<title>"`)

Save to `outputs/rfc-<slug>.md`, where `<slug>` is the title lowercased with
hyphens. Use this structure:

```
# RFC: <title>

- **Status:** Draft
- **Author:** Forward Deployed Engineering
- **Date:** <YYYY-MM-DD>
- **Related rules:** <RULE-IDs>

## Summary
## Motivation
Customer problem in neutral terms. No customer names, credentials, or personal data.
## Current Workaround
## Proposal
## Alternatives Considered
## Compatibility and Migration
## Risks
## Open Questions
```

Anonymize the customer unless the user confirms the RFC is internal. Log the RFC
with `vault_guard.py log --tier GREEN --tag RFC`.

## Playbook D — Handoff (`/handoff`)

Compile these, then render the book:

1. `outputs/handoff-runbook.md`
   - Purpose and architecture overview
   - Deployed components and owners
   - Configuration reference (names only, never values)
   - Operational procedures and rollback steps
   - Known risks and open items from `Open Risks`
   - Every YELLOW and RED journal entry, with status and expiry
2. `outputs/core-feature-pitch.md`
   - Customer needs that recurred, written as upstream product proposals
   - For each: problem, current workaround, proposed core capability, value
3. Run `vault_guard.py set phase Handoff`, then
   `vault_guard.py render-dashboard`, and log the handoff with
   `vault_guard.py log --tier GREEN --tag HANDOFF`.

## Playbook E — Executive Brief (`/brief`)

One page, about 350 words, saved to `outputs/manager-brief.md`:
status and stage, accomplishments, deviations (YELLOW and RED with rule IDs),
risks, decisions needed, and next steps. Plain, specific, and free of
credentials and personal data.

## Playbook F — Incident (`/incident "<issue>"`)

1. Log with `vault_guard.py log --tier RED --tag INCIDENT --title "<issue>" "<facts>"`.
2. Scan the timeline for YELLOW and RED entries that touch the affected area and
   list them as candidate root causes, with entry dates.
3. Give two lists: Containment (minutes, reversible) and Permanent Mitigation
   (days, reviewed).
4. Run `vault_guard.py set status RED`.
