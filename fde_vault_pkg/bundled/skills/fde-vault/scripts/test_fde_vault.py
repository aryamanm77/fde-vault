#!/usr/bin/env python3
"""FDE-VAULT test suite. Run: python3 test_fde_vault.py

Secret-shaped fixtures are assembled at runtime so no literal credential
appears in this file.
"""

import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import install_cli  # noqa: E402
import vault_guard as vg  # noqa: E402

PASS = "correct horse battery"
AWS = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GH = "gh" + "p_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
CARD = "4111 1111 " + "1111 1111"
SSN = "123-45-" + "6789"


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fde-test-"))
        self.vault = self.tmp / ".fde-vault"
        self._old_env = dict(os.environ)
        os.environ["FDE_VAULT_DIR"] = str(self.vault)
        os.environ.pop("FDE_SESSION_TTL_HOURS", None)
        self._cwd = os.getcwd()
        os.chdir(str(self.tmp))

    def tearDown(self):
        os.chdir(self._cwd)
        os.environ.clear()
        os.environ.update(self._old_env)
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def unlock(self):
        vg.ensure_layout()
        vg.set_passphrase(PASS)
        vg.create_session()

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = vg.main(list(argv))
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
        return code, out.getvalue(), err.getvalue()

    def script(self, name, payload, env=None):
        e = dict(os.environ)
        e.update(env or {})
        return subprocess.run([sys.executable, str(HERE / name)], input=payload,
                              capture_output=True, text=True, env=e, cwd=str(self.tmp))


class AuthTests(VaultCase):
    def test_pbkdf2_hash_is_salted_and_never_plaintext(self):
        vg.ensure_layout()
        vg.set_passphrase(PASS)
        raw = vg.auth_path().read_text()
        data = json.loads(raw)
        self.assertEqual(data["iterations"], 100000)
        self.assertEqual(data["algorithm"], "pbkdf2-hmac-sha256")
        self.assertNotIn(PASS, raw)
        self.assertTrue(vg.verify_passphrase(PASS))
        self.assertFalse(vg.verify_passphrase("wrong passphrase"))
        first_salt = data["salt"]
        vg.set_passphrase(PASS)
        self.assertNotEqual(first_salt, json.loads(vg.auth_path().read_text())["salt"])

    def test_session_lifecycle_and_ttl(self):
        self.unlock()
        self.assertTrue(vg.session_info()["active"])
        remaining = vg.session_info()["remaining"]
        self.assertGreater(remaining, 7.9 * 3600)
        self.assertLessEqual(remaining, 8 * 3600)
        vg.destroy_session()
        self.assertFalse(vg.session_info()["active"])

    def test_expired_session_is_rejected_and_removed(self):
        self.unlock()
        data = json.loads(vg.session_path().read_text())
        data["expires"] = time.time() - 5
        vg.session_path().write_text(json.dumps(data))
        self.assertFalse(vg.session_info()["active"])
        self.assertFalse(vg.session_path().exists())

    def test_changing_passphrase_invalidates_old_session(self):
        self.unlock()
        vg.set_passphrase("a different passphrase")
        self.assertFalse(vg.session_info()["active"])

    def test_failure_backoff(self):
        vg.ensure_layout()
        vg.record_failure()
        vg.record_failure()
        self.assertGreater(vg.lockout_remaining(), 0)
        vg.clear_failures()
        self.assertEqual(vg.lockout_remaining(), 0)

    def test_locked_commands_are_refused(self):
        vg.ensure_layout()
        vg.set_passphrase(PASS)
        for argv in (["status"], ["switch", "demo"], ["reindex"], ["steps"],
                     ["ingest", "--clipboard"], ["render-dashboard"], ["set", "status", "RED"]):
            code, _, _ = self.run_main(*argv)
            self.assertEqual(code, 3, argv)

    def test_lock_and_redact_need_no_session(self):
        vg.ensure_layout()
        code, out, _ = self.run_main("lock")
        self.assertEqual(code, 0)
        code, out, _ = self.run_main("redact", "--text", "mail " + "a@b.com", "--quiet")
        self.assertEqual(code, 0)
        self.assertIn("[REDACTED:EMAIL]", out)

    def test_lock_seals_immediately(self):
        self.unlock()
        code, out, _ = self.run_main("lock")
        self.assertEqual(code, 0)
        self.assertFalse(vg.session_info()["active"])
        self.assertEqual(self.run_main("status")[0], 3)


