# FDE-VAULT Global One-Line GitHub Installer for Windows PowerShell.
# Usage: irm https://raw.githubusercontent.com/aryamanm77/fde-vault/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$AppDir = if ($env:FDE_APP_DIR) { $env:FDE_APP_DIR } else { Join-Path $env:USERPROFILE ".fde-vault-app" }
$RepoUrl = $env:FDE_REPO_URL

if (-not $RepoUrl) {
    try {
        $detected = git config --get remote.origin.url 2>$null
        if ($detected) { $RepoUrl = $detected }
    } catch {}
}
if (-not $RepoUrl) {
    $RepoUrl = "https://github.com/aryamanm77/fde-vault.git"
}

Write-Host "[FDE-VAULT] Installing from $RepoUrl into $AppDir..."

if (Test-Path (Join-Path $AppDir ".git")) {
    Write-Host "  - Updating existing clone in $AppDir..."
    try {
        git -C $AppDir fetch --depth 1 origin
        git -C $AppDir reset --hard origin/HEAD
    } catch {
        Write-Host "  - Warning: git pull failed; continuing with existing directory."
    }
} else {
    $parent = Split-Path -Parent $AppDir
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Write-Host "  - Cloning repository..."
    git clone --depth 1 $RepoUrl $AppDir
}

Write-Host "  - Installing fde CLI package..."
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    pipx install $AppDir --force
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m pip install --user $AppDir
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python -m pip install --user $AppDir
}

Write-Host "  - Synchronizing skill mirrors to user home..."
$claudeSkill = Join-Path $env:USERPROFILE ".claude\skills\fde-vault"
$agentSkill = Join-Path $env:USERPROFILE ".agent\skills\fde-vault"
New-Item -ItemType Directory -Path $claudeSkill -Force | Out-Null
New-Item -ItemType Directory -Path $agentSkill -Force | Out-Null
Copy-Item -Path (Join-Path $AppDir ".claude\skills\fde-vault\*") -Destination $claudeSkill -Recurse -Force
Copy-Item -Path (Join-Path $AppDir ".claude\skills\fde-vault\*") -Destination $agentSkill -Recurse -Force

Write-Host "  - Registering global shell profiles..."
$installerScript = Join-Path $AppDir ".claude\skills\fde-vault\scripts\install_cli.py"
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 $installerScript
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python $installerScript
}

Write-Host "[FDE-VAULT] Installation complete."
Write-Host "  Run 'fde' to launch the executive ledger."
Write-Host "  Run 'fde init' inside any repository to scaffold governance assets."
