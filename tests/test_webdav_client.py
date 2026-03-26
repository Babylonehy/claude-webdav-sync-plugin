"""Tests for WebDAV client module."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.config import WebDAVConfig
from webdav_sync.webdav_client import WebDAVClient


class TestWebDAVClient:
    """Tests for WebDAVClient class."""

    @pytest.fixture
    def client(self, sample_config):
        """Create a WebDAV client with sample config."""
        return WebDAVClient(sample_config)

    @pytest.fixture
    def mock_wd_client(self):
        """Create a mock webdav3 client."""
        mock = MagicMock()
        mock.check.return_value = True
        mock.list.return_value = []
        mock.info.return_value = {
            "size": "100",
            "modified": "Mon, 01 Jan 2024 00:00:00 GMT",
        }
        return mock

    def test_client_initialization(self, sample_config):
        """Test client is initialized correctly."""
        client = WebDAVClient(sample_config)

        assert client.config == sample_config
        assert client._client is None

    def test_client_lazy_initialization(self, client, mock_wd_client):
        """Test lazy initialization of underlying client."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            _ = client.client

            assert client._client is not None

    def test_test_connection_success(self, client, mock_wd_client):
        """Test successful connection test."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.test_connection() is True

    def test_test_connection_failure(self, client, mock_wd_client):
        """Test failed connection test."""
        from webdav3.exceptions import WebDavException

        mock_wd_client.check.side_effect = WebDavException("Connection failed")
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.test_connection() is False

    def test_upload_file_success(self, client, mock_wd_client, tmp_path):
        """Test successful file upload."""
        local_file = tmp_path / "test.json"
        local_file.write_text('{"test": true}')

        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            result = client.upload_file(local_file, "/remote/test.json")

            assert result is True
            mock_wd_client.upload_sync.assert_called_once()

    def test_upload_file_failure(self, client, mock_wd_client, tmp_path):
        """Test failed file upload."""
        from webdav3.exceptions import WebDavException

        local_file = tmp_path / "test.json"
        local_file.write_text('{"test": true}')
        mock_wd_client.upload_sync.side_effect = WebDavException("Upload failed")

        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            result = client.upload_file(local_file, "/remote/test.json")

            assert result is False

    def test_download_file_success(self, client, mock_wd_client, tmp_path):
        """Test successful file download."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            local_path = tmp_path / "downloaded.json"
            result = client.download_file("/remote/test.json", local_path)

            assert result is True
            mock_wd_client.download_sync.assert_called_once()

    def test_download_file_creates_directories(self, client, mock_wd_client, tmp_path):
        """Test download creates parent directories."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            local_path = tmp_path / "subdir" / "deep" / "file.json"
            result = client.download_file("/remote/test.json", local_path)

            assert result is True
            assert local_path.parent.exists()

    def test_list_remote_files_empty(self, client, mock_wd_client):
        """Test listing empty remote directory."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            files = client.list_remote_files()

            assert files == []

    def test_list_remote_files_with_files(self, client, mock_wd_client):
        """Test listing remote files."""
        mock_wd_client.list.return_value = [
            {"path": "/file1.json", "isdir": False, "size": "100"},
            {"path": "/file2.json", "isdir": False, "size": "200"},
            {"path": "/dir", "isdir": True},
        ]

        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            files = client.list_remote_files()

            assert len(files) == 2
            assert files[0]["path"] == "/file1.json"

    def test_list_remote_files_nonexistent(self, client, mock_wd_client):
        """Test listing nonexistent remote directory."""
        mock_wd_client.check.return_value = False

        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            files = client.list_remote_files()

            assert files == []

    def test_get_remote_file_info(self, client, mock_wd_client):
        """Test getting remote file info."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            info = client.get_remote_file_info("/test.json")

            assert info is not None
            assert info["size"] == 100
            assert "modified" in info

    def test_delete_remote_file(self, client, mock_wd_client):
        """Test deleting remote file."""
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            result = client.delete_remote_file("/test.json")

            assert result is True
            mock_wd_client.clean.assert_called_once()

    def test_get_local_path_for_remote(self, client):
        """Test converting remote path to local path."""
        local = client.get_local_path_for_remote("/claude-code-sync/.claude/test.json")

        assert ".claude" in str(local)
        assert "test.json" in str(local)

    def test_get_remote_path_for_local(self, client, temp_home):
        """Test converting local path to remote path."""
        local_path = temp_home / ".claude" / "test.json"
        remote = client.get_remote_path_for_local(local_path)

        assert remote.startswith("/claude-code-sync")
        assert "test.json" in remote
