"""MCP facade for strchive-link."""

from __future__ import annotations

from fastmcp import FastMCP

from strchive_link import __version__
from strchive_link.mcp.capabilities import register_capability_resources
from strchive_link.mcp.middleware import ArgValidationMiddleware
from strchive_link.mcp.notfound_guard import (
    NotFoundGuard,
    install_notfound_log_filter,
    install_protocol_error_handler,
)
from strchive_link.mcp.resources import STRCHIVE_SERVER_INSTRUCTIONS
from strchive_link.mcp.tools import register_discovery_tools, register_locus_tools


def create_strchive_mcp() -> FastMCP:
    """Build a FastMCP instance with all strchive-link tools and resources."""
    mcp = FastMCP(
        name="strchive-link",
        version=__version__,
        instructions=STRCHIVE_SERVER_INSTRUCTIONS,
        mask_error_details=True,
        # Tool-Surface Budget Standard v1: no $ref appears in any input schema, so
        # inlining is free and keeps the published tool surface compact.
        dereference_schemas=False,
    )

    # Guard the FastMCP-core not-found reflection surface: core echoes the
    # caller's OWN requested tool name / resource URI / prompt name (with any
    # control/zero-width/bidi/NUL code points) to the caller and to logs BEFORE
    # backend middleware runs. NotFoundGuard preflights the tool NAME (unknown ->
    # fixed name-free envelope) and fixes the on_read_resource boundary; add it
    # FIRST so it is the OUTERMOST middleware (before ArgValidationMiddleware).
    # See notfound_guard.py.
    mcp.add_middleware(NotFoundGuard())

    register_discovery_tools(mcp)
    register_locus_tools(mcp)
    register_capability_resources(mcp)
    mcp.add_middleware(ArgValidationMiddleware())

    # Layer 3: install the protocol-handler backstop AFTER every tool/resource/
    # prompt is registered, so it is the outermost wrapper on the raw CallTool/
    # ReadResource/GetPrompt handlers. It catches the unknown-tool *return* path
    # and any resource/prompt dispatch error that would echo the requested
    # name/URI (the only layer covering the unknown-prompt surface).
    install_protocol_error_handler(mcp)
    # Layer 5: scrub FastMCP-core / MCP-SDK validation logs that would echo the
    # caller-supplied name/URI (idempotent; process-global).
    install_notfound_log_filter()

    return mcp