@unittest.skipUnless(os.name == "posix", "stdin passphrase fallback test is POSIX only")
class OpenFlowTests(VaultCase):
    def run_open(self, stdin):
        env = dict(os.environ)
        return subprocess.run([sys.executable, str(HERE / "vault_guard.py"), "open"],
                              input=stdin, capture_output=True, text=True, env=env,
                              cwd=str(self.tmp), start_new_session=True)

    def test_first_launch_then_reopen(self):
        res = self.run_open(PASS + "\n" + PASS + "\n")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("FDE-VAULT \u2014 Enterprise Forward Deployed Engineering Ledger", res.stdout)
        self.assertIn("Vault unlocked", res.stdout)
        self.assertTrue(vg.session_info()["active"])
        self.assertNotIn("\x1b", res.stdout)
        vg.destroy_session()
        bad = self.run_open("wrong\nwrong\nwrong\n")
        self.assertNotEqual(bad.returncode, 0)
        self.assertFalse(vg.session_info()["active"])
        vg.clear_failures()
        good = self.run_open(PASS + "\n")
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertTrue(vg.session_info()["active"])

    def test_cover_lists_every_assistant_command(self):
        res = self.run_open(PASS + "\n" + PASS + "\n")
        for token in ("open", "lock", "status", "switch", "discover", "sync",
                      "scope", "preflight", "incident", "rfc", "brief", "handoff",
                      "steps", "fde ingest --clipboard", "fde lock"):
            self.assertIn(token, res.stdout)


class LayoutTests(VaultCase):
    def test_zero_demo_data_and_empty_index(self):
        vg.ensure_layout()
        self.assertEqual(json.loads((self.vault / "index.json").read_text()),
                         {"generated_at": "", "vaults": {}})
        self.assertEqual(vg.account_dirs(), [])
        self.assertTrue((self.vault / "_blueprint" / "brain.md").exists())
        for name in ("acme", "globex", "initech", "stripe", "openai", "netflix"):
            self.assertFalse((self.vault / name).exists())

    def test_gitignore_is_idempotent(self):
        vg.ensure_layout()
        vg.ensure_gitignore()
        text = (self.tmp / ".gitignore").read_text()
        self.assertEqual(text.count(vg.MARKER_START), 1)

    def test_switch_creates_binds_and_is_idempotent(self):
        self.unlock()
        code, out, _ = self.run_main("switch", "Big Corp_Test!")
        self.assertEqual(code, 0, out)
        self.assertIn("account: big-corp-test", out)
        self.assertIn("created: yes", out)
        acct = self.vault / "big-corp-test"
        brain = (acct / "brain.md").read_text()
        self.assertIn("**Working Directory:** " + str(self.tmp.resolve()), brain)
        self.assertEqual((self.vault / ".active-vault").read_text().strip(), "big-corp-test")
        code, out, _ = self.run_main("switch", "big-corp-test")
        self.assertIn("created: no", out)
        idx = json.loads((self.vault / "index.json").read_text())
        self.assertIn("big-corp-test", idx["vaults"])
        self.assertTrue(idx["generated_at"])

    def test_sanitize_rejects_empty(self):
        self.unlock()
        self.assertEqual(self.run_main("switch", "!!!")[0], 2)

    def test_reindex_detects_drift(self):
        self.unlock()
        self.run_main("switch", "alpha")
        self.assertEqual(self.run_main("reindex", "--check")[0], 0)
        (self.vault / "beta").mkdir()
        shutil.copy(str(self.vault / "alpha" / "brain.md"), str(self.vault / "beta" / "brain.md"))
        code, out, _ = self.run_main("reindex", "--check")
        self.assertEqual(code, 1)
        self.assertIn("beta", out)
        self.assertEqual(self.run_main("reindex")[0], 0)
        self.assertEqual(self.run_main("reindex", "--check")[0], 0)

    def test_log_set_steps_and_counts(self):
        self.unlock()
        self.run_main("switch", "alpha")
        code, out, _ = self.run_main("log", "--tier", "yellow", "Added", "adapter",
                                     "for", "contact", "bob@example.com")
        self.assertEqual(code, 0)
        self.assertIn("entry: 01", out)
        self.assertIn("EDGE-ADAPTER", out)
        self.run_main("log", "--tier", "RED", "--tag", "INCIDENT", "--title", "Outage", "Down")
        timeline = (self.vault / "alpha" / "timeline.md").read_text()
        self.assertNotIn("bob@example.com", timeline)
        entries = vg.parse_timeline(timeline)
        self.assertEqual([e["tier"] for e in entries], ["YELLOW", "RED"])
        idx = json.loads((self.vault / "index.json").read_text())["vaults"]["alpha"]
        self.assertEqual((idx["entries"], idx["yellow"], idx["red"]), (2, 1, 1))
        self.assertEqual(self.run_main("set", "status", "RED")[0], 0)
        self.assertEqual(self.run_main("set", "phase", "build")[0], 0)
        self.assertEqual(self.run_main("set", "phase", "nonsense")[0], 2)
        code, out, _ = self.run_main("steps")
        self.assertIn("Chapter II \u2014 Build **[Current Chapter]**", out)
        self.assertIn("**Status:** RED", out)
        self.assertEqual(self.run_main("reindex", "--check")[0], 0)

    def test_status_reports_state(self):
        self.unlock()
        self.run_main("switch", "alpha")
        code, out, _ = self.run_main("status")
        self.assertEqual(code, 0)
        self.assertIn("state: unlocked", out)
        self.assertIn("active_account: alpha", out)
        self.assertIn("index_drift: none", out)
        code, out, _ = self.run_main("status", "--json")
        self.assertEqual(json.loads(out)["active"], "alpha")


