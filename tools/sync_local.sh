#!/usr/bin/env bash
set -e

# Syncs To-Fusion skills to local Antigravity environment via symlinks
# Ensuring local Antigravity always uses the live tracked repository code.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
AGY_SKILLS_DIR="$HOME/.gemini/antigravity/skills"
CONFIG_SKILLS_DIR="$HOME/.gemini/config/skills"

echo "🔄 Linking To-Fusion skills to Antigravity environment..."

mkdir -p "$AGY_SKILLS_DIR"
mkdir -p "$CONFIG_SKILLS_DIR"

SKILLS=("3mf-to-fusion" "media-to-fusion" "text-to-fusion")

for skill in "${SKILLS[@]}"; do
    SRC="$SKILLS_DIR/$skill"
    AGY_TARGET="$AGY_SKILLS_DIR/$skill"
    CONFIG_TARGET="$CONFIG_SKILLS_DIR/$skill"

    echo "📦 Processing $skill..."

    # If it exists and is a directory (not a symlink), backup first
    if [ -d "$AGY_TARGET" ] && [ ! -L "$AGY_TARGET" ]; then
        BACKUP_DIR="${AGY_TARGET}_backup_$(date +%Y%m%d_%H%M%S)"
        echo "   Backing up existing directory to $BACKUP_DIR"
        mv "$AGY_TARGET" "$BACKUP_DIR"
    elif [ -L "$AGY_TARGET" ]; then
        rm "$AGY_TARGET"
    fi

    # Create symlink in ~/.gemini/antigravity/skills/
    ln -s "$SRC" "$AGY_TARGET"
    echo "   ✅ Symlinked $AGY_TARGET -> $SRC"

    # Ensure ~/.gemini/config/skills/ also points to it
    if [ -L "$CONFIG_TARGET" ] || [ -e "$CONFIG_TARGET" ]; then
        rm -rf "$CONFIG_TARGET"
    fi
    ln -s "$AGY_TARGET" "$CONFIG_TARGET"
    echo "   ✅ Symlinked $CONFIG_TARGET -> $AGY_TARGET"
done

echo "🎉 All To-Fusion skills are now live-linked to Antigravity!"
