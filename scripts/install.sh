#!/bin/bash
# WebDAV Sync Plugin Installation Script for Claude Code
# This script installs the plugin following Claude Code's plugin installation standards

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_NAME="webdav-sync"
MARKETPLACE_NAME="webdav-sync-marketplace"
VERSION="1.0.0"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== WebDAV Sync Plugin Installer ===${NC}"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

CLAUDE_PLUGINS_DIR="$HOME/.claude/plugins"
CACHE_DIR="$CLAUDE_PLUGINS_DIR/cache/$MARKETPLACE_NAME/$PLUGIN_NAME/$VERSION"
DATA_DIR="$CLAUDE_PLUGINS_DIR/data/$PLUGIN_NAME"

echo "Installation paths:"
echo "  Plugin cache: $CACHE_DIR"
echo "  Plugin data:  $DATA_DIR"
echo ""

echo "Creating directories..."
mkdir -p "$CACHE_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$CLAUDE_PLUGINS_DIR/marketplaces/$MARKETPLACE_NAME"

echo "Copying plugin files..."
cp -r "$PLUGIN_ROOT/.claude-plugin" "$CACHE_DIR/"
cp -r "$PLUGIN_ROOT/commands" "$CACHE_DIR/"
cp -r "$PLUGIN_ROOT/hooks" "$CACHE_DIR/"
cp -r "$PLUGIN_ROOT/scripts" "$CACHE_DIR/"
cp -r "$PLUGIN_ROOT/src" "$CACHE_DIR/"
cp "$PLUGIN_ROOT/pyproject.toml" "$CACHE_DIR/"
cp "$PLUGIN_ROOT/setup.py" "$CACHE_DIR/"
cp "$PLUGIN_ROOT/pytest.ini" "$CACHE_DIR/"
cp "$PLUGIN_ROOT/README.md" "$CACHE_DIR/"
cp "$PLUGIN_ROOT/LICENSE" "$CACHE_DIR/"
cp "$PLUGIN_ROOT/.gitignore" "$CACHE_DIR/"

ln -sf "$CACHE_DIR" "$CLAUDE_PLUGINS_DIR/marketplaces/$MARKETPLACE_NAME/$PLUGIN_NAME"

echo "Installing Python dependencies..."
pip3 install -q webdavclient3 pyyaml click python-dateutil 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not install some dependencies. Run: pip3 install webdavclient3 pyyaml click python-dateutil${NC}"
}

echo "Registering plugin..."
python3 << 'EOF'
import json
import os
from datetime import datetime

plugins_file = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
plugin_key = "webdav-sync@webdav-sync-marketplace"
install_path = os.path.expanduser("~/.claude/plugins/cache/webdav-sync-marketplace/webdav-sync/1.0.0")

if os.path.exists(plugins_file):
    with open(plugins_file, "r") as f:
        data = json.load(f)
else:
    data = {"version": 2, "plugins": {}}

data["plugins"][plugin_key] = [{
    "scope": "user",
    "installPath": install_path,
    "version": "1.0.0",
    "installedAt": datetime.now().isoformat() + "Z",
    "lastUpdated": datetime.now().isoformat() + "Z"
}]

os.makedirs(os.path.dirname(plugins_file), exist_ok=True)
with open(plugins_file, "w") as f:
    json.dump(data, f, indent=2)
EOF

python3 << 'EOF'
import json
import os
from datetime import datetime

marketplaces_file = os.path.expanduser("~/.claude/plugins/known_marketplaces.json")
marketplace_name = "webdav-sync-marketplace"
marketplace_path = os.path.expanduser("~/.claude/plugins/marketplaces/webdav-sync-marketplace")

if os.path.exists(marketplaces_file):
    with open(marketplaces_file, "r") as f:
        data = json.load(f)
else:
    data = {}

data[marketplace_name] = {
    "source": {
        "source": "local",
        "path": os.path.expanduser("~/claude-webdav-sync-plugin")
    },
    "installLocation": marketplace_path,
    "lastUpdated": datetime.now().isoformat() + "Z"
}

os.makedirs(os.path.dirname(marketplaces_file), exist_ok=True)
with open(marketplaces_file, "w") as f:
    json.dump(data, f, indent=2)
EOF

echo ""
echo -e "${GREEN}=== Installation Complete! ===${NC}"
echo ""
echo "To configure:"
echo "  python3 $CACHE_DIR/scripts/webdav_sync.py configure"
echo ""
echo "To check status:"
echo "  python3 $CACHE_DIR/scripts/webdav_sync.py status"
echo ""
echo "To uninstall:"
echo "  rm -rf ~/.claude/plugins/cache/webdav-sync-marketplace"
echo "  rm -rf ~/.claude/plugins/marketplaces/webdav-sync-marketplace"
echo ""