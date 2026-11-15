#!/usr/bin/env bash
# FDE-VAULT Global One-Line GitHub Installer for macOS and Linux.
# Usage: curl -fsSL https://raw.githubusercontent.com/fde-vault/fde-vault/main/install.sh | bash

set -euo pipefail

APP_DIR="${FDE_APP_DIR:-$HOME/.fde-vault-app}"
REPO_URL="${FDE_REPO_URL:-}"

if [ -z "$REPO_URL" ]; then
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        REPO_URL=$(git config --get remote.origin.url || true)
    fi
fi
if [ -z "$REPO_URL" ]; then
    REPO_URL="https://github.com/fde-vault/fde-vault.git"
fi

echo "[FDE-VAULT] Installing from $REPO_URL into $APP_DIR..."

if [ -d "$APP_DIR/.git" ]; then
    echo "  - Updating existing clone in $APP_DIR..."
    git -C "$APP_DIR" fetch --depth 1 origin || true
    git -C "$APP_DIR" reset --hard origin/HEAD || git -C "$APP_DIR" pull --ff-only || true
else
    mkdir -p "$(dirname "$APP_DIR")"
    echo "  - Cloning repository..."
    git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi

echo "  - Installing fde CLI package..."
if command -v pipx >/dev/null 2>&1; then
    pipx install "$APP_DIR" --force
elif command -v python3 >/dev/null 2>&1; then
    python3 -m pip install --user "$APP_DIR"
elif command -v python >/dev/null 2>&1; then
    python -m pip install --user "$APP_DIR"
fi

echo "  - Synchronizing skill mirrors to user home..."
mkdir -p "$HOME/.claude/skills/fde-vault"
mkdir -p "$HOME/.agent/skills/fde-vault"
cp -R "$APP_DIR/.claude/skills/fde-vault/"* "$HOME/.claude/skills/fde-vault/"
cp -R "$APP_DIR/.claude/skills/fde-vault/"* "$HOME/.agent/skills/fde-vault/"

echo "  - Registering global shell profiles..."
if command -v python3 >/dev/null 2>&1; then
    python3 "$APP_DIR/.claude/skills/fde-vault/scripts/install_cli.py"
elif command -v python >/dev/null 2>&1; then
    python "$APP_DIR/.claude/skills/fde-vault/scripts/install_cli.py"
fi

echo "[FDE-VAULT] Installation complete."
echo "  Run 'fde' to launch the executive ledger."
echo "  Run 'fde init' inside any repository to scaffold governance assets."
