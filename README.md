# WebDAV Sync Plugin for Claude Code

Synchronize your Claude Code configuration and history across multiple machines via WebDAV.

## Features

- **Configuration Sync**: Sync `~/.claude.json`, settings, and OpenCode config
- **History Sync**: Sync conversation history and project sessions
- **Manual Commands**: `push` and `pull` with conflict detection
- **Auto-Sync**: Optional sync on Claude Code startup/shutdown
- **Conflict Resolution**: Interactive prompts with diff viewing

## Installation

### Method 1: Install from GitHub (Recommended)

```bash
# In Claude Code, run:
claude /plugins install Babylonehy/claude-webdav-sync-plugin
```

### Method 2: Local Installation

```bash
# Clone the repository
git clone https://github.com/Babylonehy/claude-webdav-sync-plugin.git
cd claude-webdav-sync-plugin

# Run the install script
chmod +x scripts/install.sh
./scripts/install.sh
```

This will:
1. Copy plugin files to `~/.claude/plugins/cache/webdav-sync-marketplace/`
2. Register the plugin in Claude Code's plugin system
3. Install Python dependencies

### Method 3: Manual Installation

```bash
git clone https://github.com/Babylonehy/claude-webdav-sync-plugin.git
cd claude-webdav-sync-plugin
pip install webdavclient3 pyyaml click python-dateutil
```

## Configuration

After installation, configure the WebDAV connection:

```bash
# Using installed plugin
python3 ~/.claude/plugins/cache/webdav-sync-marketplace/webdav-sync/1.0.0/scripts/webdav_sync.py configure

# Or if installed manually
python3 scripts/webdav_sync.py configure
```

Interactive configuration will prompt for:
- WebDAV server URL
- Username
- Password
- Auto-sync options

## Usage

After installation, use the plugin:

```bash
# Set alias for convenience (add to ~/.bashrc or ~/.zshrc)
alias webdav-sync='python3 ~/.claude/plugins/cache/webdav-sync-marketplace/webdav-sync/1.0.0/scripts/webdav_sync.py'

# Then use:
webdav-sync status
webdav-sync push
webdav-sync pull
```

### Manual Sync

```bash
# Push local data to WebDAV
webdav-sync push

# Pull data from WebDAV
webdav-sync pull

# Force sync (skip conflict detection)
webdav-sync push --force
webdav-sync pull --force
```

### Check Status

```bash
webdav-sync status
```

### Auto-Sync

Enable auto-sync during configuration:
```bash
webdav-sync configure --sync-on-startup --sync-on-shutdown
```

## What Gets Synced

### Always Synced
| Path | Description |
|------|-------------|
| `~/.claude.json` | Main user settings, project configs |
| `~/.claude/settings.json` | Project-level settings |
| `~/.claude/config.json` | API key configuration |
| `~/.config/opencode/opencode.json` | OpenCode configuration |

### History
| Path | Description |
|------|-------------|
| `~/.claude/history.jsonl` | Conversation history |
| `~/.claude/projects/*/` | Project session files |

### Not Synced
- Plugin cache
- Telemetry data
- Shell snapshots
- Debug logs

## Conflict Resolution

When a conflict is detected:

- **[L] Keep Local** - Overwrite remote with local
- **[R] Keep Remote** - Overwrite local with remote
- **[B] Keep Both** - Rename local with timestamp
- **[S] Skip** - Skip this file
- **[A] Abort** - Abort sync
- **[D] Show Diff** - View differences

## Configuration File

Stored at: `~/.claude/plugins/data/webdav-sync/config.yaml`

```yaml
webdav_url: https://your-webdav-server.com/dav
username: your-username
password: your-password
auto_sync: false
sync_on_startup: false
sync_on_shutdown: false
exclude_patterns:
  - telemetry/*
  - debug/*
  - shell-snapshots/*
  - statsig/*
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Running All Tests with Coverage

```bash
pytest tests/ -v --cov=src/webdav_sync --cov-report=html
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Uninstallation

```bash
# Remove plugin files
rm -rf ~/.claude/plugins/cache/webdav-sync-marketplace
rm -rf ~/.claude/plugins/marketplaces/webdav-sync-marketplace
rm -rf ~/.claude/plugins/data/webdav-sync

# Remove from installed_plugins.json (edit manually or run):
python3 -c "
import json
f = '$HOME/.claude/plugins/installed_plugins.json'
with open(f) as fp: d = json.load(fp)
d['plugins'].pop('webdav-sync@webdav-sync-marketplace', None)
with open(f, 'w') as fp: json.dump(d, fp, indent=2)
"
```