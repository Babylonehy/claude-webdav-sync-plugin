# WebDAV Sync Plugin for Claude Code

Synchronize your Claude Code configuration and history across multiple machines via WebDAV.

## Features

- **Configuration Sync**: Sync `~/.claude.json`, settings, and OpenCode config
- **History Sync**: Sync conversation history and project sessions
- **Manual Commands**: `push` and `pull` with conflict detection
- **Auto-Sync**: Optional sync on Claude Code startup/shutdown
- **Conflict Resolution**: Interactive prompts with diff viewing

## Installation

### From Source

```bash
git clone https://github.com/yourusername/claude-webdav-sync-plugin.git
cd claude-webdav-sync-plugin
pip install -e ".[dev]"
```

### For Claude Code

1. Clone the repository
2. Run the install script:
```bash
./scripts/install.sh
```

## Configuration

```bash
# Interactive configuration
webdav-sync configure

# Or with options
webdav-sync configure \
  --url https://your-webdav-server.com/dav \
  --username your-username \
  --sync-on-startup \
  --sync-on-shutdown
```

## Usage

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