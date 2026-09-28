"""Tests for scripts/select_plugin_suites.py.

Feature: a pull request runs the plugin suites its change can break
  As a contributor opening a PR that touches one plugin
  I want CI to run that plugin's suite and its direct dependents' suites
  So that 24 jobs do not spin up for a one-plugin change, while a change
  to shared test configuration still runs every suite

Push to master and workflow_dispatch pass no changed-file list and get
the full set. Dependents come from docs/plugin-dependencies.json, which
test_plugin_dependency_manifest.py pins to the import scan.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "select_plugin_suites.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "plugin-tests.yml"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import select_plugin_suites as sps


def _load_glob_translator():
    """Reuse the GitHub ``paths:`` translator the ecosystem guard defines."""
    path = REPO_ROOT / "tests" / "test_ci_covers_ecosystem_gates.py"
    spec = importlib.util.spec_from_file_location("_ecosystem_gates", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._github_glob_to_regex


_github_glob_to_regex = _load_glob_translator()

DISCOVERED = ["abstract", "conjure", "egregore", "herald", "leyline", "sanctum"]
DEPENDENTS = {
    "abstract": ["conjure", "egregore", "herald", "leyline", "sanctum"],
    "leyline": ["conjure", "sanctum"],
    "herald": ["egregore"],
}


class TestSelect:
    @pytest.mark.unit
    def test_no_changed_list_selects_every_suite(self) -> None:
        """
        Scenario: push to master or a manual run
        Given no changed-file list
        When suites are selected
        Then every discovered suite runs
        """
        assert sps.select(DISCOVERED, None, DEPENDENTS) == DISCOVERED

    @pytest.mark.unit
    def test_changed_plugin_selects_itself(self) -> None:
        assert sps.select(DISCOVERED, ["plugins/sanctum/x.py"], DEPENDENTS) == [
            "sanctum"
        ]

    @pytest.mark.unit
    def test_changed_provider_selects_its_direct_dependents(self) -> None:
        """
        Scenario: a PR changes leyline
        Given sanctum and conjure import leyline
        When suites are selected
        Then leyline, sanctum and conjure run, and nothing else
        """
        selected = sps.select(DISCOVERED, ["plugins/leyline/src/x.py"], DEPENDENTS)
        assert selected == ["conjure", "leyline", "sanctum"]

    @pytest.mark.unit
    def test_herald_change_selects_egregore(self) -> None:
        selected = sps.select(DISCOVERED, ["plugins/herald/hooks/h.py"], DEPENDENTS)
        assert selected == ["egregore", "herald"]

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "shared",
        [
            "conftest.py",
            "plugins/conftest_shared.py",
            "pyproject.toml",
            ".github/workflows/plugin-tests.yml",
            "plugins/abstract/config/make/common.mk",
        ],
    )
    def test_shared_path_selects_every_suite(self, shared: str) -> None:
        """
        Scenario: a PR changes configuration every suite reads
        Given a shared path among the changed files
        When suites are selected
        Then every suite runs
        """
        selected = sps.select(DISCOVERED, ["plugins/sanctum/x.py", shared], {})
        assert selected == DISCOVERED

    @pytest.mark.unit
    def test_plugin_without_suite_is_not_selected(self) -> None:
        """A changed plugin with no tests/ directory has no job to run."""
        assert sps.select(DISCOVERED, ["plugins/scry/README.md"], DEPENDENTS) == []

    @pytest.mark.unit
    def test_non_plugin_change_selects_nothing(self) -> None:
        assert sps.select(DISCOVERED, ["README.md", "docs/x.md"], DEPENDENTS) == []


class TestCli:
    @pytest.mark.unit
    def test_cli_reads_discovered_suites_and_prints_json(self, tmp_path: Path) -> None:
        """The workflow pipes `find` output in and reads a JSON list back."""
        changed = tmp_path / "changed.txt"
        changed.write_text("plugins/herald/hooks/h.py\n", encoding="utf-8")

        outcome = subprocess.run(
            [sys.executable, str(SCRIPT), "--changed-files", str(changed)],
            input="abstract\negregore\nherald\n",
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        assert json.loads(outcome.stdout) == ["egregore", "herald"]

    @pytest.mark.unit
    def test_cli_without_changed_files_prints_every_suite(self) -> None:
        outcome = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="abstract\nherald\n",
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        assert json.loads(outcome.stdout) == ["abstract", "herald"]

    @pytest.mark.unit
    def test_real_manifest_names_the_reviewed_edges(self) -> None:
        """leyline and herald dependents come from the committed manifest."""
        dependents = sps.load_dependents(
            REPO_ROOT / "docs" / "plugin-dependencies.json"
        )
        assert {"sanctum", "gauntlet", "memory-palace", "conjure"} <= set(
            dependents["leyline"]
        )
        assert "egregore" in dependents["herald"]


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


class TestWorkflowWiring:
    @pytest.mark.unit
    def test_discover_step_pipes_through_the_selector(self, workflow: dict) -> None:
        listing = next(
            s for s in workflow["jobs"]["discover"]["steps"] if s.get("id") == "list"
        )
        assert "scripts/select_plugin_suites.py" in listing["run"]

    @pytest.mark.unit
    @pytest.mark.parametrize("event", ["push", "pull_request"])
    def test_every_shared_path_triggers_the_workflow(
        self, workflow: dict, event: str
    ) -> None:
        """A shared-path-only PR must start the workflow for the fallback to run."""
        triggers = workflow.get("on") or workflow[True]
        patterns = triggers[event]["paths"]

        filters = [_github_glob_to_regex(p) for p in patterns]

        def matches(path: str) -> bool:
            return any(f.match(path) for f in filters)

        probes = [p if not p.endswith("/") else p + "probe" for p in sps.SHARED_PATHS]
        missed = [p for p in probes if not matches(p)]
        assert not missed, f"{event} paths miss shared inputs {missed}"

    @pytest.mark.unit
    def test_suite_job_skips_an_empty_selection(self, workflow: dict) -> None:
        """GitHub rejects a matrix with no values, so an empty pick must skip."""
        condition = str(workflow["jobs"]["plugin-suite"].get("if", ""))
        assert "needs.discover.outputs.plugins" in condition
        assert "[]" in condition
