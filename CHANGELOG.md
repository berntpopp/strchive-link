# Changelog

All notable changes to strchive-link are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.1] - 2026-11-26

### Fixed

- `search_loci` `_meta.pagination` also carries `next_cursor` (always `null`; paging is by
  offset) and `next_offset`, as Response-Envelope Standard v1 §5 asks.

## [0.4.0] - 2026-11-26

### Added

- Response-Envelope v1.2 provenance: every successful data result carries
  `_meta.retrieved_at`, the UTC time the server downloaded the pinned snapshot (for a
  local snapshot file, its modification time), next to `_meta.source` and
  `_meta.data_version`.
- Every error envelope carries `_meta.elapsed_ms` (Response-Envelope v1 §4).

### Tests

- Every data tool result and the error envelopes are validated against the published
  envelope JSON Schema v1.2.0, vendored with a pinned SHA-256
  (`tests/conformance/envelope-v1.2.schema.json`).
- Re-vendored the behaviour gate, which now checks the provenance rule.

## [0.3.0] - 2026-11-19

### Added

- `get_locus` / `compare_repeat_length` `not_found` for a key that is not a locus id, gene
  or abbreviation (e.g. a disease name) now carries up to three `candidates` from the
  `search_loci` ranking, each flagged `match: "weak"` with its `matched_on` basis, and
  `next_commands` to open them; `search_loci` stays the last step. A miss with no hit
  points at `search_loci` (it pointed at `get_server_capabilities`), and the message names
  `mondo_resolve_disease` for diseases STRchive does not list.

### Changed

- `search_loci` description leads with what it returns (Tool-Schema Documentation v1.1,
  rule D1).

### Tests

- Guard: every `next_commands` step names a real tool and real arguments
  (`tests/unit/test_hint_targets.py`); every field a tool description names is returned.

## [0.2.1] - 2026-11-18

### Security

- SDK 2 echoed an unknown JSON-RPC method name verbatim in the METHOD_NOT_FOUND error
  `data` (both protocol eras); a low-level middleware now strips it (fixed
  `-32601 Method not found`), and the log scrub covers the SDK 2 runner/dispatcher lines
  (`mcp.server.runner`) that echo the method.

## [0.2.0] - 2026-11-18

### Changed

- Upgrade FastMCP 3.4 → 4.2.2 and MCP SDK 1.x → 2.x; supports the 2026-07-28 sessionless protocol era alongside the legacy handshake.
- Not-found reflection guard: the protocol backstop is ported to the SDK v2 request-handler registry (`get_request_handler`/`add_request_handler`). A malformed or unknown resource URI now reaches the handler (SDK v2 no longer rejects it at deserialization) and is answered with the same fixed, input-free message as an `INVALID_PARAMS` JSON-RPC error.
- Tests: a modern-era `server/discover` → `tools/list` → `tools/call` HTTP test, including the unknown-tool fence; the log-cleanliness probes also cover the SDK v2 `mcp.server.runner` and `mcp.shared.jsonrpc_dispatcher` loggers.

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
