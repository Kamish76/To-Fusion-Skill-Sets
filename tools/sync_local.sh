#!/usr/bin/env bash
set -e

# Syncs To-Fusion skills to local Antigravity & Claude environment via symlinks
# Ensuring local AI agents always use live tracked repository code.
# Dynamically discovers all skills under skills/ (both registered and beta).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Check if Python is available to run universal sync manager
if command -v python3 &>/dev/null; then
    python3 tools/sync_manager.py link
    exit 0
elif command -v python &>/dev/null; then
    python tools/sync_manager.py link
    exit 0
fi

echo "🔄 Linking To-Fusion skills to Antigravity environment (Bash fallback)..."

SKILLS_DIR="$REPO_ROOT/skills"
AGY_SKILLS_DIR="$HOME/.gemini/antigravity/skills"
CONFIG_SKILLS_DIR="$HOME/.gemini/config/skills"

mkdir -p "$AGY_SKILLS_DIR"
mkdir -p "$CONFIG_SKILLS_DIR"

# Dynamically discover all directories under skills/ containing SKILL.md
for skill_path in "$SKILLS_DIR"/*; do
    if [ -d "$skill_path" ] && [ -f "$skill_path/SKILL.md" ]; then
        skill="$(basename "$skill_path")"
        SRC="$skill_path"
        AGY_TARGET="$AGY_SKILLS_DIR/$skill"
        CONFIG_TARGET="$CONFIG_SKILLS_DIR/$skill"

        echo "📦 Processing $skill..."

        # Backup real directory if it exists and is not a symlink
        if [ -d "$AGY_TARGET" ] && [ ! -L "$AGY_TARGET" ]; then
            BACKUP_DIR="${AGY_TARGET}_backup_$(date +%Y%m%d_%H%M%S)"
            echo "   Backing up existing directory to $BACKUP_DIR"
            mv "$AGY_TARGET" "$BACKUP_DIR"
        elif [ -L "$AGY_TARGET" ]; then
            rm "$AGY_TARGET"
        fi

        ln -s "$SRC" "$AGY_TARGET"
        echo "   ✅ Symlinked $AGY_TARGET -> $SRC"

        if [ -L "$CONFIG_TARGET" ] || [ -e "$CONFIG_TARGET" ]; then
            rm -rf "$CONFIG_TARGET"
        fi
        ln -s "$AGY_TARGET" "$CONFIG_TARGET"
        echo "   ✅ Symlinked $CONFIG_TARGET -> $AGY_TARGET"
    fi
done

echo "🎉 All To-Fusion skills are dynamically linked to Antigravity!"
