"""Tests for sync manager module."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.sync_manager import SyncManager, SyncResult
from webdav_sync.config import WebDAVConfig
from webdav_sync.conflict_resolver import ConflictAction


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_default_values(self):
        """Test default result values."""
        result = SyncResult()

        assert result.pushed == 0
        assert result.pulled == 0
        assert result.skipped == 0
        assert result.conflicts == 0
        assert result.errors == []

    def test_success_property(self):
        """Test success property."""
        result = SyncResult()
        assert result.success is True

        result.errors.append("error")
        assert result.success is False

    def test_str_representation(self):
        """Test string representation."""
        result = SyncResult(pushed=5, pulled=3, skipped=1)
        assert "pushed=5" in str(result)
        assert "pulled=3" in str(result)


class TestSyncManager:
    """Tests for SyncManager class."""

    @pytest.fixture
    def manager(self, sample_config, mock_webdav_client, temp_home):
        """Create a sync manager with mocked dependencies."""
        with patch("webdav_sync.sync_manager.Path.home", return_value=temp_home):
            manager = SyncManager(sample_config)
            manager.client._client = mock_webdav_client
            yield manager

    def test_push_connection_failure(self, sample_config):
        """Test push when connection fails."""
        manager = SyncManager(sample_config)
        manager.client.test_connection = MagicMock(return_value=False)

        result = manager.push()

        assert not result.success
        assert "Cannot connect" in result.errors[0]

    def test_push_success(self, manager, temp_home):
        """Test successful push."""
        manager.client.test_connection = MagicMock(return_value=True)
        manager.client.upload_file = MagicMock(return_value=True)
        manager.client.get_remote_file_info = MagicMock(return_value=None)

        with patch("webdav_sync.sync_manager.Path.home", return_value=temp_home):
            result = manager.push(force=True)

        assert result.pushed > 0

    def test_push_skips_excluded(self, manager, temp_home):
        """Test push skips excluded files."""
        manager.config.exclude_patterns = [".claude.json"]
        manager.client.test_connection = MagicMock(return_value=True)

        with patch("webdav_sync.sync_manager.Path.home", return_value=temp_home):
            result = manager.push(force=True)

        assert ".claude.json" not in [
            str(p) for p in manager.paths.get_all_sync_paths()
        ]

    def test_pull_connection_failure(self, sample_config):
        """Test pull when connection fails."""
        manager = SyncManager(sample_config)
        manager.client.test_connection = MagicMock(return_value=False)

        result = manager.pull()

        assert not result.success
        assert "Cannot connect" in result.errors[0]

    def test_pull_downloads_files(self, manager):
        """Test pull downloads remote files."""
        manager.client.test_connection = MagicMock(return_value=True)
        manager.client.list_remote_files = MagicMock(
            return_value=[
                {
                    "path": "/claude-code-sync/.claude/test.json",
                    "size": 100,
                    "modified": "",
                }
            ]
        )
        manager.client.download_file = MagicMock(return_value=True)

        result = manager.pull(force=True)

        assert result.pulled == 1

    def test_pull_empty_remote(self, manager):
        """Test pull with empty remote."""
        manager.client.test_connection = MagicMock(return_value=True)
        manager.client.list_remote_files = MagicMock(return_value=[])

        result = manager.pull(force=True)

        assert result.pulled == 0
        assert result.success

    def test_status_configured(self, manager):
        """Test status returns configured state."""
        manager.client.test_connection = MagicMock(return_value=True)

        status = manager.status()

        assert status["configured"] is True

    def test_status_not_configured(self):
        """Test status when not configured."""
        config = WebDAVConfig()
        manager = SyncManager(config)

        status = manager.status()

        assert status["configured"] is False
        assert status["connected"] is False

    def test_status_last_sync(self, manager, tmp_path):
        """Test status shows last sync time."""
        manager.SYNC_STATE_FILE = tmp_path / "sync_state.json"
        manager._save_sync_state("push")

        status = manager.status()

        assert status["last_sync"] is not None
        assert status["last_action"] == "push"

    def test_should_exclude(self, manager):
        """Test exclude pattern matching."""
        manager.config.exclude_patterns = ["telemetry/*", "debug/*"]

        assert (
            manager._should_exclude(Path("/home/.claude/telemetry/file.json")) is True
        )
        assert manager._should_exclude(Path("/home/.claude/config.json")) is False

    def test_backup_local(self, manager, tmp_path):
        """Test local file backup."""
        local_file = tmp_path / "test.json"
        local_file.write_text('{"test": true}')

        manager._backup_local(local_file)

        backups = list(tmp_path.glob("test.*.bak"))
        assert len(backups) == 1
