"""FastAPI host for strchive-link (thin: health + service info + data bootstrap)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from strchive_link import __version__
from strchive_link.buildinfo import build_info
from strchive_link.config import settings
from strchive_link.exceptions import DataUnavailableError
from strchive_link.logging_config import configure_logging
from strchive_link.mcp.service_adapters import get_catalog, peek_catalog

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# Backends are unauthenticated by design (edge auth lives at the router), so CORS
# credentials are meaningless. Keep them off; wiring them back on with a wildcard
# origin is a footgun the startup guard below rejects.
_CORS_ALLOW_CREDENTIALS = False


def _validate_cors(origins: list[str], allow_credentials: bool) -> None:
    """Fail closed on the unsafe wildcard-origin + credentials CORS combination.

    An unauthenticated backend holds no cookies/session, so credentials are
    pointless; combined with a ``*`` origin they are also forbidden by the CORS
    spec. Reject that combination at startup rather than silently shipping a
    permissive policy.
    """
    if allow_credentials and "*" in origins:
        raise ValueError(
            "CORS misconfiguration: allow_credentials=True with a wildcard '*' "
            "origin. Backends are unauthenticated by design; disable credentials "
            "or pin explicit origins."
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Warm the pinned STRchive snapshot (a failure is retried on the next tool call)."""
    logger = configure_logging()
    logger.info("strchive-link starting", host=settings.host, port=settings.port)
    try:
        catalog = await get_catalog()
        logger.info("strchive snapshot verified", loci=len(catalog.loci), sha256=catalog.sha256)
    except DataUnavailableError as exc:
        logger.warning("strchive snapshot unavailable; will retry on use", error=exc.message)
    yield
    logger.info("strchive-link shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="strchive-link",
        description="MCP/API server for STRchive tandem-repeat disease loci.",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    _validate_cors(settings.cors_origins, _CORS_ALLOW_CREDENTIALS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=_CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Liveness probe (reports build provenance for deploy checks)."""
        return {
            "status": "ok",
            "service": "strchive-link",
            "transport": "streamable-http-stateless",
            "data_loaded": peek_catalog() is not None,
            **build_info(),
        }

    @app.get("/")
    async def root() -> dict[str, Any]:
        """Service information."""
        return {
            "name": "strchive-link",
            "version": __version__,
            "data_source": "STRchive data/STRchive-loci.json, pinned commit + SHA-256",
            "mcp_endpoint": settings.mcp_path,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()
