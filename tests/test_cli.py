"""Tests for CLI module."""

from click.testing import CliRunner
from unittest.mock import MagicMock, patch
import pytest

from webdav_sync.cli import cli


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "WebDAV Sync" in result.output

    def test_cli_version(self, runner):
        """Test CLI version command."""
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_status_not_configured(self, runner):
        """Test status command when not configured."""
        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            mock_load.return_value = MagicMock(
                is_configured=MagicMock(return_value=False)
            )

            result = runner.invoke(cli, ["status"])

            assert result.exit_code == 0
            assert "Configured: No" in result.output

    def test_status_configured(self, runner):
        """Test status command when configured."""
        mock_config = MagicMock()
        mock_config.is_configured.return_value = True

        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            with patch("webdav_sync.cli.SyncManager") as mock_manager:
                mock_load.return_value = mock_config
                mock_manager.return_value.status.return_value = {
                    "configured": True,
                    "connected": True,
                    "last_sync": "2024-01-01T00:00:00",
                    "last_action": "push",
                }

                result = runner.invoke(cli, ["status"])

                assert result.exit_code == 0
                assert "Configured: Yes" in result.output
                assert "Connected: Yes" in result.output

    def test_push_not_configured(self, runner):
        """Test push command when not configured."""
        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            mock_load.return_value = MagicMock(
                is_configured=MagicMock(return_value=False)
            )

            result = runner.invoke(cli, ["push"])

            assert result.exit_code == 1
            assert "not configured" in result.output.lower()

    def test_pull_not_configured(self, runner):
        """Test pull command when not configured."""
        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            mock_load.return_value = MagicMock(
                is_configured=MagicMock(return_value=False)
            )

            result = runner.invoke(cli, ["pull"])

            assert result.exit_code == 1
            assert "not configured" in result.output.lower()

    def test_configure_interactive(self, runner):
        """Test configure command with interactive input."""
        with patch("webdav_sync.webdav_client.WebDAVClient") as mock_client:
            with patch("webdav_sync.cli.WebDAVConfig.save") as mock_save:
                mock_client.return_value.test_connection.return_value = True

                result = runner.invoke(
                    cli, ["configure"], input="https://test.com\nuser\npass\n"
                )

                assert result.exit_code == 0
                assert "Connection successful" in result.output
                mock_save.assert_called_once()

    def test_configure_connection_failure(self, runner):
        """Test configure command with connection failure."""
        with patch("webdav_sync.webdav_client.WebDAVClient") as mock_client:
            mock_client.return_value.test_connection.return_value = False

            result = runner.invoke(
                cli, ["configure"], input="https://test.com\nuser\npass\n"
            )

            assert result.exit_code == 1
            assert "Could not connect" in result.output

    def test_push_force_flag(self, runner):
        """Test push with force flag."""
        mock_config = MagicMock()
        mock_config.is_configured.return_value = True

        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            with patch("webdav_sync.cli.SyncManager") as mock_manager:
                mock_load.return_value = mock_config
                mock_manager.return_value.push.return_value = MagicMock(
                    pushed=5, skipped=1, conflicts=0, errors=[], success=True
                )

                result = runner.invoke(cli, ["push", "--force"])

                assert result.exit_code == 0
                mock_manager.return_value.push.assert_called_with(force=True)

    def test_pull_force_flag(self, runner):
        """Test pull with force flag."""
        mock_config = MagicMock()
        mock_config.is_configured.return_value = True

        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            with patch("webdav_sync.cli.SyncManager") as mock_manager:
                mock_load.return_value = mock_config
                mock_manager.return_value.pull.return_value = MagicMock(
                    pulled=3, skipped=0, conflicts=0, errors=[], success=True
                )

                result = runner.invoke(cli, ["pull", "--force"])

                assert result.exit_code == 0
                mock_manager.return_value.pull.assert_called_with(force=True)

    def test_sync_startup_disabled(self, runner):
        """Test sync-startup when disabled."""
        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            mock_load.return_value.sync_on_startup = False

            result = runner.invoke(cli, ["sync-startup"])

            assert result.exit_code == 0
            assert "Auto-syncing" not in result.output

    def test_sync_shutdown_disabled(self, runner):
        """Test sync-shutdown when disabled."""
        with patch("webdav_sync.cli.WebDAVConfig.load") as mock_load:
            mock_load.return_value.sync_on_shutdown = False

            result = runner.invoke(cli, ["sync-shutdown"])

            assert result.exit_code == 0
            assert "Auto-syncing" not in result.output
