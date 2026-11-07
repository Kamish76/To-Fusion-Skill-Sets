#!/usr/bin/env python3
"""
tools/sync_manager.py — Universal Cross-Platform Synchronization Engine for To-Fusion Skills

Synchronizes the To-Fusion-Skill-Sets repository, active feature/dev branches,
and local AI agent environments (Google Antigravity, Claude Code) across machines
(e.g., Desktop <-> Laptop), with first-class support for beta skills and dev iterations.

Zero external dependencies: uses Python standard library only.
Works on Windows (PowerShell/cmd), macOS, and Linux.

Usage:
    # Check sync status and skill inventory:
    python tools/sync_manager.py status

    # Link all discovered skills (registered + beta) into Antigravity & Claude:
    python tools/sync_manager.py link

    # Push dev/feature branch with clean WIP checkpoint & generate laptop receipt:
    python tools/sync_manager.py dev-push --message "feat: cantilever kinematics v8"
    python tools/sync_manager.py dev-push   # creates structured WIP checkpoint

    # Pull dev/feature branch on laptop & hot-link any newly created beta skills:
    python tools/sync_manager.py dev-pull

    # Inspect beta or unreleased skills:
    python tools/sync_manager.py check-beta

    # Print laptop/desktop handoff instructions:
    python tools/sync_manager.py handoff
"""

import argparse
import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
MANIFEST_PATH = REPO_ROOT / "skills_manifest.json"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"

HOME_DIR = Path.home()
AGY_SKILLS_DIR = HOME_DIR / ".gemini" / "antigravity" / "skills"
CONFIG_SKILLS_DIR = HOME_DIR / ".gemini" / "config" / "skills"
CLAUDE_SKILLS_DIR = HOME_DIR / ".claude" / "skills"


def run_git(args, check=True, capture=True):
    """Run a git command in the repository root and return output."""
    cmd = ["git"] + args
    res = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if check and res.returncode != 0:
        err_msg = res.stderr.strip() if res.stderr else f"Exit code {res.returncode}"
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{err_msg}")
    return res


def get_current_branch():
    """Return the name of the current git branch."""
    res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], check=False)
    if res.returncode == 0:
        return res.stdout.strip()
    return "unknown"


def get_git_status():
    """Retrieve detailed git status dictionary."""
    branch = get_current_branch()
    
    # Check upstream tracking branch
    upstream_res = run_git(["rev-parse", "--abbrev-ref", "@{upstream}"], check=False)
    upstream = upstream_res.stdout.strip() if upstream_res.returncode == 0 else None

    ahead, behind = 0, 0
    if upstream:
        count_res = run_git(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"], check=False)
        if count_res.returncode == 0 and count_res.stdout.strip():
            parts = count_res.stdout.strip().split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])

    # Working tree changes
    status_res = run_git(["status", "--porcelain"], check=False)
    status_lines = [line for line in status_res.stdout.splitlines() if line.strip()]

    staged = []
    unstaged = []
    untracked = []

    for line in status_lines:
        code = line[:2]
        file_path = line[3:].strip()
        if code[0] in ("M", "A", "D", "R", "C"):
            staged.append(file_path)
        if code[1] in ("M", "D"):
            unstaged.append(file_path)
        if code.startswith("??"):
            untracked.append(file_path)

    return {
        "branch": branch,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
        "is_dirty": len(staged) > 0 or len(unstaged) > 0 or len(untracked) > 0,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
    }


