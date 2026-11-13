"""Static provenance: citation, license, attribution, and the research-use notice."""

from __future__ import annotations

from strchive_link.catalog import PINNED_COMMIT, PINNED_COMMIT_DATE

SOURCE_NAME = "strchive"

RECOMMENDED_CITATION = (
    "STRchive by Harriet Dashnow et al., CC BY 4.0 (https://strchive.org; data "
    f"dashnowlab/STRchive@{PINNED_COMMIT[:7]}, {PINNED_COMMIT_DATE}). Hiatt L, Weisburd B, "
    "Dolzhenko E, Rubinetti V, Avvaru AK, VanNoy GE, Kurtas NE, Rehm HL, Quinlan AR, "
    "Dashnow H. STRchive: a dynamic resource detailing population-level and locus-specific "
    "insights at tandem repeat disease loci. Genome Med. 2025. doi:10.1186/s13073-025-01454-4"
)

LICENSE = (
    "STRchive data (data/STRchive-loci.json) are licensed CC BY 4.0 by Harriet Dashnow "
    "et al. (https://creativecommons.org/licenses/by/4.0/); attribution is required. "
    "The STRchive code is MIT. strchive-link serves the data unmodified apart from "
    "reshaping into this envelope."
)

RESEARCH_USE_NOTICE = (
    "Research use only; not for clinical decision support, diagnosis, "
    "treatment, or patient management."
)

RANGE_SEMANTICS = {
    "unit": "repeat_units",
    "unit_description": "copies of the repeat motif, as stated by STRchive",
    "interval": "closed [min, max] per category, exactly as stated by the source",
    "missing": "a category the source does not state is null with status not_stated_by_source",
    "overlap": "overlapping or adjacent ranges are kept as the source states them, not merged",
}

COORDINATE_CONVENTION = "BED: 0-based start, half-open end (as published by STRchive)"

MAX_SEARCH_LIMIT = 100
