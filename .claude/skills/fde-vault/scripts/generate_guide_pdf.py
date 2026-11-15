#!/usr/bin/env python3
"""Generate the comprehensive FDE-VAULT Field Manual and User Guide as a print-ready PDF.

Standard library only + headless Chrome / Edge for pixel-perfect PDF rendering.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
OUTPUTS_DIR = REPO_ROOT / "outputs"
ASSETS_DIR = REPO_ROOT / "assets"
LOGO_SVG_PATH = ASSETS_DIR / "fde-vault-logo.svg"

HTML_PATH = OUTPUTS_DIR / "fde-vault-user-guide.html"
PDF_PATH = OUTPUTS_DIR / "fde-vault-user-guide.pdf"
ROOT_PDF_PATH = REPO_ROOT / "FDE-VAULT-USER-GUIDE.pdf"


def get_logo_svg():
    if LOGO_SVG_PATH.is_file():
        return LOGO_SVG_PATH.read_text(encoding="utf-8")
    return '<h1 style="color:#D4AA6D; text-align:center;">F D E · V A U L T</h1>'


def build_html():
    logo_svg = get_logo_svg()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FDE-VAULT — Field Manual & User Guide</title>
<style>
  @page {{
    size: letter;
    margin: 0.75in 0.85in 0.85in 0.85in;
    @bottom-center {{
      content: counter(page);
      font-family: Georgia, serif;
      font-size: 9pt;
      color: #8A6E4B;
    }}
  }}

  *, *:before, *:after {{
    box-sizing: border-box;
  }}

  body {{
    font-family: "Georgia", "Charter", "Times New Roman", serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #24201A;
    background-color: #FAF8F5;
    margin: 0;
    padding: 0;
  }}

  /* Page Break Helpers */
  .page-break {{
    page-break-after: always;
    break-after: page;
  }}

  /* Cover Page */
  .cover {{
    background: #141312;
    color: #F8F0DE;
    padding: 2.2in 0.8in 1.5in 0.8in;
    min-height: 9.5in;
    text-align: center;
    border: 3px double #8A6E4B;
    position: relative;
    page-break-after: always;
    break-after: page;
  }}

  .cover-logo {{
    max-width: 580px;
    margin: 0 auto 0.6in auto;
    display: block;
  }}

  .cover h1 {{
    font-size: 28pt;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #FCEFD2;
    margin: 0 0 0.15in 0;
    font-weight: 700;
  }}

  .cover-subtitle {{
    font-size: 13pt;
    font-style: italic;
    color: #D4AA6D;
    margin: 0 0 0.4in 0;
    line-height: 1.4;
  }}

  .cover-rule {{
    width: 220px;
    height: 1px;
    background: #8A6E4B;
    margin: 0 auto 0.4in auto;
  }}

  .cover-meta {{
    font-size: 9pt;
    color: #A89580;
    letter-spacing: 0.05em;
    line-height: 1.8;
  }}

  /* Typography */
  h1, h2, h3, h4 {{
    font-family: "Georgia", serif;
    color: #171513;
    font-weight: 700;
  }}

  h1.chapter-title {{
    font-size: 20pt;
    border-bottom: 2px solid #8A6E4B;
    padding-bottom: 0.1in;
    margin-top: 0.2in;
    margin-bottom: 0.25in;
    color: #1A1714;
  }}

  h1.chapter-title .chapter-num {{
    display: block;
    font-size: 10pt;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #965C1E;
    font-weight: 600;
    margin-bottom: 0.05in;
  }}

  h2 {{
    font-size: 13pt;
    color: #965C1E;
    margin-top: 0.28in;
    margin-bottom: 0.12in;
    border-bottom: 1px dashed #D4AA6D;
    padding-bottom: 0.04in;
  }}

  h3 {{
    font-size: 11pt;
    color: #2E2A24;
    margin-top: 0.2in;
    margin-bottom: 0.08in;
  }}

  p {{
    margin: 0 0 0.15in 0;
    text-align: justify;
    text-justify: inter-word;
  }}

  /* Drop Cap for opening paragraphs */
  .drop-cap:first-letter {{
    float: left;
    font-size: 38pt;
    line-height: 0.8;
    padding-top: 4px;
    padding-right: 8px;
    padding-bottom: 2px;
    font-family: "Georgia", serif;
    color: #965C1E;
    font-weight: 700;
  }}

  /* Code Blocks & Monospace */
  pre, code {{
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
  }}

  code {{
    font-size: 9pt;
    background: #EDE6DA;
    padding: 0.02in 0.05in;
    border-radius: 3px;
    color: #684112;
  }}

  pre {{
    background: #171513;
    color: #F8F0DE;
    padding: 0.14in 0.18in;
    border-radius: 6px;
    border-left: 4px solid #CE8A2E;
    font-size: 8.5pt;
    line-height: 1.45;
    overflow-x: auto;
    margin: 0.12in 0 0.18in 0;
  }}

  pre code {{
    background: transparent;
    color: inherit;
    padding: 0;
  }}

  /* Callout Boxes */
  .callout {{
    background: #F3ECE0;
    border-left: 4px solid #8A6E4B;
    padding: 0.12in 0.16in;
    margin: 0.16in 0;
    border-radius: 0 6px 6px 0;
    font-size: 9.5pt;
  }}

  .callout-title {{
    font-weight: bold;
    color: #965C1E;
    margin-bottom: 0.04in;
    text-transform: uppercase;
    font-size: 8.5pt;
    letter-spacing: 0.08em;
  }}

  .callout-security {{
    background: #F4EBE8;
    border-left-color: #A33A26;
  }}
  .callout-security .callout-title {{
    color: #A33A26;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.15in 0 0.22in 0;
    font-size: 9pt;
  }}

  th, td {{
    padding: 0.08in 0.1in;
    text-align: left;
    vertical-align: top;
    border-bottom: 1px solid #DDD3C3;
  }}

  th {{
    background: #2E2A24;
    color: #F8F0DE;
    font-family: "Georgia", serif;
    font-weight: 600;
    font-size: 8.5pt;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-bottom: 2px solid #8A6E4B;
  }}

  tr:nth-child(even) {{
    background-color: #F3ECE0;
  }}

  /* Step Badges */
  .step-num {{
    display: inline-block;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #965C1E;
    color: #FFF;
    text-align: center;
    line-height: 20px;
    font-size: 8pt;
    font-weight: bold;
    margin-right: 6px;
  }}

  /* Footer folio */
  .footer-rule {{
    margin-top: 0.4in;
    border-top: 1px solid #DDD3C3;
    padding-top: 0.08in;
    text-align: center;
    font-style: italic;
    font-size: 8pt;
    color: #8A6E4B;
  }}
</style>
</head>
<body>

<!-- ================= COVER PAGE ================= -->
<div class="cover">
  <div class="cover-logo">
    {logo_svg}
  </div>
  <h1>Field Manual</h1>
  <div class="cover-subtitle">Complete Operational Guide: From Download to Production Governance</div>
  <div class="cover-rule"></div>
  <div class="cover-meta">
    FORWARD DEPLOYED ENGINEER OPERATING SYSTEM<br />
    Universal Cross-Agent Ledger &bull; Standard Library &bull; Version 1.0.0<br />
    Compatible with Claude Code, Google Antigravity, Cursor &amp; Codex CLI
  </div>
</div>

<!-- ================= CHAPTER 1: INSTALLATION ================= -->
<div class="page-break">
  <h1 class="chapter-title">
    <span class="chapter-num">Chapter I</span>
    Installation &amp; First Launch
  </h1>

  <p class="drop-cap">
    Forward Deployed Engineers operate directly inside client infrastructure where speed, discretion, and operational hygiene are paramount. Setting up FDE-VAULT requires zero external dependencies, no administrator privileges, and exactly one terminal command.
  </p>

  <h2>1. One-Line Automatic Installation</h2>
  <p>Run the official installer for your operating system. It downloads the engine, registers the global <code>fde</code> shortcut, configures shell profiles, and mirrors the skill into your AI coding harnesses:</p>

  <h3>Windows PowerShell (Command Prompt or PowerShell)</h3>
  <pre><code>irm https://raw.githubusercontent.com/aryamanm77/fde-vault/main/install.ps1 | iex</code></pre>

  <h3>macOS &amp; Linux (Zsh or Bash)</h3>
  <pre><code>curl -fsSL https://raw.githubusercontent.com/aryamanm77/fde-vault/main/install.sh | bash</code></pre>

  <div class="callout">
    <div class="callout-title">What the Installer Configures</div>
    The installer executes idempotently: it places the application into <code>~/.fde-vault-app</code>, registers the global <code>fde</code> CLI shortcut into your shell profile (<code>$PROFILE</code>, <code>~/.zshrc</code>, or <code>~/.bashrc</code>), mirrors the skill suite to <code>~/.claude/skills/fde-vault/</code> and <code>~/.agent/skills/fde-vault/</code>, and configures permissions in <code>~/.claude/settings.json</code>.
  </div>

  <h2>2. Master Passphrase &amp; Session Security</h2>
  <p>
    FDE-VAULT protects client ledgers using salted <strong>PBKDF2-HMAC-SHA256</strong> password hashing (100,000 iterations). Raw credentials and passphrases are never stored in plaintext and never leave your local CPU.
  </p>
  <p>
    When you first launch the app by typing <code>fde</code> in your terminal:
  </p>
  <pre><code>fde</code></pre>
  <ol>
    <li>The kinetic startup emblem materializes on your console.</li>
    <li>You are prompted to enter and confirm your master vault passphrase (minimum 8 characters).</li>
    <li>An 8-hour authenticated local session token (<code>.session-unlocked</code>) is minted in <code>~/.fde-vault/</code>.</li>
    <li>All AI coding tools (Claude Code, Antigravity, Cursor) now share this unlocked ledger without prompting for passwords in chat.</li>
  </ol>

  <div class="callout callout-security">
    <div class="callout-title">Zero-Chat-Exposure Rule</div>
    Never enter your master passphrase into an AI chat window. Always unlock via <code>fde</code> in your local terminal. If your session expires, typing <code>fde lock</code> will instantly seal it, and <code>fde</code> will prompt to unlock.
  </div>
</div>

<!-- ================= CHAPTER 2: SCAFFOLDING A PROJECT ================= -->
<div class="page-break">
  <h1 class="chapter-title">
    <span class="chapter-num">Chapter II</span>
    Scaffolding an Engineering Repository
  </h1>

  <p class="drop-cap">
    FDE-VAULT is designed to govern codebases across multi-tenant client environments. You can equip any existing customer codebase or clean Git repository with FDE governance in seconds.
  </p>

  <h2>The Scaffolding Command: <code>fde init</code></h2>
  <p>Navigate to the code repository you are deploying to and execute:</p>
  <pre><code>cd /path/to/customer-project
fde init</code></pre>

  <h2>What <code>fde init</code> Scaffolds</h2>
  <p>The command safely creates the canonical governance hierarchy without modifying any existing production code or client account data:</p>

  <table>
    <thead>
      <tr>
        <th style="width: 38%;">Scaffolded Path</th>
        <th>Governance Purpose</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>.fde-vault/_blueprint/</code></td>
        <td>Template master containing clean <code>brain.md</code>, <code>timeline.md</code>, <code>inbox.md</code>, and <code>outputs/</code> used when provisioning new client accounts.</td>
      </tr>
      <tr>
        <td><code>.fde-vault/index.json</code></td>
        <td>The canonical portfolio registry tracking client accounts, delivery stages, and health scores. Preserved if already existing.</td>
      </tr>
      <tr>
        <td><code>.claude/skills/fde-vault/</code></td>
        <td>Skill definition, core rulebooks, playbooks, and local Python guard engine for Claude Code.</td>
      </tr>
      <tr>
        <td><code>.agent/skills/fde-vault/</code></td>
        <td>Identical skill mirror for Google Antigravity, Cursor, and other agent systems.</td>
      </tr>
      <tr>
        <td><code>.claude/settings.json</code></td>
        <td>PreToolUse and UserPromptSubmit firewall hooks preventing accidental secret leakage to cloud models.</td>
      </tr>
      <tr>
        <td><code>CLAUDE.md</code>, <code>AGENTS.md</code>, <code>GEMINI.md</code>, <code>.cursorrules</code></td>
        <td>Cross-agent root instructions directing all coding assistants to the central ledger.</td>
      </tr>
      <tr>
        <td><code>.gitignore</code></td>
        <td>Ensures live customer account data and session auth tokens are strictly ignored by Git while tracking templates.</td>
      </tr>
    </tbody>
  </table>

  <div class="callout">
    <div class="callout-title">Zero Demo Data Invariant</div>
    FDE-VAULT ships 100% pristine. It contains zero fictional account folders (no Acme or Globex). Every account in your vault represents genuine engineering engagements provisioned by you.
  </div>
</div>

<!-- ================= CHAPTER 3: LAUNCHING & COMMAND CENTER ================= -->
<div class="page-break">
  <h1 class="chapter-title">
    <span class="chapter-num">Chapter III</span>
    The Command Center &amp; AI Integration
  </h1>

  <p class="drop-cap">
    FDE-VAULT functions identically across terminal shells and AI chat environments. Whether you are working in bash, PowerShell, Claude Code, or Antigravity, the command center provides unified governance.
  </p>

  <h2>1. Launching from Terminal (Kinetic Motion Emblem)</h2>
  <p>
    Typing <code>fde</code> in any interactive terminal runs the ~1.2s 60 FPS typographic startup animation in full 24-bit TrueColor amber and gold, followed by the Home Screen and active session status:
  </p>
  <pre><code>fde</code></pre>

  <h2>2. Launching Inside AI Coding Tools (Claude Code, Antigravity, Cursor)</h2>
  <p>
    When working in Claude Code, Google Antigravity, or Cursor chat, you do not need shell prefixes. Simply type:
  </p>
  <pre><code>fde</code></pre>
  <p><em>(or type <code>home</code>)</em></p>
  <p>
    The assistant immediately responds in ~0.1s with the geometric emblem logo and the 1-line command directory table. Because permissions are pre-configured, it <strong>never interrupts you with permission popups</strong>.
  </p>

  <h2>The Home Screen Display</h2>
  <pre><code>                    ▄████████▄        
                  ▄██▀  ██  ▀██▄      ██████   █████▄   ██████
                 ██▀   ▄██▄   ▀██     ██▄▄     ██  ██   ██▄▄  
                 ██▄▄▄██████▄▄▄██     ██▀▀     ██  ██   ██▀▀  
                 ██▀▀▀██████▀▀▀██     ██       █████▀   ██████
                 ██▄   ▀██▀   ▄██     
                  ▀██▄  ██  ▄██▀      V A U L T               
                    ▀████████▀        

                       ● Ready.                        

## F D E · V A U L T
> STATUS: UNLOCKED — Active Account: none (Session active)</code></pre>

  <div class="callout">
    <div class="callout-title">Instant Chat Trigger</div>
    Typing <code>fde</code> or <code>home</code> in AI chat executes with zero shell latency. The assistant reads the session state from <code>.fde-vault/.session-unlocked</code> directly and renders the Home Screen in milliseconds.
  </div>
</div>

<!-- ================= CHAPTER 4: THE 13 EVERYDAY COMMANDS ================= -->
<div class="page-break">
  <h1 class="chapter-title">
    <span class="chapter-num">Chapter IV</span>
    The 13 Everyday Commands
  </h1>

  <p class="drop-cap">
    FDE-VAULT replaces obscure corporate jargon with intuitive, everyday plain English words. Below is the complete operational guide for each command.
  </p>

  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Command</th>
        <th style="width: 20%;">Aliases</th>
        <th>What It Does &amp; When to Use It</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>home</code></td>
        <td><code>open</code></td>
        <td>Displays the Cover Page, logo emblem, session expiration, and full command directory.</td>
      </tr>
      <tr>
        <td><code>lock</code></td>
        <td>—</td>
        <td>Destroys active session tokens immediately. Use when stepping away from your machine.</td>
      </tr>
      <tr>
        <td><code>accounts</code></td>
        <td><code>status</code>, <code>vaults</code></td>
        <td>Verifies index synchronization and displays the portfolio index of all customer accounts, stages, and health scores.</td>
      </tr>
      <tr>
        <td><code>select &lt;acct&gt;</code></td>
        <td><code>switch</code>, <code>start</code></td>
        <td>Mounts an existing customer ledger or provisions a new one from <code>_blueprint/</code>. Sets the active context for all operations.</td>
      </tr>
      <tr>
        <td><code>setup</code></td>
        <td><code>discover</code></td>
        <td>Conducts the Day-1 technical discovery interview: systems, integration points, stakeholders, and boundaries. Saves answers to <code>brain.md</code>.</td>
      </tr>
      <tr>
        <td><code>notes [text]</code></td>
        <td><code>sync</code>, <code>log</code></td>
        <td>Processes scrubbed raw notes from <code>inbox.md</code> into <code>timeline.md</code> and updates the account charter.</td>
      </tr>
      <tr>
        <td><code>check-request "&lt;req&gt;"</code></td>
        <td><code>scope</code></td>
        <td>Evaluates a client feature request against agreed scope boundaries (<code>IN SCOPE</code> vs. <code>OUT OF SCOPE</code>). Drafts diplomatic replies.</td>
      </tr>
      <tr>
        <td><code>check-code "&lt;prop&gt;"</code></td>
        <td><code>preflight</code>, <code>guard</code></td>
        <td>Triages architectural proposals against 5 core enterprise rules before writing code: SAFE (Green), CAUTION (Yellow), or STOP (Red).</td>
      </tr>
      <tr>
        <td><code>issue "&lt;desc&gt;"</code></td>
        <td><code>incident</code></td>
        <td>Logs a live production incident with UTC timestamp, severity, candidate root cause, and immediate containment runbook.</td>
      </tr>
      <tr>
        <td><code>proposal "&lt;title&gt;"</code></td>
        <td><code>rfc</code></td>
        <td>Drafts a formal upstream engineering Request for Comments (RFC) document in <code>outputs/rfc-&lt;title&gt;.md</code>.</td>
      </tr>
      <tr>
        <td><code>summary</code></td>
        <td><code>brief</code>, <code>report</code></td>
        <td>Generates a crisp 1-page executive status brief for leadership and non-technical stakeholders in <code>outputs/manager-brief.md</code>.</td>
      </tr>
      <tr>
        <td><code>finish</code></td>
        <td><code>handoff</code>, <code>done</code></td>
        <td>Compiles final customer transition manual (<code>outputs/handoff-runbook.md</code>) and renders the interactive hardcover book dashboard.</td>
      </tr>
      <tr>
        <td><code>roadmap</code></td>
        <td><code>steps</code></td>
        <td>Displays the engagement table of contents, delivery milestones, and phase checklist (Discovery &rarr; PoC &rarr; Pilot &rarr; Production).</td>
      </tr>
    </tbody>
  </table>
</div>

<!-- ================= CHAPTER 5: ZERO-CHAT-EXPOSURE SECURITY ================= -->
<div class="page-break">
  <h1 class="chapter-title">
    <span class="chapter-num">Chapter V</span>
    Zero-Chat-Exposure Security Pipeline
  </h1>

  <p class="drop-cap">
    The central vulnerability of terminal AI agents is accidental credential leakage. Engineers copy-paste API tokens, customer database connection strings, or personal data into chat, exposing secrets to model training and cloud telemetry. FDE-VAULT eliminates this completely.
  </p>

  <h2>1. Local CPU Secret Redaction (No Cloud Exposure)</h2>
  <p>
    FDE-VAULT features a local, CPU-side regex scrubbing pipeline in <code>vault_guard.py</code> that scrubs 18+ enterprise secret formats before text leaves your machine:
  </p>
  <ul>
    <li>AWS Access Keys (<code>AKIA...</code>) &amp; GitHub Personal Access Tokens (<code>ghp_...</code>)</li>
    <li>Stripe API Keys (<code>sk_live_...</code>) &amp; Slack Tokens (<code>xoxb-...</code>)</li>
    <li>RSA / OpenSSH Private Keys (<code>BEGIN PRIVATE KEY</code>)</li>
    <li>Bearer JWT Tokens &amp; Database Connection Strings (<code>postgres://...</code>)</li>
    <li>Personal PII: Credit card numbers, Social Security Numbers, and email addresses</li>
  </ul>

  <h2>2. Safe Ingestion Commands</h2>
  <h3>Ingest from Host Clipboard Directly</h3>
  <pre><code>fde ingest --clipboard</code></pre>
  <p>Reads your clipboard, scrubs all detected credentials into safe tokens (e.g. <code>[REDACTED:AWS_KEY]</code>), appends clean text to <code>inbox.md</code>, and clears the clipboard.</p>

  <h3>Ingest from File and Securely Shred</h3>
  <pre><code>fde ingest --file sensitive-notes.txt --wipe</code></pre>
  <p>Scrubs the file into <code>inbox.md</code>, then performs a 3-pass DOD-standard secure file shredding overwrite before unlinking the source.</p>

  <h2>3. Active Terminal Firewall Hooks</h2>
  <p>
    When running inside Claude Code, <code>.claude/settings.json</code> activates two hooks:
  </p>
  <ul>
    <li><strong><code>UserPromptSubmit</code> (Prompt Firewall):</strong> Inspects every message you submit in chat. If you accidentally paste a credential, the hook intercepts the submission locally and rejects it before it reaches the network.</li>
    <li><strong><code>PreToolUse</code> (Tool Guard):</strong> Verifies that any file read, write, or bash operation is gated by an active vault session.</li>
  </ul>
</div>

<!-- ================= CHAPTER 6: FIELD WORKFLOW ================= -->
<div class="page-break">
  <h1 class="chapter-title">
    <span class="chapter-num">Chapter VI</span>
    Step-by-Step Field Engagement Lifecycle
  </h1>

  <p class="drop-cap">
    Here is the exact lifecycle of an FDE engagement using the everyday commands, from the first discovery call to final client offboarding:
  </p>

  <h2>Phase 1: Day 1 — Kickoff &amp; Account Provisioning</h2>
  <ol>
    <li><strong>Start Your Day:</strong> Unlock your session:
      <pre><code>fde</code></pre>
    </li>
    <li><strong>Select or Create Account:</strong> Mount the customer ledger in AI chat:
      <pre><code>select client-enterprise</code></pre>
    </li>
    <li><strong>Run Discovery Interview:</strong> Generate the technical questionnaire:
      <pre><code>setup</code></pre>
      Answer the questions with customer architects to establish mission, systems, and constraints.
    </li>
  </ol>

  <h2>Phase 2: Days 2–10 — Scoping &amp; Architectural Guardrails</h2>
  <ol>
    <li><strong>Ingest Meeting Notes:</strong> Paste raw notes via clipboard without exposing secrets:
      <pre><code>fde ingest --clipboard</code></pre>
      Then in AI chat, process them into the ledger:
      <pre><code>notes</code></pre>
    </li>
    <li><strong>Guard Against Scope Creep:</strong> When customer stakeholders request extra features:
      <pre><code>check-request "Add support for real-time Kafka streaming"</code></pre>
      FDE-VAULT evaluates the request against <code>brain.md</code> and drafts a diplomatic response.
    </li>
    <li><strong>Pre-Flight Architectural Check:</strong> Before committing code changes:
      <pre><code>check-code "Add Redis caching bypass around core auth service"</code></pre>
      Evaluates the proposal against Rule 01–05, flagging core hacks vs. edge adapters.
    </li>
  </ol>

  <h2>Phase 3: Days 11–20 — Production Delivery &amp; Incident Triage</h2>
  <ol>
    <li><strong>Incident Response:</strong> If an outage or deployment failure occurs:
      <pre><code>issue "Memory leak in background sync worker on Kubernetes"</code></pre>
      Logs the incident, assigns severity, identifies root causes, and creates containment steps.
    </li>
    <li><strong>Upstream Proposals:</strong> If an architectural change requires customer core team buy-in:
      <pre><code>proposal "Dedicated Webhook Consumer Queue"</code></pre>
    </li>
    <li><strong>Leadership Briefing:</strong> Generate a 1-page executive brief for stakeholders:
      <pre><code>summary</code></pre>
    </li>
  </ol>

  <h2>Phase 4: Day 21 — Handover &amp; Hardcover Book Generation</h2>
  <ol>
    <li><strong>Generate Handover Runbook:</strong> Complete the engagement:
      <pre><code>finish</code></pre>
      Compiles <code>outputs/handoff-runbook.md</code>, pitch deck, and compiles <code>outputs/dashboard.html</code>.
    </li>
    <li><strong>Interactive Hardcover Book:</strong> Open <code>outputs/dashboard.html</code> in any browser to review your complete engagement as a page-turning archival book.</li>
    <li><strong>Seal the Session:</strong> Lock down your vault:
      <pre><code>lock</code></pre>
    </li>
  </ol>

  <div class="footer-rule">
    FDE-VAULT &bull; Enterprise Forward Deployed Engineering Ledger &bull; End of Field Manual
  </div>
</div>

</body>
</html>
"""
    return html


