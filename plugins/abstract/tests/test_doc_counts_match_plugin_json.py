"""Documented plugin, skill, command and agent counts equal plugin.json.

`book/src/introduction.md` said 16 plugins while 23 shipped, and
`docs/api-overview.md` carried totals and a per-plugin table that fell
behind every skill added or pruned. plugin.json is what Claude Code loads,
so it is the source these numbers have to match.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INTRODUCTION = REPO_ROOT / "book" / "src" / "introduction.md"
API_OVERVIEW = REPO_ROOT / "docs" / "api-overview.md"


def _registrations() -> dict[str, dict[str, int]]:
    """Per-plugin counts of registered commands, skills and agents."""
    counts: dict[str, dict[str, int]] = {}
    for manifest in sorted(REPO_ROOT.glob("plugins/*/.claude-plugin/plugin.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        counts[data["name"]] = {
            kind: len(data.get(kind, [])) for kind in ("commands", "skills", "agents")
        }
    return counts


def _flat(path: Path) -> str:
    """Collapse whitespace so a number wrapped onto the next line still matches."""
    return " ".join(path.read_text(encoding="utf-8").split())


def test_introduction_plugin_count_matches_manifests() -> None:
    """The book's opening sentence names the number of shipped plugins."""
    match = re.search(r"contains (\d+) plugins", _flat(INTRODUCTION))
    assert match, "introduction.md no longer states a plugin count"
    assert int(match.group(1)) == len(_registrations())


def test_api_overview_plugin_count_matches_manifests() -> None:
    """The API summary names the number of plugins."""
    match = re.search(r"exposes (\d+) plugins", _flat(API_OVERVIEW))
    assert match, "api-overview.md no longer states a plugin count"
    assert int(match.group(1)) == len(_registrations())


@pytest.mark.parametrize(
    ("kind", "phrase"),
    [
        ("commands", r"(\d+) CLI commands"),
        ("skills", r"(\d+) modular skills"),
        ("agents", r"(\d+) specialized agents"),
    ],
)
def test_api_overview_totals_match_manifests(kind: str, phrase: str) -> None:
    """Each ecosystem total is the sum over every plugin.json."""
    match = re.search(phrase, _flat(API_OVERVIEW))
    assert match, f"api-overview.md no longer states a {kind} total"
    expected = sum(plugin[kind] for plugin in _registrations().values())
    assert int(match.group(1)) == expected


def test_api_overview_table_rows_match_manifests() -> None:
    """Each inventory row carries that plugin's registered counts."""
    rows = re.findall(
        r"^\| ([a-z-]+) \| [\d.]+ \| (\d+) \| (\d+) \| (\d+) \|",
        API_OVERVIEW.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    documented = {
        name: {"commands": int(c), "skills": int(s), "agents": int(a)}
        for name, c, s, a in rows
    }
    assert documented == _registrations()
