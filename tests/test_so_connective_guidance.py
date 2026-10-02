"""Guidance on the ", so" consequence tail stays consistent.

Four guidance files once offered "so" as the replacement for a
semicolon splice, the tail they now warn against. These tests pin
both halves: nothing recommends the swap, and the rewrite ladder
exists where the other files point.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_SO_AS_SPLICE_FIX = re.compile(
    r'"and"\s*/\s*"but"\s*/\s*"so"|"and",\s*"but",\s*"so"', re.IGNORECASE
)

_GUIDANCE_GLOBS = (
    ".claude/rules/*.md",
    "plugins/*/skills/**/*.md",
    "plugins/*/agents/*.md",
    "plugins/*/commands/**/*.md",
)

_CANONICAL = REPO_ROOT / (
    "plugins/scribe/skills/slop-detector/modules/structural-patterns.md"
)


def _guidance_files() -> list[Path]:
    return sorted({p for g in _GUIDANCE_GLOBS for p in REPO_ROOT.glob(g)})


@pytest.mark.unit
def test_no_guidance_offers_so_as_the_splice_replacement() -> None:
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in _guidance_files()
        if _SO_AS_SPLICE_FIX.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


@pytest.mark.unit
def test_canonical_section_carries_the_rewrite_ladder_in_order() -> None:
    text = _CANONICAL.read_text(encoding="utf-8")
    section = text.split('## Consequence Tail (", so")', 1)[1].split("\n## ", 1)[0]
    steps = [
        "**Delete the consequence.**",
        "**Give it its own sentence.**",
        "**Lead with the cause.**",
        "**Name the mechanism.**",
    ]
    positions = [section.index(step) for step in steps]
    assert positions == sorted(positions)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("relative", "anchor"),
    [
        (".claude/rules/slop-scan-for-docs.md", "tier5.so_connective"),
        ("plugins/sanctum/commands/shared/output-hygiene.md", "Consequence tails"),
        ("plugins/sanctum/skills/commit-messages/SKILL.md", "`, so` tail"),
        ("plugins/scribe/agents/slop-hunter.md", '", so" consequence tails'),
        (
            "plugins/scribe/skills/doc-generator/modules/generation-guidelines.md",
            "Consequence Tail",
        ),
    ],
)
def test_writing_workflows_name_the_tail(relative: str, anchor: str) -> None:
    assert anchor in (REPO_ROOT / relative).read_text(encoding="utf-8")
