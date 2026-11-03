#!/usr/bin/env python3
"""
tools/export_for_claude.py - Export To-Fusion skills & rules for Claude Code & Claude Desktop

Usage:
    # Print Claude Desktop MCP configuration:
    python3 tools/export_for_claude.py --mcp-config

    # Export skills & rules for Claude Code in current directory:
    python3 tools/export_for_claude.py --claude-code

    # Export skills globally for Claude Code (~/.claude/skills):
    python3 tools/export_for_claude.py --global-claude
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
RULES_DIR = REPO_ROOT / "rules"


def print_mcp_config():
    """Outputs the Claude Desktop configuration block for Fusion 360 MCP."""
    cfg = {
        "mcpServers": {
            "fusion-mcp": {
                "command": "python3",
                "args": [
                    str(Path.home() / ".gemini" / "antigravity" / "mcp" / "fusion-mcp" / "server.py")
                ],
                "env": {
                    "FUSION_API_PORT": "12345"
                }
            }
        }
    }
    print("\n=== Claude Desktop Configuration (`claude_desktop_config.json`) ===")
    print("Add this entry under 'mcpServers' in your Claude Desktop configuration:")
    print(json.dumps(cfg, indent=2))
    print("===================================================================\n")


def export_claude_code(target_dir):
    target_path = Path(target_dir).resolve()
    target_skills = target_path / ".claude" / "skills"
    os.makedirs(target_skills, exist_ok=True)

    # Copy / symlink skills
    for skill_name in ["3mf-to-fusion", "media-to-fusion", "text-to-fusion"]:
        src = SKILLS_DIR / skill_name
        dest = target_skills / skill_name
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink():
                dest.unlink()
            else:
                shutil.rmtree(dest)
        dest.symlink_to(src, target_is_directory=True)
        print(f"🔗 Linked skill '{skill_name}' -> {dest}")

    # Copy CLAUDE.md to project root
    dest_claude_md = target_path / "CLAUDE.md"
    shutil.copy2(RULES_DIR / "CLAUDE.md", dest_claude_md)
    print(f"📄 Copied rules to {dest_claude_md}")
    print(f"✅ Claude Code setup complete at {target_path}!")


def export_global_claude():
    user_home = Path.home()
    target_skills = user_home / ".claude" / "skills"
    os.makedirs(target_skills, exist_ok=True)

    for skill_name in ["3mf-to-fusion", "media-to-fusion", "text-to-fusion"]:
        src = SKILLS_DIR / skill_name
        dest = target_skills / skill_name
        if dest.exists() or dest.is_symlink():
            if dest.is_symlink():
                dest.unlink()
            else:
                shutil.rmtree(dest)
        dest.symlink_to(src, target_is_directory=True)
        print(f"🔗 Linked global skill '{skill_name}' -> {dest}")

    print(f"✅ Global Claude skills installed in {target_skills}!")


def main():
    parser = argparse.ArgumentParser(description="Export skills & rules for Claude Code and Claude Desktop.")
    parser.add_argument("--mcp-config", action="store_true", help="Print Claude Desktop MCP configuration")
    parser.add_argument("--claude-code", metavar="DIR", nargs="?", const=".", help="Setup Claude Code in target project directory (default: .)")
    parser.add_argument("--global-claude", action="store_true", help="Install skills globally to ~/.claude/skills")

    args = parser.parse_args()

    if args.mcp-config if hasattr(args, "mcp-config") else False:
        pass
    if args.mcp_config:
        print_mcp_config()
    elif args.global_claude:
        export_global_claude()
    elif args.claude_code:
        export_claude_code(args.claude_code)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
