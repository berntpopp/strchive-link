"""Tests for the exception hierarchy and build info."""

from __future__ import annotations

from pathlib import Path

from strchive_link.buildinfo import _resolve_gitdir, _resolve_ref, build_info
from strchive_link.exceptions import NotFoundError, StrchiveError


def test_error_str_with_status() -> None:
    assert str(StrchiveError("boom", status_code=503)) == "[503] boom"
    assert str(StrchiveError("boom")) == "boom"
    assert NotFoundError().status_code == 404


def test_build_info_keys(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("STRCHIVE_LINK_GIT_SHA", "deadbeef")
    info = build_info()
    assert info["git_sha"] == "deadbeef"
    assert "version" in info


def test_build_info_falls_back_to_git(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("STRCHIVE_LINK_GIT_SHA", raising=False)
    monkeypatch.delenv("STRCHIVE_LINK_BUILT_AT", raising=False)
    info = build_info()
    # In a git checkout the sha resolves from .git; built_at falls back to a timestamp.
    assert info["git_sha"] != "unknown"
    assert info["built_at"] is not None


def test_git_sha_resolves_through_worktree_gitlink(tmp_path: Path) -> None:
    """A worktree ``.git`` is a gitlink file; refs live in the shared common dir."""
    sha = "0123456789abcdef0123456789abcdef01234567"
    ref = "refs/heads/feature/x"
    # Shared common dir holds the loose ref for the checked-out branch.
    common = tmp_path / "main.git"
    (common / "refs" / "heads" / "feature").mkdir(parents=True)
    (common / ref).write_text(sha + "\n", encoding="utf-8")
    # Per-worktree gitdir holds HEAD + a commondir pointer back to the common dir.
    wt_gitdir = common / "worktrees" / "x"
    wt_gitdir.mkdir(parents=True)
    (wt_gitdir / "HEAD").write_text(f"ref: {ref}\n", encoding="utf-8")
    (wt_gitdir / "commondir").write_text("../..\n", encoding="utf-8")
    # The checkout's ``.git`` is a file pointing at the per-worktree gitdir.
    gitlink = tmp_path / "checkout" / ".git"
    gitlink.parent.mkdir(parents=True)
    gitlink.write_text(f"gitdir: {wt_gitdir}\n", encoding="utf-8")

    git_dir = _resolve_gitdir(gitlink)
    assert git_dir == wt_gitdir
    common_dir = (git_dir / (git_dir / "commondir").read_text().strip()).resolve()
    assert _resolve_ref(ref, git_dir, common_dir) == sha[:12]
