# WebDAV Sync Plugin for Claude Code

Synchronize your Claude Code configuration and history across multiple machines via WebDAV.

## Features

- **Archive-based sync**: All files are packed into a single `tar.gz` before transfer — efficient and reliable
- **Integrity verification**: SHA-256 checksums on every file and the archive itself
- **Smart diff**: Only extracts files that actually changed on pull
- **坚果云 / Jianguoyun support**: Built-in preset, handles all known WebDAV quirks
- **Auto-Sync**: Optional sync on Claude Code startup/shutdown

## How It Works

```
Push: local files → tar.gz + manifest.json → WebDAV
Pull: WebDAV → verify sha256 → extract only changed files → local
```

Remote layout:
```
/claude-code-sync/
  claude-sync.tar.gz        # all synced files packed
  claude-sync.manifest.json # per-file sha256 + archive sha256
```

## Installation

### Method 1: Install from GitHub (Recommended)

```bash
# In Claude Code, run:
claude /plugins install Babylonehy/claude-webdav-sync-plugin
```

### Method 2: Local Installation

```bash
git clone https://github.com/Babylonehy/claude-webdav-sync-plugin.git
cd claude-webdav-sync-plugin
chmod +x scripts/install.sh
./scripts/install.sh
```

### Method 3: Manual

```bash
git clone https://github.com/Babylonehy/claude-webdav-sync-plugin.git
cd claude-webdav-sync-plugin
pip install webdavclient3 pyyaml click python-dateutil
```

## Configuration

### Generic WebDAV

```bash
webdav-sync configure
```

Prompts for URL, username, and password.

### 坚果云 (Jianguoyun)

```bash
webdav-sync configure --preset jianguoyun
```

Automatically sets the URL to `https://dav.jianguoyun.com/dav/` and prompts for:
- **Username**: your 坚果云 account email
- **Password**: an **app-specific password** (not your login password)

Create an app password at: <https://www.jianguoyun.com/d/account#security>

## Usage

```bash
# Set alias (add to ~/.bashrc or ~/.zshrc)
alias webdav-sync='python3 ~/.claude/plugins/cache/webdav-sync-marketplace/webdav-sync/1.0.0/scripts/webdav_sync.py'
```

### Sync

```bash
webdav-sync push           # pack and upload (skips if nothing changed)
webdav-sync pull           # download and extract changed files only
webdav-sync push --force   # always re-upload
webdav-sync pull --force   # extract all files unconditionally
webdav-sync status         # show connection and last sync time
```

### Auto-Sync

```bash
webdav-sync configure --sync-on-startup --sync-on-shutdown
```

## What Gets Synced

| Path | Description |
|------|-------------|
| `~/.claude.json` | Main user settings |
| `~/.claude/settings.json` | Project-level settings |
| `~/.claude/config.json` | API key configuration |
| `~/.config/opencode/opencode.json` | OpenCode configuration |
| `~/.claude/history.jsonl` | Conversation history |
| `~/.claude/projects/*/` | Project session files |

Not synced: plugin cache, telemetry, shell snapshots, debug logs.

## Configuration File

Stored at `~/.claude/plugins/data/webdav-sync/config.yaml`:

```yaml
webdav_url: https://your-webdav-server.com/dav
username: your-username
password: your-password
provider: generic          # or: jianguoyun
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

```bash
pip install -e ".[dev]"
pytest tests/ -v
pytest tests/ -v --cov=src/webdav_sync --cov-report=html
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Uninstallation

```bash
rm -rf ~/.claude/plugins/cache/webdav-sync-marketplace
rm -rf ~/.claude/plugins/marketplaces/webdav-sync-marketplace
rm -rf ~/.claude/plugins/data/webdav-sync
```
