# Claude WebDAV Sync Plugin

WebDAV sync plugin for Claude Code - enables automatic backup and synchronization of Claude conversation data to WebDAV servers.

## Installation

```bash
pip install claude-webdav-sync
```

## Usage

```bash
webdav-sync --help
```

## Configuration

Create a configuration file at `~/.config/webdav-sync/config.yaml`:

```yaml
webdav:
  url: https://your-webdav-server.com/dav
  username: your-username
  password: your-password
  
sync:
  local_dir: ~/.claude/conversations
  remote_dir: /claude-backups
```

## License

MIT License - see LICENSE file for details.