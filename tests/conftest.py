"""Pytest fixtures for WebDAV sync plugin tests."""

import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from webdav_sync.config import WebDAVConfig, SyncPaths


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".claude" / "plugins" / "data" / "webdav-sync"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary home directory with sample Claude files."""
    home = tmp_path / "home"
    home.mkdir()

    claude_dir = home / ".claude"
    claude_dir.mkdir()

    (claude_dir / ".claude.json").write_text('{"test": "data"}')
    (claude_dir / "settings.json").write_text('{"settings": {}}')
    (claude_dir / "config.json").write_text('{"api_key": "test"}')
    (claude_dir / "history.jsonl").write_text('{"type": "message"}\n')

    projects_dir = claude_dir / "projects"
    projects_dir.mkdir()

    project1 = projects_dir / "test-project"
    project1.mkdir()
    (project1 / "session1.jsonl").write_text('{"session": 1}\n')
    (project1 / "session2.jsonl").write_text('{"session": 2}\n')

    opencode_dir = home / ".config" / "opencode"
    opencode_dir.mkdir(parents=True)
    (opencode_dir / "opencode.json").write_text('{"provider": {}}')

    return home


@pytest.fixture
def sample_config():
    """Create a sample WebDAV configuration."""
    return WebDAVConfig(
        webdav_url="https://webdav.example.com/dav",
        username="testuser",
        password="testpass",
        auto_sync=True,
        sync_on_startup=True,
        sync_on_shutdown=True,
    )


@pytest.fixture
def mock_webdav_client():
    """Create a mock WebDAV client."""
    client = MagicMock()
    client.test_connection.return_value = True
    client.list_remote_files.return_value = []
    client.upload_file.return_value = True
    client.download_file.return_value = True
    return client


@pytest.fixture
def mock_conflict_resolver():
    """Create a mock conflict resolver."""
    resolver = MagicMock()
    resolver.detect_conflict.return_value = None
    return resolver
