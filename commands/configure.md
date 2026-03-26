---
description: "Configure WebDAV connection settings"
---

Configure your WebDAV server connection for syncing Claude Code data.

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py configure [OPTIONS]
```

## Options

- `--url`: WebDAV server URL
- `--username`: WebDAV username
- `--password`: WebDAV password (will be prompted if not provided)
- `--auto-sync`: Enable automatic sync
- `--sync-on-startup`: Sync when Claude Code starts
- `--sync-on-shutdown`: Sync when Claude Code exits

## Example

```bash
# Interactive configuration
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py configure

# Non-interactive configuration
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py configure \
  --url https://webdav.example.com/dav \
  --username myuser \
  --sync-on-startup \
  --sync-on-shutdown
```