# strchive-link

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/berntpopp/strchive-link/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/strchive-link/actions/workflows/ci.yml)
[![Conformance](https://github.com/berntpopp/strchive-link/actions/workflows/conformance.yml/badge.svg)](https://github.com/berntpopp/strchive-link/actions/workflows/conformance.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An MCP (Model Context Protocol) server for [STRchive](https://strchive.org), the curated
catalog of short-tandem-repeat (STR) disease loci: repeat-count ranges, pathogenic motifs,
interruptions and per-assembly coordinates, served from a snapshot pinned to an exact
upstream commit and SHA-256, over Streamable HTTP or stdio.

> [!IMPORTANT]
> Research use only. Not clinical decision support. Do not use for diagnosis,
> treatment, triage, or patient management.

## Why

Repeat-expansion thresholds are scattered across papers and easy to misquote: HTT has a
reduced-penetrance band, RFC1 is pathogenic only for certain motifs, and many loci have no
stated intermediate range at all. STRchive curates these per locus with citations.

`strchive-link` hands an agent that record without paraphrase. Ranges are reported exactly
as the source states them (closed intervals in repeat units). A missing range stays `null`
with `status: not_stated_by_source`, and overlapping ranges are kept as stated. Every
alternative pathogenic motif is listed in both gene and reference orientation. Coordinates
are given per assembly (hg38, hg19, T2T) and never converted. Upstream prose is fenced as
`untrusted_text`. The tools complement PanelApp STR entities and HGNC/HPO/Mondo resolution
elsewhere in the fleet. They do not genotype reads or classify alleles.

## Quick start

Hosted — no install, through the GeneFoundry router (namespace `strchive`, once deployed):

```bash
claude mcp add --transport http genefoundry https://genefoundry.org/mcp
```

Local (Python 3.14+, [uv](https://github.com/astral-sh/uv)). The server downloads the
pinned file (~526 KB) from GitHub at startup and verifies its digest; set
`STRCHIVE_LINK_DATA__LOCAL_PATH` to serve a local copy instead:

```bash
make install          # uv sync --group dev
make dev              # unified REST + MCP on http://127.0.0.1:8000/mcp
make mcp-serve        # ...or a stdio MCP server, for Claude Desktop
```

```bash
claude mcp add --transport http strchive-link --scope user http://127.0.0.1:8000/mcp
```

Serving over HTTP behind a proxy requires adding the public hostname to the exact Host
allowlist — read [Configuration](docs/configuration.md) first.

## Tools

| Tool | Purpose |
|------|---------|
| `search_loci` | **Start here.** Find loci by gene, locus id, MONDO/OMIM/Orphanet id, motif or disease words. |
| `get_locus` | One locus: ranges, motifs (all orientations), interruptions, inheritance, coordinates, ids, PMIDs. |
| `compare_repeat_length` | Which stated ranges contain a repeat count. Descriptive only, not a diagnosis. |
| `get_server_capabilities` | Discovery surface: tools, signatures, semantics, license, data pin. |
| `get_diagnostics` | Whether the pinned snapshot is loaded and its digest verified. |

`serverInfo.name` is `strchive-link`, and leaf tool names are intentionally **unprefixed** per
the GeneFoundry Tool-Naming Standard v1. The canonical gateway namespace token is
`strchive`: behind [`genefoundry-router`](https://github.com/berntpopp/genefoundry-router)
these surface as `strchive_<tool>` (e.g. `strchive_get_locus`).

Every response carries `_meta.next_commands` and `recommended_citation`, and honours
`response_mode ∈ {minimal, compact, standard, full}` (default `compact`). See
[Usage](docs/usage.md).

## Data & provenance

- **Source** — `data/STRchive-loci.json` from
  [dashnowlab/STRchive](https://github.com/dashnowlab/STRchive), pinned to commit
  `e964fa88df3b2189ee478cbd6eaad15bb28e3a0a` (2026-10-08), SHA-256
  `16301ecb00239f0e3c684913aefc2f48c6f5a7c2a481958aab4db55d282bca86`. Every record is
  schema-validated before it is served. See [Data](docs/data.md).
- **Refresh** — none at runtime: STRchive has no tagged releases, so a new snapshot is a
  reviewed pin bump and a new release of this server.
- **Licence** — STRchive data are **CC BY 4.0** (STRchive by Harriet Dashnow et al.;
  attribution required). STRchive code is MIT.
- **Citation** — Hiatt L, Weisburd B, Dolzhenko E, Rubinetti V, Avvaru AK, VanNoy GE,
  Kurtas NE, Rehm HL, Quinlan AR, Dashnow H. STRchive: a dynamic resource detailing
  population-level and locus-specific insights at tandem repeat disease loci. *Genome Med.*
  2025. doi:10.1186/s13073-025-01454-4.

## Documentation

- [Usage](docs/usage.md) — workflows, range and coordinate semantics, `response_mode`, fencing.
- [Configuration](docs/configuration.md) — every `STRCHIVE_LINK_*` variable, the transports, and the Host / Origin / CORS boundary.
- [Data](docs/data.md) — the pin, validation, licence, and how to bump the snapshot.
- [Deployment](docs/deployment.md) — the hardened container and the release flow.

## Contributing

See [`AGENTS.md`](AGENTS.md) for engineering conventions. `make ci-local` is the
definition-of-done gate: format, lint, line budget, README standard, mypy strict, and tests.

## License

[MIT](LICENSE) © strchive-link contributors. STRchive **data** are CC BY 4.0 (Harriet
Dashnow et al.); cite them as above.
