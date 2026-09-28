"""Every shipped SKILL.md carries an Exit Criteria section.

`.claude/rules/skill-exit-criteria.md` requires one: a skill without exit
criteria gives the model no observable point at which to stop. The rule
alone let most skills ship without the section until a backfill closed the
gap, so this sweep is what keeps it closed.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXIT_CRITERIA = re.compile(r"^## Exit Criteria\s*$", re.MULTILINE)


def test_every_skill_file_has_an_exit_criteria_section() -> None:
    """List every skill missing the section, so the fix needs no search."""
    missing = [
        skill.relative_to(REPO_ROOT).as_posix()
        for skill in sorted(REPO_ROOT.glob("plugins/*/skills/*/SKILL.md"))
        if not EXIT_CRITERIA.search(skill.read_text(encoding="utf-8"))
    ]
    assert missing == [], "\n".join(missing)
