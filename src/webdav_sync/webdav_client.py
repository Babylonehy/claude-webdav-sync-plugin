"""WebDAV client wrapper for sync operations."""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from webdav3.client import Client
from webdav3.exceptions import WebDavException

from .config import WebDAVConfig

logger = logging.getLogger(__name__)


class WebDAVClient:
    """Wrapper for WebDAV operations."""

    REMOTE_BASE_PATH = "/claude-code-sync"

    def __init__(self, config: WebDAVConfig):
        self.config = config
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy initialization of WebDAV client."""
        if self._client is None:
            options = {
                "webdav_hostname": self.config.webdav_url,
                "webdav_login": self.config.username,
                "webdav_password": self.config.password,
            }
            self._client = Client(options)
        return self._client

    def test_connection(self) -> bool:
        """Test if connection to WebDAV server works."""
        try:
            return self.client.check()
        except WebDavException:
            return False

    def ensure_remote_dir(self, path: str) -> bool:
        """Ensure a remote directory exists."""
        try:
            if not self.client.check(path):
                self.client.mkdir(path)
            return True
        except WebDavException:
            return False

    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """Upload a local file to remote path."""
        try:
            remote_dir = os.path.dirname(remote_path)
            self.ensure_remote_dir(remote_dir)
            self.client.upload_sync(remote_path=remote_path, local_path=str(local_path))
            return True
        except WebDavException as e:
            logger.error(f"Error uploading {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """Download a remote file to local path."""
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_sync(
                remote_path=remote_path, local_path=str(local_path)
            )
            return True
        except WebDavException as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def list_remote_files(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all files in remote directory recursively."""
        if path is None:
            path = self.REMOTE_BASE_PATH
        try:
            if not self.client.check(path):
                return []
            files = self.client.list(path)
            result = []
            for f in files:
                if f.get("isdir", False):
                    continue
                result.append(
                    {
                        "path": f["path"],
                        "size": int(f.get("size", 0)),
                        "modified": f.get("modified", ""),
                    }
                )
            return result
        except WebDavException:
            return []

    def get_remote_file_info(self, remote_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a remote file."""
        try:
            info = self.client.info(remote_path)
            return {
                "size": int(info.get("size", 0)),
                "modified": info.get("modified", ""),
            }
        except WebDavException:
            return None

    def delete_remote_file(self, remote_path: str) -> bool:
        """Delete a remote file."""
        try:
            self.client.clean(remote_path)
            return True
        except WebDavException:
            return False

    def get_local_path_for_remote(self, remote_path: str) -> Path:
        """Convert remote path to corresponding local path."""
        rel_path = remote_path.replace(self.REMOTE_BASE_PATH, "").lstrip("/")
        home = Path.home()
        return home / rel_path

    def get_remote_path_for_local(self, local_path: Path) -> str:
        """Convert local path to corresponding remote path."""
        home = str(Path.home())
        rel_path = str(local_path).replace(home, "").lstrip("/")
        return f"{self.REMOTE_BASE_PATH}/{rel_path}"
