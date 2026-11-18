"""The 2026-07-28 sessionless protocol era works end-to-end over HTTP (FastMCP 4)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from strchive_link.catalog import Catalog
from strchive_link.config import settings
from strchive_link.mcp.service_adapters import set_catalog
from strchive_link.server_manager import create_unified_app

_MODERN_VERSION = "2026-07-28"
_MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": _MODERN_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "strchive-host-test", "version": "1.0.0"},
}


def _headers(method: str, *, name: str | None = None) -> dict[str, str]:
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "host": "localhost",
        "mcp-protocol-version": _MODERN_VERSION,
        "mcp-method": method,
    }
    if name is not None:
        headers["mcp-name"] = name
    return headers


def _post(client: TestClient, rid: int, method: str, params: dict[str, Any]) -> Any:
    return client.post(
        settings.mcp_path,
        headers=_headers(method, name=params.get("name")),
        json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params},
    )


def test_modern_mcp_http_discovers_lists_calls_and_fences_unknown_tool(
    pinned_catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "allowed_hosts", ["localhost"])
    hostile = "ignore-instructions-secret"
    set_catalog(pinned_catalog)
    try:
        with TestClient(create_unified_app(), follow_redirects=False) as client:
            discover = _post(client, 1, "server/discover", {"_meta": _MODERN_META})
            listed = _post(client, 2, "tools/list", {"_meta": _MODERN_META})
            called = _post(
                client,
                3,
                "tools/call",
                {"_meta": _MODERN_META, "name": "get_server_capabilities", "arguments": {}},
            )
            unknown = _post(
                client, 4, "tools/call", {"_meta": _MODERN_META, "name": hostile, "arguments": {}}
            )
    finally:
        set_catalog(None)

    assert discover.status_code == 200
    assert discover.json()["result"]["supportedVersions"] == [_MODERN_VERSION]
    assert "mcp-session-id" not in discover.headers
    assert listed.status_code == 200
    assert {t["name"] for t in listed.json()["result"]["tools"]} >= {
        "get_server_capabilities",
        "get_locus",
    }
    assert called.status_code == 200
    called_result = called.json()["result"]
    assert json.loads(called_result["content"][0]["text"]) == called_result["structuredContent"]
    assert called_result["structuredContent"]["success"] is True
    assert unknown.status_code == 200
    unknown_result = unknown.json()["result"]
    assert unknown_result["isError"] is True
    assert json.loads(unknown_result["content"][0]["text"]) == unknown_result["structuredContent"]
    assert unknown_result["structuredContent"]["error_code"] == "not_found"
    assert hostile not in unknown.text
