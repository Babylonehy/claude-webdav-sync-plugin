#!/bin/bash
set -e

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing WebDAV Sync Plugin..."

pip install -r "$PLUGIN_ROOT/scripts/requirements.txt" -q

echo "Installation complete!"
echo ""
echo "To configure, run:"
echo "  python $PLUGIN_ROOT/scripts/webdav_sync.py configure"