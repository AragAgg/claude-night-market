"""Shared parse_frontmatter shim for validator modules (AR-06).

Routes through ``leyline.frontmatter.parse_frontmatter`` when
available; falls back to a generated copy of that module
(``scripts/sync_vendored.py``) so the validators do not hard-fail on
systems without leyline. Public
under ``sanctum.validators`` because two scripts already import
``parse_frontmatter`` from there for backward compatibility.
"""

from __future__ import annotations

try:
    from leyline.frontmatter import parse_frontmatter
except ImportError:
    from sanctum._vendored_leyline_frontmatter import parse_frontmatter


__all__ = ["parse_frontmatter"]