class RedactionTests(VaultCase):
    def test_detects_credentials_and_pii(self):
        text = "\n".join([
            "key " + AWS, "token " + GH, "card " + CARD, "ssn " + SSN,
            "mail jane.doe@example.com", "call (415) 555-0134",
            "password=hunter2xyz", "db postgres://admin:s3cr3t@host/db",
        ])
        out, counts = vg.redact(text)
        for needle in (AWS, GH, CARD, SSN, "jane.doe@example.com", "555-0134",
                       "hunter2xyz", "s3cr3t"):
            self.assertNotIn(needle, out)
        for name in ("AWS-KEY", "GITHUB-TOKEN", "CARD", "SSN", "EMAIL", "PHONE",
                     "SECRET-VALUE", "URL-CREDENTIALS"):
            self.assertIn(name, counts)

    def test_private_key_block(self):
        pem = "-----BEGIN RSA PRIVATE" + " KEY-----\nMIIB\nabc\n-----END RSA PRIVATE" + " KEY-----"
        out, counts = vg.redact("x\n" + pem + "\ny")
        self.assertIn("PRIVATE-KEY", counts)
        self.assertNotIn("MIIB", out)

    def test_no_false_positive_on_plain_text(self):
        text = "Configure the retry token bucket. Order 12345 shipped on 2026-11-15."
        out, counts = vg.redact(text)
        self.assertEqual(out, text)
        self.assertEqual(counts, {})

    def test_invalid_luhn_number_is_kept(self):
        out, counts = vg.redact("ref 1234 5678 9012 3456")
        self.assertNotIn("CARD", counts)

    def test_tools_profile_skips_pii_and_generic(self):
        _, counts = vg.redact("mail a@b.com password=hunter2xyz", "tools")
        self.assertEqual(counts, {})

    def test_redaction_is_idempotent(self):
        once, _ = vg.redact("pw token=abcd1234efgh " + AWS)
        twice, counts = vg.redact(once)
        self.assertEqual(once, twice)
        self.assertEqual(counts, {})


