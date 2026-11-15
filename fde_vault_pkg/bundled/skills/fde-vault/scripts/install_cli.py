#!/usr/bin/env python3
"""Install the global `fde` command and mirror the skill.

Idempotent: shell profile edits are wrapped in marker comments, so repeated runs
replace the block instead of duplicating it. Use --uninstall to remove it.

    python3 install_cli.py              install and mirror
    python3 install_cli.py --dry-run    show what would change
    python3 install_cli.py --uninstall  remove the blocks and launchers
    python3 install_cli.py --no-mirror  skip skill mirroring

Python 3 standard library only.
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MARKER_START = "# >>> fde-vault >>>"
MARKER_END = "# <<< fde-vault <<<"
SKILL_NAME = "fde-vault"

POSIX_BLOCK = MARKER_START + r'''
fde() {
  _fde_g=""
  _fde_d="$PWD"
  while [ -n "$_fde_d" ] && [ "$_fde_d" != "/" ]; do
    if [ -f "$_fde_d/.claude/skills/fde-vault/scripts/vault_guard.py" ]; then
      _fde_g="$_fde_d/.claude/skills/fde-vault/scripts/vault_guard.py"
      break
    fi
    _fde_d=$(dirname "$_fde_d")
  done
  if [ -z "$_fde_g" ] && [ -f "$HOME/.claude/skills/fde-vault/scripts/vault_guard.py" ]; then
    _fde_g="$HOME/.claude/skills/fde-vault/scripts/vault_guard.py"
  fi
  if [ -z "$_fde_g" ]; then
    echo "fde: vault_guard.py not found in this project or in ~/.claude/skills/fde-vault" >&2
    return 1
  fi
  if [ "$#" -eq 0 ]; then set -- open; fi
  if command -v python3 >/dev/null 2>&1; then python3 "$_fde_g" "$@"; else python "$_fde_g" "$@"; fi
  _fde_rc=$?
  unset _fde_g _fde_d
  return $_fde_rc
}
''' + MARKER_END + "\n"

POWERSHELL_BLOCK = MARKER_START + r'''
function fde {
  $g = $null
  $d = (Get-Location).Path
  while ($d) {
    $c = Join-Path $d '.claude\skills\fde-vault\scripts\vault_guard.py'
    if (Test-Path $c) { $g = $c; break }
    $p = Split-Path $d -Parent
    if (-not $p -or $p -eq $d) { break }
    $d = $p
  }
  if (-not $g) {
    $c = Join-Path $HOME '.claude\skills\fde-vault\scripts\vault_guard.py'
    if (Test-Path $c) { $g = $c }
  }
  if (-not $g) { Write-Error 'fde: vault_guard.py not found in this project or in ~/.claude/skills/fde-vault'; return }
  if ($args.Count -eq 0) {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 $g @('open') }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { & python3 $g @('open') }
    else { & python $g @('open') }
  } else {
    if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 $g @args }
    elseif (Get-Command python3 -ErrorAction SilentlyContinue) { & python3 $g @args }
    else { & python $g @args }
  }
}
''' + MARKER_END + "\n"

SH_LAUNCHER = r'''#!/bin/sh
# fde launcher: project copy first (walking up from the current directory), then global.
g=""
d="$PWD"
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -f "$d/.claude/skills/fde-vault/scripts/vault_guard.py" ]; then
    g="$d/.claude/skills/fde-vault/scripts/vault_guard.py"
    break
  fi
  d=$(dirname "$d")
done
if [ -z "$g" ] && [ -f "$HOME/.claude/skills/fde-vault/scripts/vault_guard.py" ]; then
  g="$HOME/.claude/skills/fde-vault/scripts/vault_guard.py"
fi
if [ -z "$g" ]; then
  echo "fde: vault_guard.py not found" >&2
  exit 1
fi
if [ "$#" -eq 0 ]; then set -- open; fi
if command -v python3 >/dev/null 2>&1; then exec python3 "$g" "$@"; fi
exec python "$g" "$@"
'''

BAT_LAUNCHER = r'''@echo off
setlocal
set "G="
set "D=%CD%"
:walk
if exist "%D%\.claude\skills\fde-vault\scripts\vault_guard.py" set "G=%D%\.claude\skills\fde-vault\scripts\vault_guard.py"
if defined G goto run
for %%I in ("%D%\..") do set "P=%%~fI"
if /I "%P%"=="%D%" goto global
set "D=%P%"
goto walk
:global
if exist "%USERPROFILE%\.claude\skills\fde-vault\scripts\vault_guard.py" set "G=%USERPROFILE%\.claude\skills\fde-vault\scripts\vault_guard.py"
:run
if not defined G (
  echo fde: vault_guard.py not found 1>&2
  exit /b 1
)
set "ARGS=%*"
if "%~1"=="" set "ARGS=open"
where py >nul 2>nul
if %errorlevel%==0 goto usepy
python "%G%" %ARGS%
exit /b %errorlevel%
:usepy
py -3 "%G%" %ARGS%
exit /b %errorlevel%
'''

log = print


def atomic_write(path, text, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        if mode is None and path.exists():
            mode = path.stat().st_mode & 0o777
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


BLOCK_RE = re.compile(
    r"\n?" + re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\n?", re.S)


def upsert_block(path, block, dry):
    path = Path(path)
    existing = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if BLOCK_RE.search(existing):
        updated = BLOCK_RE.sub(
            lambda m: ("\n" if m.group(0).startswith("\n") else "") + block,
            existing, count=1)
    else:
        sep = "" if (not existing or existing.endswith("\n")) else "\n"
        updated = existing + sep + ("\n" if existing else "") + block
    if updated == existing:
        log("  unchanged   %s" % path)
        return
    log("  %s  %s" % ("would write" if dry else "wrote      ", path))
    if not dry:
        atomic_write(path, updated)


def remove_block(path, dry):
    path = Path(path)
    if not path.exists():
        return
    existing = path.read_text(encoding="utf-8", errors="replace")
    if not BLOCK_RE.search(existing):
        return
    updated = BLOCK_RE.sub("\n", existing, count=1).rstrip("\n") + "\n"
    log("  %s  %s" % ("would clean" if dry else "cleaned    ", path))
    if not dry:
        atomic_write(path, updated)


def powershell_profiles(system, home):
    paths = []
    if system == "windows":
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", "$PROFILE"],
                                 capture_output=True, timeout=10)
            line = res.stdout.decode("utf-8", "replace").strip()
            if res.returncode == 0 and line:
                paths.append(Path(line))
        except (OSError, subprocess.SubprocessError):
            pass
        docs = home / "Documents"
        for rel in ("WindowsPowerShell", "PowerShell"):
            candidate = docs / rel / "Microsoft.PowerShell_profile.ps1"
            if candidate not in paths:
                paths.append(candidate)
    return paths


def shell_profiles(system, home):
    if system == "darwin":
        return [home / ".zshrc", home / ".bashrc"]
    if system == "linux":
        paths = [home / ".bashrc", home / ".profile"]
        if (home / ".zshrc").exists():
            paths.append(home / ".zshrc")
        return paths
    return []


def write_launcher(path, text, executable, dry):
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8", errors="replace") == text:
        log("  unchanged   %s" % path)
        return
    log("  %s  %s" % ("would write" if dry else "wrote      ", path))
    if not dry:
        atomic_write(path, text, 0o755 if executable else None)


def remove_file(path, dry):
    path = Path(path)
    if path.exists():
        log("  %s  %s" % ("would remove" if dry else "removed     ", path))
        if not dry:
            path.unlink()


def mirror_skill(skill_dir, home, dry):
    root = skill_dir.parents[2]
    targets = [home / ".claude" / "skills" / SKILL_NAME]
    if root.resolve() != home.resolve():
        targets.insert(0, root / ".agent" / "skills" / SKILL_NAME)
    for target in targets:
        if target.resolve() == skill_dir.resolve():
            continue
        log("  %s  %s" % ("would mirror" if dry else "mirrored    ", target))
        if not dry:
            shutil.copytree(str(skill_dir), str(target), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    commands_dir = root / ".claude" / "commands"
    if commands_dir.is_dir():
        dest_cmds = home / ".claude" / "commands"
        log("  %s  %s" % ("would mirror" if dry else "mirrored    ", dest_cmds))
        if not dry:
            dest_cmds.mkdir(parents=True, exist_ok=True)
            for f in commands_dir.glob("*.md"):
                shutil.copy2(f, dest_cmds / f.name)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install the global fde command.")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--platform", choices=["darwin", "linux", "windows"],
                        help="override platform detection (testing)")
    args = parser.parse_args(argv)

    system = args.platform or platform.system().lower()
    home = Path.home()
    skill_dir = Path(__file__).resolve().parents[1]
    dry = args.dry_run

    if args.uninstall:
        log("Removing the fde command")
        for p in shell_profiles(system, home) + powershell_profiles(system, home):
            remove_block(p, dry)
        remove_file(home / ".local" / "bin" / "fde", dry)
        remove_file(home / "bin" / "fde.bat", dry)
        log("Skill mirrors and vault data were left untouched.")
        return 0

    log("Registering the fde command (%s)" % system)
    for p in shell_profiles(system, home):
        upsert_block(p, POSIX_BLOCK, dry)
    for p in powershell_profiles(system, home):
        upsert_block(p, POWERSHELL_BLOCK, dry)
    write_launcher(home / ".local" / "bin" / "fde", SH_LAUNCHER.replace("\r\n", "\n"), True, dry)
    if system == "windows":
        write_launcher(home / "bin" / "fde.bat", BAT_LAUNCHER.replace("\n", "\r\n"), False, dry)

    if not args.no_mirror:
        log("Mirroring the skill")
        mirror_skill(skill_dir, home, dry)

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    local_bin = str(home / ".local" / "bin")
    if local_bin not in path_dirs:
        log("Note: add %s to PATH for non-interactive use. Interactive shells already "
            "have the fde function." % local_bin)
    log("Installed FDE-VAULT. Type 'fde' in your terminal or inside Claude Code / Antigravity to launch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
