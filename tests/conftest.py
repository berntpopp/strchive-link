"""Shared fixtures: the pinned STRchive catalog and a facade wired to it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from strchive_link.catalog import PINNED_SHA256, Catalog, parse_catalog

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "STRchive-loci.json"


def _structured(result: Any) -> dict[str, Any]:
    """Read structured_content defensively (with TextContent JSON fallback)."""
    sc = result.structured_content
    if isinstance(sc, dict):
        return sc
    return json.loads(result.content[0].text)


@pytest.fixture
def structured() -> Any:
    """Expose the structured-content reader to tests."""
    return _structured


@pytest.fixture(scope="session")
def pinned_catalog() -> Catalog:
    """The pinned STRchive snapshot parsed once per session."""
    return parse_catalog(FIXTURE.read_bytes(), PINNED_SHA256)


@pytest.fixture
def facade(pinned_catalog: Catalog) -> Any:
    """A FastMCP facade with the pinned catalog injected; cleans up after."""
    from strchive_link.mcp.facade import create_strchive_mcp
    from strchive_link.mcp.service_adapters import set_catalog

    set_catalog(pinned_catalog)
    mcp = create_strchive_mcp()
    yield mcp
    set_catalog(None)
