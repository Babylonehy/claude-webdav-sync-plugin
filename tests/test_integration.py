"""Integration tests for WebDAV sync plugin."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.config import WebDAVConfig
from webdav_sync.sync_manager import SyncManager
from webdav_sync.webdav_client import WebDAVClient


class TestIntegration:
    """Integration tests for full sync workflows."""

    @pytest.fixture
    def mock_webdav(self):
        """Create a fully mocked WebDAV environment."""
        mock_client = MagicMock()
        mock_client.check.return_value = True
        mock_client.mkdir.return_value = True
        mock_client.upload_sync.return_value = None
        mock_client.download_sync.return_value = None
        mock_client.list.return_value = []
        mock_client.info.return_value = {"size": "100", "modified": ""}
        mock_client.clean.return_value = None
        return mock_client

    @pytest.fixture
    def full_setup(self, temp_home, mock_webdav):
        """Create a full test environment."""
        config = WebDAVConfig(
            webdav_url="https://webdav.test.com/dav",
            username="testuser",
            password="testpass",
        )

        return {
            "config": config,
            "home": temp_home,
            "mock_webdav": mock_webdav,
        }

    def test_full_push_workflow(self, full_setup):
        """Test complete push workflow."""
        with patch(
            "webdav_sync.sync_manager.Path.home", return_value=full_setup["home"]
        ):
            with patch(
                "webdav_sync.webdav_client.Client",
                return_value=full_setup["mock_webdav"],
            ):
                manager = SyncManager(full_setup["config"])
                result = manager.push(force=True)

                assert result.success
                assert result.pushed > 0

    def test_full_pull_workflow(self, full_setup):
        """Test complete pull workflow."""
        full_setup["mock_webdav"].list.return_value = [
            {"path": "/claude-code-sync/.claude/test.json", "isdir": False, "size": 100}
        ]

        with patch(
            "webdav_sync.sync_manager.Path.home", return_value=full_setup["home"]
        ):
            with patch(
                "webdav_sync.webdav_client.Client",
                return_value=full_setup["mock_webdav"],
            ):
                manager = SyncManager(full_setup["config"])
                result = manager.pull(force=True)

                assert result.success

    def test_error_handling_in_push(self, full_setup):
        """Test error handling during push."""
        from webdav3.exceptions import WebDavException

        full_setup["mock_webdav"].upload_sync.side_effect = WebDavException(
            "Upload failed"
        )

        with patch(
            "webdav_sync.sync_manager.Path.home", return_value=full_setup["home"]
        ):
            with patch(
                "webdav_sync.webdav_client.Client",
                return_value=full_setup["mock_webdav"],
            ):
                manager = SyncManager(full_setup["config"])
                result = manager.push(force=True)

                assert not result.success
                assert len(result.errors) > 0

    def test_auto_sync_hooks(self, full_setup):
        """Test auto-sync on startup and shutdown."""
        full_setup["config"].sync_on_startup = True
        full_setup["config"].sync_on_shutdown = True

        with patch(
            "webdav_sync.sync_manager.Path.home", return_value=full_setup["home"]
        ):
            with patch(
                "webdav_sync.webdav_client.Client",
                return_value=full_setup["mock_webdav"],
            ):
                manager = SyncManager(full_setup["config"])

                result = manager.pull(force=True)
                assert result.success


class TestFileSystemOperations:
    """Tests for actual filesystem operations."""

    def test_config_directory_creation(self, tmp_path):
        """Test config directory is created."""
        config = WebDAVConfig(
            webdav_url="https://test.com",
            username="user",
        )

        with patch.object(
            WebDAVConfig, "config_path", return_value=tmp_path / "config.yaml"
        ):
            config.save()

            assert (tmp_path / "config.yaml").exists()

    def test_sync_state_persistence(self, tmp_path):
        """Test sync state is persisted."""
        config = WebDAVConfig(webdav_url="https://test.com", username="user")
        manager = SyncManager(config)
        manager.SYNC_STATE_FILE = tmp_path / "sync_state.json"

        manager._save_sync_state("push")

        state = manager._load_sync_state()
        assert state["last_action"] == "push"
        assert "last_sync" in state
