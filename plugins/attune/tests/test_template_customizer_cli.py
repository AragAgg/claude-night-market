"""CLI contract for scripts/template_customizer.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "template_customizer.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


@pytest.mark.unit
def test_prints_the_paradigm_structure_with_the_module_substituted() -> None:
    """Each template path is printed with {module} filled in."""
    result = _run("--paradigm", "functional-core", "--module", "billing")

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "Generated structure for functional-core:"
    assert "  - src/billing/core/domain.py" in lines
    assert not any("{module}" in line for line in lines)


@pytest.mark.unit
def test_unknown_paradigm_exits_nonzero_naming_it() -> None:
    """A paradigm missing from the YAML fails loudly, printing no structure."""
    result = _run("--paradigm", "no-such-paradigm", "--module", "billing")

    assert result.returncode != 0
    assert "Unknown paradigm: no-such-paradigm" in result.stderr
    assert result.stdout == ""
