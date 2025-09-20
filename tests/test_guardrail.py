import pytest

from agentvault_mcp.guardrail import check_text


def test_guardrail_ok_with_patch():
    txt = (
        "*** Begin Patch\n*** Update File: a.py\n@@\n- a\n+ b\n*** End Patch\n"
    )
    assert check_text(txt) == []


def test_guardrail_flags_banned_and_missing_patch():
    txt = "This is a TODO with ... and no patch"
    issues = check_text(txt)
    assert any("banned" in i for i in issues)
    assert any("no unified diff" in i for i in issues)

