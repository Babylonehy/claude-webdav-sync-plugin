"""Configuration management for WebDAV sync plugin."""

import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import yaml


@dataclass
class WebDAVConfig:
    """WebDAV connection and sync configuration."""

    webdav_url: str = ""
    username: str = ""
    password: str = ""
    auto_sync: bool = False
    sync_on_startup: bool = False
    sync_on_shutdown: bool = False
    exclude_patterns: List[str] = field(
        default_factory=lambda: [
            "telemetry/*",
            "debug/*",
            "shell-snapshots/*",
            "statsig/*",
        ]
    )

    @classmethod
    def config_path(cls) -> Path:
        return (
            Path.home() / ".claude" / "plugins" / "data" / "webdav-sync" / "config.yaml"
        )

    @classmethod
    def load(cls) -> "WebDAVConfig":
        path = cls.config_path()
        if path.exists():
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
                return cls(
                    **{k: v for k, v in data.items() if k in cls.__dataclass_fields__}
                )
        return cls()

    def save(self) -> None:
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(asdict(self), f, default_flow_style=False)

    def is_configured(self) -> bool:
        return bool(self.webdav_url and self.username)


@dataclass
class SyncPaths:
    """Paths to synchronize between machines."""

    ALWAYS_SYNC: List[str] = field(
        default_factory=lambda: [
            "~/.claude.json",
            "~/.claude/settings.json",
            "~/.claude/config.json",
            "~/.config/opencode/opencode.json",
        ]
    )

    HISTORY_SYNC: List[str] = field(
        default_factory=lambda: [
            "~/.claude/history.jsonl",
        ]
    )

    PROJECTS_DIR: str = "~/.claude/projects"

    @staticmethod
    def expand_path(path: str) -> Path:
        return Path(os.path.expanduser(path))

    def get_all_sync_paths(self) -> List[Path]:
        """Get all paths that should be synced."""
        paths = []
        for p in self.ALWAYS_SYNC + self.HISTORY_SYNC:
            expanded = self.expand_path(p)
            if expanded.exists():
                paths.append(expanded)
        projects_dir = self.expand_path(self.PROJECTS_DIR)
        if projects_dir.exists():
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for f in project.rglob("*.jsonl"):
                        paths.append(f)
        return paths

    def get_config_paths(self) -> List[Path]:
        """Get configuration file paths only."""
        paths = []
        for p in self.ALWAYS_SYNC:
            expanded = self.expand_path(p)
            if expanded.exists():
                paths.append(expanded)
        return paths

    def get_history_paths(self) -> List[Path]:
        """Get history file paths only."""
        paths = []
        for p in self.HISTORY_SYNC:
            expanded = self.expand_path(p)
            if expanded.exists():
                paths.append(expanded)
        projects_dir = self.expand_path(self.PROJECTS_DIR)
        if projects_dir.exists():
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for f in project.rglob("*.jsonl"):
                        paths.append(f)
        return paths
