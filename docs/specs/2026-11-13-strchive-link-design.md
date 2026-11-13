# strchive-link design (v0.1.0)

> Historical record — the design decided for the first release (genefoundry-router#190,
> owner decision 2026-11-13). Current behaviour is documented in README.md and docs/.

## Decision

- Separate backend `strchive-link` (namespace `strchive`). STRipy stays out of scope until
  its reuse terms are confirmed; MITOMAP and UCSC are separate builds.
- Source: STRchive `data/STRchive-loci.json`, CC BY 4.0. No upstream tags, so the snapshot
  is pinned to commit `e964fa88df3b2189ee478cbd6eaad15bb28e3a0a` plus the file SHA-256.
- Data mode: `upstream-live` with a pinned, digest-verified URL. The ~526 KB file is
  fetched at startup into memory. This keeps the image code-only (Container Hardening
  rule 9) without a data-release artifact and init container, which a file this small
  does not justify. Egress is `raw.githubusercontent.com` only.

## Surface

`search_loci`, `get_locus`, `compare_repeat_length`, `get_server_capabilities`,
`get_diagnostics`. Ranges are reported as stated (closed intervals, repeat units);
missing ranges are explicit; overlaps are not merged; coordinates are per assembly
(BED) and never lifted over. `compare_repeat_length` is descriptive and flags
motif-dependent loci (RFC1). Upstream prose is fenced as `untrusted_text`.

## Rejected

- Vendoring the JSON into the image: violates the code-only image rule.
- A `data-*` release asset + init container (clinvar/orphanet pattern): correct but
  heavy for one small immutable file; revisit if STRchive grows or needs offline deploys.
- Interpreting ranges (penetrance bands, premutation labels): not stated by the source.
