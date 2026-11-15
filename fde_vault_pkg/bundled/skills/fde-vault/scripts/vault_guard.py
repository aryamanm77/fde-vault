#!/usr/bin/env python3
"""FDE-VAULT guard.

Passphrase-locked sessions, local secret and PII redaction, the multi-account
ledger, and the printed-book dashboard renderer.

Python 3 standard library only. Works on macOS, Linux and Windows.
"""

import argparse
import datetime
import getpass
import hashlib
import html
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VERSION = "1.0.0"
APP_TITLE = "FDE-VAULT"
APP_SUBTITLE = "Enterprise Forward Deployed Engineering Ledger"
ITERATIONS = 100000
DEFAULT_TTL_HOURS = 8.0
MIN_PASSPHRASE = 10
PHASES = ["Discovery", "Build", "Deploy", "Stabilize", "Handoff"]
STATUSES = ["GREEN", "YELLOW", "RED"]
TIER_TAGS = {"GREEN": "CONFIG-TWEAK", "YELLOW": "EDGE-ADAPTER", "RED": "CORE-HACK"}
ACCOUNT_RE = re.compile(r"^[a-z0-9-]{1,48}$")
TAG_RE = re.compile(r"^[A-Z0-9-]{3,24}$")
ENTRY_RE = re.compile(
    r"^### (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) UTC \u2014 (GREEN|YELLOW|RED)"
    r"(?: \[([A-Z0-9-]+)\])?[ \t]*$",
    re.M,
)
MARKER_START = "# >>> fde-vault >>>"
MARKER_END = "# <<< fde-vault <<<"

TERMINAL_COMMANDS = [
    ("fde  |  fde open", "Unlock the vault with your passphrase and open the ledger"),
    ("fde lock", "Seal the vault session immediately"),
    ("fde status", "Session state, active account and portfolio index"),
    ("fde steps", "Engagement table of contents for the active account"),
    ("fde ingest --clipboard", "Scrub the clipboard into the active inbox locally"),
    ("fde ingest --file PATH --wipe", "Scrub a file into the inbox, then shred the source"),
    ("fde redact", "Scrub text from standard input; no session required"),
    ("fde reindex [--check]", "Rebuild or verify the portfolio index"),
    ("fde render-dashboard", "Render the hardcover book to outputs/dashboard.html"),
    ("fde passwd", "Change the vault passphrase"),
]
ASSISTANT_COMMANDS = [
    ("/open", "Cover page and full command directory"),
    ("/lock", "Seal the vault session immediately"),
    ("/status  (/vaults)", "Verify index drift and show the portfolio index"),
    ("/switch <account>  (/start)", "Create or activate an account ledger"),
    ("/discover", "Day-1 technical discovery charter"),
    ("/sync [notes]  (/log)", "Process the scrubbed inbox into the ledger"),
    ('/scope "<request>"', "Check a request against scope boundaries"),
    ('/preflight "<proposal>"  (/guard)', "Check a proposal against the core rules"),
    ('/incident "<issue>"', "Log a live production issue and mitigation"),
    ('/rfc "<title>"', "Draft an upstream engineering RFC"),
    ("/brief  (/report)", "One-page executive status brief"),
    ("/handoff  (/done)", "Runbook, pitch and hardcover dashboard"),
    ("/steps", "Engagement table of contents"),
]

BLUEPRINT = {
    "brain.md": (
        "# Account Brain: {{ACCOUNT}}\n\n"
        "- **Account:** {{ACCOUNT}}\n"
        "- **Phase:** Discovery\n"
        "- **Status:** GREEN\n"
        "- **Working Directory:** \n"
        "- **Created:** {{DATE}}\n"
        "- **Updated:** {{DATE}}\n\n"
        "## Mission\n"
        "<!-- One paragraph: the customer outcome this engagement exists to deliver. -->\n\n"
        "## IN SCOPE\n"
        "<!-- One boundary per bullet. -->\n\n"
        "## OUT OF SCOPE\n"
        "<!-- One exclusion per bullet. -->\n\n"
        "## Stakeholders\n"
        "<!-- Role and responsibility only. No personal contact details. -->\n\n"
        "## Architecture Notes\n"
        "<!-- Systems, integration points and constraints. No credentials. -->\n\n"
        "## Discovery Answers\n"
        "<!-- Recorded by /discover. -->\n\n"
        "## Decisions\n"
        "<!-- Dated architectural decisions with the rule IDs that governed them. -->\n\n"
        "## Open Risks\n"
        "<!-- Risks, owners and mitigation status. -->\n"
    ),
    "timeline.md": (
        "# Engineering Journal: {{ACCOUNT}}\n\n"
        "<!-- Entries are appended by: vault_guard.py log -->\n"
    ),
    "inbox.md": (
        "# Inbox: {{ACCOUNT}}\n\n"
        "<!-- Scrubbed notes await /sync. Clear with: vault_guard.py inbox-clear -->\n"
    ),
}


# ---------------------------------------------------------------- utilities

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def stamp():
    return utcnow().strftime("%Y-%m-%d %H:%M")


def iso_now():
    return utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg, code=1):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def read_text(path):
    return Path(path).read_text(encoding="utf-8", errors="replace")


def load_json(path, default=None):
    try:
        return json.loads(read_text(path))
    except (OSError, ValueError):
        return default


