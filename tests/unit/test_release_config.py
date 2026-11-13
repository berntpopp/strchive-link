"""container-release.json must seal the same data identity the server enforces.

The release manifest requires release_tag + digest for an upstream-live service;
v0.1.0 was published without them and its evidence assembly failed closed.
"""

from __future__ import annotations

import json
from pathlib import Path

from strchive_link.catalog import PINNED_COMMIT, PINNED_SHA256

CONFIG = Path(__file__).resolve().parents[2] / "container-release.json"


def test_release_config_seals_the_pinned_data_identity() -> None:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))["data"]
    assert data["mode"] == "upstream-live"
    assert data["release_tag"] == f"strchive-{PINNED_COMMIT}"
    assert data["digest"] == f"sha256:{PINNED_SHA256}"
