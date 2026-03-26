"""Core sync logic for WebDAV sync plugin."""

import fnmatch
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable
from dataclasses import dataclass, field

from .config import WebDAVConfig, SyncPaths
from .webdav_client import WebDAVClient
from .conflict_resolver import ConflictResolver, ConflictAction


@dataclass
class SyncResult:
    """Result of a sync operation."""

    pushed: int = 0
    pulled: int = 0
    skipped: int = 0
    conflicts: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        return f"SyncResult(pushed={self.pushed}, pulled={self.pulled}, skipped={self.skipped}, errors={len(self.errors)})"


class SyncManager:
    """Manages synchronization between local and remote."""

    SYNC_STATE_FILE = (
        Path.home() / ".claude" / "plugins" / "data" / "webdav-sync" / "sync_state.json"
    )

    def __init__(self, config: WebDAVConfig, prompt_func: Callable = None):
        self.config = config
        self.client = WebDAVClient(config)
        self.resolver = ConflictResolver(self.client, prompt_func)
        self.paths = SyncPaths()

    def push(self, force: bool = False) -> SyncResult:
        """Push local files to WebDAV server."""
        result = SyncResult()

        if not self.client.test_connection():
            result.errors.append("Cannot connect to WebDAV server")
            return result

        sync_paths = self.paths.get_all_sync_paths()

        for local_path in sync_paths:
            if not local_path.exists():
                continue

            if self._should_exclude(local_path):
                result.skipped += 1
                continue

            remote_path = self.client.get_remote_path_for_local(local_path)

            if not force:
                conflict = self.resolver.detect_conflict(local_path, remote_path)
                if conflict:
                    action = self.resolver.resolve(conflict)
                    result.conflicts += 1
                    if action == ConflictAction.KEEP_REMOTE:
                        result.skipped += 1
                        continue
                    elif action == ConflictAction.SKIP:
                        result.skipped += 1
                        continue
                    elif action == ConflictAction.ABORT:
                        result.errors.append("Sync aborted by user")
                        return result

            success = self.client.upload_file(local_path, remote_path)
            if success:
                result.pushed += 1
            else:
                result.errors.append(f"Failed to push {local_path}")

        self._save_sync_state("push")
        return result

    def pull(self, force: bool = False) -> SyncResult:
        """Pull files from WebDAV server."""
        result = SyncResult()

        if not self.client.test_connection():
            result.errors.append("Cannot connect to WebDAV server")
            return result

        remote_files = self.client.list_remote_files()

        for remote_info in remote_files:
            remote_path = remote_info["path"]
            local_path = self.client.get_local_path_for_remote(remote_path)

            if self._should_exclude(local_path):
                result.skipped += 1
                continue

            if not force and local_path.exists():
                conflict = self.resolver.detect_conflict(local_path, remote_path)
                if conflict:
                    action = self.resolver.resolve(conflict)
                    result.conflicts += 1
                    if action == ConflictAction.KEEP_LOCAL:
                        result.skipped += 1
                        continue
                    elif action == ConflictAction.KEEP_BOTH:
                        self._backup_local(local_path)
                    elif action == ConflictAction.SKIP:
                        result.skipped += 1
                        continue
                    elif action == ConflictAction.ABORT:
                        result.errors.append("Sync aborted by user")
                        return result

            success = self.client.download_file(remote_path, local_path)
            if success:
                result.pulled += 1
            else:
                result.errors.append(f"Failed to pull {remote_path}")

        self._save_sync_state("pull")
        return result

    def status(self) -> dict:
        """Get current sync status."""
        state = self._load_sync_state()
        return {
            "last_sync": state.get("last_sync"),
            "last_action": state.get("last_action"),
            "configured": self.config.is_configured(),
            "connected": self.client.test_connection()
            if self.config.is_configured()
            else False,
        }

    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded from sync."""
        path_str = str(path)
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(path_str, pattern) or pattern in path_str:
                return True
        return False

    def _backup_local(self, local_path: Path) -> None:
        """Create backup of local file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = local_path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(local_path, backup_path)
        print(f"Backup created: {backup_path}")

    def _save_sync_state(self, action: str) -> None:
        """Save sync state to file."""
        self.SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_sync": datetime.now().isoformat(),
            "last_action": action,
        }
        with open(self.SYNC_STATE_FILE, "w") as f:
            json.dump(state, f)

    def _load_sync_state(self) -> dict:
        """Load sync state from file."""
        if self.SYNC_STATE_FILE.exists():
            with open(self.SYNC_STATE_FILE, "r") as f:
                return json.load(f)
        return {}
