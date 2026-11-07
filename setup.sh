#!/usr/bin/env bash
set -e

# ==============================================================================
# To-Fusion-Skill-Sets: Autonomous Fusion 360 CAD Setup Script
# Works on macOS and Linux. Supports Antigravity, Claude Code, and standalone.
# ==============================================================================

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "=========================================================="
echo "  🚀 Installing To-Fusion Skill Sets & Rulesets"
echo "=========================================================="

# 1. Check Python version (>= 3.10 required)
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH."
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo "❌ Error: Python 3.10 or higher is required. Found Python $PY_VERSION."
    exit 1
fi
echo "✅ Python $PY_VERSION detected."

# 2. Virtual Environment Setup
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment (.venv)..."
    if command -v uv &>/dev/null; then
        uv venv .venv --python python3
    else
        python3 -m venv .venv
    fi
fi

# Activate venv
source .venv/bin/activate

# 3. Install dependencies
echo "📥 Installing dependencies from requirements.txt..."
if command -v uv &>/dev/null; then
    uv pip install -r requirements.txt
else
    pip install --upgrade pip
    pip install -r requirements.txt
fi
echo "✅ Python dependencies installed."

# 4. Make scripts executable
chmod +x skills/3mf-to-fusion/scripts/*.py 2>/dev/null || true
chmod +x skills/media-to-fusion/scripts/*.py 2>/dev/null || true
chmod +x skills/text-to-fusion/scripts/*.py 2>/dev/null || true
chmod +x tools/*.py tools/*.sh 2>/dev/null || true

# 5. Antigravity Linking
if [ -d "$HOME/.gemini" ]; then
    echo ""
    echo "🤖 Antigravity environment detected."
    read -p "   Do you want to link skills to ~/.gemini/antigravity/skills? [Y/n] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        bash tools/sync_local.sh
    fi
fi

# 6. Claude Code Integration
if command -v claude &>/dev/null || [ -d "$HOME/.claude" ]; then
    echo ""
    echo "🧠 Claude environment detected."
    read -p "   Do you want to install skills globally for Claude Code (~/.claude/skills)? [Y/n] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        python3 tools/export_for_claude.py --global-claude
    fi
fi

echo ""
echo "=========================================================="
echo "  🎉 Setup Complete!"
echo "  Skills available:"
echo "    - 3mf-to-fusion        (Mesh reverse-engineering & tier classification)"
echo "    - media-to-fusion      (Vision metrology & kinematic synthesis)"
echo "    - text-to-fusion       (Natural language to parametric assemblies)"
echo "    - to-fusion-sync       (Repository & agent runtime synchronization)"
echo "    - to-fusion-dev-sync   (Dedicated dev branch & beta skill synchronization)"
echo ""
echo "  To check sync status:        python3 tools/sync_manager.py status"
echo "  To push dev work to laptop:  python3 tools/sync_manager.py dev-push"
echo "  To record changes to skills: python3 tools/log_change.py"
echo "  To view Claude MCP config:   python3 tools/export_for_claude.py --mcp-config"
echo "=========================================================="
