"""A git command that fails stops the walk, and the proof says which one.

Six reads of git output ignored the exit code. A failed ``git diff
--name-only`` read as "nothing changed", so the scope fence passed an
empty list, and a failed ``git checkout -- .`` at park left the edits
in place while the proof said they were reverted. Each case here fails
exactly one git command and checks that the item does not end ready,
that the proof names the command, and that ``main`` reports a broken
walk rather than a finished one.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import night_run
import pytest

from tests.test_handoff_gate import write_item
from tests.test_item_walk import HANDOFF, mktask

#: The evidence command ``mktask("T1")`` declares, as argv.
EVIDENCE = ("pytest", "-q", "-k", "T1")


class FailOneGitCommand:
    """Answer every command with exit 0 except one exact git argv.

    Matching the whole argv rather than a substring keeps ``git diff``
    apart from ``git diff --name-only``, which is the distinction the
    discard path depends on.
    """

    def __init__(
        self,
        failing: tuple[str, ...],
        outputs: dict[tuple[str, ...], tuple[int, str]] | None = None,
    ) -> None:
        """Fail ``failing`` exactly; answer the argv in ``outputs`` as scripted."""
        self.failing = failing
        self.outputs = outputs or {}
        self.calls: list[tuple[str, ...]] = []

    def run(
        self,
        command: Sequence[str],
        cwd: Path | None = None,
        timeout: int = 0,
        env=None,
    ) -> night_run.Completed:
        del cwd, timeout, env
        argv = tuple(command)
        self.calls.append(argv)
        if argv == self.failing:
            return night_run.Completed(returncode=128, output="fatal: not a git repo")
        code, output = self.outputs.get(argv, (0, ""))
        return night_run.Completed(returncode=code, output=output)


def _passing_sitter(**_: object) -> tuple[str, str, str]:
    return ("PASS", "", "")


#: Git reads made while a task is judged. The evidence passes, so the
#: walk reaches every one of them unless the failing one stops it.
WALK_READS = [
    ("git", "diff", "--name-only"),
    ("git", "status", "--porcelain", "-uall"),
    ("git", "diff", "--numstat"),
    ("git", "diff", "--unified=0"),
]

#: Git commands made when a parked item discards what the task left.
DISCARD_COMMANDS = [
    ("git", "diff"),
    ("git", "checkout", "--", "."),
]


class TestAGitFailureStopsTheWalk:
    """Feature: no git failure is read as an empty answer."""

    @pytest.mark.parametrize("failing", WALK_READS, ids=" ".join)
    def test_a_failed_read_while_judging_a_task(
        self, tmp_path: Path, failing: tuple[str, ...]
    ) -> None:
        runner = FailOneGitCommand(failing, {EVIDENCE: (0, "1 passed")})

        result = night_run.run_item(
            HANDOFF, [mktask("T1", [])], tmp_path, runner, babysitter=_passing_sitter
        )

        assert result.status == "git_failed"
        assert " ".join(failing) in result.reason
        assert result.committed == []

    @pytest.mark.parametrize("failing", DISCARD_COMMANDS, ids=" ".join)
    def test_a_failed_command_while_discarding_at_park(
        self, tmp_path: Path, failing: tuple[str, ...]
    ) -> None:
        """The task fails its evidence, so the item parks and discards."""
        runner = FailOneGitCommand(
            failing,
            {
                EVIDENCE: (1, "1 failed"),
                ("git", "diff", "--name-only"): (0, "a/T1.py\n"),
            },
        )

        result = night_run.run_item(
            HANDOFF, [mktask("T1", [])], tmp_path, runner, babysitter=_passing_sitter
        )

        assert result.status == "git_failed"
        assert " ".join(failing) in result.reason
        proof = night_run.write_proof(tmp_path / "item", result).read_text()
        assert "git_failed" in proof


class TestMainReportsABrokenWalk:
    """Feature: the exit code tells a git failure from a finished night."""

    def test_main_exits_walk_broken_and_still_writes_the_proof(
        self, tmp_path: Path
    ) -> None:
        item = write_item(tmp_path)
        runner = FailOneGitCommand(("git", "diff", "--name-only"))

        code = night_run.main(
            ["--item-dir", str(item), "--root", str(tmp_path)],
            runner=runner,
            babysitter=_passing_sitter,
        )

        assert code == night_run.WALK_BROKEN_EXIT
        proof = (item / "proof.md").read_text()
        assert "**Status**: git_failed" in proof
        assert "git diff --name-only" in proof
