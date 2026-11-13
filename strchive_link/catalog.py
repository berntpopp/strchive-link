"""The pinned STRchive snapshot: fetch, verify, validate, index, search, compare.

STRchive publishes no tagged releases, so the snapshot is pinned to an exact upstream
commit AND the SHA-256 of ``data/STRchive-loci.json`` at that commit. The downloaded file
is untrusted input: its digest must match the pin, and every record is validated against
the field grammar below before any of it is served. Bumping the pin is a code change
(update both constants + the test fixture) and therefore a reviewed release.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Annotated, Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from strchive_link.exceptions import (
    AmbiguousQueryError,
    DataUnavailableError,
    InvalidInputError,
    NotFoundError,
)

PINNED_COMMIT = "e964fa88df3b2189ee478cbd6eaad15bb28e3a0a"
PINNED_COMMIT_DATE = "2026-10-08"
PINNED_SHA256 = "16301ecb00239f0e3c684913aefc2f48c6f5a7c2a481958aab4db55d282bca86"
SOURCE_URL = (
    f"https://raw.githubusercontent.com/dashnowlab/STRchive/{PINNED_COMMIT}/data/STRchive-loci.json"
)

RANGE_CATEGORIES: tuple[str, ...] = ("benign", "intermediate", "pathogenic")
ASSEMBLIES: tuple[str, ...] = ("hg38", "hg19", "t2t")

# Field grammars. Anything prose-shaped is either fenced at the MCP boundary
# (FreeText) or refused here; identifiers never carry whitespace.
Token = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/+?-]{0,63}$")]
Digits = Annotated[str, Field(pattern=r"^\d{1,12}$")]
Motif = Annotated[str, Field(pattern=r"^[ACGTN]{1,100}$")]
Reference = Annotated[str, Field(pattern=r"^[a-z]{2,12}:\S{1,300}$")]
HpoTerm = Annotated[str, Field(pattern=r"^HP:\d{7}( .{1,200})?$")]
Count = Annotated[int, Field(ge=0)] | None
Position = Annotated[int, Field(ge=0)] | None
FreeText = Annotated[str, Field(max_length=20_000)] | None


class StructureElement(BaseModel):
    """One element of the source's ordered locus structure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    motif: Motif
    count: Count
    type: Token


class Locus(BaseModel):
    """One validated STRchive locus record (fields the server serves)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: Token
    disease_id: Annotated[
        str,
        Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}(, [A-Za-z0-9][A-Za-z0-9_.-]{0,31}){0,9}$"),
    ]
    gene: Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")]
    disease: Annotated[str, Field(min_length=1, max_length=500)]
    chrom: Annotated[str, Field(pattern=r"^chr([1-9]|1[0-9]|2[0-2]|X|Y|M)$")]
    start_hg38: Position
    stop_hg38: Position
    start_hg19: Position
    stop_hg19: Position
    start_t2t: Position
    stop_t2t: Position
    evidence: list[Token]
    inheritance: list[Token]
    association_type: list[Token]
    mechanism: Token | None
    gene_strand: Literal["+", "-"]
    motif_len: Annotated[int, Field(ge=1)]
    ref_copies: Annotated[float, Field(ge=0)] | None
    novel: Literal["ref", "novel"] | None
    reference_motif_reference_orientation: list[Motif]
    pathogenic_motif_reference_orientation: list[Motif]
    benign_motif_reference_orientation: list[Motif]
    unknown_motif_reference_orientation: list[Motif]
    interruption_reference_orientation: list[Motif] = []
    pathogenic_motif_gene_orientation: list[Motif]
    benign_motif_gene_orientation: list[Motif]
    unknown_motif_gene_orientation: list[Motif]
    interruption_gene_orientation: list[Motif] = []
    locus_structure: list[StructureElement]
    benign_min: Count
    benign_max: Count
    intermediate_min: Count
    intermediate_max: Count
    pathogenic_min: Count
    pathogenic_max: Count
    mondo: list[Digits]
    omim: list[Digits]
    omim_gene: list[Digits]
    orphanet: list[Digits]
    gard: list[Token]
    medgen: list[Token]
    genereviews: list[Token]
    malacard: list[Token]
    gnomad: list[Token]
    stripy: list[Token]
    tr_atlas: list[Token]
    webstr_hg38: list[Token]
    webstr_hg19: list[Token]
    disease_tags: list[Token]
    locus_tags: list[Token]
    references: list[Reference]
    additional_literature: list[Reference]
    hpo_terms: list[HpoTerm] | None
    age_onset_min: float | None
    age_onset_max: float | None
    typ_age_onset_min: float | None
    typ_age_onset_max: float | None
    prevalence: Annotated[str, Field(pattern=r"^[0-9.]{1,12}/[0-9]{1,12}$")] | None
    year: FreeText
    location_in_gene: FreeText
    disease_description: FreeText
    details: FreeText
    detection: FreeText
    mechanism_detail: FreeText
    prevalence_details: FreeText
    age_onset: FreeText

    def range(self, category: str) -> tuple[int | None, int | None]:
        """Return the ``(min, max)`` repeat-unit range the source states for a category."""
        return getattr(self, f"{category}_min"), getattr(self, f"{category}_max")

    def all_motifs(self) -> set[str]:
        """Every motif named at this locus, in either orientation."""
        lists = (
            self.reference_motif_reference_orientation,
            self.pathogenic_motif_reference_orientation,
            self.benign_motif_reference_orientation,
            self.unknown_motif_reference_orientation,
            self.pathogenic_motif_gene_orientation,
            self.benign_motif_gene_orientation,
            self.unknown_motif_gene_orientation,
        )
        return {motif for motifs in lists for motif in motifs}

    @property
    def disease_codes(self) -> list[str]:
        """The source's disease abbreviation(s); ``disease_id`` may list several."""
        return self.disease_id.split(", ")

    @property
    def motif_dependent(self) -> bool:
        """True when length alone cannot place an allele (several or benign alt motifs)."""
        return len(self.pathogenic_motif_gene_orientation) > 1 or bool(
            self.benign_motif_gene_orientation
        )


