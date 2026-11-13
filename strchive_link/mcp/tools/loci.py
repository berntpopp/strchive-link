"""Locus tools: search_loci, get_locus, compare_repeat_length."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from strchive_link.catalog import PINNED_COMMIT, compare_length
from strchive_link.constants import (
    MAX_SEARCH_LIMIT,
    RANGE_SEMANTICS,
    RECOMMENDED_CITATION,
    SOURCE_NAME,
)
from strchive_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from strchive_link.mcp.envelope import McpErrorContext, run_mcp_tool
from strchive_link.mcp.next_commands import after_locus, after_search, cmd
from strchive_link.mcp.service_adapters import get_catalog
from strchive_link.mcp.shaping import ResponseModeValue, fenced, project_locus, project_row

if TYPE_CHECKING:
    from fastmcp import FastMCP


ResponseMode = Annotated[
    ResponseModeValue,
    Field(
        description="Verbosity: minimal (ids + ranges) | compact (default; + motifs, "
        "coordinates, ids, references) | standard (+ fenced source prose, HPO ids) | "
        "full (+ cross-references, additional literature)."
    ),
]
LocusKey = Annotated[
    str,
    Field(
        min_length=1,
        max_length=64,
        description="STRchive locus id (e.g. HD_HTT), gene symbol (e.g. HTT), or the "
        "source's disease abbreviation (e.g. SCA3). Case-insensitive. A gene with several "
        "loci (ARX, HOXA13) returns ambiguous_query with the locus ids to choose from.",
        examples=["HTT", "HD_HTT", "RFC1"],
    ),
]

COMPARE_INTERPRETATION = (
    "Descriptive only: lists which STRchive-stated ranges contain this repeat count. "
    "It is not a diagnosis or a pathogenicity classification; ranges come from the "
    "literature and may overlap or be missing. The three categories can merge "
    "sub-ranges (e.g. reduced penetrance, premutation) that source_range_notes describes."
)


def _provenance(payload: dict[str, Any]) -> dict[str, Any]:
    payload["recommended_citation"] = RECOMMENDED_CITATION
    payload["_meta"] = {
        **payload.get("_meta", {}),
        "source": SOURCE_NAME,
        "data_version": f"strchive@{PINNED_COMMIT[:12]}",
    }
    return payload


def register_locus_tools(mcp: FastMCP) -> None:
    """Register the STRchive locus tools on a FastMCP instance."""

    @mcp.tool(
        name="search_loci",
        title="Search STRchive Loci",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"str", "locus", "search"},
        description=(
            "Search the STRchive catalog of tandem-repeat (STR) disease loci. query matches, "
            "in rank order: an exact locus id / gene symbol / disease abbreviation; a "
            "MONDO:/OMIM:/ORPHA: id; a repeat motif in either orientation (e.g. CAG, AAGGG); "
            "words in the disease name, then in source tags (e.g. 'ataxia'), then in the "
            "locus HPO phenotype labels. Each row's matched_on says which. Omit query to "
            "list every locus. Returns results with total/truncated/next_offset. "
            "Signature: search_loci(query=, limit=, offset=, response_mode=)."
        ),
    )
    async def search_loci(
        query: Annotated[
            str | None,
            Field(
                max_length=200,
                description="Gene, locus id, MONDO/OMIM/Orphanet id, motif, or disease words. "
                "Omit to list all loci.",
                examples=["ataxia", "CAG", "MONDO:0007739"],
            ),
        ] = None,
        limit: Annotated[
            int, Field(ge=1, le=MAX_SEARCH_LIMIT, description="Page size (1-100, default 20).")
        ] = 20,
        offset: Annotated[int, Field(ge=0, description="Rows to skip (default 0).")] = 0,
        response_mode: ResponseMode = "compact",
    ) -> dict[str, Any]:
        async def call() -> dict[str, Any]:
            hits = (await get_catalog()).search_scored(query)
            page = [
                project_row(loc, response_mode, why) for loc, why in hits[offset : offset + limit]
            ]
            more = offset + len(page) < len(hits)
            return _provenance(
                {
                    "results": page,
                    "total": len(hits),
                    "returned": len(page),
                    "offset": offset,
                    "truncated": more,
                    "next_offset": offset + len(page) if more else None,
                    "_meta": {
                        "pagination": {"total_count": len(hits), "has_more": more},
                        "next_commands": after_search(page),
                    },
                }
            )

        return await run_mcp_tool(
            "search_loci", call, context=McpErrorContext("search_loci", arguments={"query": query})
        )

    @mcp.tool(
        name="get_locus",
        title="Get STRchive Locus",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"str", "locus"},
        description=(
            "Get one STRchive tandem-repeat disease locus: benign/intermediate/pathogenic "
            "repeat-count ranges exactly as the source states them (closed [min,max] in "
            "repeat units; a range the source does not state is null with status "
            "not_stated_by_source), pathogenic/benign/unknown motifs and interruptions in "
            "gene and reference orientation (all alternative pathogenic motifs, e.g. RFC1), "
            "inheritance, evidence level, hg38/hg19/T2T coordinates (BED 0-based half-open; "
            "never lifted over), MONDO/OMIM ids and PMIDs. "
            "Signature: get_locus(locus, response_mode=)."
        ),
    )
    async def get_locus(locus: LocusKey, response_mode: ResponseMode = "compact") -> dict[str, Any]:
        async def call() -> dict[str, Any]:
            record = (await get_catalog()).get(locus)
            payload = {"result": project_locus(record, response_mode)}
            payload["range_semantics"] = RANGE_SEMANTICS
            payload["_meta"] = {"next_commands": after_locus(record.id)}
            return _provenance(payload)

        return await run_mcp_tool(
            "get_locus", call, context=McpErrorContext("get_locus", arguments={"locus": locus})
        )

    @mcp.tool(
        name="compare_repeat_length",
        title="Compare Repeat Length to STRchive Ranges",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"str", "locus"},
        description=(
            "Compare an observed repeat count (repeat units, i.e. motif copies) with the "
            "ranges STRchive states for one locus and list every range that contains it "
            "(overlapping ranges can both match; none may match). Descriptive only, NOT a "
            "diagnosis. motif_dependent=true flags loci (e.g. RFC1) where motif identity, "
            "not length alone, decides the category. "
            "Signature: compare_repeat_length(locus, repeat_count)."
        ),
    )
    async def compare_repeat_length(
        locus: LocusKey,
        repeat_count: Annotated[
            int,
            Field(
                ge=0,
                le=1_000_000,
                description="Observed allele size in repeat units (copies of the motif), "
                "not base pairs.",
                examples=[38, 45],
            ),
        ],
    ) -> dict[str, Any]:
        async def call() -> dict[str, Any]:
            record = (await get_catalog()).get(locus)
            result = compare_length(record, repeat_count)
            result["unit"] = "repeat_units"
            result["interpretation"] = COMPARE_INTERPRETATION
            notes = fenced(record, "details")
            if notes is not None:
                result["source_range_notes"] = notes
            next_step = [cmd("get_locus", locus=record.id, response_mode="standard")]
            payload = {"result": result, "_meta": {"next_commands": next_step}}
            return _provenance(payload)

        return await run_mcp_tool(
            "compare_repeat_length",
            call,
            context=McpErrorContext("compare_repeat_length", arguments={"locus": locus}),
        )
