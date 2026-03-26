---
description: "Push local Claude Code data to WebDAV server"
---

Push your local Claude Code configuration and history to the configured WebDAV server.

## Usage

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py push [--force]
```

## Options

- `--force, -f`: Force push without conflict checking

## What Gets Pushed

- `~/.claude.json` - Main user settings
- `~/.claude/settings.json` - Project-level settings  
- `~/.claude/config.json` - API key configuration
- `~/.config/opencode/opencode.json` - OpenCode configuration
- `~/.claude/history.jsonl` - Conversation history
- `~/.claude/projects/*/` - Project session history

## Example

```bash
# Normal push (with conflict detection)
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py push

# Force push (overwrite remote)
python ${CLAUDE_PLUGIN_ROOT}/scripts/webdav_sync.py push --force
```