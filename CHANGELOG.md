# Changelog

All notable changes to strchive-link are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.3] - 2026-11-13

### Changed

- CI: re-pin the reusable container CI/release workflows to genefoundry-router v0.10.17 (`2cd86e3`), picking up the release recovery-path platform fix (v0.10.14), `validate-config` applying the evidence assembler's data predicate (v0.10.16), and recovery attestation verification, the GHCR tag race and partial-rerun evidence lookup fixes (v0.10.17).
- Docker: Python base image digest bump (`0741d10` -> `9aaa474`, #2); CI: `github/codeql-action` 4.39.1 -> 4.39.3 (#3).

## [0.1.2] - 2026-11-13

### Fixed

- `search_loci`: an abbreviation followed by a type number now ranks first
  (`matched_on: id_prefix`; e.g. `FRA` -> FRA2A, FRA7A, FRA12A) instead of being buried
  under equal-score substring hits; minimal rows keep `matched_on`; the `response_mode`
  description now states what search rows actually carry.
- `get_locus` / `compare_repeat_length`: an abbreviation shared by several numbered
  loci returns `ambiguous_query` with candidates instead of `not_found`.
- `get_locus` `next_commands` no longer suggests `compare_repeat_length` without its
  required `repeat_count`; every suggested step is executable as given.
- Argument errors: a float for an integer says "must be an integer"; a too-short or
  too-long string states the length bounds instead of listing parameter names.

## [0.1.1] - 2026-11-13

### Fixed

- Container release: `container-release.json` now seals the pinned data identity
  (`release_tag: strchive-<commit>`, `digest: sha256:<file digest>`) that the release
  manifest requires for an `upstream-live` service. v0.1.0 published its image but its
  evidence assembly failed closed, so no v0.1.0 GitHub Release exists; use 0.1.1.

## [0.1.0] - 2026-11-13

### Added

- First release. MCP server for STRchive tandem-repeat disease loci, served from
  `data/STRchive-loci.json` pinned to dashnowlab/STRchive@e964fa8 (SHA-256
  `16301ecb…bca86`), digest-verified and schema-validated at startup.
- Tools: `search_loci`, `get_locus`, `compare_repeat_length`, `get_server_capabilities`,
  `get_diagnostics`. Ranges as stated by the source (missing ranges explicit, overlaps
  kept), all pathogenic motifs in both orientations, hg38/hg19/T2T coordinates (BED),
  fenced upstream prose, CC BY 4.0 `recommended_citation` on every data response.
- Fleet standards: Tool-Naming v1.1, Response-Envelope v1/v1.1, Tool-Schema
  Documentation, Container Hardening v1 (non-root 10001, read-only rootfs, code-only
  image), vendored transport/behaviour/contract-truth conformance probes.
