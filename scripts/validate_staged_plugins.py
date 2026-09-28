"""Run validate_plugin.py once per plugin that owns a staged file.

Pre-commit passes the staged paths. The plugin set is derived from them
rather than listed, because a hand-kept hook per plugin drifted: 19 hooks
covered 23 plugins, and four could change their manifests unchecked. A
directory under plugins/ is a plugin when it carries
.claude-plugin/plugin.json, the same test run-plugin-typecheck.sh applies.

Runs under system Python 3.9 like every pre-commit entry here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "plugins" / "abstract" / "scripts" / "validate_plugin.py"


def plugin_dirs(paths: list[str], root: Path) -> list[str]:
    """Return plugins/<name> for each plugin a path belongs to, sorted.

    A file directly under plugins/ (conftest_shared.py) has two parts and
    belongs to no plugin, so only paths at least three deep count.
    """
    names = {
        Path(path).parts[1]
        for path in paths
        if Path(path).parts[:1] == ("plugins",) and len(Path(path).parts) > 2
    }
    return sorted(
        f"plugins/{name}"
        for name in names
        if (root / "plugins" / name / ".claude-plugin" / "plugin.json").is_file()
    )


def validate(dirs: list[str], root: Path) -> int:
    """Validate every plugin, then return nonzero if any failed."""
    failed = []
    for plugin in dirs:
        outcome = subprocess.run(
            [sys.executable, str(VALIDATOR), str(root / plugin)], check=False
        )
        if outcome.returncode != 0:
            failed.append(plugin)
    if failed:
        print(f"plugin validation failed: {' '.join(failed)}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    return validate(plugin_dirs(argv, Path.cwd()), Path.cwd())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