def load_manifest():
    """Load skills_manifest.json if present."""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def parse_skill_metadata(skill_dir: Path):
    """Parse name, description, and metadata from SKILL.md YAML frontmatter."""
    skill_md = skill_dir / "SKILL.md"
    name = skill_dir.name
    description = ""
    version = "beta"

    if skill_md.exists():
        try:
            with open(skill_md, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm_block = fm_match.group(1)
                for line in fm_block.splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip('"\'')
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"\'')
                    elif line.startswith("version:"):
                        version = line.split(":", 1)[1].strip().strip('"\'')
        except Exception:
            pass

    return {
        "dir_name": skill_dir.name,
        "name": name,
        "description": description,
        "version": version,
        "has_skill_md": skill_md.exists(),
        "scripts": [p.name for p in (skill_dir / "scripts").glob("*.py")] if (skill_dir / "scripts").exists() else [],
        "path": skill_dir,
    }


def discover_skills():
    """Scan skills/ directory and categorize into registered vs beta."""
    manifest = load_manifest()
    registered_dict = manifest.get("skills", {})

    all_skills = []
    if SKILLS_DIR.exists():
        for entry in sorted(SKILLS_DIR.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").exists():
                meta = parse_skill_metadata(entry)
                is_registered = meta["name"] in registered_dict or meta["dir_name"] in registered_dict
                if is_registered:
                    reg_info = registered_dict.get(meta["name"]) or registered_dict.get(meta["dir_name"])
                    meta["status"] = "Registered"
                    meta["manifest_version"] = reg_info.get("version", "1.0.0") if isinstance(reg_info, dict) else "1.0.0"
                else:
                    meta["status"] = "Beta"
                    meta["manifest_version"] = meta.get("version", "beta")
                all_skills.append(meta)

    return all_skills


def create_dir_link(source_dir: Path, target_link: Path):
    """
    Cross-platform directory link creation.
    Creates NTFS directory junction or symlink on Windows; POSIX symlink on Unix.
    Returns True if successfully linked, False otherwise.
    """
    target_link = Path(target_link)
    source_dir = Path(source_dir).resolve()

    if not source_dir.exists():
        return False, f"Source does not exist: {source_dir}"

    target_link.parent.mkdir(parents=True, exist_ok=True)

    # Check if target already exists
    if target_link.is_symlink() or (hasattr(target_link, "is_junction") and target_link.is_junction()):
        try:
            target_link.unlink()
        except OSError:
            # On Windows directory symlink / junction unlinking
            try:
                os.rmdir(target_link)
            except OSError:
                pass
    elif target_link.exists():
        if target_link.is_dir():
            # Backup non-link existing folder
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = target_link.parent / f"{target_link.name}_backup_{ts}"
            shutil.move(str(target_link), str(backup_path))
            print(f"   ⚠️  Existing folder backed up to {backup_path.name}")
        else:
            target_link.unlink()

    # Try creating symlink or junction
    if platform.system() == "Windows":
        # 1. Try Windows native junction via _winapi (zero privileges required)
        try:
            import _winapi
            _winapi.CreateJunction(str(source_dir), str(target_link))
            return True, "NTFS Junction"
        except Exception:
            pass

        # 2. Try mklink /J via cmd
        try:
            res = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(target_link), str(source_dir)],
                capture_output=True,
                text=True
            )
            if res.returncode == 0:
                return True, "NTFS Junction (mklink)"
        except Exception:
            pass

        # 3. Fallback to os.symlink
        try:
            os.symlink(str(source_dir), str(target_link), target_is_directory=True)
            return True, "Symlink"
        except Exception as e:
            return False, f"Windows link failed: {e}"
    else:
        # Unix / macOS
        try:
            os.symlink(str(source_dir), str(target_link), target_is_directory=True)
            return True, "Symlink"
        except Exception as e:
            return False, f"Symlink failed: {e}"


def check_target_link(target_link: Path):
    """Check if target_link exists and is a link."""
    if not target_link.exists() and not target_link.is_symlink():
        return False, "missing"
    if target_link.is_symlink():
        return True, "symlink"
    # On Windows, junctions may report is_dir but not is_symlink in older Python
    try:
        if bool(os.readlink(str(target_link))):
            return True, "junction"
    except (OSError, ValueError, AttributeError):
        pass
    if target_link.is_dir():
        return True, "folder"
    return True, "present"


