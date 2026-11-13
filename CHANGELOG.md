# Changelog

All notable changes to strchive-link are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
