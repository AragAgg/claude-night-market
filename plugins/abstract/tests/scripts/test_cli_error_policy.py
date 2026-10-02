"""The analysis scripts share the error policy of ``abstract.cli._run``.

I/O and input failures (``FileNotFoundError``, ``OSError``, ``ValueError``)
become a failed ``CLIResult``. Any other exception is a programming error and
propagates, so a ``KeyError`` is never reported as ``error="'path'"``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import context_optimizer
from context_optimizer import ContextOptimizer, ContextOptimizerCLI
from skill_analyzer import SkillAnalyzer, SkillAnalyzerCLI
from token_estimator import TokenEstimator, TokenEstimatorCLI

from abstract.config import AbstractConfig


def _skill(tmp_path: Path) -> Path:
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\nname: x\n---\n\n# Skill\n", encoding="utf-8")
    return skill


def _context_optimizer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> tuple[Any, argparse.Namespace]:
    monkeypatch.setattr(
        context_optimizer, "load_config_with_defaults", lambda root: AbstractConfig()
    )
    monkeypatch.setattr(context_optimizer, "find_project_root", lambda path: tmp_path)

    def explode(self: object, path: Path) -> None:
        raise error

    monkeypatch.setattr(ContextOptimizer, "analyze_skill_size", explode)
    args = argparse.Namespace(command="analyze", path=_skill(tmp_path), config=None)
    return ContextOptimizerCLI(), args


def _token_estimator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> tuple[Any, argparse.Namespace]:
    def explode(self: object, *args: object) -> None:
        raise error

    monkeypatch.setattr(TokenEstimator, "analyze_file", explode)
    args = argparse.Namespace(
        file=_skill(tmp_path), directory=None, include_dependencies=False
    )
    return TokenEstimatorCLI(), args


def _skill_analyzer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> tuple[Any, argparse.Namespace]:
    def explode(self: object, *args: object) -> None:
        raise error

    monkeypatch.setattr(SkillAnalyzer, "analyze_file", explode)
    args = argparse.Namespace(
        file=_skill(tmp_path), directory=None, threshold=150, verbose=0
    )
    return SkillAnalyzerCLI(), args


CLIS = pytest.mark.parametrize(
    "build",
    [_context_optimizer, _token_estimator, _skill_analyzer],
    ids=["context_optimizer", "token_estimator", "skill_analyzer"],
)

Build = Callable[
    [Path, pytest.MonkeyPatch, Exception], "tuple[Any, argparse.Namespace]"
]


@pytest.mark.unit
@CLIS
def test_programming_error_propagates_instead_of_becoming_a_result(
    build: Build, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli, args = build(tmp_path, monkeypatch, KeyError("path"))
    with pytest.raises(KeyError, match="path"):
        cli.execute(args)


@pytest.mark.unit
@CLIS
@pytest.mark.parametrize(
    "error",
    [FileNotFoundError("gone"), OSError("disk"), ValueError("bad frontmatter")],
    ids=["FileNotFoundError", "OSError", "ValueError"],
)
def test_io_and_input_errors_become_a_failed_result(
    build: Build,
    error: Exception,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cli, args = build(tmp_path, monkeypatch, error)
    result = cli.execute(args)
    assert result.success is False
    assert result.error == str(error)
