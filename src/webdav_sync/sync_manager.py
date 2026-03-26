"""Core sync logic for WebDAV sync plugin — archive-based approach."""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Callable
from dataclasses import dataclass, field

from .config import WebDAVConfig, SyncPaths
from .webdav_client import WebDAVClient
from .archiver import (
    build_manifest,
    create_archive,
    extract_archive,
    diff_manifests,
    manifests_equal,
    sha256_bytes,
    sha256_file,
    MANIFEST_FILENAME,
    ARCHIVE_FILENAME,
)


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
        return (
            f"SyncResult(pushed={self.pushed}, pulled={self.pulled}, "
            f"skipped={self.skipped}, errors={len(self.errors)})"
        )


class SyncManager:
    """Manages synchronization between local and remote via single archive."""

    SYNC_STATE_FILE = (
        Path.home() / ".claude" / "plugins" / "data" / "webdav-sync" / "sync_state.json"
    )

    def __init__(self, config: WebDAVConfig, prompt_func: Callable = None):
        self.config = config
        self.client = WebDAVClient(config)
        self.paths = SyncPaths()
        # prompt_func kept for API compatibility but not used in archive mode
        self._prompt_func = prompt_func

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def push(self, force: bool = False) -> SyncResult:
        """Pack local files into an archive and upload to WebDAV."""
        result = SyncResult()

        if not self.client.test_connection():
            result.errors.append("Cannot connect to WebDAV server")
            return result

        home = Path.home()
        local_files = self._get_local_files(home)

        if not local_files:
            print("No local files to sync.")
            self._save_sync_state("push")
            return result

        # Build local manifest (no archive sha256 yet)
        local_manifest = build_manifest(local_files, home)

        if not force:
            remote_manifest = self._download_manifest()
            if remote_manifest and manifests_equal(local_manifest, remote_manifest):
                print("Already up to date — no changes detected.")
                result.skipped = len(local_files)
                self._save_sync_state("push")
                return result

        # Pack archive
        print(f"Packing {len(local_files)} files...")
        archive_path = create_archive(local_files, home)
        try:
            # Compute archive integrity hash
            archive_sha256 = sha256_file(archive_path)
            local_manifest["archive_sha256"] = archive_sha256

            # Ensure remote base dir exists
            if not self.client.ensure_remote_base():
                result.errors.append("Cannot create remote base directory")
                return result

            # Upload archive
            print(f"Uploading archive ({archive_path.stat().st_size // 1024} KB)...")
            if not self.client.upload_file(archive_path, self.client.REMOTE_ARCHIVE):
                result.errors.append("Failed to upload archive")
                return result

            # Upload manifest
            manifest_bytes = json.dumps(local_manifest, indent=2, ensure_ascii=False).encode()
            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False, prefix="claude-manifest-"
            ) as tmp:
                tmp.write(manifest_bytes)
                manifest_tmp = Path(tmp.name)
            try:
                if not self.client.upload_file(manifest_tmp, self.client.REMOTE_MANIFEST):
                    result.errors.append("Failed to upload manifest")
                    return result
            finally:
                manifest_tmp.unlink(missing_ok=True)

            result.pushed = len(local_files)
        finally:
            archive_path.unlink(missing_ok=True)

        self._save_sync_state("push")
        return result

    # ------------------------------------------------------------------
    # Pull
    # ------------------------------------------------------------------

    def pull(self, force: bool = False) -> SyncResult:
        """Download remote archive and extract changed files."""
        result = SyncResult()

        if not self.client.test_connection():
            result.errors.append("Cannot connect to WebDAV server")
            return result

        # Download manifest
        remote_manifest = self._download_manifest()
        if not remote_manifest:
            print("No remote data found. Push from another machine first.")
            return result

        home = Path.home()

        # Determine which files need updating
        if force:
            # Extract everything
            to_extract = set(remote_manifest["files"].keys())
            result.skipped = 0
        else:
            changed, missing = diff_manifests(remote_manifest, home)
            to_extract = changed | missing
            total = len(remote_manifest["files"])
            result.skipped = total - len(to_extract)

        if not to_extract:
            print("Already up to date — no changes detected.")
            self._save_sync_state("pull")
            return result

        print(f"Downloading archive ({len(to_extract)} files to update)...")

        # Download archive to temp file
        with tempfile.NamedTemporaryFile(
            suffix=".tar.gz", delete=False, prefix="claude-sync-dl-"
        ) as tmp:
            archive_path = Path(tmp.name)

        try:
            if not self.client.download_file(self.client.REMOTE_ARCHIVE, archive_path):
                result.errors.append("Failed to download archive")
                return result

            # Verify archive integrity
            expected_sha256 = remote_manifest.get("archive_sha256", "")
            if expected_sha256:
                actual_sha256 = sha256_file(archive_path)
                if actual_sha256 != expected_sha256:
                    result.errors.append(
                        f"Archive integrity check failed: "
                        f"expected {expected_sha256[:12]}… got {actual_sha256[:12]}…"
                    )
                    return result

            # Extract only changed/missing files
            extracted = extract_archive(archive_path, home, only_these=to_extract)
            result.pulled = len(extracted)
        finally:
            archive_path.unlink(missing_ok=True)

        self._save_sync_state("pull")
        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Get current sync status."""
        state = self._load_sync_state()
        return {
            "last_sync": state.get("last_sync"),
            "last_action": state.get("last_action"),
            "configured": self.config.is_configured(),
            "connected": (
                self.client.test_connection() if self.config.is_configured() else False
            ),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_local_files(self, home: Optional[Path] = None) -> List[Path]:
        """Return local files to sync that are under home."""
        if home is None:
            home = Path.home()
        return [
            p for p in self.paths.get_all_sync_paths()
            if p.exists() and p.is_relative_to(home)
        ]

    def _download_manifest(self) -> Optional[dict]:
        """Download and parse the remote manifest. Returns None if not found."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, prefix="claude-manifest-dl-"
        ) as tmp:
            manifest_path = Path(tmp.name)
        try:
            if not self.client.download_file(self.client.REMOTE_MANIFEST, manifest_path):
                return None
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        finally:
            manifest_path.unlink(missing_ok=True)

    def _save_sync_state(self, action: str) -> None:
        self.SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_sync": datetime.now().isoformat(),
            "last_action": action,
        }
        with open(self.SYNC_STATE_FILE, "w") as f:
            json.dump(state, f)

    def _load_sync_state(self) -> dict:
        if self.SYNC_STATE_FILE.exists():
            with open(self.SYNC_STATE_FILE, "r") as f:
                return json.load(f)
        return {}