class IngestTests(VaultCase):
    def test_clipboard_ingest_scrubs_without_echo(self):
        self.unlock()
        self.run_main("switch", "alpha")
        original = vg.read_clipboard
        vg.read_clipboard = lambda: "note " + AWS + " owner jane@example.com"
        try:
            code, out, _ = self.run_main("ingest", "--clipboard")
        finally:
            vg.read_clipboard = original
        self.assertEqual(code, 0)
        self.assertNotIn(AWS, out)
        inbox = (self.vault / "alpha" / "inbox.md").read_text()
        self.assertIn("[REDACTED:AWS-KEY]", inbox)
        self.assertNotIn(AWS, inbox)
        self.assertNotIn("jane@example.com", inbox)
        self.assertEqual(self.run_main("inbox-clear")[0], 0)
        self.assertNotIn("REDACTED", (self.vault / "alpha" / "inbox.md").read_text())

    def test_file_ingest_with_wipe(self):
        self.unlock()
        self.run_main("switch", "alpha")
        src = self.tmp / "notes.txt"
        src.write_text("secret=" + "abcd1234efgh5678\nplain line\n")
        code, out, _ = self.run_main("ingest", "--file", str(src), "--wipe")
        self.assertEqual(code, 0)
        self.assertFalse(src.exists())
        inbox = (self.vault / "alpha" / "inbox.md").read_text()
        self.assertIn("plain line", inbox)
        self.assertNotIn("abcd1234efgh5678", inbox)

    def test_ingest_argument_validation(self):
        self.unlock()
        self.run_main("switch", "alpha")
        self.assertEqual(self.run_main("ingest")[0], 2)
        self.assertEqual(self.run_main("ingest", "--clipboard", "--wipe")[0], 2)


