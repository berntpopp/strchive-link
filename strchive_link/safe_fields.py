"""Build caller-visible structured fields from trusted sources ONLY.

The fleet rule: NEVER copy an exception attribute or an upstream value into a
caller-visible structured field. Every value a caller sees must be a FIXED
server string, a member of a CLOSED ENUM, or an identifier VALIDATED against its
exact grammar (non-conforming -> dropped). Code-point stripping alone is not
enough: injection prose carries no forbidden code points.
"""

from __future__ import annotations

import re
from typing import Any

# Byte-identical to the fleet Response-Envelope v1.1 forbidden code-point set.
FORBIDDEN_CODEPOINTS = frozenset(
    {
        *range(0x0000, 0x0009),
        *range(0x000B, 0x000D),
        *range(0x000E, 0x0020),
        *range(0x007F, 0x00A0),
        0x200B,
        0x200C,
        0x200D,
        0x2060,
        0xFEFF,
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
    }
)

# Anchored, whitespace-free grammars (prose needs spaces, so an instruction
# phrase cannot match).
_LOCUS_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/+?-]{0,63}$")
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")
_ALLOWED_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,63}$")
_ALLOWED_RANGE_RE = re.compile(r"^\d+\.\.\d+( items)?$")


def strip_forbidden(text: str) -> str:
    """Remove every forbidden control/zero-width/bidi/NUL code point (no length cap)."""
    return "".join(char for char in text if ord(char) not in FORBIDDEN_CODEPOINTS)


def is_locus_key(value: Any) -> bool:
    """True for a value shaped like a locus id / gene symbol (safe to echo as an argument)."""
    return isinstance(value, str) and _LOCUS_ID_RE.match(value) is not None


def safe_allowed_value(value: Any) -> bool:
    """True for an allowed-value token / range descriptor (no prose, no whitespace)."""
    return isinstance(value, str) and bool(
        _ALLOWED_TOKEN_RE.match(value) or _ALLOWED_RANGE_RE.match(value)
    )


def safe_allowed_values(values: Any) -> list[str]:
    """Filter a list to entries matching the allowed-value grammar; drop the rest."""
    if not isinstance(values, list):
        return []
    return [v for v in values if safe_allowed_value(v)]


def safe_candidates(candidates: Any) -> list[dict[str, str]]:
    """Rebuild ``{locus_id, gene}`` candidates from validated identifiers only."""
    if not isinstance(candidates, list):
        return []
    out: list[dict[str, str]] = []
    for item in candidates:
        if not isinstance(item, dict) or not is_locus_key(item.get("locus_id")):
            continue
        entry = {"locus_id": item["locus_id"]}
        gene = item.get("gene")
        if isinstance(gene, str) and _SYMBOL_RE.match(gene):
            entry["gene"] = gene
        out.append(entry)
    return out
