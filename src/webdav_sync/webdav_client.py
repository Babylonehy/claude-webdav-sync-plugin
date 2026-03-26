"""WebDAV client wrapper for sync operations."""

import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
from webdav3.client import Client
from webdav3.exceptions import WebDavException

from .config import WebDAVConfig

logger = logging.getLogger(__name__)


class WebDAVClient:
    """Wrapper for WebDAV operations."""

    REMOTE_BASE_PATH = "/claude-code-sync"
    REMOTE_ARCHIVE = "/claude-code-sync/claude-sync.tar.gz"
    REMOTE_MANIFEST = "/claude-code-sync/claude-sync.manifest.json"

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
                # disable_check skips internal HEAD requests that many servers
                # (including 坚果云/Jianguoyun) return 403 for on subdirectories.
                "disable_check": True,
            }
            self._client = Client(options)
        return self._client

    @property
    def _webdav_root(self) -> str:
        """Extract the WebDAV root path from the configured URL.
        e.g. 'https://dav.jianguoyun.com/dav/' → '/dav'
        """
        return urlparse(self.config.webdav_url).path.rstrip("/")

    def test_connection(self) -> bool:
        """Test if connection to WebDAV server works."""
        try:
            self.client.list("/")
            return True
        except WebDavException:
            return False

    def ensure_remote_base(self) -> bool:
        """Ensure the /claude-code-sync base directory exists."""
        try:
            self.client.list(self.REMOTE_BASE_PATH)
            return True
        except WebDavException:
            pass
        try:
            self.client.mkdir(self.REMOTE_BASE_PATH)
            return True
        except WebDavException:
            try:
                self.client.list(self.REMOTE_BASE_PATH)
                return True
            except WebDavException:
                return False

    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """Upload a local file to a remote path."""
        try:
            self.client.upload_sync(remote_path=remote_path, local_path=str(local_path))
            return True
        except WebDavException as e:
            logger.error(f"Error uploading {local_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """Download a remote file to a local path."""
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_sync(remote_path=remote_path, local_path=str(local_path))
            return True
        except WebDavException as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def remote_file_exists(self, remote_path: str) -> bool:
        """Check if a remote file exists by attempting to get its info."""
        try:
            self.client.info(remote_path)
            return True
        except WebDavException:
            return False

    def delete_remote_file(self, remote_path: str) -> bool:
        """Delete a remote file."""
        try:
            self.client.clean(remote_path)
            return True
        except WebDavException:
            return False
