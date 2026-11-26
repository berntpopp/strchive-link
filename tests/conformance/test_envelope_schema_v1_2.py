"""Response-Envelope v1.2: every tool result validates against the published JSON Schema.

The schema is vendored from https://github.com/berntpopp/genefoundry-envelope at tag v1.2.0.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).with_name("envelope-v1.2.schema.json")
SCHEMA_SHA256 = "c3c47e20d7dd189aac2568fc963b5514d7a5ac2c3e5f21d126f42c96d1ad1ae3"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

# Every data tool, at each response_mode it takes (get_server_capabilities and
# get_diagnostics are ops/meta tools, outside the v1.2 provenance rule).
DATA_CALLS: list[tuple[str, dict[str, Any]]] = [
    *[
        (tool, {**args, "response_mode": mode})
        for tool, args in (("search_loci", {"query": "ataxia"}), ("get_locus", {"locus": "HTT"}))
        for mode in ("minimal", "compact", "standard", "full")
    ],
    ("search_loci", {}),
    ("search_loci", {"query": "no-such-locus-xyz"}),
    ("compare_repeat_length", {"locus": "HTT", "repeat_count": 38}),
]
ERROR_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("get_locus", {"locus": "no-such-locus-xyz"}),
    ("get_locus", {"locus": "ARX"}),
    ("get_locus", {"wrong_argument": "HTT"}),
    ("no_such_tool", {}),
]


def test_vendored_schema_is_the_v1_2_0_release() -> None:
    assert hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest() == SCHEMA_SHA256


async def test_data_tools_cover_the_registered_tools(facade: Any) -> None:
    registered = {tool.name for tool in await facade.list_tools()}
    assert {name for name, _ in DATA_CALLS} == registered - {
        "get_server_capabilities",
        "get_diagnostics",
    }


@pytest.mark.parametrize(("tool", "arguments"), DATA_CALLS)
async def test_success_validates_and_carries_provenance(
    facade: Any, structured: Any, tool: str, arguments: dict[str, Any]
) -> None:
    envelope = structured(await facade.call_tool(tool, arguments))
    assert envelope["success"] is True
    jsonschema.validate(envelope, SCHEMA)
    meta = envelope["_meta"]
    assert meta["source"] == "strchive"
    assert meta["data_version"].startswith("strchive@")
    assert meta["retrieved_at"].endswith("Z")


@pytest.mark.parametrize(("tool", "arguments"), ERROR_CALLS)
async def test_error_validates(
    facade: Any, structured: Any, tool: str, arguments: dict[str, Any]
) -> None:
    from fastmcp import Client

    async with Client(facade) as client:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
    envelope = structured(result)
    assert envelope["success"] is False
    assert result.is_error is True
    jsonschema.validate(envelope, SCHEMA)


async def test_retrieved_at_is_the_snapshot_fetch_time_not_the_call_time(
    facade: Any, structured: Any, pinned_catalog: Any
) -> None:
    first = structured(await facade.call_tool("get_locus", {"locus": "HTT"}))
    second = structured(await facade.call_tool("search_loci", {"query": "CAG"}))
    assert first["_meta"]["retrieved_at"] == second["_meta"]["retrieved_at"]
    assert first["_meta"]["retrieved_at"] == pinned_catalog.retrieved_at