def link_all_skills():
    """Hot-link all discovered skills into Antigravity & Claude environments."""
    skills = discover_skills()
    print("==========================================================")
    print("  🔄 Hot-Linking To-Fusion Skills to AI Agent Runtimes")
    print("==========================================================")
    print(f"Discovered {len(skills)} skill(s) in {SKILLS_DIR}:")
    for s in skills:
        badge = "✨ [BETA]" if s["status"] == "Beta" else "📦 [STABLE]"
        print(f"  - {badge} {s['name']} (v{s['manifest_version']})")

    targets = [
        ("Antigravity Global", CONFIG_SKILLS_DIR),
        ("Antigravity Local", AGY_SKILLS_DIR),
    ]

    # Include Claude Code if directory exists
    if CLAUDE_SKILLS_DIR.parent.exists() or CLAUDE_SKILLS_DIR.exists():
        targets.append(("Claude Code", CLAUDE_SKILLS_DIR))

    success_count = 0
    total_links = 0

    for env_name, target_base in targets:
        print(f"\n🔗 Linking into {env_name} ({target_base})...")
        target_base.mkdir(parents=True, exist_ok=True)
        for s in skills:
            dest = target_base / s["dir_name"]
            ok, method = create_dir_link(s["path"], dest)
            total_links += 1
            if ok:
                success_count += 1
                print(f"   ✅ {s['dir_name']} -> {method}")
            else:
                print(f"   ❌ {s['dir_name']} failed: {method}")

    print("\n----------------------------------------------------------")
    print(f"🎉 Hot-link complete: {success_count}/{total_links} links established.")
    print("==========================================================")
    return success_count == total_links


def print_status():
    """Display comprehensive git and skill status report."""
    git_st = get_git_status()
    skills = discover_skills()

    print("==========================================================")
    print("  📡 To-Fusion Synchronization Status Report")
    print("==========================================================")
    print(f"Current Branch:   {git_st['branch']}")
    print(f"Upstream Remote:  {git_st['upstream'] or '(None - branch not pushed)'}")

    if git_st['upstream']:
        ahead_str = f"Ahead by {git_st['ahead']} commit(s)" if git_st['ahead'] > 0 else "Up to date"
        behind_str = f"Behind by {git_st['behind']} commit(s)" if git_st['behind'] > 0 else "Up to date"
        print(f"Commits Ahead:    {ahead_str}")
        print(f"Commits Behind:   {behind_str}")

    print("\n📁 Working Tree:")
    if not git_st['is_dirty']:
        print("   ✅ Working tree is clean.")
    else:
        if git_st['staged']:
            print(f"   🟢 Staged changes ({len(git_st['staged'])}):")
            for f in git_st['staged'][:5]:
                print(f"      - {f}")
            if len(git_st['staged']) > 5:
                print(f"      ... and {len(git_st['staged']) - 5} more")
        if git_st['unstaged']:
            print(f"   🟡 Unstaged modifications ({len(git_st['unstaged'])}):")
            for f in git_st['unstaged'][:5]:
                print(f"      - {f}")
            if len(git_st['unstaged']) > 5:
                print(f"      ... and {len(git_st['unstaged']) - 5} more")
        if git_st['untracked']:
            print(f"   ⚪ Untracked files ({len(git_st['untracked'])}):")
            for f in git_st['untracked'][:5]:
                print(f"      - {f}")
            if len(git_st['untracked']) > 5:
                print(f"      ... and {len(git_st['untracked']) - 5} more")

    print("\n🧠 Discovered Skills Inventory:")
    print(f"{'Skill Name':<22} {'Version':<10} {'Status':<12} {'Antigravity':<14} {'Claude':<10}")
    print("-" * 72)
    for s in skills:
        agy_ok, _ = check_target_link(CONFIG_SKILLS_DIR / s["dir_name"])
        claude_ok, _ = check_target_link(CLAUDE_SKILLS_DIR / s["dir_name"])
        agy_str = "Linked ✅" if agy_ok else "Unlinked ❌"
        claude_str = "Linked ✅" if claude_ok else "Unlinked ❌"
        print(f"{s['name']:<22} {s['manifest_version']:<10} {s['status']:<12} {agy_str:<14} {claude_str:<10}")

    print("==========================================================")


