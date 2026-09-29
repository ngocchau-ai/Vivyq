"""Tests for vivy.runtime/help — catalogue of real verbs/methods only."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_MAIN = Path(__file__).resolve().parents[1] / "plugins" / "vivy.runtime" / "logic" / "main.py"
_SPEC = importlib.util.spec_from_file_location("vivy_runtime_help_main", _MAIN)
assert _SPEC and _SPEC.loader
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
Plugin = _MOD.Plugin



def test_help_lists_real_verbs_and_methods() -> None:
    out = Plugin().help()
    assert out["summary"] == "hướng dẫn lệnh"
    verbs = {row["verb"].split()[0] for row in out["verbs"]}
    assert {"đọc", "ghi", "hỏi", "tra", "help"} <= verbs
    methods = {row["method"] for row in out["methods"]}
    assert "vivy.runtime/ask" in methods
    assert "vivy.runtime/help" in methods
    host_methods = {row["method"] for row in out["host_methods"]}
    assert "host.body-map" in host_methods
    assert "host.link-probe" in host_methods


def test_help_topic_lookup() -> None:
    out = Plugin().help(topic="tra")
    assert "vivy.runtime/recall" in out["answer"]


def test_help_unknown_topic_does_not_invent() -> None:
    out = Plugin().help(topic="warp-drive")
    assert "Không tìm thấy" in out["answer"]
    assert out["topic"] == "warp-drive"
