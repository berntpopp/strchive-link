"""Project a validated locus into the response_mode tiers, fencing every prose field."""

from __future__ import annotations

import re
from typing import Any, Literal

from strchive_link.catalog import ASSEMBLIES, RANGE_CATEGORIES, Locus, range_block
from strchive_link.constants import COORDINATE_CONVENTION, SOURCE_NAME
from strchive_link.mcp.untrusted_content import UntrustedText, fence_untrusted_text

ResponseModeValue = Literal["minimal", "compact", "standard", "full"]
RESPONSE_MODES: tuple[str, ...] = ("minimal", "compact", "standard", "full")
DEFAULT_RESPONSE_MODE = "compact"

# Upstream prose. Served only fenced (Response-Envelope v1.1). `details` carries the
# source's range qualifiers (e.g. reduced-penetrance or premutation bands), so it is
# served from `compact`; the rest from `standard`.
PROSE_FIELDS: tuple[str, ...] = (
    "disease_description",
    "mechanism_detail",
    "detection",
    "age_onset",
    "location_in_gene",
)
FULL_PROSE_FIELDS: tuple[str, ...] = ("prevalence_details", "year")
_XREF_FIELDS: tuple[str, ...] = (
    "orphanet",
    "gard",
    "medgen",
    "genereviews",
    "malacard",
    "gnomad",
    "stripy",
    "tr_atlas",
    "webstr_hg38",
    "webstr_hg19",
)
_HPO_ID = re.compile(r"^HP:\d{7}")


def fenced(locus: Locus, field: str) -> dict[str, Any] | None:
    """A prose field as a JSON-ready fenced object, or None when the source has none."""
    obj = _fence(locus, field)
    return None if obj is None else obj.model_dump(mode="json")


def _fence(locus: Locus, field: str) -> UntrustedText | None:
    raw = getattr(locus, field)
    if raw is None:
        return None
    return fence_untrusted_text(raw, source=SOURCE_NAME, record_id=f"{locus.id}#{field}")


def _ranges(locus: Locus) -> dict[str, Any]:
    block: dict[str, Any] = {"unit": "repeat_units"}
    for category in RANGE_CATEGORIES:
        block[category] = range_block(locus, category)
    return block


def _coordinates(locus: Locus) -> dict[str, Any]:
    coords: dict[str, Any] = {"chrom": locus.chrom, "convention": COORDINATE_CONVENTION}
    for assembly in ASSEMBLIES:
        start = getattr(locus, f"start_{assembly}")
        end = getattr(locus, f"stop_{assembly}")
        coords[assembly] = (
            {"start": start, "end": end}
            if start is not None and end is not None
            else {"start": None, "end": None, "status": "not_stated_by_source"}
        )
    return coords


def _motifs(locus: Locus) -> dict[str, Any]:
    def pair(kind: str) -> dict[str, list[str]]:
        return {
            "gene_orientation": list(getattr(locus, f"{kind}_motif_gene_orientation")),
            "reference_orientation": list(getattr(locus, f"{kind}_motif_reference_orientation")),
        }

    return {
        "gene_strand": locus.gene_strand,
        "motif_length": locus.motif_len,
        "reference_motif_reference_orientation": list(locus.reference_motif_reference_orientation),
        "pathogenic": pair("pathogenic"),
        "benign": pair("benign"),
        "unknown": pair("unknown"),
        "interruptions": {
            "gene_orientation": list(locus.interruption_gene_orientation),
            "reference_orientation": list(locus.interruption_reference_orientation),
        },
        "multiple_pathogenic_motifs": len(locus.pathogenic_motif_gene_orientation) > 1,
        "pathogenic_motif_in_hg38_reference": locus.novel,
        "reference_copies_hg38": locus.ref_copies,
    }


def project_locus(locus: Locus, mode: str) -> dict[str, Any]:
    """The single-record payload for ``get_locus`` at a response_mode."""
    out: dict[str, Any] = {
        "locus_id": locus.id,
        "gene": locus.gene,
        "disease_id": locus.disease_id,
        "disease": locus.disease,
        "repeat_ranges": _ranges(locus),
    }
    if mode == "minimal":
        return out
    out.update(
        inheritance=list(locus.inheritance),
        evidence=list(locus.evidence),
        motifs=_motifs(locus),
        coordinates=_coordinates(locus),
        mondo_ids=[f"MONDO:{n}" for n in locus.mondo],
        omim_ids=list(locus.omim),
        omim_gene_ids=list(locus.omim_gene),
        references=list(locus.references),
    )
    details = fenced(locus, "details")
    if details is not None:
        out["details"] = details
    if mode == "compact":
        return out
    out.update(
        association_type=list(locus.association_type),
        mechanism=locus.mechanism,
        locus_structure=[element.model_dump() for element in locus.locus_structure],
        age_onset_range_years={"min": locus.age_onset_min, "max": locus.age_onset_max},
        typical_age_onset_years={"min": locus.typ_age_onset_min, "max": locus.typ_age_onset_max},
        prevalence=locus.prevalence,
        hpo_ids=[m.group(0) for t in locus.hpo_terms or [] if (m := _HPO_ID.match(t))],
        disease_tags=list(locus.disease_tags),
        locus_tags=list(locus.locus_tags),
    )
    fields = PROSE_FIELDS + (FULL_PROSE_FIELDS if mode == "full" else ())
    for field in fields:
        value = fenced(locus, field)
        if value is not None:
            out[field] = value
    if mode == "full":
        out["additional_literature"] = list(locus.additional_literature)
        out["cross_references"] = {f: list(getattr(locus, f)) for f in _XREF_FIELDS}
    return out


def project_row(locus: Locus, mode: str, matched_on: str) -> dict[str, Any]:
    """One search hit at a response_mode (no prose at any mode)."""
    row: dict[str, Any] = {"locus_id": locus.id, "gene": locus.gene}
    if mode == "minimal":
        return row
    row.update(
        matched_on=matched_on,
        disease_id=locus.disease_id,
        disease=locus.disease,
        inheritance=list(locus.inheritance),
        evidence=list(locus.evidence),
        pathogenic_motifs_gene_orientation=list(locus.pathogenic_motif_gene_orientation),
        pathogenic_min=locus.pathogenic_min,
    )
    if mode in ("standard", "full"):
        row["repeat_ranges"] = _ranges(locus)
        row["mondo_ids"] = [f"MONDO:{n}" for n in locus.mondo]
        row["omim_ids"] = list(locus.omim)
    if mode == "full":
        row["coordinates"] = _coordinates(locus)
        row["disease_tags"] = list(locus.disease_tags)
    return row
