#!/usr/bin/env python3
"""
tools/log_change.py - Change & Evolution Tracker for To-Fusion Skills

Records updates, fixes, and feature additions into CHANGELOG.md and skills_manifest.json.
Used by developers and AI agents to systematically document changes whenever skills are modified.

Usage:
    # Log an addition to a skill:
    python3 tools/log_change.py --skill 3mf-to-fusion --type added --message "Added chord error compensation for hex pockets"

    # Log a fix:
    python3 tools/log_change.py --skill media-to-fusion --type fixed --message "Fixed skew in split-viewport orthographic Canny detection"

    # Cut a new release:
    python3 tools/log_change.py --release 1.1.0
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
MANIFEST_PATH = REPO_ROOT / "skills_manifest.json"
AUDIT_LOG_PATH = REPO_ROOT / "logs" / "change_audit.jsonl"

VALID_TYPES = ["added", "changed", "deprecated", "removed", "fixed", "security", "docs"]


def load_manifest():
    if not MANIFEST_PATH.exists():
        return {}
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(data):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def append_audit_log(entry):
    os.makedirs(AUDIT_LOG_PATH.parent, exist_ok=True)
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def log_change(skill, change_type, message, author="Kamish"):
    change_type = change_type.lower()
    if change_type not in VALID_TYPES:
        sys.stderr.write(f"Invalid change type '{change_type}'. Must be one of: {', '.join(VALID_TYPES)}\n")
        sys.exit(1)

    today = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now().isoformat()

    manifest = load_manifest()
    valid_skills = list(manifest.get("skills", {}).keys()) + ["rules", "core", "general"]
    if skill not in valid_skills:
        print(f"Warning: '{skill}' not in known skills {valid_skills}. Proceeding anyway.")

    # Read CHANGELOG.md
    if not CHANGELOG_PATH.exists():
        sys.stderr.write(f"CHANGELOG.md not found at {CHANGELOG_PATH}\n")
        sys.exit(1)

    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    section_header = f"### {change_type.capitalize()}"
    bullet = f"- **[{skill}]**: {message}"

    # Find [Unreleased] section
    unreleased_pattern = r"(## \[Unreleased\]\s*\n)"
    match = re.search(unreleased_pattern, content)
    if not match:
        sys.stderr.write("Could not locate '## [Unreleased]' section in CHANGELOG.md\n")
        sys.exit(1)

    # Check if section header exists between [Unreleased] and next release '## ['
    unreleased_start = match.end()
    next_release_match = re.search(r"\n## \[", content[unreleased_start:])
    unreleased_end = unreleased_start + next_release_match.start() if next_release_match else len(content)

    unreleased_block = content[unreleased_start:unreleased_end]

    if section_header in unreleased_block:
        # Header exists, append bullet after header
        target_str = section_header + "\n"
        idx = unreleased_block.find(target_str) + len(target_str)
        new_unreleased_block = unreleased_block[:idx] + f"{bullet}\n" + unreleased_block[idx:]
    else:
        # Header doesn't exist, create it at the top of unreleased block
        new_unreleased_block = f"\n{section_header}\n{bullet}\n" + unreleased_block.lstrip()

    new_content = content[:unreleased_start] + new_unreleased_block + content[unreleased_end:]

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Update manifest timestamp
    manifest["last_updated"] = now_iso
    if skill in manifest.get("skills", {}):
        manifest["skills"][skill]["last_modified"] = today
    save_manifest(manifest)

    # Append to JSONL audit log
    audit_entry = {
        "timestamp": now_iso,
        "skill": skill,
        "type": change_type,
        "message": message,
        "author": author,
    }
    append_audit_log(audit_entry)

    print(f"✅ Successfully logged '{change_type}' for '{skill}' in CHANGELOG.md and audit log.")


def release_version(version):
    today = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now().isoformat()

    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    unreleased_pattern = r"## \[Unreleased\]\s*\n(.*?)(?=\n## \[|\Z)"
    match = re.search(unreleased_pattern, content, re.DOTALL)
    if not match:
        sys.stderr.write("Could not find [Unreleased] block in CHANGELOG.md\n")
        sys.exit(1)

    unreleased_body = match.group(1).strip()
    if not unreleased_body:
        print("Notice: No unreleased changes found to release.")

    # Format new release block
    new_release_header = f"## [{version}] - {today}\n\n{unreleased_body}\n\n---\n\n"
    fresh_unreleased = "## [Unreleased]\n\n### Added\n- \n\n---\n\n"

    # Replace [Unreleased] block
    full_unreleased_block = match.group(0)
    new_content = content.replace(full_unreleased_block, f"## [Unreleased]\n\n---\n\n## [{version}] - {today}\n\n{unreleased_body}\n\n")

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    manifest = load_manifest()
    manifest["version"] = version
    manifest["last_released"] = today
    manifest["last_updated"] = now_iso
    save_manifest(manifest)

    print(f"🎉 Released version [{version}] on {today} in CHANGELOG.md and skills_manifest.json!")


def main():
    parser = argparse.ArgumentParser(description="Log changes and version releases for To-Fusion Skill Sets.")
    parser.add_argument("--skill", help="Name of the skill modified (e.g. '3mf-to-fusion', 'media-to-fusion', 'text-to-fusion', 'rules')")
    parser.add_argument("--type", choices=VALID_TYPES, help="Category of change (added, changed, fixed, etc.)")
    parser.add_argument("--message", help="Clear, concise description of what changed and why")
    parser.add_argument("--author", default="Kamish", help="Author of the change")
    parser.add_argument("--release", help="Bump to new version (e.g. '1.1.0')")

    args = parser.parse_args()

    if args.release:
        release_version(args.release)
    elif args.skill and args.type and args.message:
        log_change(args.skill, args.type, args.message, args.author)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
