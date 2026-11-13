# AGENTS.md — engineering conventions for strchive-link

Guidance for AI agents and contributors working in this repo. `strchive-link` is a
sibling of `uniprot-link`, `gnomad-link`, `gencc-link`, `clingen-link`; keep it
consistent with those.

## Golden rules

1. **Run the gate before claiming done:** `make ci-local`
   (format-check → lint → line-budget → README standard → mypy strict → tests).
   All must pass.
2. **Per-file line budget: 500 lines** (`make lint-loc`). Split modules that grow.
3. **mypy is strict.** Fully type new code; no untyped defs.
4. **stdout is sacred on stdio.** Logs go to stderr; never `print` to stdout in
   server/library code (the CLI is the only place `print` is allowed).

## Make targets

| Target | What it does |
|--------|--------------|
| `make install` | `uv sync --group dev`. |
| `make dev` / `make mcp-serve` | Unified REST + MCP server / stdio MCP server. |
| `make check` | `format` + `lint`. |
| `make typecheck` | `mypy --strict`. |
| `make test` / `make test-fast` / `make test-cov` | Unit tests / parallel / with coverage. |
| `make lint-loc` / `make lint-readme` | 500-line budget / GeneFoundry README Standard v1. |
| `make ci-local` | The definition-of-done gate. |

`docs/` holds what a README must not carry: `configuration.md` (every
`STRCHIVE_LINK_*` var, the Host/Origin/CORS boundary), `data.md` (the pin, validation,
licence, how to bump the snapshot), `deployment.md`, `usage.md`.

## Architecture invariants (do not break)

- **One data source, pinned.** `catalog.py` holds `PINNED_COMMIT` + `PINNED_SHA256` for
  STRchive `data/STRchive-loci.json`. The downloaded file is untrusted: digest first,
  then strict schema validation, fail closed. Bumping the pin is a reviewed release
  (see `docs/data.md`); never fetch an unpinned ref.
- **Report the source, never reinterpret it.** Ranges stay exactly as stated (missing ->
  null + `not_stated_by_source`, overlaps kept). No liftover, no invented thresholds, no
  diagnostic call. `compare_repeat_length` is descriptive.
- **Upstream prose is fenced** (`mcp/untrusted_content.py`, Response-Envelope v1.1) and
  only appears at `response_mode=standard|full`. Never surface an upstream string
  unfenced unless it passes an identifier grammar.
- **The MCP layer owns the envelope.** `mcp/envelope.run_mcp_tool` injects
  `success`/`_meta`, converts exceptions into typed error envelopes with `isError`, and
  never interpolates caller input into a message. Error codes are the closed fleet enum.
- **Every response carries `_meta.next_commands`**; build them in
  `mcp/next_commands.py` from validated identifiers only.
- **Tool descriptions end with `Signature: tool(args...)`**; every required parameter
  carries `examples` (the behaviour probe builds its calls from them).
- Keep `mcp/capabilities.TOOLS`, the README `## Tools` table and `docs/usage.md` in sync
  with the registered tools (tests assert it).

### Fleet deploy contract

- `docker/docker-compose.npm.yml` is the file the fleet controller
  (`strato_v6_docker_npm`) deploys and validates. Every service there declares
  `user: "<uid>:<gid>"` numerically — this image's own uid:gid from
  `docker/Dockerfile` (currently `10001:10001`), never copied from a sibling `-link`
  repo.
- `user` must **not** appear in the Compose files listed in
  `container-release.json` (`docker/docker-compose.yml`,
  `docker/docker-compose.prod.yml`) — the shared release gate
  (`container_release.py validate-compose`) forbids it there.
- Both rules are enforced by `tests/unit/test_deploy_overlay_user.py`.
- `container-release.json` declares `service.deployed_compose_files:
  ["docker/docker-compose.npm.yml"]` — the exact file the controller deploys.
  Both reusable-workflow pins (`.github/workflows/container-ci.yml`,
  `.github/workflows/container-release.yml`) must track the same
  `genefoundry-router` revision: the shared `_container-release.yml` workflow
  runs `container_release.py validate-deployed-overlay` against the declared
  file before every release, and `_container-ci.yml` loads the same
  `ReleaseConfig` schema from its own pin to validate this JSON, so an older
  pin there rejects new fields.
- **Release checklist** (fleet controller pulls a tagged, attested image — it
  never builds from source): bump `pyproject.toml`, `uv lock`, add a
  `CHANGELOG.md` heading `## [x.y.z] - YYYY-MM-DD`, bump `CITATION.cff`
  `version:` (the file is generated — see its header comment; `date-released`
  is **not** touched by this repo's release process, it is regenerated
  externally by `genefoundry-router`'s `make citation-write`), tag `vx.y.z`,
  then approve the `release` environment gate via
  `gh api repos/berntpopp/strchive-link/actions/runs/<id>/pending_deployments`
  (may need approving twice; `status: waiting` is the gate).

## Testing

- Unit tests are network-free and use the pinned file vendored at
  `tests/fixtures/STRchive-loci.json` (CC BY 4.0). Mock HTTP with `respx`.
- Call tools through the **real facade** and read `structured_content`.
- `tests/conformance/` vendors the router's transport, behaviour and contract-truth
  probes byte-identical; the live probes run in `conformance.yml`.

## Adding a tool

1. Tool in `mcp/tools/<area>.py`, registered from `tools/__init__.py` and `mcp/facade.py`.
2. Projection in `mcp/shaping.py`; chain builder in `mcp/next_commands.py`.
3. Add to `capabilities.TOOLS`, the README `## Tools` table and `docs/usage.md`.
4. Unit + facade tests; run the behaviour probe locally against `make dev`.
