"""The process-wide STRchive catalog, loaded lazily and cached once verified.

A failed load is not cached: the next tool call retries, so a transient GitHub
outage at boot heals itself without a scheduler. The snapshot is immutable (pinned
commit + digest), so a successful load never needs refreshing.
"""

from __future__ import annotations

import asyncio

from strchive_link.catalog import Catalog, fetch_catalog, parse_catalog
from strchive_link.config import settings
from strchive_link.exceptions import DataUnavailableError

_catalog: Catalog | None = None
_lock = asyncio.Lock()


async def get_catalog() -> Catalog:
    """Return the verified catalog, loading it on first use (raises DataUnavailableError)."""
    global _catalog
    if _catalog is not None:
        return _catalog
    async with _lock:
        if _catalog is None:
            cfg = settings.data
            if cfg.local_path is not None:
                try:
                    raw = await asyncio.to_thread(cfg.local_path.read_bytes)
                except OSError as exc:
                    raise DataUnavailableError("Local STRchive snapshot is unreadable.") from exc
                _catalog = parse_catalog(raw, cfg.expected_sha256)
            else:
                _catalog = await fetch_catalog(
                    cfg.source_url,
                    cfg.expected_sha256,
                    timeout=cfg.download_timeout,
                    max_bytes=cfg.max_download_bytes,
                )
    return _catalog


def peek_catalog() -> Catalog | None:
    """The catalog if already loaded (never triggers a download)."""
    return _catalog


def set_catalog(catalog: Catalog | None) -> None:
    """Override the singleton (used by tests)."""
    global _catalog
    _catalog = catalog
