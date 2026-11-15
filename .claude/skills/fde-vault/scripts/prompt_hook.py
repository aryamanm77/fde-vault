#!/usr/bin/env python3
"""FDE-VAULT UserPromptSubmit firewall hook.

Blocks prompts that contain credentials or personal data before they reach the
model. Exit code 2 blocks the prompt and erases it from context; the stderr
message is shown to the user and never repeats the detected content.

FDE_FIREWALL=strict       (default) credentials plus personal data
FDE_FIREWALL=credentials  credentials only
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vault_guard as vg  # noqa: E402


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        sys.stderr.write("FDE-VAULT firewall: no hook payload received; failing closed.\n")
        sys.exit(2)
    try:
        payload = json.loads(raw)
    except ValueError:
        sys.stderr.write("FDE-VAULT firewall: unreadable hook payload; failing closed.\n")
        sys.exit(2)
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        sys.exit(0)
    mode = os.environ.get("FDE_FIREWALL", "strict").strip().lower()
    profile = "credentials" if mode == "credentials" else "all"
    _, counts = vg.redact(prompt, profile)
    if counts:
        sys.stderr.write(
            "FDE-VAULT firewall: prompt blocked locally and not sent to the model.\n"
            "Detected: %s.\n"
            "Copy the material, run `fde ingest --clipboard` in your own terminal, "
            "then run 'sync' here.\n" % vg.summarize_counts(counts))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
