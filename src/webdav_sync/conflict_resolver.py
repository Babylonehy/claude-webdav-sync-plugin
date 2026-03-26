"""Conflict detection and resolution for sync operations."""

import difflib
import os
import tempfile
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Optional, List, Tuple, Callable
from dataclasses import dataclass

from .webdav_client import WebDAVClient


class ConflictAction(Enum):
    """Actions to resolve conflicts."""

    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"
    KEEP_BOTH = "keep_both"
    SKIP = "skip"
    ABORT = "abort"


@dataclass
class ConflictInfo:
    """Information about a file conflict."""

    local_path: Path
    remote_path: str
    local_modified: datetime
    remote_modified: datetime
    local_size: int
    remote_size: int


def get_file_diff(
    local_content: str, remote_content: str, filename: str = "file"
) -> str:
    """Generate unified diff between two file contents."""
    diff = difflib.unified_diff(
        remote_content.splitlines(keepends=True),
        local_content.splitlines(keepends=True),
        fromfile=f"remote/{filename}",
        tofile=f"local/{filename}",
    )
    return "".join(diff)


class ConflictResolver:
    """Detects and resolves sync conflicts."""

    def __init__(self, webdav_client: WebDAVClient, prompt_func: Callable = None):
        self.client = webdav_client
        self.prompt_func = prompt_func or self._default_prompt

    def detect_conflict(
        self, local_path: Path, remote_path: str
    ) -> Optional[ConflictInfo]:
        """Detect if there's a conflict between local and remote files."""
        remote_info = self.client.get_remote_file_info(remote_path)
        if not remote_info:
            return None

        if not local_path.exists():
            return None

        local_stat = local_path.stat()
        local_modified = datetime.fromtimestamp(local_stat.st_mtime)

        try:
            remote_modified = datetime.strptime(
                remote_info["modified"], "%a, %d %b %Y %H:%M:%S %Z"
            )
        except (ValueError, TypeError):
            remote_modified = datetime.min

        local_size = local_stat.st_size
        remote_size = remote_info["size"]

        if local_size == remote_size and local_modified == remote_modified:
            return None

        return ConflictInfo(
            local_path=local_path,
            remote_path=remote_path,
            local_modified=local_modified,
            remote_modified=remote_modified,
            local_size=local_size,
            remote_size=remote_size,
        )

    def resolve(
        self, conflict: ConflictInfo, force_action: ConflictAction = None
    ) -> ConflictAction:
        """Resolve a conflict by prompting user or using force_action."""
        if force_action:
            return force_action
        return self.prompt_func(conflict)

    def _default_prompt(self, conflict: ConflictInfo) -> ConflictAction:
        """Default interactive prompt for conflict resolution."""
        print(f"\n{'=' * 60}")
        print(f"CONFLICT DETECTED: {conflict.local_path}")
        print(f"{'=' * 60}")
        print(
            f"  Local:  {conflict.local_modified.strftime('%Y-%m-%d %H:%M:%S')} ({conflict.local_size} bytes)"
        )
        print(
            f"  Remote: {conflict.remote_modified.strftime('%Y-%m-%d %H:%M:%S')} ({conflict.remote_size} bytes)"
        )
        print(f"{'=' * 60}")

        while True:
            print("\nChoose an action:")
            print("  [L] Keep Local (overwrite remote)")
            print("  [R] Keep Remote (overwrite local)")
            print("  [B] Keep Both (rename local with timestamp)")
            print("  [S] Skip this file")
            print("  [A] Abort sync")
            print("  [D] Show diff")

            choice = input("\nYour choice [L/R/B/S/A/D]: ").strip().upper()

            if choice == "L":
                return ConflictAction.KEEP_LOCAL
            elif choice == "R":
                return ConflictAction.KEEP_REMOTE
            elif choice == "B":
                return ConflictAction.KEEP_BOTH
            elif choice == "S":
                return ConflictAction.SKIP
            elif choice == "A":
                return ConflictAction.ABORT
            elif choice == "D":
                self._show_diff(conflict)
            else:
                print("Invalid choice. Please try again.")

    def _show_diff(self, conflict: ConflictInfo) -> None:
        """Show diff between local and remote file."""
        remote_content = self._download_remote_to_temp(conflict.remote_path)
        if remote_content is None:
            print("Could not fetch remote content for diff.")
            return

        try:
            with open(conflict.local_path, "r") as f:
                local_content = f.read()
            diff = get_file_diff(
                local_content, remote_content, conflict.local_path.name
            )
            print(f"\n--- DIFF ---\n{diff}\n--- END DIFF ---\n")
        except Exception as e:
            print(f"Error generating diff: {e}")

    def _download_remote_to_temp(self, remote_path: str) -> Optional[str]:
        """Download remote file to temp and return content."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+", delete=False, suffix=".tmp"
            ) as tmp:
                tmp_path = tmp.name
            self.client.download_file(remote_path, Path(tmp_path))
            with open(tmp_path, "r") as f:
                content = f.read()
            os.unlink(tmp_path)
            return content
        except Exception:
            return None
