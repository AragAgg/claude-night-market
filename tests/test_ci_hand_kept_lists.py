"""Guard that every hand-kept plugin list in CI still matches the tree.

Four lists were written out by hand and drifted as plugins were added:

- ``.pre-commit-config.yaml`` carried one ``validate-<name>-plugin`` hook
  per plugin, 19 hooks for 23 plugins. cartograph, gauntlet, herald and
  oracle could change their manifests with no structural check at all.
- ``python39-compat.yml`` named the hooks directories it lints and
  triggers on. herald and hookify ship Python hooks and were in neither
  list, so a PEP 604 union in either reached system Python 3.9 unchecked.
- The ``check-json-utils-drift`` pre-commit trigger watched
  ``hooks/session-start.sh``, while the vendored copies it compares live
  at ``hooks/shared/json_utils.sh``. Editing a copy never ran the check,
  and no workflow ran it either.

Each test derives the expected set from the directory tree, so adding a
plugin or a vendored copy fails here until the list that should cover it
does.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from fnmatch import fnmatch
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PRECOMMIT = REPO_ROOT / ".pre-commit-config.yaml"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PY39_WORKFLOW = WORKFLOWS / "python39-compat.yml"
DRIFT_SCRIPT = "scripts/shared/check-json-utils-drift.sh"


def _load_glob_translator():
    """Reuse the GitHub ``paths:`` translator the ecosystem guard defines."""
    path = Path(__file__).parent / "test_ci_covers_ecosystem_gates.py"
    spec = importlib.util.spec_from_file_location("_ecosystem_gates", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._github_glob_to_regex


_github_glob_to_regex = _load_glob_translator()


def _workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _trigger_paths(workflow: dict, event: str) -> list[re.Pattern[str]]:
    # PyYAML reads a bare `on:` key as the boolean True.
    triggers = workflow.get("on") or workflow[True]
    return [_github_glob_to_regex(p) for p in triggers[event].get("paths", [])]


def _precommit_hooks() -> list[dict]:
    config = yaml.safe_load(PRECOMMIT.read_text(encoding="utf-8"))
    return [hook for repo in config["repos"] for hook in repo["hooks"]]


def _plugins() -> list[str]:
    return sorted(
        p.name
        for p in (REPO_ROOT / "plugins").iterdir()
        if (p / ".claude-plugin" / "plugin.json").is_file()
    )


def _plugins_with_python_hooks() -> list[str]:
    return sorted(
        name
        for name in _plugins()
        if any(
            "__pycache__" not in f.parts
            for f in (REPO_ROOT / "plugins" / name / "hooks").glob("**/*.py")
        )
    )


def _vendored_json_utils() -> list[str]:
    tracked = subprocess.run(
        ["git", "ls-files", "plugins/*/hooks/shared/json_utils.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return sorted(tracked)


# --------------------------------------------------------------------------
# 2a: plugin structure validation reaches every plugin
# --------------------------------------------------------------------------


def test_the_tree_has_plugins() -> None:
    assert len(_plugins()) > 20


@pytest.mark.parametrize("plugin", _plugins())
def test_plugin_validation_hook_covers_every_plugin(plugin: str) -> None:
    """GIVEN a plugin with a manifest
    WHEN its manifest is staged
    THEN some pre-commit hook running validate_plugin.py fires on it.
    """
    manifest = f"plugins/{plugin}/.claude-plugin/plugin.json"
    validators = [
        hook
        for hook in _precommit_hooks()
        if "validate_plugin.py" in hook.get("entry", "")
        or "validate_staged_plugins.py" in hook.get("entry", "")
    ]
    assert validators, "no pre-commit hook runs validate_plugin.py"
    assert any(re.search(hook.get("files", ""), manifest) for hook in validators), (
        f"no plugin validation hook triggers on {manifest}"
    )


# --------------------------------------------------------------------------
# 2b: python39-compat.yml reaches every plugin that ships Python hooks
# --------------------------------------------------------------------------


def test_some_plugins_ship_python_hooks() -> None:
    assert len(_plugins_with_python_hooks()) > 10


@pytest.mark.parametrize("event", ["push", "pull_request"])
@pytest.mark.parametrize("plugin", _plugins_with_python_hooks())
def test_python39_trigger_covers_every_python_hooks_dir(
    plugin: str, event: str
) -> None:
    filters = _trigger_paths(_workflow(PY39_WORKFLOW), event)
    probe = f"plugins/{plugin}/hooks/probe.py"
    assert any(f.match(probe) for f in filters), (
        f"a {event} touching {probe} does not trigger {PY39_WORKFLOW.name}"
    )


@pytest.mark.parametrize("plugin", _plugins_with_python_hooks())
def test_python39_syntax_gate_lints_every_python_hooks_dir(plugin: str) -> None:
    steps = _workflow(PY39_WORKFLOW)["jobs"]["syntax-check"]["steps"]
    command = next(s["run"] for s in steps if "ruff check" in str(s.get("run", "")))
    targets = [tok for tok in command.split() if tok.startswith("plugins/")]
    hooks_dir = f"plugins/{plugin}/hooks/"
    assert any(fnmatch(hooks_dir, t) for t in targets), (
        f"the ruff step does not lint {hooks_dir}; targets are {targets}"
    )


def test_python39_matrix_names_exactly_the_plugins_with_python_hooks() -> None:
    """The matrix carries a per-plugin test path, so it stays hand-kept.

    A plugin missing from it ships hooks that system Python 3.9 never
    runs in CI. A plugin listed without Python hooks passes by testing
    nothing relevant.
    """
    matrix = _workflow(PY39_WORKFLOW)["jobs"]["hook-tests"]["strategy"]["matrix"]
    listed = {entry["plugin"] for entry in matrix["include"]}
    assert listed == set(_plugins_with_python_hooks())


# --------------------------------------------------------------------------
# 2d: the json_utils.sh drift check runs whenever a copy changes
# --------------------------------------------------------------------------


def test_json_utils_has_vendored_copies() -> None:
    assert len(_vendored_json_utils()) >= 2


def test_drift_script_compares_every_vendored_copy() -> None:
    script = (REPO_ROOT / DRIFT_SCRIPT).read_text(encoding="utf-8")
    listed = sorted(re.findall(r'"(plugins/[^"]+/json_utils\.sh)"', script))
    assert listed == _vendored_json_utils()


def test_drift_hook_triggers_on_every_copy() -> None:
    hook = next(h for h in _precommit_hooks() if h["id"] == "check-json-utils-drift")
    watched = [
        "scripts/shared/json_utils.sh",
        DRIFT_SCRIPT,
        *_vendored_json_utils(),
    ]
    missed = [path for path in watched if not re.search(hook["files"], path)]
    assert not missed, f"check-json-utils-drift does not fire on {missed}"


def _workflows_running_drift_script() -> list[Path]:
    return [
        path
        for path in sorted(WORKFLOWS.glob("*.y*ml"))
        if DRIFT_SCRIPT in path.read_text(encoding="utf-8")
    ]


def test_a_workflow_runs_the_drift_script() -> None:
    assert _workflows_running_drift_script(), (
        f"no workflow runs {DRIFT_SCRIPT}; the check exists only on "
        "contributors' machines"
    )


@pytest.mark.parametrize("event", ["push", "pull_request"])
def test_drift_workflow_triggers_on_every_copy(event: str) -> None:
    for path in _workflows_running_drift_script():
        filters = _trigger_paths(_workflow(path), event)
        watched = ["scripts/shared/json_utils.sh", *_vendored_json_utils()]
        missed = [p for p in watched if not any(f.match(p) for f in filters)]
        assert not missed, f"{path.name} {event} filter misses {missed}"
