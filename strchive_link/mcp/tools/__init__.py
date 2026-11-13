"""MCP tool registration entry points."""

from __future__ import annotations

from strchive_link.mcp.tools.discovery import register_discovery_tools
from strchive_link.mcp.tools.loci import register_locus_tools

__all__ = ["register_discovery_tools", "register_locus_tools"]
