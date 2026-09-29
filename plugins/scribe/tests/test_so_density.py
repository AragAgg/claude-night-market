"""Tests for the ", so" density check.

One consequence tail is ordinary English. A page that explains every
fact with ", so ..." reads as generated, and no single sentence is the
defect. The check reports a rate per 1000 words and leaves the rewrite
to a person.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scribe.connectives import (
    DEFAULT_MIN_WORDS,
    DEFAULT_THRESHOLD,
    check_so_density,
)

_FILLER = "The daemon reads the queue and writes one row per event. " * 60


def _doc(tails: int, filler: str = _FILLER) -> str:
    """Filler prose with *tails* consequence tails appended."""
    tail = "The index was stale, so the lookup missed. "
    return filler + tail * tails


@pytest.mark.unit
def test_defaults_are_the_documented_bar() -> None:
    assert DEFAULT_THRESHOLD == 2.0
    assert DEFAULT_MIN_WORDS == 500


@pytest.mark.unit
def test_overuse_is_reported_with_its_arithmetic() -> None:
    findings = check_so_density(_doc(tails=4))

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule == "so_density"
    assert finding.hits == 4
    assert finding.per_thousand > DEFAULT_THRESHOLD
    assert finding.confidence == "low"
    assert "4" in finding.detail
    assert "per 1000 words" in finding.detail


@pytest.mark.unit
def test_occasional_use_is_silent() -> None:
    assert check_so_density(_doc(tails=1)) == []


@pytest.mark.unit
def test_a_rate_exactly_at_the_bar_is_silent() -> None:
    """Strictly above the bar fires: 2 hits in 1000 words is 2.0."""
    filler = "word " * 1000
    text = filler + "It was stale, so it missed. It was stale, so it missed."
    words = len(text.split())
    threshold = 2 * 1000 / words
    assert check_so_density(text, threshold=threshold) == []


@pytest.mark.unit
def test_a_short_document_is_never_judged() -> None:
    """Under the floor, two tails say nothing about habit."""
    text = "It was stale, so it missed. " * 10
    assert len(text.split()) < DEFAULT_MIN_WORDS
    assert check_so_density(text) == []


@pytest.mark.unit
def test_tails_inside_code_are_not_prose() -> None:
    code = "\n```text\n" + "It was stale, so it missed.\n" * 20 + "```\n"
    inline = "`a, so b` " * 20
    assert check_so_density(_FILLER + code + inline) == []


@pytest.mark.unit
def test_counts_the_same_shapes_as_the_pattern_category() -> None:
    """Density and the per-instance category read one regex.

    "so far" and "so-called" are excluded there, and must not count here.
    """
    text = _FILLER + "The results, so far, match. The so-called path. " * 20
    assert check_so_density(text) == []
