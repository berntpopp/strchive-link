# Data

## Source

[STRchive](https://strchive.org) curates tandem-repeat disease loci in one JSON file,
`data/STRchive-loci.json` in [dashnowlab/STRchive](https://github.com/dashnowlab/STRchive).
STRchive publishes no tagged releases, so this server pins:

| | |
|---|---|
| Commit | `e964fa88df3b2189ee478cbd6eaad15bb28e3a0a` (2026-10-08) |
| File SHA-256 | `16301ecb00239f0e3c684913aefc2f48c6f5a7c2a481958aab4db55d282bca86` |
| Loci | 82 |

The pin lives in `strchive_link/catalog.py` (`PINNED_COMMIT`, `PINNED_SHA256`).

## Load and validation

At startup the server downloads the file from the pinned-commit
`raw.githubusercontent.com` URL (size-capped, no redirects), or reads
`STRCHIVE_LINK_DATA__LOCAL_PATH`. Then:

1. The SHA-256 must equal the pin. Otherwise nothing is served.
2. Every record is validated against a strict field grammar (identifiers, motifs
   `^[ACGTN]+$`, non-negative integer ranges, coordinates, reference prefixes). Upstream
   data is untrusted input, so a malformed record fails the whole load.
3. The validated catalog is kept in memory. A failed load is not cached; the next tool call
   retries, and tools report `upstream_unavailable` meanwhile.

The application image is code-only: the dataset is never baked into it. The container
needs egress to `raw.githubusercontent.com` (declared in `container-release.json`) unless
`LOCAL_PATH` is mounted.

## Licence and attribution

STRchive data are licensed **CC BY 4.0** — "STRchive by Harriet Dashnow et al." — and the
STRchive code is MIT. Every data response carries `recommended_citation` with the
attribution, the pinned commit, and the STRchive paper:

> Hiatt L, Weisburd B, Dolzhenko E, Rubinetti V, Avvaru AK, VanNoy GE, Kurtas NE, Rehm HL,
> Quinlan AR, Dashnow H. STRchive: a dynamic resource detailing population-level and
> locus-specific insights at tandem repeat disease loci. *Genome Med.* 2025.
> doi:10.1186/s13073-025-01454-4.

The repository vendors the pinned file at `tests/fixtures/STRchive-loci.json` as a test
fixture under the same CC BY 4.0 terms.

## Bumping the snapshot

1. Pick the new upstream commit that touches `data/STRchive-loci.json`.
2. Download it, compute its SHA-256, and replace `tests/fixtures/STRchive-loci.json`.
3. Update `PINNED_COMMIT`, `PINNED_COMMIT_DATE` and `PINNED_SHA256` in
   `strchive_link/catalog.py`, and the table above and in the README.
4. Run `make ci-local`. Fixture assertions (HTT ranges, RFC1 motifs, missing ranges) catch
   upstream edits that change meaning, and the schema catches shape drift.
5. Release a new version.

## Out of scope

STRipy population statistics (terms unconfirmed), BAM/CRAM genotyping, liftover between
assemblies, and any diagnostic classification.