def atomic_write(path, text, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if mode is not None:
            try:
                os.chmod(tmp, mode)
            except OSError:
                pass
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def fmt_remaining(seconds):
    seconds = max(0, int(seconds))
    return "%dh %02dm" % (seconds // 3600, (seconds % 3600) // 60)


# ------------------------------------------------------------------- paths

def vault_dir():
    env = os.environ.get("FDE_VAULT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    cur = Path.cwd().resolve()
    for p in [cur] + list(cur.parents):
        if (p / ".fde-vault").is_dir():
            return p / ".fde-vault"
    return cur / ".fde-vault"


def auth_path():
    return vault_dir() / ".vault.auth"


def session_path():
    return vault_dir() / ".session-unlocked"


def fail_path():
    return vault_dir() / ".vault.fail"


def index_path():
    return vault_dir() / "index.json"


def active_path():
    return vault_dir() / ".active-vault"


# ---------------------------------------------------------------- redaction

def _luhn(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _looks_secret(value):
    if value.startswith(("[REDACTED", "<", "$", "{", "*", "%", "@")):
        return False
    if set(value) <= set("*xX.-_"):
        return False
    if "(" in value or ")" in value:
        return False
    return (any(c.isdigit() for c in value)
            or any(not c.isalnum() for c in value)
            or len(value) >= 12)


# (name, compiled regex, level). Level 0 = high-confidence credential formats
# (used by tool hooks), 1 = adds generic secret assignments, 2 = adds PII.
SPECIFIC_PATTERNS = [
    ("PRIVATE-KEY", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)"), 0),
    ("AWS-KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("GITHUB-TOKEN", re.compile(
        r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b"), 0),
    ("SLACK-TOKEN", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), 0),
    ("STRIPE-KEY", re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b"), 0),
    ("GOOGLE-KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), 0),
    ("API-KEY", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}\b"), 0),
    ("JWT", re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"), 0),
    ("BEARER-TOKEN", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"), 0),
]
URL_CRED_RE = re.compile(r"\b([a-z][a-z0-9+.-]*://)[^\s/:@]+:[^\s/@]+@")
GENERIC_RE = re.compile(
    r"(?i)\b([\w.-]*(?:password|passphrase|passwd|pwd|secret|token|api[_-]?key|"
    r"access[_-]?key|private[_-]?key)[\w.-]*[\"']?\s*[:=]\s*[\"']?)([^\s\"',;]{6,})")
CARD_RE = re.compile(r"(?<![\d-])(?:\d[ -]?){13,19}(?!\d)")
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\d)")

PROFILE_LEVELS = {"tools": 0, "credentials": 1, "all": 2}


def redact(text, profile="all"):
    """Return (scrubbed_text, counts). Never raises on odd input."""
    level = PROFILE_LEVELS.get(profile, 2)
    counts = {}

    def bump(name):
        counts[name] = counts.get(name, 0) + 1

    for name, rx, lvl in SPECIFIC_PATTERNS:
        if lvl <= level:
            text = rx.sub(
                lambda m, n=name: (bump(n), "[REDACTED:%s]" % n)[1], text)
    text = URL_CRED_RE.sub(
        lambda m: (bump("URL-CREDENTIALS"),
                   m.group(1) + "[REDACTED:URL-CREDENTIALS]@")[1], text)
    if level >= 1:
        def generic(m):
            if _looks_secret(m.group(2)):
                bump("SECRET-VALUE")
                return m.group(1) + "[REDACTED:SECRET-VALUE]"
            return m.group(0)
        text = GENERIC_RE.sub(generic, text)
    if level >= 2:
        def card(m):
            digits = re.sub(r"\D", "", m.group(0))
            if 13 <= len(digits) <= 19 and _luhn(digits):
                bump("CARD")
                return "[REDACTED:CARD]"
            return m.group(0)
        text = CARD_RE.sub(card, text)
        text = SSN_RE.sub(lambda m: (bump("SSN"), "[REDACTED:SSN]")[1], text)
        text = EMAIL_RE.sub(lambda m: (bump("EMAIL"), "[REDACTED:EMAIL]")[1], text)
        text = PHONE_RE.sub(lambda m: (bump("PHONE"), "[REDACTED:PHONE]")[1], text)
    return text, counts


def summarize_counts(counts):
    return ", ".join("%s x%d" % (k, v) for k, v in sorted(counts.items())) or "none"


# ------------------------------------------------------ passphrase + session

def _hash_pass(passphrase, salt, iterations=ITERATIONS):
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode("utf-8"), salt, iterations)


def set_passphrase(passphrase):
    salt = secrets.token_bytes(16)
    data = {
        "algorithm": "pbkdf2-hmac-sha256",
        "iterations": ITERATIONS,
        "salt": salt.hex(),
        "hash": _hash_pass(passphrase, salt).hex(),
        "created": iso_now(),
    }
    atomic_write(auth_path(), json.dumps(data, indent=2) + "\n", 0o600)


def verify_passphrase(passphrase):
    data = load_json(auth_path())
    if not data:
        return False
    try:
        salt = bytes.fromhex(data["salt"])
        expected = bytes.fromhex(data["hash"])
        iters = int(data.get("iterations", ITERATIONS))
    except (KeyError, ValueError):
        return False
    return secrets.compare_digest(_hash_pass(passphrase, salt, iters), expected)


def _auth_fingerprint():
    data = load_json(auth_path())
    if not data or "hash" not in data:
        return ""
    return hashlib.sha256(str(data["hash"]).encode("utf-8")).hexdigest()[:16]


def session_ttl_seconds():
    try:
        hours = float(os.environ.get("FDE_SESSION_TTL_HOURS", DEFAULT_TTL_HOURS))
    except ValueError:
        hours = DEFAULT_TTL_HOURS
    return max(1.0, hours * 3600.0)


def create_session():
    now = time.time()
    data = {
        "token": secrets.token_hex(16),
        "created": now,
        "expires": now + session_ttl_seconds(),
        "auth": _auth_fingerprint(),
    }
    atomic_write(session_path(), json.dumps(data) + "\n", 0o600)
    return data


def destroy_session():
    try:
        session_path().unlink()
        return True
    except OSError:
        return False


def session_info():
    data = load_json(session_path()) if session_path().exists() else None
    if (not data or data.get("auth") != _auth_fingerprint()
            or float(data.get("expires", 0)) <= time.time()):
        if session_path().exists():
            destroy_session()
        return {"active": False, "remaining": 0}
    return {"active": True, "remaining": int(float(data["expires"]) - time.time()),
            "expires": float(data["expires"])}


def lockout_remaining():
    data = load_json(fail_path(), {}) or {}
    return max(0, int(float(data.get("until", 0)) - time.time()))


def record_failure():
    data = load_json(fail_path(), {}) or {}
    count = int(data.get("count", 0)) + 1
    atomic_write(fail_path(), json.dumps(
        {"count": count, "until": time.time() + min(300, 2 ** count)}) + "\n", 0o600)


def clear_failures():
    try:
        fail_path().unlink()
    except OSError:
        pass


def require_unlocked():
    if not auth_path().exists():
        die("Vault is not initialised. Run `fde` in your local terminal to set a "
            "passphrase. Never type the passphrase into AI chat.", 3)
    if not session_info()["active"]:
        die("Vault is locked. Run `fde` in your local terminal to unlock it with "
            "your passphrase. Never type the passphrase into AI chat.", 3)


# ------------------------------------------------------------ vault layout

def ensure_blueprint():
    bp = vault_dir() / "_blueprint"
    for name, content in BLUEPRINT.items():
        if not (bp / name).exists():
            atomic_write(bp / name, content)
    keep = bp / "outputs" / ".gitkeep"
    if not keep.exists():
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.write_text("", encoding="utf-8")


def ensure_index():
    if not index_path().exists():
        atomic_write(index_path(), '{"generated_at": "", "vaults": {}}\n')


def ensure_gitignore():
    root = vault_dir().parent
    gi = root / ".gitignore"
    block = "%s\n.fde-vault/*\n!.fde-vault/_blueprint/\n%s\n" % (MARKER_START, MARKER_END)
    existing = read_text(gi) if gi.exists() else ""
    if MARKER_START in existing:
        return
    sep = "" if (not existing or existing.endswith("\n")) else "\n"
    atomic_write(gi, existing + sep + block)


def ensure_layout():
    vault_dir().mkdir(parents=True, exist_ok=True)
    ensure_blueprint()
    ensure_index()
    ensure_gitignore()


def sanitize_account(raw):
    name = re.sub(r"[^a-z0-9-]+", "-", raw.strip().lower())
    name = re.sub(r"-{2,}", "-", name).strip("-")[:48].strip("-")
    if not name or not ACCOUNT_RE.match(name):
        die("Account name must contain letters or digits (allowed: a-z, 0-9, hyphen).", 2)
    return name


def active_account(required=True):
    p = active_path()
    name = read_text(p).strip() if p.exists() else ""
    if name and ACCOUNT_RE.match(name) and (vault_dir() / name / "brain.md").exists():
        return name
    if required:
        die("No active account. Run /switch <account> first.", 4)
    return ""


def field_re(name):
    return re.compile(r"^- \*\*" + re.escape(name) + r":\*\*[ \t]*(.*)$", re.M)


def get_field(text, name):
    m = field_re(name).search(text)
    return m.group(1).strip() if m else ""


def set_field(text, name, value):
    line = "- **%s:** %s" % (name, value)
    rx = field_re(name)
    if rx.search(text):
        return rx.sub(lambda m: line, text, count=1)
    found = list(re.finditer(r"^- \*\*[^*]+:\*\*.*$", text, re.M))
    if found:
        pos = found[-1].end()
        return text[:pos] + "\n" + line + text[pos:]
    return line + "\n" + text


def update_brain(acct, **fields):
    path = vault_dir() / acct / "brain.md"
    text = read_text(path)
    for key, value in fields.items():
        text = set_field(text, key.replace("_", " "), value)
    text = set_field(text, "Updated", stamp() + " UTC")
    atomic_write(path, text)


def parse_timeline(text):
    matches = list(ENTRY_RE.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        entries.append({"date": m.group(1), "time": m.group(2), "tier": m.group(3),
                        "tag": m.group(4) or "", "body": text[m.end():end].strip()})
    return entries


def account_dirs():
    vd = vault_dir()
    if not vd.is_dir():
        return []
    return sorted(p for p in vd.iterdir()
                  if p.is_dir() and ACCOUNT_RE.match(p.name) and (p / "brain.md").exists())


def compute_index():
    vaults = {}
    for d in account_dirs():
        brain = read_text(d / "brain.md")
        tl = d / "timeline.md"
        entries = parse_timeline(read_text(tl)) if tl.exists() else []
        vaults[d.name] = {
            "phase": get_field(brain, "Phase"),
            "status": get_field(brain, "Status"),
            "cwd": get_field(brain, "Working Directory"),
            "entries": len(entries),
            "yellow": sum(1 for e in entries if e["tier"] == "YELLOW"),
            "red": sum(1 for e in entries if e["tier"] == "RED"),
            "updated": get_field(brain, "Updated"),
        }
    return vaults


def reindex(check=False):
    """Return (ok, diffs). With check=False the index is rewritten atomically."""
    ensure_index()
    fresh = compute_index()
    existing = (load_json(index_path(), {}) or {}).get("vaults", {})
    diffs = []
    for name in sorted(set(fresh) | set(existing)):
        if name not in existing:
            diffs.append("missing from index: %s" % name)
        elif name not in fresh:
            diffs.append("stale in index: %s" % name)
        elif fresh[name] != existing[name]:
            diffs.append("changed: %s" % name)
    if check:
        return (not diffs), diffs
    atomic_write(index_path(), json.dumps(
        {"generated_at": iso_now(), "vaults": fresh}, indent=2) + "\n")
    return True, diffs


# ------------------------------------------------------- terminal animation

AMBER = "\033[38;5;179m"
IVORY = "\033[38;5;230m"
DIM = "\033[2m"
RESET = "\033[0m"
BOX_WIDTH = 60


def _paint(code, text, color):
    return "%s%s%s" % (code, text, RESET) if color else text


def _box_row(text=""):
    return "\u2551 \u2503" + text.center(BOX_WIDTH - 4) + "\u2551"


def play_animation(color):
    if os.name == "nt":
        os.system("")
    out = sys.stdout
    top = "\u2554" + "\u2550" * (BOX_WIDTH - 2) + "\u2557"
    bottom = "\u255a" + "\u2550" * (BOX_WIDTH - 2) + "\u255d"
    title = "F D E - V A U L T"
    out.write("\n")
    for line in (top, _box_row()):
        out.write("  " + _paint(AMBER, line, color) + "\n")
        out.flush()
        time.sleep(0.04)
    for i in range(len(title) + 1):
        out.write("\r  " + _paint(IVORY, _box_row(title[:i]), color))
        out.flush()
        time.sleep(0.02)
    out.write("\n")
    for line in (_box_row(APP_SUBTITLE), _box_row(), bottom):
        out.write("  " + _paint(AMBER, line, color) + "\n")
        out.flush()
        time.sleep(0.04)
    out.write("\n")
    steps = ["[1/3] Mounting isolated account ledger...",
             "[2/3] Arming Zero-Chat-Exposure redaction engine...",
             "[3/3] Opening engineering journal..."]
    for step in steps:
        out.write("  " + _paint(IVORY, step, color) + "\n")
        out.flush()
        time.sleep(0.17)
    out.write("\n")
    out.flush()


def cover_text(color=False):
    rule = "\u2550" * 74
    lines = [_paint(AMBER, rule, color),
             _paint(IVORY, "%s \u2014 %s" % (APP_TITLE, APP_SUBTITLE), color),
             _paint(DIM, "Version %s  |  Vault: %s" % (VERSION, vault_dir()), color),
             _paint(AMBER, rule, color), "", "Terminal Commands"]
    for cmd, use in TERMINAL_COMMANDS:
        lines.append("  %-34s%s" % (cmd, use))
    lines += ["", "Assistant Commands (inside Claude Code, Antigravity, Cursor, Codex CLI)"]
    for cmd, use in ASSISTANT_COMMANDS:
        lines.append("  %-34s%s" % (cmd, use))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- commands

def cmd_open(args):
    ensure_layout()
    tty = sys.stdout.isatty()
    color = tty and not os.environ.get("NO_COLOR")
    if tty:
        play_animation(color)
    print(cover_text(color))
    info = session_info()
    if auth_path().exists() and info["active"]:
        print("Session already unlocked; %s remaining. Seal it with: fde lock"
              % fmt_remaining(info["remaining"]))
        return 0
    if not auth_path().exists():
        print("First launch. Choose a vault passphrase (minimum %d characters). It is "
              "stored only as a salted PBKDF2-HMAC-SHA256 hash." % MIN_PASSPHRASE)
        for _ in range(3):
            first = getpass.getpass("New passphrase: ")
            second = getpass.getpass("Confirm passphrase: ")
            if len(first) < MIN_PASSPHRASE:
                print("Passphrase must be at least %d characters." % MIN_PASSPHRASE)
            elif first != second:
                print("Passphrases did not match.")
            else:
                set_passphrase(first)
                break
        else:
            die("Passphrase setup aborted after three attempts.", 1)
    else:
        wait = lockout_remaining()
        if wait:
            die("Too many failed attempts. Try again in %d seconds." % wait, 1)
        verified = False
        for _ in range(3):
            if verify_passphrase(getpass.getpass("Vault passphrase: ")):
                verified = True
                clear_failures()
                break
            record_failure()
            print("Incorrect passphrase.")
            if lockout_remaining() > 8:
                break
        if not verified:
            die("Unlock failed.", 1)
    data = create_session()
    expires = datetime.datetime.fromtimestamp(data["expires"]).strftime("%H:%M")
    print("Vault unlocked. Session ends at %s local time. Return to your AI tool and "
          "run /status." % expires)
    return 0


def cmd_lock(args):
    sealed = destroy_session()
    print("Vault sealed." if sealed else "Vault was already sealed.")
    return 0


def cmd_status(args):
    info = session_info()
    if not auth_path().exists() or not info["active"]:
        state = "uninitialised" if not auth_path().exists() else "locked"
        if args.json:
            print(json.dumps({"state": state}))
        else:
            print("state: %s" % state)
            print("Run `fde` in your local terminal to unlock. Never type the "
                  "passphrase into AI chat.")
        return 3
    ensure_layout()
    ok, diffs = reindex(check=True)
    vaults = compute_index()
    active = active_account(required=False)
    if args.json:
        print(json.dumps({"state": "unlocked", "remaining_seconds": info["remaining"],
                          "utc_now": stamp(), "active": active, "drift": diffs,
                          "vaults": vaults}, indent=2))
        return 0
    print("state: unlocked")
    print("session_remaining: %s" % fmt_remaining(info["remaining"]))
    print("utc_now: %s UTC" % stamp())
    print("vault: %s" % vault_dir())
    print("active_account: %s" % (active or "none"))
    print("index_drift: %s" % ("none" if ok else "DRIFT (" + "; ".join(diffs) + ")"))
    print("accounts: %d" % len(vaults))
    if vaults:
        print("%-24s %-10s %-7s %-8s %-7s %-4s %s"
              % ("account", "phase", "status", "entries", "yellow", "red", "active"))
        for name, v in vaults.items():
            print("%-24s %-10s %-7s %-8d %-7d %-4d %s"
                  % (name, v["phase"], v["status"], v["entries"], v["yellow"],
                     v["red"], "*" if name == active else ""))
    return 0


def cmd_steps(args):
    require_unlocked()
    acct = active_account()
    brain = read_text(vault_dir() / acct / "brain.md")
    phase = get_field(brain, "Phase")
    status = get_field(brain, "Status")
    current = [p.lower() for p in PHASES].index(phase.lower()) \
        if phase.lower() in [p.lower() for p in PHASES] else -1
    print("## Engagement Table of Contents")
    print("**Account:** %s  |  **Stage:** %s  |  **Status:** %s\n" % (acct, phase, status))
    for i, name in enumerate(PHASES):
        if i < current:
            mark = "(complete)"
        elif i == current:
            mark = "**[Current Chapter]**"
        else:
            mark = "(upcoming)"
        print("- Chapter %s \u2014 %s %s" % (roman(i + 1), name, mark))
    return 0


def cmd_switch(args):
    require_unlocked()
    ensure_layout()
    acct = sanitize_account(args.account)
    target = vault_dir() / acct
    created = not target.exists()
    if created:
        shutil.copytree(str(vault_dir() / "_blueprint"), str(target))
        for name in BLUEPRINT:
            p = target / name
            text = read_text(p).replace("{{ACCOUNT}}", acct)
            text = text.replace("{{DATE}}", stamp() + " UTC")
            atomic_write(p, text)
    brain = read_text(target / "brain.md")
    previous = get_field(brain, "Working Directory")
    cwd = str(Path.cwd().resolve())
    update_brain(acct, Working_Directory=cwd)
    atomic_write(active_path(), acct + "\n")
    reindex()
    brain = read_text(target / "brain.md")
    print("account: %s" % acct)
    print("created: %s" % ("yes" if created else "no"))
    print("phase: %s" % get_field(brain, "Phase"))
    print("status: %s" % get_field(brain, "Status"))
    print("working_directory: %s" % cwd)
    if previous and previous != cwd:
        print("rebound_from: %s" % previous)
    print("utc_now: %s UTC" % stamp())
    return 0


def cmd_reindex(args):
    require_unlocked()
    ensure_layout()
    ok, diffs = reindex(check=args.check)
    if args.check:
        if ok:
            print("index: in sync")
            return 0
        print("index: DRIFT")
        for d in diffs:
            print("  " + d)
        return 1
    print("index: rebuilt (%d accounts)" % len(compute_index()))
    return 0


def cmd_log(args):
    require_unlocked()
    acct = active_account()
    tier = args.tier.upper()
    tag = (args.tag or TIER_TAGS[tier]).upper()
    if not TAG_RE.match(tag):
        die("Tag must be 3-24 characters: A-Z, 0-9, hyphen.", 2)
    body = " ".join(args.text).strip()
    if args.stdin or not body:
        body = (body + "\n" + sys.stdin.read()).strip() if not sys.stdin.isatty() else body
    if not body:
        die("Entry text is required (arguments or --stdin).", 2)
    body, counts = redact(body, "all")
    path = vault_dir() / acct / "timeline.md"
    text = read_text(path)
    number = len(parse_timeline(text)) + 1
    head = "### %s UTC \u2014 %s [%s]" % (stamp(), tier, tag)
    entry = head + "\n" + ("**%s**\n\n" % args.title.strip() if args.title else "\n") + body
    atomic_write(path, text.rstrip() + "\n\n" + entry + "\n")
    update_brain(acct)
    reindex()
    print("entry: %02d" % number)
    print("logged: %s UTC  %s [%s]" % (stamp(), tier, tag))
    if counts:
        print("redacted: %s" % summarize_counts(counts))
    return 0


def cmd_set(args):
    require_unlocked()
    acct = active_account()
    key = args.field.strip().lower()
    value = args.value.strip()
    if key == "phase":
        match = [p for p in PHASES if p.lower() == value.lower()]
        if not match:
            die("Phase must be one of: %s" % ", ".join(PHASES), 2)
        update_brain(acct, Phase=match[0])
    elif key == "status":
        if value.upper() not in STATUSES:
            die("Status must be one of: %s" % ", ".join(STATUSES), 2)
        update_brain(acct, Status=value.upper())
    else:
        die("Only 'phase' and 'status' can be set with this command.", 2)
    reindex()
    print("%s set to %s" % (key, value))
    return 0


def read_clipboard():
    system = platform.system()
    if system == "Darwin":
        cmds = [["pbpaste"]]
    elif system == "Windows":
        cmds = [["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]]
    else:
        cmds = [["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"],
                ["xsel", "--clipboard", "--output"]]
    for cmd in cmds:
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=8)
            if res.returncode == 0:
                return res.stdout.decode("utf-8", "replace")
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def clear_clipboard():
    system = platform.system()
    if system == "Darwin":
        cmds = [(["pbcopy"], b"")]
    elif system == "Windows":
        cmds = [(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ' '"], None)]
    else:
        cmds = [(["wl-copy", "--clear"], None),
                (["xclip", "-selection", "clipboard"], b""),
                (["xsel", "--clipboard", "--clear"], None)]
    for cmd, data in cmds:
        try:
            if subprocess.run(cmd, input=data, capture_output=True, timeout=8).returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def wipe_file(path):
    path = Path(path)
    size = path.stat().st_size
    with open(str(path), "r+b") as fh:
        fh.write(secrets.token_bytes(size))
        fh.flush()
        os.fsync(fh.fileno())
    path.unlink()


def cmd_ingest(args):
    require_unlocked()
    acct = active_account()
    if args.clipboard == bool(args.file):
        die("Choose exactly one source: --clipboard or --file PATH.", 2)
    if args.wipe and not args.file:
        die("--wipe applies to --file only.", 2)
    if args.clipboard:
        raw = read_clipboard()
        source = "clipboard"
        if raw is None:
            die("No clipboard utility available (pbpaste, wl-paste, xclip, xsel, PowerShell).", 5)
    else:
        src = Path(args.file).expanduser()
        if not src.is_file():
            die("File not found: %s" % args.file, 2)
        if src.stat().st_size > 2 * 1024 * 1024:
            die("File exceeds the 2 MB ingest limit.", 2)
        raw = read_text(src)
        source = "file"
    if not raw.strip():
        die("Nothing to ingest.", 2)
    scrubbed, counts = redact(raw, "all")
    path = vault_dir() / acct / "inbox.md"
    existing = read_text(path)
    block = "### Inbox Item \u2014 %s UTC (source: %s)\n%s\n\n_Redactions: %s_\n" % (
        stamp(), source, scrubbed.strip(), summarize_counts(counts))
    atomic_write(path, existing.rstrip() + "\n\n" + block)
    print("ingested: %d characters into %s/inbox.md" % (len(raw), acct))
    print("redactions: %s" % summarize_counts(counts))
    print("No content was displayed. Run /sync in your AI tool to process the inbox.")
    if args.file and args.wipe:
        wipe_file(Path(args.file).expanduser())
        print("source file shredded and removed")
    if args.clipboard and args.clear_clipboard:
        print("clipboard cleared" if clear_clipboard() else "clipboard could not be cleared")
    return 0


def cmd_inbox_clear(args):
    require_unlocked()
    acct = active_account()
    atomic_write(vault_dir() / acct / "inbox.md",
                 BLUEPRINT["inbox.md"].replace("{{ACCOUNT}}", acct))
    print("inbox cleared")
    return 0


def cmd_redact(args):
    text = args.text if args.text is not None else sys.stdin.read()
    out, counts = redact(text, args.profile)
    sys.stdout.write(out)
    if counts and not args.quiet:
        sys.stderr.write("\nredactions: %s\n" % summarize_counts(counts))
    return 0


def cmd_passwd(args):
    require_unlocked()
    if not verify_passphrase(getpass.getpass("Current passphrase: ")):
        die("Incorrect passphrase.", 1)
    first = getpass.getpass("New passphrase: ")
    second = getpass.getpass("Confirm new passphrase: ")
    if len(first) < MIN_PASSPHRASE or first != second:
        die("New passphrase rejected (too short or mismatch).", 1)
    set_passphrase(first)
    create_session()
    print("Passphrase changed. Session renewed.")
    return 0


# --------------------------------------------------------- dashboard book

def roman(n):
    out = ""
    for value, sym in ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= value:
            out += sym
            n -= value
    return out


def inline_md(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<!\w)_(?!\s)(.+?)(?<!\s)_(?!\w)", r"<em>\1</em>", s)
    return s


def md_blocks(md):
    """Convert markdown to a list of (html, weight, kind) blocks."""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    blocks, para, quote = [], [], []

    def flush():
        if para:
            text = " ".join(para).strip()
            blocks.append(("<p>%s</p>" % inline_md(text), len(text) + 90, "p"))
            del para[:]
        if quote:
            text = " ".join(quote).strip()
            blocks.append(("<blockquote>%s</blockquote>" % inline_md(text),
                           len(text) + 110, "q"))
            del quote[:]

    for raw in md.splitlines():
        s = raw.strip()
        if not s:
            flush()
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            level = 3 if len(m.group(1)) <= 3 else 4
            blocks.append(("<h%d>%s</h%d>" % (level, inline_md(m.group(2)), level), 140, "h"))
        elif s.startswith(">"):
            if para:
                flush()
            quote.append(s.lstrip("> ").strip())
        elif re.match(r"^[-*]\s+", s):
            flush()
            item = re.sub(r"^[-*]\s+(\[[ xX]\]\s+)?", "", s)
            blocks.append(('<ul class="tight"><li>%s</li></ul>' % inline_md(item),
                           len(item) + 70, "l"))
        elif re.match(r"^\d+[.)]\s+", s):
            flush()
            num = re.match(r"^(\d+)", s).group(1)
            item = re.sub(r"^\d+[.)]\s+", "", s)
            blocks.append(('<ol class="tight" start="%s"><li>%s</li></ol>' % (num, inline_md(item)),
                           len(item) + 70, "l"))
        elif s in ("---", "***"):
            flush()
            blocks.append(("<hr>", 30, "r"))
        else:
            if quote:
                flush()
            para.append(s)
    flush()
    return blocks


def paginate(blocks, budget=1750):
    pages = [[]]
    used = 0
    for block in blocks:
        if pages[-1] and used + block[1] > budget:
            carry = []
            while len(pages[-1]) > 1 and pages[-1][-1][2] == "h":
                carry.insert(0, pages[-1].pop())
            pages.append(carry)
            used = sum(b[1] for b in carry)
        pages[-1].append(block)
        used += block[1]
    return pages


def chapter_pages(label, title, blocks):
    out = []
    for i, page in enumerate(paginate(blocks)):
        inner = "".join(b[0] for b in page)
        if i == 0:
            if page and page[0][2] == "p":
                inner = inner.replace("<p>", '<p class="dropcap">', 1)
            head = ('<div class="chapter-no">%s</div><h2>%s</h2><div class="orn">&sect;</div>'
                    % (html.escape(label), html.escape(title)))
            out.append('<div class="chapter-open">%s%s</div>' % (head, inner))
        else:
            out.append('<div class="chapter-cont"><div class="running">%s &mdash; continued'
                       '</div>%s</div>' % (html.escape(title), inner))
    return out


def split_sections(md):
    parts = re.split(r"^## +(.+)$", md, flags=re.M)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


BOOK_CSS = """
:root{--paper:#FAF7F0;--ink:#2a241c;--rule:#b9a98a;--accent:#7a4b1e;--desk:#e7dfcf;
--green:#4a6b3a;--yellow:#9a7420;--red:#8c2f2f;--muted:#6b5d44}
*{box-sizing:border-box}
html,body{margin:0;background:var(--desk);color:var(--ink);
font-family:Georgia,"Iowan Old Style","Palatino Linotype",Palatino,"Times New Roman",serif}
.book{max-width:800px;margin:20px auto;padding:0 12px}
.leaf{position:relative;background:var(--paper);border:1px solid var(--rule);
outline:3px double var(--rule);outline-offset:-10px;
box-shadow:0 14px 34px rgba(60,40,10,.28),inset 16px 0 20px -14px rgba(60,40,10,.4)}
.page{display:none;position:relative;padding:58px 58px 78px 68px;min-height:min(86vh,980px)}
.page.active{display:block;animation:turn .5s ease both;transform-origin:left center}
@keyframes turn{from{opacity:0;transform:perspective(1400px) rotateY(-14deg)}
to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.page.active{animation:none}}
.folio{position:absolute;left:0;right:0;bottom:28px;text-align:center;
font-size:.95rem;letter-spacing:.2em;color:var(--muted)}
p{text-align:justify;hyphens:auto;line-height:1.72;margin:0 0 .9em;text-indent:1.5em}
.chapter-open p:first-of-type,.chapter-cont p:first-of-type,p.dropcap{text-indent:0}
p.dropcap::first-letter{float:left;font-size:3.9em;line-height:.82;padding:.06em .1em 0 0;
color:var(--accent);font-weight:bold}
.chapter-no{text-align:center;letter-spacing:.35em;text-transform:uppercase;
font-size:.8rem;color:var(--muted);margin-bottom:.4em}
h2{text-align:center;font-weight:normal;font-size:2rem;margin:.1em 0 .2em;letter-spacing:.04em}
h3{font-size:1.1rem;margin:1.2em 0 .4em}
h4{font-size:1rem;font-style:italic;margin:1em 0 .3em}
.orn{text-align:center;color:var(--rule);margin:.2em 0 1.4em;font-size:1.1rem}
.running{font-style:italic;color:var(--muted);text-align:center;font-size:.85rem;
border-bottom:1px solid var(--rule);padding-bottom:.6em;margin-bottom:1.4em}
blockquote{margin:1em 0 1em 1.6em;padding:.2em 0 .2em 1em;border-left:3px solid var(--accent);
font-style:italic}
ul.tight,ol.tight{margin:0 0 .3em 1.4em;padding:0;line-height:1.6}
code{font-family:"Courier New",monospace;font-size:.9em}
hr{border:0;border-top:1px solid var(--rule);margin:1.2em 0}
.cover{text-align:center;padding-top:9vh}
.cover-rule{border-top:3px double var(--accent);margin:1.8em 12%}
.cover-kicker{letter-spacing:.5em;text-indent:.5em;font-size:.85rem;color:var(--muted);text-align:center}
.cover h1{font-weight:normal;font-size:2.6rem;margin:.3em 0}
.cover-sub,.cover-meta,.cover-date{text-align:center;text-indent:0;font-style:italic}
.toc{list-style:none;margin:1.4em 0 0;padding:0}
.toc li{margin:.7em 0}
.toc a{display:flex;align-items:baseline;gap:.5em;color:var(--ink);text-decoration:none}
.toc a:hover span:first-child{color:var(--accent)}
.toc .leader{flex:1;border-bottom:1px dotted var(--rule)}
.entry{margin:0 0 1.3em;padding-left:.9em;border-left:3px solid var(--rule)}
.entry h3{margin:.1em 0 .4em;font-size:1rem}
.tier{font-size:.75rem;letter-spacing:.12em;margin-left:.6em;font-weight:bold}
.tier-green{border-left-color:var(--green)}.tier-green .tier{color:var(--green)}
.tier-yellow{border-left-color:var(--yellow)}.tier-yellow .tier{color:var(--yellow)}
.tier-red{border-left-color:var(--red)}.tier-red .tier{color:var(--red)}
.controls{display:flex;justify-content:space-between;align-items:center;margin:16px 0 28px}
.controls button{font:inherit;padding:.55em 1.2em;background:var(--paper);color:var(--ink);
border:1px solid var(--rule);cursor:pointer}
.controls button:disabled{opacity:.4;cursor:default}
.controls span{font-style:italic;color:var(--muted)}
.colophon{text-align:center;padding-top:20vh;font-style:italic}
.colophon p{text-align:center;text-indent:0}
@media (max-width:560px){.page{padding:36px 28px 70px 34px}h2{font-size:1.5rem}}
@media print{.controls{display:none}.page{display:block!important;page-break-after:always;
animation:none!important;min-height:0}.leaf{box-shadow:none;outline:0}}
"""

BOOK_JS = """
(function(){
var pages=[].slice.call(document.querySelectorAll('.page'));
var cur=0,prev=document.getElementById('prev'),next=document.getElementById('next'),
label=document.getElementById('where');
function show(i){
if(i<0||i>=pages.length){return;}
pages[cur].classList.remove('active');cur=i;pages[cur].classList.add('active');
prev.disabled=(cur===0);next.disabled=(cur===pages.length-1);
label.textContent='Page '+(cur+1)+' of '+pages.length;
window.scrollTo(0,0);
try{history.replaceState(null,'','#p'+(cur+1));}catch(e){}
}
prev.addEventListener('click',function(){show(cur-1);});
next.addEventListener('click',function(){show(cur+1);});
document.addEventListener('keydown',function(e){
if(e.key==='ArrowLeft'){show(cur-1);}else if(e.key==='ArrowRight'){show(cur+1);}
});
[].slice.call(document.querySelectorAll('[data-go]')).forEach(function(a){
a.addEventListener('click',function(e){e.preventDefault();show(parseInt(a.getAttribute('data-go'),10)-1);});
});
var m=/^#p(\\d+)$/.exec(location.hash||'');
show(m?Math.min(pages.length,Math.max(1,parseInt(m[1],10)))-1:0);
})();
"""


def build_book(acct):
    d = vault_dir() / acct
    brain = redact(read_text(d / "brain.md"), "all")[0]
    timeline = redact(read_text(d / "timeline.md"), "all")[0] if (d / "timeline.md").exists() else ""
    phase = get_field(brain, "Phase") or "Discovery"
    status = get_field(brain, "Status") or "GREEN"
    title = acct.replace("-", " ").title()
    today = utcnow().strftime("%Y-%m-%d")
    chapters = []
    n = 0
    for heading, body in split_sections(brain):
        n += 1
        blocks = md_blocks(body) or [("<p><em>No entries recorded yet.</em></p>", 40, "p")]
        label = "Chapter " + roman(n)
        chapters.append((label, heading, chapter_pages(label, heading, blocks)))
    n += 1
    entries = parse_timeline(timeline)
    jblocks = []
    for i, e in enumerate(entries, 1):
        tag = (" [%s]" % e["tag"]) if e["tag"] else ""
        body_html = "".join(b[0] for b in md_blocks(e["body"]))
        jblocks.append(('<article class="entry tier-%s"><h3>Entry %02d &mdash; %s %s UTC'
                        '<span class="tier">%s%s</span></h3>%s</article>'
                        % (e["tier"].lower(), i, e["date"], e["time"], e["tier"],
                           html.escape(tag), body_html), len(e["body"]) + 260, "entry"))
    if not jblocks:
        jblocks = [("<p><em>No journal entries have been recorded.</em></p>", 40, "p")]
    label = "Chapter " + roman(n)
    chapters.append((label, "Engineering Journal", chapter_pages(label, "Engineering Journal", jblocks)))
    out_dir = d / "outputs"
    letter = 0
    if out_dir.is_dir():
        for f in sorted(out_dir.glob("*.md")):
            letter += 1
            text = redact(read_text(f), "all")[0]
            label = "Appendix " + chr(64 + letter)
            blocks = md_blocks(text) or [("<p><em>Empty document.</em></p>", 40, "p")]
            chapters.append((label, f.stem.replace("-", " ").title(),
                             chapter_pages(label, f.stem.replace("-", " ").title(), blocks)))
    pages = []
    cover = ('<div class="cover"><div class="cover-kicker">FDE-VAULT</div>'
             '<div class="cover-rule"></div><h1>%s</h1>'
             '<p class="cover-sub">Engagement Ledger and Engineering Journal</p>'
             '<div class="cover-rule"></div>'
             '<p class="cover-meta">Stage: %s &middot; Status: %s</p>'
             '<p class="cover-date">Compiled %s</p></div>'
             % (html.escape(title), html.escape(phase), html.escape(status), today))
    pages.append((cover, False))
    folio = 3
    toc_items = []
    for label, ctitle, ps in chapters:
        toc_items.append('<li><a href="#" data-go="%d"><span>%s &mdash; %s</span>'
                         '<span class="leader"></span><span>%d</span></a></li>'
                         % (folio, html.escape(label), html.escape(ctitle), folio))
        folio += len(ps)
    toc = ('<div class="chapter-open"><div class="chapter-no">Contents</div>'
           '<h2>Table of Contents</h2><div class="orn">&sect;</div>'
           '<ul class="toc">%s</ul></div>' % "".join(toc_items))
    pages.append((toc, True))
    for _, _, ps in chapters:
        for inner in ps:
            pages.append((inner, True))
    colophon = ('<div class="colophon"><p>Compiled by FDE-VAULT %s on %s.</p>'
                '<p>All content was scrubbed locally for credentials and personal data '
                'before rendering.</p></div>' % (VERSION, today))
    pages.append((colophon, False))
    sections = []
    for i, (inner, show_folio) in enumerate(pages):
        foot = '<footer class="folio">%d</footer>' % (i + 1) if show_folio else ""
        sections.append('<section class="page" data-page="%d">%s%s</section>'
                        % (i + 1, inner, foot))
    doc = ("<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
           "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
           "<title>%s &mdash; Engagement Ledger</title><style>%s</style>"
           "<noscript><style>.page{display:block}</style></noscript></head><body>"
           "<main class=\"book\"><div class=\"leaf\">%s</div>"
           "<nav class=\"controls\"><button id=\"prev\" type=\"button\">Previous Page</button>"
           "<span id=\"where\"></span>"
           "<button id=\"next\" type=\"button\">Next Page</button></nav></main>"
           "<script>%s</script></body></html>\n"
           % (html.escape(title), BOOK_CSS, "".join(sections), BOOK_JS))
    return doc, len(pages)


def cmd_render_dashboard(args):
    require_unlocked()
    acct = active_account()
    doc, count = build_book(acct)
    out = vault_dir() / acct / "outputs" / "dashboard.html"
    atomic_write(out, doc)
    print("dashboard: %s" % out)
    print("pages: %d" % count)
    return 0


# -------------------------------------------------------------------- main

def build_parser():
    p = argparse.ArgumentParser(prog="vault_guard.py",
                                description="%s %s" % (APP_TITLE, APP_SUBTITLE))
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("open", help="unlock the vault")
    sub.add_parser("lock", help="seal the session")
    s = sub.add_parser("status", help="session and portfolio state")
    s.add_argument("--json", action="store_true")
    sub.add_parser("steps", help="engagement table of contents")
    s = sub.add_parser("switch", help="create or activate an account")
    s.add_argument("account")
    s = sub.add_parser("reindex", help="rebuild or verify index.json")
    s.add_argument("--check", action="store_true")
    s = sub.add_parser("log", help="append a timeline entry")
    s.add_argument("--tier", required=True, choices=STATUSES + [t.lower() for t in STATUSES])
    s.add_argument("--tag")
    s.add_argument("--title")
    s.add_argument("--stdin", action="store_true")
    s.add_argument("text", nargs="*")
    s = sub.add_parser("set", help="set phase or status")
    s.add_argument("field")
    s.add_argument("value")
    s = sub.add_parser("ingest", help="scrub the clipboard or a file into the inbox")
    s.add_argument("--clipboard", action="store_true")
    s.add_argument("--file")
    s.add_argument("--wipe", action="store_true")
    s.add_argument("--clear-clipboard", action="store_true")
    sub.add_parser("inbox-clear", help="reset the active inbox")
    s = sub.add_parser("redact", help="scrub text locally")
    s.add_argument("--text")
    s.add_argument("--profile", choices=sorted(PROFILE_LEVELS), default="all")
    s.add_argument("--quiet", action="store_true")
    sub.add_parser("render-dashboard", help="render outputs/dashboard.html")
    sub.add_parser("passwd", help="change the passphrase")
    return p


HANDLERS = {
    "open": cmd_open, "lock": cmd_lock, "status": cmd_status, "steps": cmd_steps,
    "switch": cmd_switch, "reindex": cmd_reindex, "log": cmd_log, "set": cmd_set,
    "ingest": cmd_ingest, "inbox-clear": cmd_inbox_clear, "redact": cmd_redact,
    "render-dashboard": cmd_render_dashboard, "passwd": cmd_passwd,
}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if not args.cmd:
        args = parser.parse_args(["open"])
    return HANDLERS[args.cmd](args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted.\n")
        sys.exit(130)
