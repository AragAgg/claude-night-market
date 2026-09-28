"""Pick which plugin test suites plugin-tests.yml runs.

Reads the discovered suites (one plugin name per line) on stdin and prints
the selection as a JSON list. With ``--changed-files`` it narrows to the
plugins a pull request touched plus their direct dependents; without it,
as on a push to master, it selects every suite.

Dependents come from docs/plugin-dependencies.json, which
tests/test_plugin_dependency_manifest.py pins to the import scan. Reading
it rather than listing edges here keeps this selection from drifting the
way the hand-kept CI lists did. One hop only: abstract is a dependency of
every plugin, so following edges transitively would turn any leyline
change into the full set, and push to master runs the full set anyway.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "docs" / "plugin-dependencies.json"

# Inputs every suite reads. A path ending in "/" matches everything under it.
SHARED_PATHS = (
    "conftest.py",
    "plugins/conftest_shared.py",
    "pyproject.toml",
    ".github/workflows/plugin-tests.yml",
    "plugins/abstract/config/",
    "scripts/select_plugin_suites.py",
)


def _is_shared(path: str) -> bool:
    return any(
        path.startswith(shared) if shared.endswith("/") else path == shared
        for shared in SHARED_PATHS
    )


def load_dependents(manifest: Path) -> dict[str, list[str]]:
    """Map each provider plugin to the plugins that import it."""
    dependencies = json.loads(manifest.read_text(encoding="utf-8"))["dependencies"]
    return {name: entry["dependents"] for name, entry in dependencies.items()}


def select(
    discovered: list[str],
    changed: list[str] | None,
    dependents: dict[str, list[str]],
) -> list[str]:
    """Return the discovered suites a change can break, sorted."""
    if changed is None or any(_is_shared(path) for path in changed):
        return sorted(discovered)
    touched = {
        Path(path).parts[1]
        for path in changed
        if Path(path).parts[:1] == ("plugins",) and len(Path(path).parts) > 2
    }
    for plugin in list(touched):
        touched.update(dependents.get(plugin, []))
    return sorted(touched.intersection(discovered))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--changed-files",
        type=Path,
        help="newline-separated changed paths; omit to select every suite",
    )
    args = parser.parse_args(argv)
    discovered = [line.strip() for line in sys.stdin if line.strip()]
    changed = None
    if args.changed_files is not None:
        changed = args.changed_files.read_text(encoding="utf-8").split()
    print(json.dumps(select(discovered, changed, load_dependents(MANIFEST))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
