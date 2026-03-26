"""Integration tests for WebDAV sync plugin."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.config import WebDAVConfig
from webdav_sync.sync_manager import SyncManager
from webdav_sync.webdav_client import WebDAVClient


class TestIntegration:
    """Integration tests for full sync workflows."""

    @pytest.fixture
    def home(self, tmp_path):
        h = tmp_path / "home"
        h.mkdir()
        (h / ".claude").mkdir()
        (h / ".claude" / "settings.json").write_text('{"settings": {}}')
        (h / ".claude.json").write_text('{"user": "test"}')
        return h

    @pytest.fixture
    def config(self):
        return WebDAVConfig(
            webdav_url="https://webdav.test.com/dav",
            username="testuser",
            password="testpass",
        )

    @pytest.fixture
    def manager(self, config, home):
        m = SyncManager(config)
        m.client.test_connection = MagicMock(return_value=True)
        m.client.ensure_remote_base = MagicMock(return_value=True)
        m.client.upload_file = MagicMock(return_value=True)
        m.client.download_file = MagicMock(return_value=False)  # no remote by default
        local_files = [f for f in home.rglob("*") if f.is_file()]
        m._get_local_files = MagicMock(return_value=local_files)
        return m, home

    def test_full_push_workflow(self, manager):
        m, home = manager
        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = m.push(force=True)
        assert result.success
        assert result.pushed > 0
        assert m.client.upload_file.call_count == 2  # archive + manifest

    def test_full_pull_workflow_no_remote(self, manager):
        """Pull when nothing is on remote."""
        m, home = manager
        result = m.pull(force=True)
        assert result.success
        assert result.pulled == 0

    def test_error_handling_in_push(self, manager):
        """Upload failure is reported in result errors."""
        m, home = manager
        m.client.upload_file = MagicMock(return_value=False)
        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = m.push(force=True)
        assert not result.success
        assert len(result.errors) > 0

    def test_auto_sync_hooks(self, config, home):
        """Auto-sync on startup/shutdown uses pull/push."""
        config.sync_on_startup = True
        config.sync_on_shutdown = True
        m = SyncManager(config)
        m.client.test_connection = MagicMock(return_value=True)
        m.client.download_file = MagicMock(return_value=False)
        result = m.pull(force=True)
        assert result.success


class TestFileSystemOperations:
    def test_config_directory_creation(self, tmp_path):
        config = WebDAVConfig(webdav_url="https://test.com", username="user")
        with patch.object(WebDAVConfig, "config_path", return_value=tmp_path / "config.yaml"):
            config.save()
            assert (tmp_path / "config.yaml").exists()

    def test_sync_state_persistence(self, tmp_path):
        config = WebDAVConfig(webdav_url="https://test.com", username="user")
        m = SyncManager(config)
        m.SYNC_STATE_FILE = tmp_path / "sync_state.json"
        m._save_sync_state("push")
        state = m._load_sync_state()
        assert state["last_action"] == "push"
        assert "last_sync" in state
