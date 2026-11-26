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
    assert result["details"]["kind"] == "untrusted_text"


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
    assert env["_meta"]["pagination"]["next_cursor"] is None
    assert env["_meta"]["pagination"]["next_offset"] == env["next_offset"]
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
    assert minimal["results"] and set(minimal["results"][0]) == {"locus_id", "gene", "matched_on"}


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


async def test_compact_locus_carries_fenced_range_details(facade: Any, structured: Any) -> None:
    result = (await _call(facade, structured, "get_locus", {"locus": "FMR1"}))["result"]
    assert result["details"]["kind"] == "untrusted_text"
    assert "disease_description" not in result


async def test_compare_surfaces_fenced_source_range_notes(facade: Any, structured: Any) -> None:
    env = await _call(
        facade, structured, "compare_repeat_length", {"locus": "HTT", "repeat_count": 38}
    )
    notes = env["result"]["source_range_notes"]
    assert notes["kind"] == "untrusted_text"
    assert notes["provenance"]["record_id"] == "HD_HTT#details"


async def test_search_rows_say_what_matched(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "search_loci", {"query": "ataxia", "limit": 100})
    basis = {row["locus_id"]: row["matched_on"] for row in env["results"]}
    assert basis["SCA3_ATXN3"] == "disease_name"
    assert basis["GDPAG_GLS"] == "hpo_phenotype"
    assert basis["EPM1_CSTB"] == "disease_tag"


async def test_abbreviation_prefix_is_ambiguous_not_missing(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_locus", {"locus": "DM"})
    assert env["error_code"] == "ambiguous_query"
    assert {c["locus_id"] for c in env["candidates"]} == {"DM1_DMPK", "DM2_CNBP"}


async def test_minimal_search_rows_keep_matched_on(facade: Any, structured: Any) -> None:
    env = await _call(
        facade, structured, "search_loci", {"query": "HTT", "response_mode": "minimal"}
    )
    assert env["results"][0]["matched_on"] == "id_or_gene"


async def test_next_commands_carry_every_required_argument(facade: Any, structured: Any) -> None:
    required = {t.name: set(t.parameters.get("required", [])) for t in await facade.list_tools()}
    for name, args in [
        ("get_locus", {"locus": "HTT"}),
        ("get_locus", {"locus": "HTT", "response_mode": "full"}),
        ("compare_repeat_length", {"locus": "HTT", "repeat_count": 38}),
        ("search_loci", {"query": "HTT"}),
    ]:
        for step in (await _call(facade, structured, name, args))["_meta"]["next_commands"]:
            assert required[step["tool"]] <= set(step["arguments"]), (name, step)


async def test_documented_prefix_example_is_true(facade: Any, structured: Any) -> None:
    env = await _call(facade, structured, "get_locus", {"locus": "FRA"})
    assert env["error_code"] == "ambiguous_query"
    assert {"FRA2A_AFF3", "FRA7A_ZNF713"} <= {c["locus_id"] for c in env["candidates"]}


async def test_descriptions_name_only_returned_fields(facade: Any, structured: Any) -> None:
    """Contract truth: every snake_case field a description names appears in a response."""
    import re

    samples = {
        "search_loci": {"query": "ataxia", "limit": 1},
        "get_locus": {"locus": "ABCD3"},  # no intermediate range -> not_stated_by_source
        "compare_repeat_length": {"locus": "RFC1", "repeat_count": 400},
    }
    tools = {t.name: t for t in await facade.list_tools()}
    for name, args in samples.items():
        prose = (tools[name].description or "").split("Signature:")[0]
        named = set(re.findall(r"\b[a-z]+(?:_[a-z0-9]+)+\b|\b(?:results|total|truncated)\b", prose))
        named -= set(tools[name].parameters.get("properties", {}))
        assert named, name
        body = json.dumps(await _call(facade, structured, name, args))
        missing = {f for f in named if f'"{f}"' not in body}
        assert not missing, f"{name} description names unreturned {missing}"


async def test_disease_name_miss_offers_weak_candidates_and_search(
    facade: Any, structured: Any
) -> None:
    """A free-text miss is an honest not_found with weak, in-catalog candidates to open."""
    from fastmcp import Client

    async with Client(facade) as client:
        hit = structured(
            await client.call_tool(
                "get_locus", {"locus": "Huntington disease"}, raise_on_error=False
            )
        )
        none = structured(
            await client.call_tool("get_locus", {"locus": "zzzz qqqq"}, raise_on_error=False)
        )
    assert hit["error_code"] == "not_found"
    assert [c["locus_id"] for c in hit["candidates"]] == ["HD_HTT", "HDL2_JPH3"]
    assert {(c["match"], c["matched_on"]) for c in hit["candidates"]} == {("weak", "disease_name")}
    assert hit["_meta"]["next_commands"][0] == {
        "tool": "get_locus",
        "arguments": {"locus": "HD_HTT"},
    }
    assert hit["_meta"]["next_commands"][-1] == {"tool": "search_loci", "arguments": {}}
    assert "candidates" not in none
    assert none["_meta"]["next_commands"] == [{"tool": "search_loci", "arguments": {}}]
    assert "mondo_resolve_disease" in none["message"]
