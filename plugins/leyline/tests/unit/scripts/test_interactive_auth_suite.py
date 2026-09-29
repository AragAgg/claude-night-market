"""Run the interactive_auth.sh suite, which nothing else executes.

The suite drives the sourced library end to end under ``set -u``. It
stopped at Test 13 for as long as it has existed, because looking up an
unknown service in an associative array is fatal there, and no gate ran
it to notice.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SUITE = (
    Path(__file__).resolve().parents[3]
    / "skills"
    / "authentication-patterns"
    / "tests"
    / "test-interactive-auth.sh"
)
# The library uses `declare -A`, which bash 4 introduced.
MIN_BASH_MAJOR = 4


def _modern_bash() -> str | None:
    for candidate in (shutil.which("bash"), "/opt/homebrew/bin/bash", "/bin/bash"):
        if not candidate or not Path(candidate).exists():
            continue
        major = subprocess.run(
            [candidate, "-c", "printf %s ${BASH_VERSINFO[0]}"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        if major.isdigit() and int(major) >= MIN_BASH_MAJOR:
            return candidate
    return None


def test_interactive_auth_suite_runs_to_completion(tmp_path: Path) -> None:
    bash = _modern_bash()
    if bash is None:
        pytest.skip("interactive_auth.sh needs bash 4 or newer")

    result = subprocess.run(
        [bash, str(SUITE)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "CI": ""},
    )

    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert "Correctly rejected unsupported service" in result.stdout


LIBRARY = Path(__file__).resolve().parents[3] / "scripts" / "interactive_auth.sh"


def _source(bash: str, path: str, home: Path, body: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [bash, "-c", f'source "{LIBRARY}" || exit 7; {body}'],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={"PATH": path, "HOME": str(home), "CI": ""},
    )


def test_sourcing_without_jq_reports_the_missing_dependency(tmp_path: Path) -> None:
    """The cache stores numbers jq alone can read, so jq is required."""
    bash = _modern_bash()
    if bash is None:
        pytest.skip("interactive_auth.sh needs bash 4 or newer")
    empty_bin = tmp_path / "bin"
    empty_bin.mkdir()

    result = _source(bash, str(empty_bin), tmp_path, "exit 0")

    assert result.returncode == 7
    assert "[CRIT]" in result.stderr
    assert "jq" in result.stderr


def test_a_freshly_written_cache_entry_is_a_hit(tmp_path: Path) -> None:
    """write_cache stores last_verified unquoted; check_cache must read it."""
    bash = _modern_bash()
    jq = shutil.which("jq")
    if bash is None or jq is None:
        pytest.skip("needs bash 4 or newer and jq")
    path = f"{Path(jq).parent}:/usr/bin:/bin"

    result = _source(
        bash, path, tmp_path, "write_cache github true; check_cache github"
    )

    assert result.returncode == 0, result.stderr
