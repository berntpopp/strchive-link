"""End-to-end tool behaviour through the FastMCP facade, against the pinned snapshot."""

from __future__ import annotations

import json
from typing import Any

EXPECTED_TOOLS = {
    "get_server_capabilities",
    "get_diagnostics",
    "search_loci",
    "get_locus",
    "compare_repeat_length",
}


async def _call(facade: Any, structured: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    return structured(await facade.call_tool(name, args))


async def test_tool_inventory(facade: Any) -> None:
    assert {t.name for t in await facade.list_tools()} == EXPECTED_TOOLS


async def test_get_locus_htt_ranges_units_and_convention(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_locus", {"locus": "HTT"})
    assert env["success"] is True
    result = env["result"]
    assert result["locus_id"] == "HD_HTT"
    ranges = result["repeat_ranges"]
    assert ranges["unit"] == "repeat_units"
    assert ranges["pathogenic"] == {"min": 36, "max": 250}
    assert ranges["intermediate"] == {"min": 27, "max": 35}
    coords = result["coordinates"]
    assert coords["convention"].startswith("BED")
    assert set(coords) >= {"hg38", "hg19", "t2t"}
    assert "STRchive" in env["recommended_citation"]
    assert env["_meta"]["unsafe_for_clinical_use"] is True
    assert env["_meta"]["data_version"].startswith("strchive@")


async def test_get_locus_rfc1_lists_every_pathogenic_motif(facade: Any, structured: Any) -> None:
    result = (await _call(facade, structured, "get_locus", {"locus": "RFC1"}))["result"]
    motifs = result["motifs"]
    assert motifs["pathogenic"]["gene_orientation"] == ["CCCTT", "CCTGT", "CCTTT", "CCCTG"]
    assert motifs["pathogenic"]["reference_orientation"] == ["AAGGG", "ACAGG", "AAAGG", "CAGGG"]
    assert motifs["multiple_pathogenic_motifs"] is True


async def test_get_locus_missing_range_is_explicit(facade: Any, structured: Any) -> None:
    result = (await _call(facade, structured, "get_locus", {"locus": "SCA31_BEAN1"}))["result"]
    assert result["repeat_ranges"]["intermediate"]["status"] == "not_stated_by_source"
    assert result["repeat_ranges"]["intermediate"]["min"] is None


async def test_free_text_is_fenced_at_standard(facade: Any, structured: Any) -> None:
    result = (
        await _call(facade, structured, "get_locus", {"locus": "HTT", "response_mode": "standard"})
    )["result"]
    fenced = result["disease_description"]
    assert fenced["kind"] == "untrusted_text"
    assert fenced["provenance"]["source"] == "strchive"
    assert fenced["provenance"]["record_id"] == "HD_HTT#disease_description"
    assert len(fenced["raw_sha256"]) == 64


async def test_compact_carries_no_unfenced_prose(facade: Any, structured: Any) -> None:
    result = (await _call(facade, structured, "get_locus", {"locus": "HTT"}))["result"]
    assert "disease_description" not in result
    assert "details" not in result


async def test_get_locus_ambiguous_gene_lists_candidates(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_locus", {"locus": "ARX"})
    assert env["success"] is False
    assert env["error_code"] == "ambiguous_query"
    assert len(env["candidates"]) == 2
    assert env["_meta"]["next_commands"][0]["tool"] == "get_locus"


async def test_get_locus_unknown_is_not_found(facade: Any, structured: Any) -> None:
    res = await facade.call_tool("get_locus", {"locus": "NOPE1"})
    env = structured(res)
    assert res.is_error is True if hasattr(res, "is_error") else True
    assert env["error_code"] == "not_found"


async def test_gene_alias_argument_is_accepted(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_locus", {"gene_symbol": "FMR1"})
    assert env["result"]["locus_id"] == "FXS_FMR1"


async def test_search_loci_ataxia_is_bounded_and_honest(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "search_loci", {"query": "ataxia", "limit": 2})
    assert env["success"] is True
    assert len(env["results"]) == 2
    assert env["total"] > 2
    assert env["truncated"] is True
    assert env["_meta"]["pagination"]["has_more"] is True
    assert env["next_offset"] == 2


async def test_search_total_is_invariant_under_limit(facade: Any, structured: Any) -> None:
    small = await _call(facade, structured, "search_loci", {"query": "ataxia", "limit": 2})
    large = await _call(facade, structured, "search_loci", {"query": "ataxia", "limit": 4})
    assert small["total"] == large["total"]


async def test_search_no_match_is_honest_empty(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "search_loci", {"query": "zzzqqq"})
    assert env["success"] is True
    assert env["results"] == []
    assert env["total"] == 0
    assert env["truncated"] is False


async def test_search_response_modes_differ(facade: Any, structured: Any) -> None:
    compact = await _call(facade, structured, "search_loci", {"query": "CAG"})
    full = await _call(facade, structured, "search_loci", {"query": "CAG", "response_mode": "full"})
    minimal = await _call(
        facade, structured, "search_loci", {"query": "CAG", "response_mode": "minimal"}
    )
    assert compact["results"] != full["results"]
    assert minimal["results"] and set(minimal["results"][0]) == {"locus_id", "gene"}


async def test_compare_htt_38(facade: Any, structured: Any) -> None:
    env = await _call(
        facade, structured, "compare_repeat_length", {"locus": "HTT", "repeat_count": 38}
    )
    result = env["result"]
    assert result["matching_categories"] == ["pathogenic"]
    assert result["unit"] == "repeat_units"
    assert "not a diagnosis" in result["interpretation"]


async def test_compare_negative_count_is_invalid_input(facade: Any, structured: Any) -> None:
    env = await _call(
        facade, structured, "compare_repeat_length", {"locus": "HTT", "repeat_count": -1}
    )
    assert env["error_code"] == "invalid_input"
    assert env["field"] == "repeat_count"


async def test_diagnostics_reports_pin(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_diagnostics", {})
    assert env["data_available"] is True
    assert env["locus_count"] == 82
    assert env["source"]["commit"] == "e964fa88df3b2189ee478cbd6eaad15bb28e3a0a"
    assert env["source"]["sha256"] == env["source"]["expected_sha256"]


async def test_capabilities_summary_lists_tools_and_license(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_server_capabilities", {})
    assert set(env["tools"]) == EXPECTED_TOOLS
    assert "CC BY 4.0" in env["license"]
    json.dumps(env)
