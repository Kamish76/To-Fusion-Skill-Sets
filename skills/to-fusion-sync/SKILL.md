---
name: to-fusion-sync
description: Synchronizes the To-Fusion-Skill-Sets repository and local agent environments across machines (Desktop & Laptop). Verifies branch parity with origin, pulls updates, pushes commits, validates manifest integrity, and live-links all skills to Antigravity and Claude Code.
---

# To-Fusion Universal Repository & Agent Sync Skill

The `to-fusion-sync` skill manages synchronization of the **`To-Fusion-Skill-Sets`** repository and local AI agent runtimes across physical workstations (e.g., Desktop and Laptop). It guarantees that both machines maintain parity with the remote GitHub repository and that agent runtimes (**Google Antigravity**, **Claude Code**) are linked directly to live tracked code.

> [!NOTE]
> - Use **`to-fusion-sync`** for stable branch synchronization (`main`, `dev`), pulling clean updates, verifying manifest integrity, and establishing runtime symlinks.
> - Use **`to-fusion-dev-sync`** when iterating on the `dev` branch, developing experimental beta skills, creating rapid WIP checkpoints, or handing off active feature work between Desktop and Laptop.

---

## 🛠️ CLI Quick Reference

All synchronization operations are driven by the zero-dependency cross-platform tool `tools/sync_manager.py` (or native helpers `tools/sync_local.ps1` on Windows / `tools/sync_local.sh` on Unix):

| Operation | Command | Description |
| :--- | :--- | :--- |
| **Status Check** | `python tools/sync_manager.py status` | Inspect current branch, ahead/behind status, uncommitted changes, and skill inventory. |
| **Hot-Link Runtimes** | `python tools/sync_manager.py link` | Dynamically link all skills in `skills/` to Antigravity and Claude Code. |
| **Windows Link** | `powershell -File tools/sync_local.ps1` | Native PowerShell NTFS Junction linker for Windows. |
| **Unix / Mac Link** | `bash tools/sync_local.sh` | Dynamic POSIX symlink linker for macOS and Linux. |
| **Handoff Cheatsheet** | `python tools/sync_manager.py handoff` | View the machine-to-machine handoff cheatsheet. |

---

## 🔄 Synchronization Workflows

### 1. Inbound Sync (Pulling Updates on Machine)
When switching to a machine or pulling recent updates from GitHub:
1. Verify working tree state:
   ```bash
   python tools/sync_manager.py status
   ```
2. Fetch and pull latest commits:
   ```bash
   git fetch origin
   git pull --rebase origin <branch>
   ```
3. Re-link local runtimes to ensure newly added skills are recognized:
   ```bash
   python tools/sync_manager.py link
   ```

### 2. Outbound Sync (Pushing Clean Changes)
When pushing tested and verified skill updates to GitHub:
1. Confirm changes are recorded:
   ```bash
   python tools/sync_manager.py status
   ```
2. Log evolution changes if skills were modified:
   ```bash
   python3 tools/log_change.py --skill <skill_name> --type added --message "Description of feature"
   ```
3. Stage, commit, and push:
   ```bash
   git add -A
   git commit -m "feat(<skill_name>): describe your change"
   git push origin <branch>
   ```

### 3. Agent Runtime Hot-Linking
Antigravity and Claude Code discover skills from specific user directories:
- **Antigravity Global:** `~/.gemini/config/skills/<skill_name>`
- **Antigravity Workspace:** `~/.gemini/antigravity/skills/<skill_name>`
- **Claude Code:** `~/.claude/skills/<skill_name>`

Running `python tools/sync_manager.py link`:
- Dynamically scans `skills/` for all subfolders containing `SKILL.md`.
- Automatically establishes NTFS Junctions on Windows (no administrator privileges needed) and POSIX symlinks on macOS/Linux.
- Backs up any conflicting legacy directory before linking.

---

## 🧪 Health Check & Diagnostics

To verify your local sync health:
1. Check that all skills report `Linked ✅` in `python tools/sync_manager.py status`.
2. Run unit tests to confirm tool integrity:
   ```bash
   python -m unittest discover tests
   ```
3. Verify that `skills_manifest.json` matches the filesystem using:
   ```bash
   python tools/sync_manager.py check-beta
   ```
