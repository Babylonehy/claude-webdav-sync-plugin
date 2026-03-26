"""Archive creation, extraction, and integrity verification for sync."""

import hashlib
import json
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


MANIFEST_FILENAME = "claude-sync.manifest.json"
ARCHIVE_FILENAME = "claude-sync.tar.gz"
MANIFEST_VERSION = "2"


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(files: List[Path], home: Path, archive_sha256: str = "") -> dict:
    """Build a manifest dict from a list of local files.

    :param files: absolute local paths
    :param home: home directory (used to compute relative paths)
    :param archive_sha256: checksum of the corresponding tar.gz (filled after packing)
    """
    file_entries: Dict[str, dict] = {}
    for f in files:
        if not f.exists():
            continue
        rel = str(f.relative_to(home))
        file_entries[rel] = {
            "sha256": sha256_file(f),
            "size": f.stat().st_size,
            "mtime": datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }
    return {
        "version": MANIFEST_VERSION,
        "created": datetime.now(tz=timezone.utc).isoformat(),
        "archive_sha256": archive_sha256,
        "files": file_entries,
    }


def create_archive(files: List[Path], home: Path) -> Path:
    """Pack files into a temp tar.gz. Returns the archive path."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=".tar.gz", delete=False, prefix="claude-sync-"
    )
    tmp.close()
    archive_path = Path(tmp.name)

    with tarfile.open(archive_path, "w:gz") as tar:
        for f in files:
            if not f.exists():
                continue
            arcname = str(f.relative_to(home))
            tar.add(f, arcname=arcname)

    return archive_path


def extract_archive(
    archive_path: Path,
    home: Path,
    only_these: Optional[Set[str]] = None,
) -> List[str]:
    """Extract files from archive to home directory.

    :param archive_path: path to the tar.gz
    :param home: destination home directory
    :param only_these: if set, only extract these relative paths
    :return: list of relative paths that were extracted
    """
    extracted = []
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue
            if only_these is not None and member.name not in only_these:
                continue
            dest = home / member.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            extracted.append(member.name)
    return extracted


def diff_manifests(
    remote_manifest: dict, home: Path
) -> tuple[Set[str], Set[str]]:
    """Compare remote manifest against local files.

    Returns (changed, missing) — sets of relative paths that need updating.
    """
    changed: Set[str] = set()
    missing: Set[str] = set()

    for rel_path, info in remote_manifest.get("files", {}).items():
        local = home / rel_path
        if not local.exists():
            missing.add(rel_path)
        elif sha256_file(local) != info["sha256"]:
            changed.add(rel_path)

    return changed, missing


def manifests_equal(local_manifest: dict, remote_manifest: dict) -> bool:
    """True when every file's sha256 matches — no upload needed."""
    local_files = local_manifest.get("files", {})
    remote_files = remote_manifest.get("files", {})
    if set(local_files) != set(remote_files):
        return False
    return all(
        local_files[k]["sha256"] == remote_files[k]["sha256"]
        for k in local_files
    )
