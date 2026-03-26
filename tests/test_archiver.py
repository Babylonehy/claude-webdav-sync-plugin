"""Tests for archiver module."""

import json
import tarfile
from pathlib import Path
import pytest

from webdav_sync.archiver import (
    sha256_file,
    build_manifest,
    create_archive,
    extract_archive,
    diff_manifests,
    manifests_equal,
)


@pytest.fixture
def home(tmp_path):
    """Fake home with some files."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text('{"a": 1}')
    (tmp_path / ".claude" / "history.jsonl").write_text('{"type":"msg"}\n')
    (tmp_path / ".claude.json").write_text('{"user": "test"}')
    return tmp_path


@pytest.fixture
def files(home):
    return [
        home / ".claude" / "settings.json",
        home / ".claude" / "history.jsonl",
        home / ".claude.json",
    ]


class TestSha256File:
    def test_consistent(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"hello")
        assert sha256_file(f) == sha256_file(f)

    def test_different_content(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"hello")
        b.write_bytes(b"world")
        assert sha256_file(a) != sha256_file(b)


class TestBuildManifest:
    def test_contains_all_files(self, files, home):
        m = build_manifest(files, home)
        assert set(m["files"].keys()) == {
            ".claude/settings.json",
            ".claude/history.jsonl",
            ".claude.json",
        }

    def test_file_entry_fields(self, files, home):
        m = build_manifest(files, home)
        entry = m["files"][".claude/settings.json"]
        assert "sha256" in entry
        assert "size" in entry
        assert "mtime" in entry
        assert len(entry["sha256"]) == 64

    def test_skips_missing_files(self, home):
        missing = home / "does_not_exist.json"
        m = build_manifest([missing], home)
        assert m["files"] == {}

    def test_archive_sha256_field(self, files, home):
        m = build_manifest(files, home, archive_sha256="abc123")
        assert m["archive_sha256"] == "abc123"


class TestCreateAndExtractArchive:
    def test_roundtrip(self, files, home, tmp_path):
        archive = create_archive(files, home)
        try:
            dest = tmp_path / "extracted"
            dest.mkdir()
            extracted = extract_archive(archive, dest)
            assert ".claude/settings.json" in extracted
            assert (dest / ".claude" / "settings.json").read_text() == '{"a": 1}'
        finally:
            archive.unlink(missing_ok=True)

    def test_is_valid_tar_gz(self, files, home):
        archive = create_archive(files, home)
        try:
            assert tarfile.is_tarfile(str(archive))
        finally:
            archive.unlink(missing_ok=True)

    def test_extract_only_these(self, files, home, tmp_path):
        archive = create_archive(files, home)
        try:
            dest = tmp_path / "partial"
            dest.mkdir()
            extracted = extract_archive(
                archive, dest, only_these={".claude/settings.json"}
            )
            assert extracted == [".claude/settings.json"]
            assert not (dest / ".claude.json").exists()
        finally:
            archive.unlink(missing_ok=True)

    def test_creates_parent_dirs(self, files, home, tmp_path):
        archive = create_archive(files, home)
        try:
            dest = tmp_path / "new_home"
            dest.mkdir()
            extract_archive(archive, dest)
            assert (dest / ".claude" / "settings.json").exists()
        finally:
            archive.unlink(missing_ok=True)


class TestDiffManifests:
    def test_all_up_to_date(self, files, home):
        m = build_manifest(files, home)
        changed, missing = diff_manifests(m, home)
        assert changed == set()
        assert missing == set()

    def test_detects_changed_file(self, files, home):
        m = build_manifest(files, home)
        # Modify a file after building manifest
        (home / ".claude" / "settings.json").write_text('{"a": 2}')
        changed, missing = diff_manifests(m, home)
        assert ".claude/settings.json" in changed

    def test_detects_missing_file(self, files, home):
        m = build_manifest(files, home)
        (home / ".claude.json").unlink()
        changed, missing = diff_manifests(m, home)
        assert ".claude.json" in missing


class TestManifestsEqual:
    def test_equal(self, files, home):
        m = build_manifest(files, home)
        assert manifests_equal(m, m) is True

    def test_different_sha256(self, files, home):
        m1 = build_manifest(files, home)
        m2 = build_manifest(files, home)
        m2["files"][".claude.json"]["sha256"] = "different"
        assert manifests_equal(m1, m2) is False

    def test_different_keys(self, files, home):
        m1 = build_manifest(files, home)
        m2 = build_manifest(files[:2], home)  # fewer files
        assert manifests_equal(m1, m2) is False
