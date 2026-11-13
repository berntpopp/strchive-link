# Configuration

Every setting is an environment variable with the `STRCHIVE_LINK_` prefix. Nested
config uses a **double underscore**, e.g. `STRCHIVE_LINK_DATA__LOCAL_PATH`. Copy
[`.env.example`](../.env.example) to `.env` to start; everything below is optional
and shown with the default that `strchive_link/config.py` actually sets.

The tables below are **exhaustive, and a test says so**: `tests/unit/test_docs_config.py`
enumerates every field of `ServerSettings` (including the nested `DATA__`
model) and fails if this page omits one — or documents one that no longer exists.

## Server

| Variable | Default | Purpose |
|----------|---------|---------|
| `STRCHIVE_LINK_HOST` | `127.0.0.1` | Bind address. |
| `STRCHIVE_LINK_PORT` | `8000` | Bind port (1024–65535). |
| `STRCHIVE_LINK_TRANSPORT` | `unified` | `unified` \| `http` \| `stdio`. |
| `STRCHIVE_LINK_MCP_PATH` | `/mcp` | MCP endpoint path. |
| `STRCHIVE_LINK_ALLOWED_HOSTS` | `["localhost","127.0.0.1","::1"]` | JSON list of **exact** `Host` values admitted. |
| `STRCHIVE_LINK_ALLOWED_ORIGINS` | `[]` | JSON list of **exact** browser `Origin` values admitted. |
| `STRCHIVE_LINK_CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | JSON list of origins that receive CORS response headers. |
| `STRCHIVE_LINK_LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL`. |
| `STRCHIVE_LINK_LOG_FORMAT` | `console` | `console` \| `json`. |
| `STRCHIVE_LINK_RELOAD` | `false` | Uvicorn auto-reload. Development only — never enable in a container. |

## STRchive snapshot

The server serves one file, `data/STRchive-loci.json`, pinned to an exact upstream
commit and SHA-256 — see [Data](data.md). Whatever its origin, the bytes must match
`EXPECTED_SHA256` or nothing is served.

| Variable | Default | Purpose |
|----------|---------|---------|
| `STRCHIVE_LINK_DATA__SOURCE_URL` | pinned-commit `raw.githubusercontent.com` URL | Where the file is downloaded from at startup. |
| `STRCHIVE_LINK_DATA__EXPECTED_SHA256` | the pinned digest | Digest the file must match. Change only together with `SOURCE_URL`. |
| `STRCHIVE_LINK_DATA__LOCAL_PATH` | unset | Load this local copy instead of downloading (air-gapped hosts; still digest-verified). |
| `STRCHIVE_LINK_DATA__DOWNLOAD_TIMEOUT` | `60.0` | HTTP timeout (s) for the download. |
| `STRCHIVE_LINK_DATA__MAX_DOWNLOAD_BYTES` | `8388608` (8 MiB) | **Download-size cap**; the pinned file is ~526 KB. |

## The Host / Origin / CORS boundary

HTTP deployments enforce **exact** `Host` and `Origin` allowlists on every route.
Wildcards are not accepted. Three rules that are easy to get wrong:

1. **Add the public hostname.** `STRCHIVE_LINK_ALLOWED_HOSTS` must contain the exact
   public reverse-proxy hostname *in addition to* the loopback defaults, or every
   proxied request is rejected.
2. **`STRCHIVE_LINK_ALLOWED_ORIGINS` defaults to `[]`, which admits requests that carry
   no `Origin` header at all** — that is what lets non-browser MCP clients (Claude
   Code, `curl`) work out of the box. It does *not* mean "allow any origin".
3. **Request validation and CORS are separate policies, and neither widens the
   other.** A browser deployment must list its origin in **both**
   `STRCHIVE_LINK_ALLOWED_ORIGINS` (admission) and `STRCHIVE_LINK_CORS_ORIGINS` (response
   headers). Note their defaults differ: admission is empty, CORS ships with the
   two localhost:3000 dev origins.

## Transports

- **`unified`** (default) — FastAPI `/health` plus the MCP endpoint at `/mcp` on one
  port. `make dev`.
- **`http`** — HTTP transport without the unified REST host.
- **`stdio`** — `make mcp-serve` (`uv run python mcp_server.py`), used by Claude
  Desktop. On stdio **stdout is reserved for the protocol** — logs go to stderr.

Register the HTTP server with Claude Code:

```bash
claude mcp add --transport http strchive-link --scope user http://127.0.0.1:8000/mcp
```
