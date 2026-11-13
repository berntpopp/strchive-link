"""Tests for the capabilities/discovery surface."""

from __future__ import annotations

from typing import Any

import pytest

from strchive_link.catalog import PINNED_COMMIT, PINNED_SHA256
from strchive_link.mcp.capabilities import (
    TOOLS,
    build_capabilities,
    collect_tool_signatures,
    project_capabilities,
)


def test_build_capabilities_core() -> None:
    cap = build_capabilities()
    assert cap["server"] == "strchive-link"
    assert cap["tool_count"] == len(TOOLS)
    assert cap["default_response_mode"] == "compact"
    assert cap["read_only"] is True
    assert cap["data_source"]["commit"] == PINNED_COMMIT
    assert cap["data_source"]["sha256"] == PINNED_SHA256
    assert "CC BY 4.0" in cap["license"]
    assert cap["research_use_only"] is True


def test_capabilities_surfaces_build_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRCHIVE_LINK_GIT_SHA", "abc123def456")
    cap = build_capabilities()
    assert cap["build"]["git_sha"] == "abc123def456"


def test_project_summary_vs_full() -> None:
    sigs = {t: f"{t}()" for t in TOOLS}
    assert "usage" not in project_capabilities("summary", sigs)
    assert "usage" in project_capabilities("full", sigs)


async def test_signatures_cover_every_registered_tool(facade: Any) -> None:
    sigs = await collect_tool_signatures(facade)
    assert set(sigs) == set(TOOLS)
    assert sigs["get_locus"].startswith("get_locus(")
