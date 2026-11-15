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
$claudeCmds = Join-Path $env:USERPROFILE ".claude\commands"
New-Item -ItemType Directory -Path $claudeSkill -Force | Out-Null
New-Item -ItemType Directory -Path $agentSkill -Force | Out-Null
New-Item -ItemType Directory -Path $claudeCmds -Force | Out-Null
Copy-Item -Path (Join-Path $AppDir ".claude\skills\fde-vault\*") -Destination $claudeSkill -Recurse -Force
Copy-Item -Path (Join-Path $AppDir ".claude\skills\fde-vault\*") -Destination $agentSkill -Recurse -Force
$appCmds = Join-Path $AppDir ".claude\commands"
if (Test-Path $appCmds) {
    Copy-Item -Path (Join-Path $appCmds "*") -Destination $claudeCmds -Recurse -Force
}

Write-Host "  - Registering global shell profiles..."
$installerScript = Join-Path $AppDir ".claude\skills\fde-vault\scripts\install_cli.py"
if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 $installerScript
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    python $installerScript
}

# Ensure %USERPROFILE%\bin is populated and present in PATH
$userBin = Join-Path $env:USERPROFILE "bin"
if (-not (Test-Path $userBin)) { New-Item -ItemType Directory -Path $userBin -Force | Out-Null }
$fdeBat = Join-Path $AppDir "fde-vault.bat"
if (Test-Path $fdeBat) {
    Copy-Item $fdeBat (Join-Path $userBin "fde.bat") -Force
    Copy-Item $fdeBat (Join-Path $userBin "fde.cmd") -Force
}

$regPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($regPath -notlike "*$userBin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userBin;$regPath", "User")
}
if ($env:PATH -notlike "*$userBin*") {
    $env:PATH = "$userBin;$env:PATH"
}

# Define fde function immediately in current PowerShell session
function global:fde {
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
    if (-not $g) {
        $c = Join-Path $env:USERPROFILE '.fde-vault-app\.claude\skills\fde-vault\scripts\vault_guard.py'
        if (Test-Path $c) { $g = $c }
    }
    if (-not $g) { Write-Error 'fde: vault_guard.py not found'; return }
    if (-not $args -or $args.Count -eq 0) {
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 $g open }
        elseif (Get-Command python3 -ErrorAction SilentlyContinue) { & python3 $g open }
        else { & python $g open }
    } else {
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 $g @args }
        elseif (Get-Command python3 -ErrorAction SilentlyContinue) { & python3 $g @args }
        else { & python $g @args }
    }
}

Write-Host "[FDE-VAULT] Installation complete."
Write-Host "Installed FDE-VAULT. Type 'fde' in your terminal or inside Claude Code / Antigravity to launch."
