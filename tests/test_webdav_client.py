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
        return WebDAVClient(sample_config)

    @pytest.fixture
    def mock_wd_client(self):
        mock = MagicMock()
        mock.list.return_value = []
        mock.info.return_value = {"size": "100", "modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
        return mock

    def test_client_initialization(self, sample_config):
        client = WebDAVClient(sample_config)
        assert client.config == sample_config
        assert client._client is None

    def test_client_disable_check_option(self, sample_config):
        """Client must set disable_check=True for 坚果云 compatibility."""
        client = WebDAVClient(sample_config)
        with patch("webdav_sync.webdav_client.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            _ = client.client
            options = mock_cls.call_args[0][0]
            assert options.get("disable_check") is True

    def test_test_connection_success(self, client, mock_wd_client):
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.test_connection() is True
            mock_wd_client.list.assert_called_once_with("/")

    def test_test_connection_failure(self, client, mock_wd_client):
        from webdav3.exceptions import WebDavException
        mock_wd_client.list.side_effect = WebDavException("fail")
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.test_connection() is False

    def test_upload_file_success(self, client, mock_wd_client, tmp_path):
        local_file = tmp_path / "test.json"
        local_file.write_text('{"test": true}')
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.upload_file(local_file, "/remote/test.json") is True
            mock_wd_client.upload_sync.assert_called_once()

    def test_upload_file_failure(self, client, mock_wd_client, tmp_path):
        from webdav3.exceptions import WebDavException
        local_file = tmp_path / "test.json"
        local_file.write_text('{}')
        mock_wd_client.upload_sync.side_effect = WebDavException("fail")
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.upload_file(local_file, "/remote/test.json") is False

    def test_download_file_success(self, client, mock_wd_client, tmp_path):
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            local_path = tmp_path / "downloaded.json"
            assert client.download_file("/remote/test.json", local_path) is True
            mock_wd_client.download_sync.assert_called_once()

    def test_download_file_creates_directories(self, client, mock_wd_client, tmp_path):
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            local_path = tmp_path / "a" / "b" / "file.json"
            assert client.download_file("/remote/test.json", local_path) is True
            assert local_path.parent.exists()

    def test_ensure_remote_base_already_exists(self, client, mock_wd_client):
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.ensure_remote_base() is True
            mock_wd_client.mkdir.assert_not_called()

    def test_ensure_remote_base_creates(self, client, mock_wd_client):
        from webdav3.exceptions import WebDavException
        mock_wd_client.list.side_effect = [WebDavException("not found"), []]
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.ensure_remote_base() is True
            mock_wd_client.mkdir.assert_called_once()

    def test_remote_file_exists_true(self, client, mock_wd_client):
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.remote_file_exists("/some/file") is True

    def test_remote_file_exists_false(self, client, mock_wd_client):
        from webdav3.exceptions import WebDavException
        mock_wd_client.info.side_effect = WebDavException("not found")
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.remote_file_exists("/some/file") is False

    def test_delete_remote_file(self, client, mock_wd_client):
        with patch("webdav_sync.webdav_client.Client", return_value=mock_wd_client):
            assert client.delete_remote_file("/test.json") is True
            mock_wd_client.clean.assert_called_once()

    def test_webdav_root_extraction(self, sample_config):
        sample_config.webdav_url = "https://dav.jianguoyun.com/dav/"
        client = WebDAVClient(sample_config)
        assert client._webdav_root == "/dav"

    def test_webdav_root_no_path(self, sample_config):
        sample_config.webdav_url = "https://webdav.example.com/"
        client = WebDAVClient(sample_config)
        assert client._webdav_root == ""


class TestJianguoyunSupport:
    """Tests for 坚果云 (Jianguoyun) specific support."""

    @pytest.fixture
    def jianguoyun_config(self):
        from webdav_sync.config import PROVIDER_JIANGUOYUN, JIANGUOYUN_WEBDAV_URL
        return WebDAVConfig(
            webdav_url=JIANGUOYUN_WEBDAV_URL,
            username="user@example.com",
            password="app-specific-password",
            provider=PROVIDER_JIANGUOYUN,
        )

    def test_jianguoyun_config_url(self, jianguoyun_config):
        assert jianguoyun_config.webdav_url == "https://dav.jianguoyun.com/dav/"

    def test_jianguoyun_provider_field(self, jianguoyun_config):
        from webdav_sync.config import PROVIDER_JIANGUOYUN
        assert jianguoyun_config.provider == PROVIDER_JIANGUOYUN

    def test_jianguoyun_config_save_load(self, tmp_path, monkeypatch):
        from webdav_sync.config import PROVIDER_JIANGUOYUN, JIANGUOYUN_WEBDAV_URL
        config_path = tmp_path / "config.yaml"
        monkeypatch.setattr(WebDAVConfig, "config_path", classmethod(lambda cls: config_path))
        config = WebDAVConfig(
            webdav_url=JIANGUOYUN_WEBDAV_URL,
            username="user@example.com",
            password="secret",
            provider=PROVIDER_JIANGUOYUN,
        )
        config.save()
        loaded = WebDAVConfig.load()
        assert loaded.provider == PROVIDER_JIANGUOYUN
        assert loaded.webdav_url == JIANGUOYUN_WEBDAV_URL

    def test_jianguoyun_client_options(self, jianguoyun_config):
        client = WebDAVClient(jianguoyun_config)
        with patch("webdav_sync.webdav_client.Client") as mock_cls:
            mock_cls.return_value = MagicMock()
            _ = client.client
            options = mock_cls.call_args[0][0]
            assert options["webdav_hostname"] == "https://dav.jianguoyun.com/dav/"
            assert options["webdav_login"] == "user@example.com"
            assert options["disable_check"] is True
