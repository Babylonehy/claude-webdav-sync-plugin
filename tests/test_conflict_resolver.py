"""Tests for conflict resolver module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.conflict_resolver import (
    ConflictResolver,
    ConflictInfo,
    ConflictAction,
    get_file_diff,
)
from webdav_sync.webdav_client import WebDAVClient
from webdav_sync.config import WebDAVConfig


class TestGetFileDiff:
    """Tests for get_file_diff function."""

    def test_identical_content(self):
        """Test diff of identical content."""
        diff = get_file_diff("same", "same", "test.txt")
        assert diff == ""

    def test_different_content(self):
        """Test diff of different content."""
        diff = get_file_diff("line1\nline2", "line1\nline3", "test.txt")
        assert "-line3" in diff or "+line2" in diff

    def test_empty_files(self):
        """Test diff of empty files."""
        diff = get_file_diff("", "", "empty.txt")
        assert diff == ""


class TestConflictInfo:
    """Tests for ConflictInfo dataclass."""

    def test_creation(self, tmp_path):
        """Test creating conflict info."""
        info = ConflictInfo(
            local_path=tmp_path / "test.json",
            remote_path="/remote/test.json",
            local_modified=datetime.now(),
            remote_modified=datetime.now(),
            local_size=100,
            remote_size=200,
        )

        assert info.local_size == 100
        assert info.remote_size == 200
        assert info.remote_path == "/remote/test.json"


class TestConflictResolver:
    """Tests for ConflictResolver class."""

    @pytest.fixture
    def resolver(self, mock_webdav_client):
        """Create a conflict resolver."""
        config = WebDAVConfig(webdav_url="https://test.com", username="user")
        client = WebDAVClient(config)
        client._client = mock_webdav_client
        return ConflictResolver(client)

    def test_no_conflict_when_remote_missing(self, resolver, tmp_path):
        """Test no conflict when remote file doesn't exist."""
        resolver.client.get_remote_file_info = MagicMock(return_value=None)

        conflict = resolver.detect_conflict(tmp_path / "local.json", "/remote.json")

        assert conflict is None

    def test_no_conflict_when_local_missing(self, resolver, tmp_path):
        """Test no conflict when local file doesn't exist."""
        resolver.client.get_remote_file_info = MagicMock(
            return_value={"size": 100, "modified": ""}
        )

        conflict = resolver.detect_conflict(
            tmp_path / "nonexistent.json", "/remote.json"
        )

        assert conflict is None

    def test_no_conflict_same_size_and_time(self, resolver, tmp_path):
        """Test no conflict when files are identical."""
        local_file = tmp_path / "test.json"
        local_file.write_text('{"test": true}')

        resolver.client.get_remote_file_info = MagicMock(
            return_value={
                "size": local_file.stat().st_size,
                "modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            }
        )

        with patch("webdav_sync.conflict_resolver.datetime") as mock_dt:
            mock_dt.fromtimestamp.return_value = datetime(2024, 1, 1)
            mock_dt.strptime.return_value = datetime(2024, 1, 1)
            mock_dt.min = datetime.min

            conflict = resolver.detect_conflict(local_file, "/remote.json")

        assert conflict is None

    def test_conflict_detected_different_sizes(self, resolver, tmp_path):
        """Test conflict detected when sizes differ."""
        local_file = tmp_path / "test.json"
        local_file.write_text('{"test": true}')

        resolver.client.get_remote_file_info = MagicMock(
            return_value={"size": 999, "modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
        )

        conflict = resolver.detect_conflict(local_file, "/remote.json")

        assert conflict is not None
        assert conflict.local_size != conflict.remote_size

    def test_resolve_with_force_action(self, resolver, tmp_path):
        """Test resolving with forced action."""
        conflict = ConflictInfo(
            local_path=tmp_path / "test.json",
            remote_path="/remote.json",
            local_modified=datetime.now(),
            remote_modified=datetime.now(),
            local_size=100,
            remote_size=200,
        )

        action = resolver.resolve(conflict, force_action=ConflictAction.KEEP_LOCAL)

        assert action == ConflictAction.KEEP_LOCAL

    def test_resolve_with_custom_prompt(self, tmp_path):
        """Test resolving with custom prompt function."""
        config = WebDAVConfig(webdav_url="https://test.com", username="user")
        client = WebDAVClient(config)

        custom_prompt = MagicMock(return_value=ConflictAction.SKIP)
        resolver = ConflictResolver(client, prompt_func=custom_prompt)

        conflict = ConflictInfo(
            local_path=tmp_path / "test.json",
            remote_path="/remote.json",
            local_modified=datetime.now(),
            remote_modified=datetime.now(),
            local_size=100,
            remote_size=200,
        )

        action = resolver.resolve(conflict)

        assert action == ConflictAction.SKIP
        custom_prompt.assert_called_once_with(conflict)


class TestConflictAction:
    """Tests for ConflictAction enum."""

    def test_all_actions_exist(self):
        """Test all expected actions exist."""
        assert ConflictAction.KEEP_LOCAL.value == "keep_local"
        assert ConflictAction.KEEP_REMOTE.value == "keep_remote"
        assert ConflictAction.KEEP_BOTH.value == "keep_both"
        assert ConflictAction.SKIP.value == "skip"
        assert ConflictAction.ABORT.value == "abort"
