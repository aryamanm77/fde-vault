#!/usr/bin/env python3
"""FDE-VAULT PreToolUse firewall hook.

Reads the Claude Code hook payload from stdin. Exit code 2 blocks the tool call
and shows the message on stderr. The hook fails closed on a missing or
unreadable payload. Python 3 standard library only.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vault_guard as vg  # noqa: E402

PROTECTED_RE = re.compile(r"\.vault\.auth|\.session-unlocked|\.vault\.fail")
GUARD_CALL_RE = re.compile(r"vault_guard\.py|(?:^|[;&|(\s])(?:fde|\./fde-vault)(?:\s|$)")


def deny(message):
    sys.stderr.write("FDE-VAULT firewall: %s\n" % message)
    sys.exit(2)


def strings_of(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            for item in strings_of(value):
                yield item
    elif isinstance(obj, list):
        for value in obj:
            for item in strings_of(value):
                yield item


def outbound_text(tool, tool_input):
    """Text the tool would write or execute (checked for raw credentials)."""
    parts = []
    for key in ("command", "content", "new_string", "text"):
        value = tool_input.get(key)
        if isinstance(value, str):
            parts.append(value)
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
            parts.append(edit["new_string"])
    return "\n".join(parts)


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        deny("no hook payload received; failing closed.")
    try:
        payload = json.loads(raw)
    except ValueError:
        deny("unreadable hook payload; failing closed.")
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and os.path.isdir(cwd):
        os.chdir(cwd)
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        deny("unexpected tool input shape; failing closed.")
    joined = "\n".join(strings_of(tool_input)).replace("\\", "/")

    if PROTECTED_RE.search(joined):
        deny("access to vault authentication and session files is never permitted.")

    command = tool_input.get("command") if isinstance(tool_input.get("command"), str) else ""
    is_guard_call = tool == "Bash" and bool(GUARD_CALL_RE.search(command))
    if ".fde-vault" in joined and not is_guard_call:
        if not vg.auth_path().exists() or not vg.session_info()["active"]:
            deny("the vault is locked. Ask the user to run `fde` in a local terminal "
                 "and enter the passphrase there. Never request it in chat.")

    _, counts = vg.redact(outbound_text(tool, tool_input), "tools")
    if counts:
        deny("raw credentials detected in tool input (%s). Nothing was executed. "
             "Have the user run `fde ingest --clipboard` locally instead."
             % vg.summarize_counts(counts))
    sys.exit(0)


if __name__ == "__main__":
    main()
