"""CLI contract for scripts/check_skill_coverage.py (the Makefile target)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import check_skill_coverage


def _plugin(root: Path, *, on_disk: list[str], plugin: list[str], meta: list[str]):
    manifests = root / ".claude-plugin"
    manifests.mkdir(parents=True)
    for manifest, names in (("plugin.json", plugin), ("metadata.json", meta)):
        entries = [f"./skills/{name}" for name in names]
        (manifests / manifest).write_text(json.dumps({"skills": entries}))
    for name in on_disk:
        (root / "skills" / name).mkdir(parents=True)
        (root / "skills" / name / "SKILL.md").write_text("---\nname: x\n---\n")


@pytest.mark.unit
def test_agreeing_manifests_and_disk_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Every skill registered in both manifests and on disk reports OK."""
    _plugin(tmp_path, on_disk=["alpha"], plugin=["alpha"], meta=["alpha"])
    monkeypatch.setattr(check_skill_coverage, "PLUGIN_ROOT", tmp_path)

    assert check_skill_coverage.main() == 0
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "[OK]" in out
    assert "failed" not in out


@pytest.mark.unit
def test_disagreement_in_either_direction_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """A skill missing from a manifest and a registered ghost both fail."""
    _plugin(
        tmp_path,
        on_disk=["alpha", "beta"],
        plugin=["alpha", "beta", "ghost"],
        meta=["alpha"],
    )
    monkeypatch.setattr(check_skill_coverage, "PLUGIN_ROOT", tmp_path)

    assert check_skill_coverage.main() == 1
    out = capsys.readouterr().out
    assert "beta                 [X] on disk, absent from metadata.json" in out
    assert "ghost                [X] registered, no SKILL.md" in out
    assert "Skill coverage failed" in out
