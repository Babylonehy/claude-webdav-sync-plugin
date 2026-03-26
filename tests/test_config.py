"""Tests for configuration module."""

import os
from pathlib import Path
import pytest
from unittest.mock import patch

from webdav_sync.config import WebDAVConfig, SyncPaths


class TestWebDAVConfig:
    """Tests for WebDAVConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WebDAVConfig()

        assert config.webdav_url == ""
        assert config.username == ""
        assert config.password == ""
        assert config.auto_sync is False
        assert config.sync_on_startup is False
        assert config.sync_on_shutdown is False
        assert len(config.exclude_patterns) == 4

    def test_is_configured(self):
        """Test is_configured method."""
        config = WebDAVConfig()
        assert config.is_configured() is False

        config.webdav_url = "https://example.com"
        assert config.is_configured() is False

        config.username = "user"
        assert config.is_configured() is True

    def test_save_and_load(self, temp_config_dir, sample_config):
        """Test saving and loading configuration."""
        with patch.object(
            WebDAVConfig, "config_path", return_value=temp_config_dir / "config.yaml"
        ):
            sample_config.save()

            loaded = WebDAVConfig.load()

            assert loaded.webdav_url == sample_config.webdav_url
            assert loaded.username == sample_config.username
            assert loaded.password == sample_config.password
            assert loaded.auto_sync == sample_config.auto_sync
            assert loaded.sync_on_startup == sample_config.sync_on_startup
            assert loaded.sync_on_shutdown == sample_config.sync_on_shutdown

    def test_load_missing_config(self, temp_config_dir):
        """Test loading when config file doesn't exist."""
        with patch.object(
            WebDAVConfig,
            "config_path",
            return_value=temp_config_dir / "nonexistent.yaml",
        ):
            config = WebDAVConfig.load()

            assert config.webdav_url == ""
            assert config.username == ""

    def test_config_path(self):
        """Test config path is correct."""
        path = WebDAVConfig.config_path()
        assert ".claude" in str(path)
        assert "webdav-sync" in str(path)
        assert path.suffix == ".yaml"


class TestSyncPaths:
    """Tests for SyncPaths class."""

    def test_default_paths(self):
        """Test default sync paths."""
        paths = SyncPaths()

        assert len(paths.ALWAYS_SYNC) == 4
        assert len(paths.HISTORY_SYNC) == 1
        assert "~/.claude.json" in paths.ALWAYS_SYNC

    def test_expand_path(self):
        """Test path expansion."""
        expanded = SyncPaths.expand_path("~/test/path")
        assert str(expanded).endswith("test/path")
        assert "~" not in str(expanded)

    def test_get_all_sync_paths(self, temp_home):
        """Test getting all sync paths."""
        with patch("webdav_sync.config.Path.home", return_value=temp_home):
            paths = SyncPaths()
            all_paths = paths.get_all_sync_paths()

            assert len(all_paths) > 0
            path_names = [p.name for p in all_paths]
            assert ".claude.json" in path_names
            assert "history.jsonl" in path_names

    def test_get_config_paths(self, temp_home):
        """Test getting config paths only."""
        with patch("webdav_sync.config.Path.home", return_value=temp_home):
            paths = SyncPaths()
            config_paths = paths.get_config_paths()

            assert len(config_paths) == 4
            for p in config_paths:
                assert p.suffix == ".json"

    def test_get_history_paths(self, temp_home):
        """Test getting history paths only."""
        with patch("webdav_sync.config.Path.home", return_value=temp_home):
            paths = SyncPaths()
            history_paths = paths.get_history_paths()

            assert len(history_paths) >= 1
            for p in history_paths:
                assert p.suffix == ".jsonl"

    def test_get_sync_paths_nonexistent_projects(self, temp_home):
        """Test getting paths when projects dir doesn't exist."""
        with patch("webdav_sync.config.Path.home", return_value=temp_home):
            paths = SyncPaths()
            paths.PROJECTS_DIR = "~/nonexistent"
            all_paths = paths.get_all_sync_paths()

            assert len(all_paths) > 0
