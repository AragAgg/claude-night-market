"""Tests for scripts/validate_staged_plugins.py.

Feature: one pre-commit hook validates the plugins a commit touches
  As a contributor adding a plugin
  I want its structure validated without editing .pre-commit-config.yaml
  So that a new plugin cannot land unchecked the way cartograph,
  gauntlet, herald and oracle did while the hooks were listed by hand
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validate_staged_plugins.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_staged_plugins as vsp


def _make_plugin(root: Path, name: str) -> Path:
    plugin = root / "plugins" / name
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": name}), encoding="utf-8"
    )
    return plugin


class TestPluginDirs:
    @pytest.mark.unit
    def test_groups_staged_files_by_plugin(self, tmp_path: Path) -> None:
        """
        Scenario: several files from two plugins are staged
        Given plugins alpha and beta with manifests
        When their files are passed in
        Then each plugin is named once, in sorted order
        """
        _make_plugin(tmp_path, "alpha")
        _make_plugin(tmp_path, "beta")
        staged = [
            "plugins/beta/skills/x/SKILL.md",
            "plugins/alpha/README.md",
            "plugins/beta/.claude-plugin/plugin.json",
        ]

        assert vsp.plugin_dirs(staged, tmp_path) == ["plugins/alpha", "plugins/beta"]

    @pytest.mark.unit
    def test_skips_directories_without_a_manifest(self, tmp_path: Path) -> None:
        """
        Scenario: a staged path sits in plugins/ but not in a plugin
        Given plugins/__pycache__ and a file directly under plugins/
        When they are passed in
        Then neither is treated as a plugin
        """
        (tmp_path / "plugins" / "__pycache__").mkdir(parents=True)
        staged = ["plugins/__pycache__/x.pyc", "plugins/conftest_shared.py"]

        assert vsp.plugin_dirs(staged, tmp_path) == []

    @pytest.mark.unit
    def test_ignores_paths_outside_plugins(self, tmp_path: Path) -> None:
        assert vsp.plugin_dirs(["scripts/x.py", "README.md"], tmp_path) == []


class TestValidate:
    @pytest.mark.unit
    def test_real_plugin_passes(self) -> None:
        """
        Scenario: a staged file belongs to a plugin that validates cleanly
        Given plugins/herald, one of the four the listed hooks missed
        When the script runs from the repository root
        Then it exits 0
        """
        outcome = subprocess.run(
            [sys.executable, str(SCRIPT), "plugins/herald/README.md"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        assert outcome.returncode == 0, outcome.stdout + outcome.stderr

    @pytest.mark.unit
    def test_failing_plugin_fails_the_run(self, tmp_path: Path) -> None:
        """
        Scenario: one staged plugin fails validation
        Given a plugin whose manifest is not valid JSON
        When the script validates it
        Then the run exits nonzero rather than reporting the others' success
        """
        broken = _make_plugin(tmp_path, "broken")
        (broken / ".claude-plugin" / "plugin.json").write_text("{", encoding="utf-8")

        assert vsp.validate(["plugins/broken"], tmp_path) != 0

    @pytest.mark.unit
    def test_nothing_to_validate_passes(self, tmp_path: Path) -> None:
        assert vsp.validate([], tmp_path) == 0