def compile_pdf():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    html_content = build_html()
    HTML_PATH.write_text(html_content, encoding="utf-8")
    print(f"[build] Wrote HTML template to {HTML_PATH}")

    # Locate Chrome or Edge
    chrome_candidates = [
        shutil.which("chrome"),
        shutil.which("msedge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser"
    ]

    browser = None
    for cand in chrome_candidates:
        if cand and Path(cand).is_file():
            browser = str(cand)
            break

    if not browser:
        print("[error] Could not locate Google Chrome or Microsoft Edge for PDF rendering.")
        return 1

    print(f"[build] Rendering PDF via headless browser: {browser}...")
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={PDF_PATH}",
        str(HTML_PATH)
    ]

    res = subprocess.run(cmd, capture_output=True, timeout=30)
    if res.returncode == 0 and PDF_PATH.is_file():
        size_kb = PDF_PATH.stat().st_size / 1024
        print(f"[success] Generated PDF: {PDF_PATH} ({size_kb:.1f} KB)")
        # Also copy to root and artifact directory for immediate user convenience
        shutil.copy2(PDF_PATH, ROOT_PDF_PATH)
        print(f"[success] Copied to repository root: {ROOT_PDF_PATH}")
        artifact_dir = Path(r"C:\Users\User\.gemini\antigravity\brain\b8bd4fa2-e47c-455d-a3b3-bb63b7520796")
        if artifact_dir.is_dir():
            artifact_pdf = artifact_dir / "FDE-VAULT-FIELD-MANUAL.pdf"
            shutil.copy2(PDF_PATH, artifact_pdf)
            print(f"[success] Copied to artifact directory: {artifact_pdf}")
        return 0
    else:
        print(f"[error] PDF generation failed with code {res.returncode}")
        print("Stderr:", res.stderr.decode("utf-8", "replace"))
        return 1


if __name__ == "__main__":
    sys.exit(compile_pdf())
