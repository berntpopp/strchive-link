"""Discovery tools: get_server_capabilities, get_diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import Field

from strchive_link.catalog import PINNED_COMMIT, PINNED_COMMIT_DATE
from strchive_link.config import settings
from strchive_link.exceptions import DataUnavailableError
from strchive_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from strchive_link.mcp.capabilities import collect_tool_signatures, project_capabilities
from strchive_link.mcp.envelope import McpErrorContext, run_mcp_tool
from strchive_link.mcp.next_commands import cmd
from strchive_link.mcp.service_adapters import get_catalog

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register discovery tools on a FastMCP instance."""

    @mcp.tool(
        name="get_server_capabilities",
        title="Get Server Capabilities",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"discovery", "meta"},
        description=(
            "Return the strchive-link discovery surface: tools with call signatures, "
            "argument aliases, response modes, range/coordinate semantics, error codes, "
            "limits, data pin, license and citation. detail='full' adds the usage notes. "
            "Signature: get_server_capabilities(detail=)."
        ),
    )
    async def get_server_capabilities(
        detail: Annotated[
            Literal["summary", "full"],
            Field(description="summary (default) or full (adds usage notes)."),
        ] = "summary",
    ) -> dict[str, Any]:
        async def call() -> dict[str, Any]:
            return project_capabilities(detail, await collect_tool_signatures(mcp))

        return await run_mcp_tool(
            "get_server_capabilities",
            call,
            context=McpErrorContext("get_server_capabilities"),
        )

    @mcp.tool(
        name="get_diagnostics",
        title="Get Diagnostics",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"discovery", "meta"},
        description=(
            "Report whether the pinned STRchive snapshot is loaded and verified: upstream "
            "commit, expected vs actual SHA-256, and locus count. Use it to confirm the data "
            "version or diagnose an upstream_unavailable error. Signature: get_diagnostics()."
        ),
    )
    async def get_diagnostics() -> dict[str, Any]:
        async def call() -> dict[str, Any]:
            cfg = settings.data
            source: dict[str, Any] = {
                "repository": "dashnowlab/STRchive",
                "path": "data/STRchive-loci.json",
                "commit": PINNED_COMMIT,
                "commit_date": PINNED_COMMIT_DATE,
                "expected_sha256": cfg.expected_sha256,
                "sha256": None,
            }
            try:
                catalog = await get_catalog()
            except DataUnavailableError:
                return {
                    "data_available": False,
                    "locus_count": 0,
                    "source": source,
                    "_meta": {"next_commands": [cmd("get_server_capabilities")]},
                }
            source["sha256"] = catalog.sha256
            return {
                "data_available": True,
                "locus_count": len(catalog.loci),
                "source": source,
                "_meta": {"next_commands": [cmd("search_loci", query="ataxia")]},
            }

        return await run_mcp_tool(
            "get_diagnostics", call, context=McpErrorContext("get_diagnostics")
        )
