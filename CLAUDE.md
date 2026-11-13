# CLAUDE.md

This file guides Claude Code when working in this repository.

**Read [`AGENTS.md`](AGENTS.md) first** — it holds the engineering conventions,
architecture invariants, and the definition of done. They apply in full here.

## TL;DR

- Run `make ci-local` before claiming anything is done.
- The server serves one STRchive file pinned to an exact commit + SHA-256
  (`strchive_link/catalog.py`), fetched at startup, validated, held in memory.
- Report ranges exactly as the source states them; fence upstream prose; no
  liftover, no diagnosis.
- Files stay under 500 lines; logs go to stderr.

## Common commands

```bash
make install          # uv sync --group dev
make dev              # unified REST + MCP server (127.0.0.1:8000/mcp)
make test             # unit tests
make ci-local         # full local gate
```

## Layout

`strchive_link/{catalog,config,constants,exceptions,logging_config,buildinfo,safe_fields}.py`
· `mcp/` (envelope, shaping, untrusted_content, next_commands, capabilities,
middleware, notfound_guard, tools, facade) · `server.py` / `mcp_server.py`.
