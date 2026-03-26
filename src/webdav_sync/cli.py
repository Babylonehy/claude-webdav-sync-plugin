"""Command-line interface for WebDAV sync plugin."""

import sys
import click

from .config import WebDAVConfig
from .sync_manager import SyncManager


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """WebDAV Sync Plugin for Claude Code."""
    pass


@cli.command()
@click.option("--url", help="WebDAV server URL")
@click.option("--username", help="WebDAV username")
@click.option(
    "--password", help="WebDAV password (prompted if not provided)", default=None
)
@click.option("--auto-sync", is_flag=True, help="Enable automatic sync")
@click.option("--sync-on-startup", is_flag=True, help="Sync on Claude Code startup")
@click.option("--sync-on-shutdown", is_flag=True, help="Sync on Claude Code shutdown")
def configure(
    url: str,
    username: str,
    password: str,
    auto_sync: bool,
    sync_on_startup: bool,
    sync_on_shutdown: bool,
):
    """Configure WebDAV connection settings."""
    if not url:
        url = click.prompt("WebDAV URL", type=str)
    if not username:
        username = click.prompt("Username", type=str)
    if password is None:
        password = click.prompt("Password", type=str, hide_input=True)

    config = WebDAVConfig(
        webdav_url=url,
        username=username,
        password=password,
        auto_sync=auto_sync,
        sync_on_startup=sync_on_startup,
        sync_on_shutdown=sync_on_shutdown,
    )

    from .webdav_client import WebDAVClient

    client = WebDAVClient(config)

    click.echo("Testing connection...")
    if client.test_connection():
        click.echo("Connection successful!")
        config.save()
        click.echo("Configuration saved.")
    else:
        click.echo(
            "Error: Could not connect to WebDAV server. Please check your credentials."
        )
        sys.exit(1)


@cli.command()
@click.option(
    "--force", "-f", is_flag=True, help="Force push without conflict checking"
)
def push(force: bool = False):
    """Push local Claude Code data to WebDAV server."""
    config = WebDAVConfig.load()

    if not config.is_configured():
        click.echo("Error: WebDAV not configured. Run 'webdav-sync configure' first.")
        sys.exit(1)

    manager = SyncManager(config)

    click.echo("Pushing to WebDAV server...")
    result = manager.push(force=force)

    click.echo(f"\nPush complete:")
    click.echo(f"  Pushed: {result.pushed} files")
    click.echo(f"  Skipped: {result.skipped} files")
    click.echo(f"  Conflicts: {result.conflicts}")

    if result.errors:
        click.echo(f"\nErrors:")
        for err in result.errors:
            click.echo(f"  - {err}")
        sys.exit(1)


@cli.command()
@click.option(
    "--force", "-f", is_flag=True, help="Force pull without conflict checking"
)
def pull(force: bool = False):
    """Pull Claude Code data from WebDAV server."""
    config = WebDAVConfig.load()

    if not config.is_configured():
        click.echo("Error: WebDAV not configured. Run 'webdav-sync configure' first.")
        sys.exit(1)

    manager = SyncManager(config)

    click.echo("Pulling from WebDAV server...")
    result = manager.pull(force=force)

    click.echo(f"\nPull complete:")
    click.echo(f"  Pulled: {result.pulled} files")
    click.echo(f"  Skipped: {result.skipped} files")
    click.echo(f"  Conflicts: {result.conflicts}")

    if result.errors:
        click.echo(f"\nErrors:")
        for err in result.errors:
            click.echo(f"  - {err}")
        sys.exit(1)


@cli.command()
def status():
    """Show sync status and last sync time."""
    config = WebDAVConfig.load()
    manager = SyncManager(config)

    status_info = manager.status()

    click.echo("WebDAV Sync Status:")
    click.echo(f"  Configured: {'Yes' if status_info['configured'] else 'No'}")
    click.echo(f"  Connected: {'Yes' if status_info['connected'] else 'No'}")
    click.echo(f"  Last sync: {status_info['last_sync'] or 'Never'}")
    click.echo(f"  Last action: {status_info['last_action'] or 'N/A'}")


@cli.command("sync-startup")
def sync_startup():
    """Hook: Sync on startup (pull)."""
    config = WebDAVConfig.load()
    if config.sync_on_startup:
        click.echo("[WebDAV Sync] Auto-syncing on startup...")
        manager = SyncManager(config)
        manager.pull(force=True)
        click.echo("[WebDAV Sync] Startup sync complete.")


@cli.command("sync-shutdown")
def sync_shutdown():
    """Hook: Sync on shutdown (push)."""
    config = WebDAVConfig.load()
    if config.sync_on_shutdown:
        click.echo("[WebDAV Sync] Auto-syncing on shutdown...")
        manager = SyncManager(config)
        manager.push(force=True)
        click.echo("[WebDAV Sync] Shutdown sync complete.")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