def check_beta_skills():
    """Inspect and validate unregistered or beta skills."""
    skills = discover_skills()
    beta_skills = [s for s in skills if s["status"] == "Beta"]

    print("==========================================================")
    print("  🧪 To-Fusion Beta Skills & Discovery Audit")
    print("==========================================================")

    if not beta_skills:
        print("✅ All discovered skills are registered in skills_manifest.json.")
        print("   No unreleased or untracked beta skills detected.")
    else:
        print(f"Detected {len(beta_skills)} unreleased / beta skill(s):")
        for s in beta_skills:
            print(f"\n📦 Beta Skill: {s['name']}")
            print(f"   Folder:       skills/{s['dir_name']}")
            print(f"   Description:  {s['description'] or '(No description in SKILL.md)'}")
            print(f"   Scripts:      {', '.join(s['scripts']) if s['scripts'] else '(None)'}")
            print("   Manifest:     ⚠️  Not yet added to skills_manifest.json")
            print("   Recommendation: Test locally via 'dev-sync' before adding to manifest.")

    print("==========================================================")


def dev_push(message=None):
    """
    Push dev or active feature branch to origin with safe WIP checkpointing
    and output copy-pasteable Laptop Handoff receipt.
    """
    git_st = get_git_status()
    branch = git_st["branch"]

    if branch in ("main", "master"):
        print(f"⚠️  WARNING: You are on default branch '{branch}'.")
        print("   Per Universal Branch-First Discipline, push is recommended on 'dev' or 'feat/*' branches.")
        confirm = input("   Do you want to proceed pushing to default branch? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Push cancelled.")
            return

    print("==========================================================")
    print(f"  🚀 Executing Dev Sync Push for branch: {branch}")
    print("==========================================================")

    # If dirty, stage and commit
    if git_st["is_dirty"]:
        print("📦 Staging working tree changes...")
        run_git(["add", "-A"])

        if not message:
            host = platform.node() or "dev-machine"
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"wip(dev-sync): auto-checkpoint from {host} at {now}"
        else:
            commit_msg = message

        print(f"📝 Creating commit: {commit_msg}")
        run_git(["commit", "-m", commit_msg])
    else:
        print("✅ Working tree clean, pushing existing commits.")

    print(f"📡 Pushing to origin/{branch}...")
    run_git(["push", "-u", "origin", branch])

    # Get latest commit
    log_res = run_git(["log", "-n", "1", "--oneline"])
    latest_commit = log_res.stdout.strip()

    print("\n==========================================================")
    print("  🎉 DEV SYNC PUSH SUCCESSFUL")
    print("==========================================================")
    print(f"Branch:         {branch}")
    print(f"Remote:         origin/{branch}")
    print(f"Latest Commit:  {latest_commit}")
    print("\n👉 TO RESUME ON YOUR LAPTOP, RUN:")
    print(f"   git fetch origin && git checkout {branch} && python tools/sync_manager.py dev-pull")
    print("==========================================================")


def dev_pull():
    """
    Pull dev or active feature branch from origin on laptop/desktop,
    re-link all skills including newly created beta skills, and audit state.
    """
    git_st = get_git_status()
    branch = git_st["branch"]

    print("==========================================================")
    print(f"  📥 Executing Dev Sync Pull for branch: {branch}")
    print("==========================================================")

    stashed = False
    if git_st["is_dirty"]:
        print("⚠️  Working tree has uncommitted local changes. Stashing temporarily...")
        stash_res = run_git(["stash", "push", "-m", f"dev-sync-auto-stash-{datetime.datetime.now().isoformat()}"])
        if "Saved working directory" in stash_res.stdout:
            stashed = True

    print("📡 Fetching updates from origin...")
    run_git(["fetch", "origin"])

    # Pull / rebase
    print(f"🔄 Pulling latest commits from origin/{branch}...")
    pull_res = run_git(["pull", "--rebase", "origin", branch], check=False)
    if pull_res.returncode != 0:
        print(f"❌ Rebase failed:\n{pull_res.stderr}")
        if stashed:
            print("   Restoring stashed changes...")
            run_git(["stash", "pop"], check=False)
        sys.exit(1)

    if stashed:
        print("📦 Re-applying stashed local changes...")
        pop_res = run_git(["stash", "pop"], check=False)
        if pop_res.returncode != 0:
            print("⚠️  Note: Conflicts occurred when re-applying stash. Please resolve manually.")

    # Hot-link all skills
    link_all_skills()

    # Beta skills check
    check_beta_skills()

    print("\n🎉 Dev sync pull complete! Runtimes are fully synced and linked.")


