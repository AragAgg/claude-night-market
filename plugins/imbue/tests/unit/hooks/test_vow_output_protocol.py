"""The PreToolUse output every vow and guard hook emits.

Claude Code honors ``permissionDecision`` values allow, deny, ask and
defer; any other value is logged and ignored, so the tool call runs
through the normal permission flow. The vow hooks emitted "block" and
"warn", which meant an enforcing vow never blocked anything.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SHARED = Path(__file__).resolve().parents[3] / "hooks" / "shared" / "vow_utils.py"
_DOCUMENTED = {"allow", "deny", "ask", "defer"}


@pytest.fixture(scope="module")
def vow_utils():
    spec = importlib.util.spec_from_file_location("vow_utils_protocol", _SHARED)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["vow_utils_protocol"] = module
    spec.loader.exec_module(module)
    return module


def test_an_enforced_vow_denies_the_call(vow_utils) -> None:
    out = vow_utils.vow_output(enforce=True, reason="no attribution")
    hook = out["hookSpecificOutput"]
    assert hook["hookEventName"] == "PreToolUse"
    assert hook["permissionDecision"] == "deny"
    assert hook["permissionDecision"] in _DOCUMENTED
    assert hook["permissionDecisionReason"] == "no attribution"


def test_a_shadow_vow_informs_without_touching_the_permission_flow(
    vow_utils,
) -> None:
    out = vow_utils.vow_output(enforce=False, reason="no attribution")
    hook = out["hookSpecificOutput"]
    assert "permissionDecision" not in hook
    assert hook["additionalContext"] == "no attribution"