_LOCI = TypeAdapter(list[Locus])


def _fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def _name_haystack(locus: Locus) -> str:
    """Disease name and identifiers."""
    return _fold(" ".join([locus.disease, locus.disease_id, locus.gene, locus.id]))


def _tag_haystack(locus: Locus) -> str:
    """Source disease/locus tags (underscores read as spaces)."""
    return _fold(" ".join(t.replace("_", " ") for t in (*locus.disease_tags, *locus.locus_tags)))


def _hpo_haystack(locus: Locus) -> str:
    """HPO phenotype labels (search only; labels are not echoed in responses)."""
    return _fold(" ".join(locus.hpo_terms or []))


def _keys(locus: Locus) -> set[str]:
    """Locus id, gene symbol and disease abbreviations, case-folded."""
    return {_fold(locus.id), _fold(locus.gene), *map(_fold, locus.disease_codes)}


def _prefix_pattern(folded: str) -> re.Pattern[str]:
    """Pattern for an abbreviation then a non-letter: DM -> DM1, DM2; SCA -> SCA1."""
    return re.compile(rf"^{re.escape(folded)}[^a-z]")


_ID_QUERY = re.compile(r"^(MONDO|OMIM|MIM|ORPHA|ORPHANET)[:_ ]?(\d{1,12})$", re.IGNORECASE)
_MOTIF_QUERY = re.compile(r"^[ACGTN]{2,100}$")