def print_handoff():
    """Print handoff instructions between machines."""
    git_st = get_git_status()
    branch = git_st["branch"]

    print("==========================================================")
    print("  🤝 Desktop <-> Laptop Handoff Cheatsheet")
    print("==========================================================")
    print("1. BEFORE LEAVING DESKTOP:")
    print(f"   python tools/sync_manager.py dev-push --message \"feat: your latest updates\"")
    print("\n2. ON OPENING LAPTOP:")
    print(f"   git checkout {branch}")
    print(f"   python tools/sync_manager.py dev-pull")
    print("\n3. BEFORE LEAVING LAPTOP:")
    print(f"   python tools/sync_manager.py dev-push")
    print("\n4. ON RETURNING TO DESKTOP:")
    print(f"   python tools/sync_manager.py dev-pull")
    print("==========================================================")


def main():
    parser = argparse.ArgumentParser(
        description="To-Fusion Universal Synchronization & Environment Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # status
    subparsers.add_parser("status", help="Show sync status, branch parity, and skill inventory")

    # link
    subparsers.add_parser("link", help="Hot-link all skills (stable + beta) to Antigravity & Claude")

    # dev-push
    p_dev_push = subparsers.add_parser("dev-push", help="Commit and push dev/feature branch with laptop handoff receipt")
    p_dev_push.add_argument("-m", "--message", help="Optional commit message (defaults to auto WIP checkpoint)")

    # dev-pull
    subparsers.add_parser("dev-pull", help="Pull latest dev/feature branch, hot-link skills, and audit beta skills")

    # check-beta
    subparsers.add_parser("check-beta", help="Inspect and validate unreleased or beta skills")

    # handoff
    subparsers.add_parser("handoff", help="Display machine-to-machine handoff cheatsheet")

    # Flags for backward compatibility or direct execution
    parser.add_argument("--status", action="store_true", help="Alias for 'status'")
    parser.add_argument("--link", action="store_true", help="Alias for 'link'")
    parser.add_argument("--dev-push", action="store_true", help="Alias for 'dev-push'")
    parser.add_argument("--dev-pull", action="store_true", help="Alias for 'dev-pull'")
    parser.add_argument("--check-beta", action="store_true", help="Alias for 'check-beta'")
    parser.add_argument("--handoff", action="store_true", help="Alias for 'handoff'")

    args = parser.parse_args()

    # Route flags if command omitted
    cmd = args.command
    if not cmd:
        if args.status:
            cmd = "status"
        elif args.link:
            cmd = "link"
        elif args.dev_push:
            cmd = "dev-push"
        elif args.dev_pull:
            cmd = "dev-pull"
        elif args.check_beta:
            cmd = "check-beta"
        elif args.handoff:
            cmd = "handoff"
        else:
            cmd = "status"

    if cmd == "status":
        print_status()
    elif cmd == "link":
        link_all_skills()
    elif cmd == "dev-push":
        msg = getattr(args, "message", None)
        dev_push(message=msg)
    elif cmd == "dev-pull":
        dev_pull()
    elif cmd == "check-beta":
        check_beta_skills()
    elif cmd == "handoff":
        print_handoff()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
