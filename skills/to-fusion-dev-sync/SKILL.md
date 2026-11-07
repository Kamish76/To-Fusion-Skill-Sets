---
name: to-fusion-dev-sync
description: Dedicated developer and beta-skills synchronization engine for To-Fusion-Skill-Sets. Built specifically for rapid Desktop <-> Laptop handoffs on the 'dev' branch. Automatically captures WIP changes, syncs active feature/beta branches, hot-links unreleased beta skills into Antigravity/Claude runtimes, and outputs deterministic handoff receipts.
---

# To-Fusion Dev & Beta Skills Synchronization Skill

The `to-fusion-dev-sync` skill is the dedicated developer workflow engine for **`To-Fusion-Skill-Sets`**. It is built specifically for rapid, friction-free synchronization between your **Desktop** and **Laptop** workstations while working on the **`dev`** branch or active feature branches (`feat/*`).

It automates safe work-in-progress (WIP) checkpointing, manages branch synchronization with GitHub, dynamically hot-links unreleased/beta skills into local AI agent runtimes (**Google Antigravity**, **Claude Code**), and outputs exact copy-pasteable handoff receipts.

---

## 🚀 Rapid Handoff Workflow (Desktop $\longleftrightarrow$ Laptop)

```
       DESKTOP                                                     LAPTOP
┌───────────────────────┐                                   ┌───────────────────────┐
│ Work on dev / feat    │                                   │                       │
│                       │                                   │                       │
│ python tools/         │                                   │                       │
│   sync_manager.py     │          git push origin          │                       │
│   dev-push            ├──────────────────────────────────►│                       │
│                       │                                   │                       │
│ (Generates Receipt)   │                                   │ Run Receipt:          │
│                       │                                   │ git checkout <branch> │
│                       │                                   │ python tools/         │
│                       │                                   │   sync_manager.py     │
│                       │                                   │   dev-pull            │
│                       │                                   │                       │
│                       │                                   │ (All beta skills      │
│                       │                                   │  instantly linked!)   │
└───────────────────────┘                                   └───────────────────────┘
```

---

## 🛠️ Dev Sync Commands

| Command | Purpose | When to Use |
| :--- | :--- | :--- |
| `python tools/sync_manager.py dev-push` | Creates structured WIP checkpoint and pushes to remote. | Run on current machine before switching workstations. |
| `python tools/sync_manager.py dev-push -m "feat: ..."` | Commits with explicit message and pushes to remote. | Run when completing a logical unit of work. |
| `python tools/sync_manager.py dev-pull` | Fetches, rebases, hot-links skills, and audits beta skills. | Run upon opening the other machine to resume instantly. |
| `python tools/sync_manager.py check-beta` | Inspects unreleased / beta skills in `skills/`. | Run to audit experimental skills before formal release. |
| `python tools/sync_manager.py status` | Shows branch ahead/behind, dirty files, and skill link table. | Run anytime to inspect sync health. |

---

## 📦 Beta Skills Lifecycle & Hot-Linking

When creating experimental or WIP CAD skills:
1. **Scaffold the Beta Skill:** Create `skills/<new-beta-skill>/SKILL.md` and any associated scripts in `skills/<new-beta-skill>/scripts/`.
2. **Automatic Discovery:** `tools/sync_manager.py` automatically discovers any directory in `skills/` with a `SKILL.md`. It detects whether the skill is registered in `skills_manifest.json` or is an unreleased `[BETA]`.
3. **Instant Runtime Linking:** Running `dev-pull` (or `link`) instantly establishes NTFS Junctions (Windows) or symlinks (macOS/Linux) in:
   - `~/.gemini/antigravity/skills/<new-beta-skill>`
   - `~/.gemini/config/skills/<new-beta-skill>`
   - `~/.claude/skills/<new-beta-skill>`
   This allows you to test the new beta skill immediately in Antigravity or Claude on **both** Desktop and Laptop without manual configuration!
4. **Promotion to Stable:**
   Once verified, formalize the skill:
   ```bash
   python3 tools/log_change.py --skill <new-skill> --type added --message "Promoted beta skill to stable"
   ```
   Add the skill entry to `skills_manifest.json`.

---

## 📋 Step-by-Step Machine Handoff Procedure

### Step 1: Leaving Your Current Machine (e.g. Desktop)
Before stepping away from your machine:
```bash
python tools/sync_manager.py dev-push
```
- Automatically stages untracked and modified files.
- Creates an auto-checkpoint commit (`wip(dev-sync): auto-checkpoint from <host> at <timestamp>`).
- Pushes the active branch to `origin`.
- Prints the exact command to run on your laptop:
  ```
  👉 TO RESUME ON YOUR LAPTOP, RUN:
     git fetch origin && git checkout <branch> && python tools/sync_manager.py dev-pull
  ```

### Step 2: Resuming on Your Target Machine (e.g. Laptop)
Open your terminal on the target machine:
```bash
git fetch origin && git checkout <branch>
python tools/sync_manager.py dev-pull
```
- Stashes any local dirty changes safely.
- Rebases cleanly against latest `origin/<branch>`.
- Re-applies any local stashes.
- Automatically discovers and links all new/beta skills.
- Displays the **Beta Skills & Discovery Audit** summary so you know what's in progress.

---

## 🛡️ Safety & Branch Protection Rules
- **No Direct Default Commits:** `dev-push` warns if you attempt to push directly to `main` or `master`. Always work on `dev` or a dedicated feature branch (`feat/*`, `fix/*`).
- **Conflict Prevention:** Always run `dev-pull` immediately after fetching a branch on your second machine to avoid divergent git histories.
- **Cross-Platform Junctions:** On Windows, `sync_manager.py` uses native NTFS Directory Junctions (`_winapi.CreateJunction`), eliminating the need for Administrator privileges or developer mode.
