"""Logging and the lazily loaded, digest-verified catalog singleton."""

from __future__ import annotations

from pathlib import Path

import pytest

import strchive_link.mcp.service_adapters as adapters
from strchive_link.exceptions import DataUnavailableError
from strchive_link.logging_config import configure_logging

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "STRchive-loci.json"


def test_configure_logging_returns_logger() -> None:
    logger = configure_logging()
    assert logger is not None
    logger.info("test event", k="v")


async def test_local_path_is_loaded_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    adapters.set_catalog(None)
    monkeypatch.setattr(adapters.settings.data, "local_path", FIXTURE)
    try:
        first = await adapters.get_catalog()
        assert len(first.loci) == 82
        assert await adapters.get_catalog() is first
        assert adapters.peek_catalog() is first
    finally:
        adapters.set_catalog(None)


async def test_failed_load_is_not_cached(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    adapters.set_catalog(None)
    monkeypatch.setattr(adapters.settings.data, "local_path", tmp_path / "missing.json")
    with pytest.raises(DataUnavailableError):
        await adapters.get_catalog()
    assert adapters.peek_catalog() is None
    monkeypatch.setattr(adapters.settings.data, "local_path", FIXTURE)
    try:
        assert len((await adapters.get_catalog()).loci) == 82
    finally:
        adapters.set_catalog(None)


async def test_tampered_local_copy_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tampered = tmp_path / "loci.json"
    tampered.write_bytes(FIXTURE.read_bytes().replace(b'"HTT"', b'"HTX"', 1))
    adapters.set_catalog(None)
    monkeypatch.setattr(adapters.settings.data, "local_path", tampered)
    with pytest.raises(DataUnavailableError):
        await adapters.get_catalog()
    adapters.set_catalog(None)
