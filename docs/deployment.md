# Deployment

`strchive-link` is a stateless container. At startup it downloads the pinned
`data/STRchive-loci.json` (~526 KB) from `raw.githubusercontent.com`, verifies its SHA-256,
validates every record, and serves from memory. There is no volume and no refresh job: a
new STRchive snapshot is a reviewed pin bump and a new release ([Data](data.md)).

## Container

The image follows the GeneFoundry Container & Deployment Hardening Standard v1:

- non-root `10001:10001`, read-only root filesystem, `/tmp` as a `noexec,nosuid` tmpfs;
- `cap_drop: ALL`, `no-new-privileges`, `init`, memory/CPU/PID limits;
- digest-pinned base image, code-only (the dataset is never baked in);
- expose-only behind the reverse proxy (`ports: !reset []` in the production overlays).

Egress: `raw.githubusercontent.com` only (declared in `container-release.json`). On a host
without egress, mount the pinned file read-only and set `STRCHIVE_LINK_DATA__LOCAL_PATH`;
the digest is still enforced.

```bash
# Local
make docker-build && make docker-up

# Production (digest-pinned image, no build)
STRCHIVE_LINK_IMAGE=ghcr.io/berntpopp/strchive-link@sha256:<digest> \
  docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d

# Fleet (Nginx Proxy Manager overlay — what the fleet controller deploys)
docker compose -f docker/docker-compose.npm.yml --env-file .env.docker up -d
```

The public hostname (`strchive-link.genefoundry.org`) is already in
`STRCHIVE_LINK_ALLOWED_HOSTS` in both production overlays. The backend is unauthenticated
by design: expose it only through the reverse proxy / router, never directly.

## Releases

A protected `vX.Y.Z` tag runs `.github/workflows/container-release.yml`, which calls the
router's reusable `_container-release.yml` (pinned by commit). It builds one
`linux/amd64` image, inspects every layer, runs the hardened container plus MCP checks,
scans it, attests provenance and an SBOM, and creates the immutable GitHub Release. The
`release` environment gate requires an owner approval. Never create a release by hand.

Health: `GET /health` returns `status`, `version`, `git_sha`, `built_at` and
`data_loaded`. `get_diagnostics` reports the pinned commit and the verified digest.