class HookTests(VaultCase):
    def test_prompt_hook_blocks_secrets_without_echo(self):
        res = self.script("prompt_hook.py", json.dumps({"prompt": "use " + AWS + " here"}))
        self.assertEqual(res.returncode, 2)
        self.assertIn("AWS-KEY", res.stderr)
        self.assertNotIn(AWS, res.stderr)

    def test_prompt_hook_allows_clean_prompt(self):
        res = self.script("prompt_hook.py", json.dumps({"prompt": "status"}))
        self.assertEqual(res.returncode, 0)

    def test_prompt_hook_pii_mode_switch(self):
        payload = json.dumps({"prompt": "ssn " + SSN})
        self.assertEqual(self.script("prompt_hook.py", payload).returncode, 2)
        self.assertEqual(self.script("prompt_hook.py", payload,
                                     {"FDE_FIREWALL": "credentials"}).returncode, 0)

    def test_hooks_fail_closed_on_empty_or_bad_payload(self):
        for name in ("prompt_hook.py", "pre_tool_hook.py"):
            self.assertEqual(self.script(name, "").returncode, 2)
            self.assertEqual(self.script(name, "{not json").returncode, 2)

    def test_pre_tool_blocks_vault_access_when_locked(self):
        vg.ensure_layout()
        vg.set_passphrase(PASS)
        payload = json.dumps({"tool_name": "Read",
                              "tool_input": {"file_path": ".fde-vault/alpha/brain.md"}})
        res = self.script("pre_tool_hook.py", payload)
        self.assertEqual(res.returncode, 2)
        self.assertIn("locked", res.stderr)

    def test_pre_tool_allows_vault_access_when_unlocked(self):
        self.unlock()
        payload = json.dumps({"tool_name": "Read",
                              "tool_input": {"file_path": ".fde-vault/alpha/brain.md"}})
        self.assertEqual(self.script("pre_tool_hook.py", payload).returncode, 0)

    def test_pre_tool_always_protects_auth_and_session_files(self):
        self.unlock()
        for target in (".fde-vault/.vault.auth", ".fde-vault/.session-unlocked"):
            payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat " + target}})
            self.assertEqual(self.script("pre_tool_hook.py", payload).returncode, 2)

    def test_pre_tool_allows_guard_calls_while_locked(self):
        vg.ensure_layout()
        vg.set_passphrase(PASS)
        cmd = "python3 .claude/skills/fde-vault/scripts/vault_guard.py status"
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
        self.assertEqual(self.script("pre_tool_hook.py", payload).returncode, 0)

    def test_pre_tool_blocks_credentials_in_written_content(self):
        payload = json.dumps({"tool_name": "Write",
                              "tool_input": {"file_path": "app.py", "content": "K='" + AWS + "'"}})
        res = self.script("pre_tool_hook.py", payload)
        self.assertEqual(res.returncode, 2)
        self.assertNotIn(AWS, res.stderr)

    def test_pre_tool_allows_ordinary_tool_use(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        self.assertEqual(self.script("pre_tool_hook.py", payload).returncode, 0)

    def test_settings_json_wires_both_hooks(self):
        settings = json.loads((SKILL.parents[1] / "settings.json").read_text())
        pre = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        prompt = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        for cmd, script in ((pre, "pre_tool_hook.py"), (prompt, "prompt_hook.py")):
            self.assertIn("python3 ", cmd)
            self.assertIn("|| py -3 ", cmd)
            self.assertIn("|| python ", cmd)
            self.assertEqual(cmd.count(script), 3)


class DashboardTests(VaultCase):
    def build(self):
        self.unlock()
        self.run_main("switch", "alpha")
        brain = self.vault / "alpha" / "brain.md"
        text = brain.read_text().replace(
            "## Mission\n<!-- One paragraph: the customer outcome this engagement exists to deliver. -->",
            "## Mission\nDeliver a resilient order pipeline for the customer. "
            "Contact owner@example.com for access.")
        brain.write_text(text)
        for i in range(9):
            self.run_main("log", "--tier", "GREEN", "Routine configuration change number %d. " % i
                          + "Details of the work. " * 12)
        self.run_main("log", "--tier", "RED", "--tag", "INCIDENT", "Queue stalled.")
        (self.vault / "alpha" / "outputs" / "manager-brief.md").write_text(
            "# Brief\n\nStatus is **green** overall.\n\n- First item\n- Second item\n")
        code, out, _ = self.run_main("render-dashboard")
        self.assertEqual(code, 0, out)
        return (self.vault / "alpha" / "outputs" / "dashboard.html").read_text(encoding="utf-8")

    def test_book_features(self):
        page = self.build()
        for token in ("Previous Page", "Next Page", "ArrowLeft", "ArrowRight", "#FAF7F0",
                      "dropcap", "folio", "Table of Contents", "Engineering Journal",
                      "Appendix A", "Manager Brief"):
            self.assertIn(token, page)
        self.assertGreater(page.count('class="page"'), 6)
        self.assertNotIn("owner@example.com", page)
        self.assertNotIn("http://", page)
        self.assertNotIn("https://", page)

    def test_every_page_has_folio_except_cover_and_colophon(self):
        page = self.build()
        sections = re.findall(r'<section class="page" data-page="(\d+)">(.*?)</section>', page, re.S)
        self.assertGreater(len(sections), 4)
        for number, body in sections[1:-1]:
            self.assertIn('<footer class="folio">%s</footer>' % number, body)

    def test_toc_page_numbers_point_to_chapter_openings(self):
        page = self.build()
        sections = dict(re.findall(r'<section class="page" data-page="(\d+)">(.*?)</section>', page, re.S))
        for target, title in re.findall(r'data-go="(\d+)"><span>[^<]*? &mdash; ([^<]+)</span>', page):
            self.assertIn("<h2>%s</h2>" % title, sections[target])


class InstallerTests(VaultCase):
    def run_install(self, *argv):
        home = self.tmp / "home"
        home.mkdir(exist_ok=True)
        os.environ["HOME"] = str(home)
        os.environ["USERPROFILE"] = str(home)
        out = io.StringIO()
        install_cli.log = lambda msg="": out.write(str(msg) + "\n")
        try:
            install_cli.main(list(argv))
        finally:
            install_cli.log = print
        return home, out.getvalue()

    def test_macos_install_is_idempotent(self):
        home, _ = self.run_install("--platform", "darwin", "--no-mirror")
        for name in (".zshrc", ".bashrc"):
            text = (home / name).read_text()
            self.assertEqual(text.count(install_cli.MARKER_START), 1)
            self.assertEqual(text.count(install_cli.MARKER_END), 1)
            self.assertIn("open", text)
        before = (home / ".zshrc").read_text()
        self.run_install("--platform", "darwin", "--no-mirror")
        self.assertEqual((home / ".zshrc").read_text(), before)
        launcher = home / ".local" / "bin" / "fde"
        self.assertTrue(launcher.exists())
        if os.name == "posix":
            self.assertTrue(os.access(str(launcher), os.X_OK))

    def test_existing_profile_content_is_preserved(self):
        home = self.tmp / "home"
        home.mkdir()
        (home / ".bashrc").write_text("export KEEP=1\nalias ll='ls -l'")
        self.run_install("--platform", "linux", "--no-mirror")
        text = (home / ".bashrc").read_text()
        self.assertIn("export KEEP=1", text)
        self.assertIn("alias ll='ls -l'", text)
        self.assertEqual(text.count(install_cli.MARKER_START), 1)
        self.assertTrue((home / ".profile").exists())

    def test_uninstall_removes_blocks_and_keeps_user_content(self):
        home = self.tmp / "home"
        home.mkdir()
        (home / ".bashrc").write_text("export KEEP=1\n")
        self.run_install("--platform", "linux", "--no-mirror")
        self.run_install("--platform", "linux", "--uninstall")
        text = (home / ".bashrc").read_text()
        self.assertNotIn(install_cli.MARKER_START, text)
        self.assertIn("export KEEP=1", text)
        self.assertFalse((home / ".local" / "bin" / "fde").exists())

    def test_windows_launcher_and_dry_run(self):
        home, out = self.run_install("--platform", "windows", "--no-mirror", "--dry-run")
        self.assertIn("would write", out)
        self.assertFalse((home / "bin" / "fde.bat").exists())
        home, _ = self.run_install("--platform", "windows", "--no-mirror")
        bat = (home / "bin" / "fde.bat").read_bytes().decode()
        self.assertIn("vault_guard.py", bat)
        self.assertIn('set "ARGS=open"', bat)
        self.assertIn("\r\n", bat)

    def test_blocks_resolve_project_first_then_global(self):
        posix = install_cli.POSIX_BLOCK
        self.assertLess(posix.index(".claude/skills/fde-vault/scripts/vault_guard.py"),
                        posix.index("$HOME/.claude/skills/fde-vault/scripts/vault_guard.py"))
        self.assertIn("set -- open", posix)
        ps = install_cli.POWERSHELL_BLOCK
        self.assertIn("@('open')", ps)

    @unittest.skipUnless(os.name == "posix", "shell function test is POSIX only")
    def test_shell_function_runs_guard(self):
        home, _ = self.run_install("--platform", "linux", "--no-mirror")
        project = self.tmp / "proj"
        shutil.copytree(str(SKILL), str(project / ".claude" / "skills" / "fde-vault"))
        script = ". '%s/.bashrc'; fde lock" % home
        res = subprocess.run(["bash", "-c", script], cwd=str(project), capture_output=True,
                             text=True, env=dict(os.environ, FDE_VAULT_DIR=str(self.vault)))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Vault", res.stdout)

    def test_mirror_copies_skill(self):
        project = self.tmp / "proj"
        skill_copy = project / ".claude" / "skills" / "fde-vault"
        shutil.copytree(str(SKILL), str(skill_copy), ignore=shutil.ignore_patterns("__pycache__"))
        home = self.tmp / "home"
        home.mkdir()
        os.environ["HOME"] = str(home)
        os.environ["USERPROFILE"] = str(home)
        install_cli.log = lambda msg="": None
        try:
            install_cli.mirror_skill(skill_copy.resolve(), home, False)
        finally:
            install_cli.log = print
        for root in (project / ".agent", home / ".claude"):
            self.assertTrue((root / "skills" / "fde-vault" / "SKILL.md").exists())
            self.assertTrue((root / "skills" / "fde-vault" / "scripts" / "vault_guard.py").exists())


class ProjectHygieneTests(unittest.TestCase):
    ROOT = SKILL.parents[1].parent

    def files(self):
        for p in self.ROOT.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and ".fde-vault" not in p.parts[-3:-1] \
                    and p.suffix in (".py", ".md", ".json", ".bat", ".html", "") \
                    and ".git" not in p.parts:
                yield p

    def test_no_emojis_anywhere(self):
        bad = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")
        for p in self.files():
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            self.assertIsNone(bad.search(text), str(p))

    def test_skill_frontmatter_and_commands(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: fde-vault\ndescription: Enterprise Forward"))
        for cmd in ("open", "lock", "status", "vaults", "switch", "start", "discover",
                    "sync", "log", "scope", "preflight", "guard", "incident", "rfc",
                    "brief", "report", "handoff", "done", "steps"):
            self.assertIn("`%s" % cmd, text)
        for rule in ("RULE-01", "RULE-05", "CRITERIA-GREEN", "CRITERIA-YELLOW", "CRITERIA-RED"):
            self.assertIn(rule, text)
            self.assertIn(rule, (SKILL / "references" / "core-rules.md").read_text(encoding="utf-8"))

    def test_standard_library_only(self):
        stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else None
        for name in ("vault_guard.py", "pre_tool_hook.py", "prompt_hook.py", "install_cli.py"):
            text = (HERE / name).read_text(encoding="utf-8")
            for mod in re.findall(r"^(?:import|from)\s+([a-zA-Z_][\w]*)", text, re.M):
                if mod in ("vault_guard",):
                    continue
                if stdlib is not None:
                    self.assertIn(mod, stdlib, "%s imports %s" % (name, mod))

    def test_no_demo_accounts_shipped(self):
        vault = self.ROOT / ".fde-vault"
        if vault.exists():
            names = sorted(p.name for p in vault.iterdir())
            self.assertEqual([n for n in names if n not in ("_blueprint", "index.json")], [])
            self.assertEqual(json.loads((vault / "index.json").read_text()),
                             {"generated_at": "", "vaults": {}})


class AnimationTests(VaultCase):
    def test_animation_runs_under_budget_and_is_plain_without_color(self):
        buf = io.StringIO()
        start = time.time()
        with contextlib.redirect_stdout(buf):
            vg.play_animation(False)
        elapsed = time.time() - start
        out = buf.getvalue()
        self.assertLess(elapsed, 1.6)
        self.assertGreater(elapsed, 0.6)
        for token in ("F D E - V A U L T", "[1/3] Mounting isolated account ledger...",
                      "[2/3] Arming Zero-Chat-Exposure redaction engine...",
                      "[3/3] Opening engineering journal..."):
            self.assertIn(token, out)
        self.assertNotIn("\x1b", out)


class PackagingAndInitTests(unittest.TestCase):
    ROOT = SKILL.parents[1].parent

    def setUp(self):
        if str(self.ROOT) not in sys.path:
            sys.path.insert(0, str(self.ROOT))

    def test_pyproject_toml_validity(self):
        pyproj = self.ROOT / "pyproject.toml"
        self.assertTrue(pyproj.is_file(), "pyproject.toml must exist in repo root")
        content = pyproj.read_text(encoding="utf-8")
        self.assertIn('name = "fde-vault"', content)
        self.assertIn('requires-python = ">=3.9"', content)
        self.assertIn('dependencies = []', content)
        self.assertIn('fde = "fde_vault_pkg.cli:main"', content)

        try:
            import tomllib
            parsed = tomllib.loads(content)
            self.assertEqual(parsed["project"]["name"], "fde-vault")
            self.assertEqual(parsed["project"]["dependencies"], [])
            self.assertEqual(parsed["project"]["scripts"]["fde"], "fde_vault_pkg.cli:main")
        except ImportError:
            pass

    def test_fde_init_scaffolding_and_idempotency(self):
        import fde_vault_pkg.cli as cli
        tmp = Path(tempfile.mkdtemp(prefix="fde-init-test-"))
        try:
            code = cli.cmd_init(str(tmp))
            self.assertEqual(code, 0)
            self.assertTrue((tmp / ".fde-vault" / "_blueprint" / "brain.md").is_file())
            self.assertTrue((tmp / ".fde-vault" / "_blueprint" / "timeline.md").is_file())
            self.assertTrue((tmp / ".fde-vault" / "_blueprint" / "inbox.md").is_file())
            self.assertTrue((tmp / ".fde-vault" / "_blueprint" / "outputs" / ".gitkeep").is_file())
            self.assertTrue((tmp / ".fde-vault" / "index.json").is_file())
            self.assertTrue((tmp / ".claude" / "skills" / "fde-vault" / "SKILL.md").is_file())
            self.assertTrue((tmp / ".agent" / "skills" / "fde-vault" / "SKILL.md").is_file())
            self.assertTrue((tmp / ".claude" / "settings.json").is_file())
            self.assertTrue((tmp / "AGENTS.md").is_file())
            self.assertTrue((tmp / "GEMINI.md").is_file())
            self.assertTrue((tmp / "CLAUDE.md").is_file())
            self.assertTrue((tmp / ".cursorrules").is_file())
            self.assertTrue((tmp / ".gitignore").is_file())

            settings = json.loads((tmp / ".claude" / "settings.json").read_text(encoding="utf-8"))
            hooks = settings.get("hooks", {})
            for hook_group in hooks.values():
                for entry in hook_group:
                    for h in entry.get("hooks", []):
                        cmd = h.get("command", "")
                        if "python3" in cmd:
                            self.assertIn("py -3", cmd, "Windows py -3 fallback must be present in hook command")

            live_acct = tmp / ".fde-vault" / "acme"
            live_acct.mkdir(parents=True)
            (live_acct / "brain.md").write_text("# LIVE ACCOUNT CHARTER", encoding="utf-8")
            code2 = cli.cmd_init(str(tmp))
            self.assertEqual(code2, 0)
            self.assertEqual((live_acct / "brain.md").read_text(encoding="utf-8"), "# LIVE ACCOUNT CHARTER")
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_find_vault_guard_resolution(self):
        import fde_vault_pkg.cli as cli
        guard = cli.find_vault_guard(cwd=str(self.ROOT))
        self.assertIsNotNone(guard)
        self.assertTrue(guard.is_file())
        self.assertEqual(guard.name, "vault_guard.py")

    def test_install_confirmation_banner(self):
        banner = "Installed FDE-VAULT. Type 'fde' in your terminal or inside Claude Code / Antigravity to launch."
        for fn in ("install.sh", "install.ps1", ".claude/skills/fde-vault/scripts/install_cli.py", "fde_vault_pkg/cli.py"):
            text = (self.ROOT / fn).read_text(encoding="utf-8")
            self.assertIn(banner, text, "Confirmation banner missing in %s" % fn)

    def test_home_screen_one_line_command_directory(self):
        cover = vg.cover_text(False)
        self.assertIn("FDE-VAULT", cover)
        self.assertIn("Session Status :", cover)
        self.assertIn("Active Account :", cover)
        self.assertIn("Store Location :", cover)
        commands = [
            "open", "lock", "status", "switch", "discover", "sync",
            "scope", "preflight", "incident", "rfc", "brief", "handoff", "steps"
        ]
        for cmd in commands:
            self.assertIn(cmd, cover)

    def test_fde_chat_trigger_documented_in_skill_and_pointers(self):
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("AI Chat Entry Triggers (fde, open)", skill)
        self.assertIn("## F D E · V A U L T", skill)
        for pointer in ("AGENTS.md", "GEMINI.md", "CLAUDE.md", ".cursorrules"):
            text = (self.ROOT / pointer).read_text(encoding="utf-8")
            self.assertIn("fde", text)
            self.assertIn("open", text)


if __name__ == "__main__":
    unittest.main(verbosity=1)
