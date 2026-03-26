---
description: "Pull Claude Code data from WebDAV server"
---

Pull Claude Code configuration and history from the configured WebDAV server to your local machine.

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py pull [--force]
```

## Options

- `--force, -f`: Force pull without conflict checking

## Example

```bash
# Normal pull (with conflict detection)
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py pull

# Force pull (overwrite local)
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py pull --force
```