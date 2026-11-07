<#
.SYNOPSIS
    Syncs To-Fusion skills to local Antigravity & Claude environments via NTFS Junctions / Symlinks.
.DESCRIPTION
    Dynamically discovers all skills under skills/ (both registered and beta)
    and ensures local AI agents (Google Antigravity, Claude Code) always run
    against live tracked repository code.
#>

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Linking To-Fusion Skills (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Locate Python executable
$PythonCmd = $null
if (Test-Path "$HOME\.local\bin\python3.12.exe") {
    $PythonCmd = "$HOME\.local\bin\python3.12.exe"
} elseif (Get-Command "python3.12" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3.12"
} elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if ($PythonCmd) {
    $env:PYTHONIOENCODING = "utf-8"
    & $PythonCmd tools/sync_manager.py link
} else {
    Write-Warning "Python not found in PATH; falling back to native PowerShell junction creation."
    
    $AgySkillsDir = Join-Path $HOME ".gemini\antigravity\skills"
    $ConfigSkillsDir = Join-Path $HOME ".gemini\config\skills"
    $ClaudeSkillsDir = Join-Path $HOME ".claude\skills"

    New-Item -ItemType Directory -Force -Path $AgySkillsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ConfigSkillsDir | Out-Null

    $Skills = Get-ChildItem -Path (Join-Path $RepoRoot "skills") -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName "SKILL.md")
    }

    foreach ($Skill in $Skills) {
        $Src = $Skill.FullName
        Write-Host "Processing $($Skill.Name)..." -ForegroundColor Yellow

        foreach ($TargetDir in @($AgySkillsDir, $ConfigSkillsDir)) {
            $Dest = Join-Path $TargetDir $Skill.Name
            if (Test-Path $Dest) {
                $item = Get-Item $Dest -Force
                if ($item.LinkType) {
                    $item.Delete()
                } else {
                    $Backup = "${Dest}_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
                    Move-Item -Path $Dest -Destination $Backup
                }
            }
            New-Item -ItemType Junction -Path $Dest -Target $Src | Out-Null
            Write-Host "   Linked $Dest -> $Src" -ForegroundColor Green
        }
    }
    Write-Host "Dynamic linking complete!" -ForegroundColor Cyan
}
