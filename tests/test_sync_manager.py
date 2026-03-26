"""Tests for sync manager module."""

import json
import tarfile
import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.sync_manager import SyncManager, SyncResult
from webdav_sync.config import WebDAVConfig
from webdav_sync.archiver import sha256_file, build_manifest


class TestSyncResult:
    def test_default_values(self):
        result = SyncResult()
        assert result.pushed == 0
        assert result.pulled == 0
        assert result.skipped == 0
        assert result.conflicts == 0
        assert result.errors == []

    def test_success_property(self):
        result = SyncResult()
        assert result.success is True
        result.errors.append("error")
        assert result.success is False

    def test_str_representation(self):
        result = SyncResult(pushed=5, pulled=3, skipped=1)
        assert "pushed=5" in str(result)
        assert "pulled=3" in str(result)


class TestSyncManager:

    @pytest.fixture
    def home(self, tmp_path):
        """Isolated home with sample files."""
        h = tmp_path / "home"
        h.mkdir()
        (h / ".claude").mkdir()
        (h / ".claude" / "settings.json").write_text('{"settings": {}}')
        (h / ".claude" / "history.jsonl").write_text('{"type": "message"}\n')
        (h / ".claude.json").write_text('{"user": "test"}')
        return h

    @pytest.fixture
    def manager(self, sample_config, home):
        m = SyncManager(sample_config)
        m.client.test_connection = MagicMock(return_value=True)
        m.client.ensure_remote_base = MagicMock(return_value=True)
        m.client.upload_file = MagicMock(return_value=True)
        m.client.download_file = MagicMock(return_value=True)
        m.client.remote_file_exists = MagicMock(return_value=True)
        # Return only files under isolated home
        local_files = [f for f in home.rglob("*") if f.is_file()]
        m._get_local_files = MagicMock(return_value=local_files)
        m._home = home
        return m

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def test_push_connection_failure(self, sample_config):
        m = SyncManager(sample_config)
        m.client.test_connection = MagicMock(return_value=False)
        result = m.push()
        assert not result.success
        assert "Cannot connect" in result.errors[0]

    def test_push_success_force(self, manager, home):
        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = manager.push(force=True)
        assert result.success
        assert result.pushed > 0
        assert manager.client.upload_file.call_count == 2  # archive + manifest

    def test_push_already_up_to_date(self, manager, home):
        """No upload when local manifest matches remote."""
        local_files = manager._get_local_files.return_value
        local_manifest = build_manifest(local_files, home)
        manifest_bytes = json.dumps(local_manifest).encode()

        def fake_download(remote_path, local_path):
            if "manifest" in remote_path:
                local_path.write_bytes(manifest_bytes)
                return True
            return False

        manager.client.download_file = MagicMock(side_effect=fake_download)

        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = manager.push(force=False)

        assert result.success
        manager.client.upload_file.assert_not_called()

    def test_push_no_files(self, sample_config, tmp_path):
        m = SyncManager(sample_config)
        m.client.test_connection = MagicMock(return_value=True)
        m.client.ensure_remote_base = MagicMock(return_value=True)
        m._get_local_files = MagicMock(return_value=[])
        empty_home = tmp_path / "empty"
        empty_home.mkdir()
        with patch("webdav_sync.sync_manager.Path.home", return_value=empty_home):
            result = m.push(force=True)
        assert result.success
        assert result.pushed == 0

    # ------------------------------------------------------------------
    # Pull
    # ------------------------------------------------------------------

    def test_pull_connection_failure(self, sample_config):
        m = SyncManager(sample_config)
        m.client.test_connection = MagicMock(return_value=False)
        result = m.pull()
        assert not result.success
        assert "Cannot connect" in result.errors[0]

    def test_pull_no_remote_data(self, manager):
        manager.client.download_file = MagicMock(return_value=False)
        result = manager.pull()
        assert result.success
        assert result.pulled == 0

    def test_pull_already_up_to_date(self, manager, home):
        """No archive download when all local files match remote."""
        local_files = manager._get_local_files.return_value
        local_manifest = build_manifest(local_files, home)
        local_manifest["archive_sha256"] = "abc123"
        manifest_bytes = json.dumps(local_manifest).encode()

        download_calls = []

        def fake_download(remote_path, local_path):
            download_calls.append(remote_path)
            if "manifest" in remote_path:
                local_path.write_bytes(manifest_bytes)
                return True
            return False

        manager.client.download_file = MagicMock(side_effect=fake_download)

        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = manager.pull(force=False)

        assert result.success
        assert result.pulled == 0
        assert result.skipped > 0
        assert not any("archive" in p for p in download_calls)

    def test_pull_integrity_check_failure(self, manager, home):
        manifest = {
            "version": "2",
            "archive_sha256": "deadbeef" * 8,
            "files": {".claude/settings.json": {"sha256": "aaa", "size": 10, "mtime": ""}},
        }
        manifest_bytes = json.dumps(manifest).encode()

        def fake_download(remote_path, local_path):
            if "manifest" in remote_path:
                local_path.write_bytes(manifest_bytes)
            else:
                local_path.write_bytes(b"wrong content")
            return True

        manager.client.download_file = MagicMock(side_effect=fake_download)

        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = manager.pull(force=True)

        assert not result.success
        assert "integrity check failed" in result.errors[0]

    def test_pull_extracts_changed_files(self, manager, home, tmp_path):
        """Pull extracts files that differ from local."""
        test_rel = ".claude/settings.json"
        test_content = b'{"updated": true}'

        archive_path = tmp_path / "test.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            info = tarfile.TarInfo(name=test_rel)
            info.size = len(test_content)
            tar.addfile(info, io.BytesIO(test_content))

        archive_sha256 = sha256_file(archive_path)
        archive_bytes = archive_path.read_bytes()

        manifest = {
            "version": "2",
            "archive_sha256": archive_sha256,
            "files": {
                test_rel: {"sha256": "old_different_sha256", "size": 10, "mtime": ""}
            },
        }
        manifest_bytes = json.dumps(manifest).encode()

        def fake_download(remote_path, local_path):
            if "manifest" in remote_path:
                local_path.write_bytes(manifest_bytes)
            else:
                local_path.write_bytes(archive_bytes)
            return True

        manager.client.download_file = MagicMock(side_effect=fake_download)

        with patch("webdav_sync.sync_manager.Path.home", return_value=home):
            result = manager.pull(force=False)

        assert result.success
        assert result.pulled >= 1
        assert (home / ".claude" / "settings.json").read_bytes() == test_content

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def test_status_configured(self, manager):
        status = manager.status()
        assert status["configured"] is True
        assert status["connected"] is True

    def test_status_not_configured(self):
        config = WebDAVConfig()
        m = SyncManager(config)
        status = m.status()
        assert status["configured"] is False
        assert status["connected"] is False

    def test_status_last_sync(self, manager, tmp_path):
        manager.SYNC_STATE_FILE = tmp_path / "sync_state.json"
        manager._save_sync_state("push")
        status = manager.status()
        assert status["last_sync"] is not None
        assert status["last_action"] == "push"
