# Docker

```bash
make docker-build       # build the image
make docker-up          # start (prints the MCP URL + Claude Code command)
make docker-logs        # follow logs
make docker-down        # stop
```

The container is stateless: at startup it downloads the pinned STRchive file (~526 KB)
from `raw.githubusercontent.com`, verifies its SHA-256, and keeps it in memory. There is
no volume and no refresh job; a new snapshot ships as a new image release.

## Ports

The host port defaults to `8000`; override with `STRCHIVE_LINK_HOST_PORT` (e.g. in
`docker/.env`). MCP endpoint: `http://127.0.0.1:<port>/mcp`. Health:
`http://127.0.0.1:<port>/health`.
