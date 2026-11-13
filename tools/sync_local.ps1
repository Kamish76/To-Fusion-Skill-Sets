<#
.SYNOPSIS
    Syncs To-Fusion skills to local Antigravity & Claude environments via Directory Copies / NTFS Junctions.
.DESCRIPTION
    Dynamically discovers all skills under skills/ (both registered and beta)
    and ensures local AI agents (Google Antigravity, Claude Code) have active,
    discoverable skills. On Windows, Antigravity requires real directories to
    discover skills, which this script handles automatically.
.PARAMETER Mode
    Sync mode: 'auto' (copies for Antigravity, links for Claude), 'copy', or 'link'. Default is 'auto'.
#>
param(
    [ValidateSet("auto", "copy", "link")]
    [string]$Mode = "auto"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Syncing To-Fusion Skills (Windows PowerShell - $Mode)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Locate Python executable
$PythonCmd = $null
if (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    $PythonCmd = "$RepoRoot\.venv\Scripts\python.exe"
} elseif (Test-Path "$HOME\.local\bin\python3.12.exe") {
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
    & $PythonCmd tools/sync_manager.py link --mode $Mode
} else {
    Write-Warning "Python not found in PATH; falling back to native PowerShell directory sync."
    
    $AgySkillsDir = Join-Path $HOME ".gemini\antigravity\skills"
    $ConfigSkillsDir = Join-Path $HOME ".gemini\config\skills"
    $ClaudeSkillsDir = Join-Path $HOME ".claude\skills"

    New-Item -ItemType Directory -Force -Path $AgySkillsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $ConfigSkillsDir | Out-Null
    if (Test-Path (Join-Path $HOME ".claude")) {
        New-Item -ItemType Directory -Force -Path $ClaudeSkillsDir | Out-Null
    }

    $Skills = Get-ChildItem -Path (Join-Path $RepoRoot "skills") -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName "SKILL.md")
    }

    foreach ($Skill in $Skills) {
        $Src = $Skill.FullName
        Write-Host "Processing $($Skill.Name)..." -ForegroundColor Yellow

        # Antigravity Global & Local: copy real directory to avoid NTFS junction discovery bug
        foreach ($TargetDir in @($AgySkillsDir, $ConfigSkillsDir)) {
            $Dest = Join-Path $TargetDir $Skill.Name
            if (Test-Path $Dest) {
                $item = Get-Item $Dest -Force
                if ($item.LinkType) {
                    $item.Delete()
                } else {
                    Remove-Item -Recurse -Force $Dest
                }
            }
            if ($Mode -eq "link") {
                New-Item -ItemType Junction -Path $Dest -Target $Src | Out-Null
                Write-Host "   Linked $Dest -> $Src" -ForegroundColor Green
            } else {
                Copy-Item -Recurse -Force $Src $Dest | Out-Null
                Write-Host "   Copied $Dest <- $Src" -ForegroundColor Green
            }
        }

        # Claude Code if present
        if (Test-Path $ClaudeSkillsDir) {
            $Dest = Join-Path $ClaudeSkillsDir $Skill.Name
            if (Test-Path $Dest) {
                $item = Get-Item $Dest -Force
                if ($item.LinkType) {
                    $item.Delete()
                } else {
                    Remove-Item -Recurse -Force $Dest
                }
            }
            if ($Mode -eq "copy") {
                Copy-Item -Recurse -Force $Src $Dest | Out-Null
                Write-Host "   Copied $Dest <- $Src" -ForegroundColor Green
            } else {
                New-Item -ItemType Junction -Path $Dest -Target $Src | Out-Null
                Write-Host "   Linked $Dest -> $Src" -ForegroundColor Green
            }
        }
    }
    Write-Host "Skill synchronization complete!" -ForegroundColor Cyan
}
