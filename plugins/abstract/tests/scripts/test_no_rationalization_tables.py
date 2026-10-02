"""Guard: no skill, command, agent or shared module ships a retired table.

bounded-autonomy.md retires the thought-versus-reality table. The rules
validator flags it one file at a time, so this sweep is what keeps a copied
table from landing anywhere in the plugin tree or the book.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from rules_validator import check_retired_patterns

REPO_ROOT = Path(__file__).resolve().parents[4]

# These two explain the retirement and quote the shape they retire.
RETIREMENT_DOCS = frozenset(
    {
        "plugins/abstract/skills/skill-authoring/modules/persuasion-principles.md",
        "plugins/abstract/skills/modular-skills/modules/enforcement-patterns.md",
    }
)

SWEPT_GLOBS = (
    "plugins/*/skills/**/*.md",
    "plugins/*/commands/**/*.md",
    "plugins/*/agents/**/*.md",
    "plugins/*/shared-modules/**/*.md",
    "book/src/**/*.md",
)


def test_no_rationalization_tables_outside_retirement_docs() -> None:
    """Every hit names its file and line so the fix is one edit away."""
    findings: list[str] = []
    for pattern in SWEPT_GLOBS:
        for md_file in sorted(REPO_ROOT.glob(pattern)):
            relative = md_file.relative_to(REPO_ROOT).as_posix()
            if relative in RETIREMENT_DOCS or "/.venv/" in relative:
                continue
            findings.extend(check_retired_patterns(md_file))
    assert findings == [], "\n".join(findings)
