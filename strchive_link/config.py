"""Configuration management for strchive-link.

Settings load from environment variables with the ``STRCHIVE_LINK_`` prefix (nested
models use ``__``, e.g. ``STRCHIVE_LINK_DATA__LOCAL_PATH=/path/STRchive-loci.json``)
and an optional ``.env`` file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from strchive_link.catalog import PINNED_SHA256, SOURCE_URL


class StrchiveDataConfig(BaseModel):
    """Where the pinned STRchive snapshot comes from (digest-verified either way)."""

    source_url: str = Field(
        default=SOURCE_URL,
        description="Pinned-commit raw URL of data/STRchive-loci.json.",
    )
    expected_sha256: str = Field(
        default=PINNED_SHA256,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 the downloaded/local file must match.",
    )
    local_path: Path | None = Field(
        default=None,
        description="Load this local copy instead of downloading (still digest-verified).",
    )
    download_timeout: float = Field(default=60.0, gt=0, le=600)
    max_download_bytes: int = Field(
        default=8 << 20,
        gt=0,
        description="Size cap; the pinned file is ~526 KB.",
    )


class ServerSettings(BaseSettings):
    """Top-level server settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="STRCHIVE_LINK_",
        env_nested_delimiter="__",
    )

    host: str = Field(default="127.0.0.1", description="Server host.")
    port: int = Field(default=8000, ge=1024, le=65535, description="Server port.")
    reload: bool = Field(default=False, description="Enable auto-reload in development.")

    transport: Literal["unified", "http", "stdio"] = Field(
        default="unified",
        description="Server transport mode.",
    )
    mcp_path: str = Field(default="/mcp", description="MCP endpoint path.")
    allowed_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1", "::1"],
        description="Exact Host header values accepted by the request guard.",
    )
    allowed_origins: list[str] = Field(
        default=[],
        description="Browser Origin values accepted by the request guard.",
    )

    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins.",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level.",
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log format.",
    )

    data: StrchiveDataConfig = Field(
        default_factory=StrchiveDataConfig,
        description="Pinned STRchive snapshot configuration.",
    )

    @field_validator("mcp_path")
    @classmethod
    def validate_mcp_path(cls, v: str) -> str:
        """Ensure the MCP path starts with a forward slash."""
        return v if v.startswith("/") else f"/{v}"

    @field_validator("allowed_hosts", "allowed_origins", "cors_origins", mode="before")
    @classmethod
    def parse_string_list(cls, v: Any) -> list[str]:
        """Parse string lists from a comma-separated value or list."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return list(v) if v else []

    @field_validator("allowed_hosts", "allowed_origins")
    @classmethod
    def reject_wildcard_pattern(cls, v: list[str]) -> list[str]:
        """Require exact values; FastMCP otherwise interprets glob patterns."""
        if any(any(marker in value for marker in "*?[]") for value in v):
            raise ValueError("wildcard patterns are not allowed in security allowlists")
        return v


settings = ServerSettings()