class Catalog:
    """An immutable, indexed STRchive snapshot."""

    def __init__(self, loci: list[Locus], sha256: str) -> None:
        """Index the validated loci by id, disease id, and gene (all case-folded)."""
        self.loci: tuple[Locus, ...] = tuple(loci)
        self.sha256 = sha256
        self._by_id: dict[str, Locus] = {}
        self._by_alias: dict[str, list[Locus]] = {}
        for locus in self.loci:
            key = _fold(locus.id)
            if key in self._by_id:
                raise DataUnavailableError("STRchive snapshot has duplicate locus ids.")
            self._by_id[key] = locus
        for locus in self.loci:
            aliases = {_fold(locus.gene), *(_fold(code) for code in locus.disease_codes)}
            for alias in aliases - {_fold(locus.id)}:
                self._by_alias.setdefault(alias, []).append(locus)

    def get(self, key: str) -> Locus:
        """Return one locus by STRchive id, gene symbol, or disease id (case-insensitive)."""
        folded = _fold(key.strip())
        if folded in self._by_id:
            return self._by_id[folded]
        matches = self._by_alias.get(folded, [])
        if len(matches) == 1:
            return matches[0]
        if not matches:
            prefix = _prefix_pattern(folded)
            prefixed = [loc for loc in self.loci if any(map(prefix.match, _keys(loc)))]
            matches = prefixed if len(prefixed) > 1 else []
        if matches:
            raise AmbiguousQueryError(
                "Several STRchive loci match; pick one locus id.",
                candidates=[{"locus_id": loc.id, "gene": loc.gene} for loc in matches],
            )
        raise NotFoundError()

    def search(self, query: str | None) -> list[Locus]:
        """Ranked loci for a query (see ``search_scored``)."""
        return [locus for locus, _ in self.search_scored(query)]

    def search_scored(self, query: str | None) -> list[tuple[Locus, str]]:
        """Rank loci by gene/id, its prefix, MONDO/OMIM/Orphanet id, motif, disease text, HPO.

        Each hit carries the basis it matched on, so a phenotype-only hit is never
        mistaken for a locus whose disease is named after the query.
        """
        if query is None or not query.strip():
            return [(loc, "all") for loc in sorted(self.loci, key=lambda loc: (loc.gene, loc.id))]
        text = query.strip()
        folded = _fold(text)
        id_match = _ID_QUERY.match(text)
        motif = text.upper() if _MOTIF_QUERY.match(text.upper()) else None
        tokens = folded.split()
        prefix = _prefix_pattern(folded)
        scored: list[tuple[int, Locus, str]] = []
        for locus in self.loci:
            exact = _keys(locus)
            if folded in exact:
                scored.append((100, locus, "id_or_gene"))
            elif any(prefix.match(key) for key in exact):
                scored.append((70, locus, "id_prefix"))
            elif id_match is not None and _id_matches(locus, *id_match.groups()):
                scored.append((90, locus, "external_id"))
            elif motif is not None and motif in locus.all_motifs():
                scored.append((80, locus, "motif"))
            elif all(token in _name_haystack(locus) for token in tokens):
                scored.append((20, locus, "disease_name"))
            elif all(
                token in f"{_name_haystack(locus)} {_tag_haystack(locus)}" for token in tokens
            ):
                scored.append((10, locus, "disease_tag"))
            elif all(token in _hpo_haystack(locus) for token in tokens):
                scored.append((5, locus, "hpo_phenotype"))
        scored.sort(key=lambda item: (-item[0], item[1].gene, item[1].id))
        return [(locus, basis) for _, locus, basis in scored]


def _id_matches(locus: Locus, prefix: str, number: str) -> bool:
    prefix = prefix.upper()
    if prefix == "MONDO":
        return number.zfill(7) in locus.mondo
    if prefix in ("OMIM", "MIM"):
        return number in locus.omim or number in locus.omim_gene
    return number in locus.orphanet


def parse_catalog(raw: bytes, expected_sha256: str) -> Catalog:
    """Verify the digest, then validate every record. Any failure fails closed."""
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise DataUnavailableError("STRchive snapshot digest does not match the pin.")
    try:
        loci = _LOCI.validate_python(json.loads(raw))
    except (ValueError, ValidationError) as exc:
        raise DataUnavailableError("STRchive snapshot failed schema validation.") from exc
    if not loci:
        raise DataUnavailableError("STRchive snapshot is empty.")
    return Catalog(loci, digest)


async def fetch_catalog(
    url: str, expected_sha256: str, *, timeout: float, max_bytes: int
) -> Catalog:
    """Download the pinned file (size-capped, no redirects) and parse it."""
    try:
        async with (
            httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client,
            client.stream("GET", url) as response,
        ):
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise DataUnavailableError("STRchive snapshot exceeds the size cap.")
    except httpx.HTTPError as exc:
        raise DataUnavailableError("STRchive snapshot download failed.") from exc
    return parse_catalog(bytes(body), expected_sha256)


def range_block(locus: Locus, category: str) -> dict[str, Any]:
    """A source-stated range; a missing bound stays null, a missing range says so."""
    low, high = locus.range(category)
    if low is None and high is None:
        return {"min": None, "max": None, "status": "not_stated_by_source"}
    return {"min": low, "max": high}


def compare_length(locus: Locus, repeat_count: int) -> dict[str, Any]:
    """Report which source-stated ranges contain a repeat count. Descriptive, not a call."""
    if repeat_count < 0:
        raise InvalidInputError("repeat_count must be >= 0.", field="repeat_count")
    matching = []
    for category in RANGE_CATEGORIES:
        low, high = locus.range(category)
        if low is None and high is None:
            continue
        if (low is None or low <= repeat_count) and (high is None or repeat_count <= high):
            matching.append(category)
    return {
        "locus_id": locus.id,
        "gene": locus.gene,
        "repeat_count": repeat_count,
        "matching_categories": matching,
        "ranges": {category: range_block(locus, category) for category in RANGE_CATEGORIES},
        "motif_dependent": locus.motif_dependent,
        "pathogenic_motifs_gene_orientation": list(locus.pathogenic_motif_gene_orientation),
    }
