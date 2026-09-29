"""Testkit tự có răng — bộ chấm mà không bắt được lỗi thì vứt đi.

Hai hướng kiểm:
  * ba plugin mẫu của host phải **qua** trọn bộ;
  * plugin cố tình sai phải **trượt** đúng mục đó, không trượt mù.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from testkit import assert_plugin_ok, format_report, grade_plugin

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PLUGINS = REPO_ROOT / "cautreo-host" / "plugins"


def write_plugin(root: Path, manifest: str, logic: str = "", name: str = "p") -> Path:
    p = root / name
    (p / "logic").mkdir(parents=True, exist_ok=True)
    (p / "plugin.toml").write_text(manifest, encoding="utf-8")
    (p / "logic" / "main.py").write_text(logic, encoding="utf-8")
    return p


def fails(checks, name: str) -> bool:
    return any(c.name == name and not c.ok for c in checks)


def passes(checks, name: str) -> bool:
    return any(c.name == name and c.ok for c in checks)


OK_LOGIC = """
class Plugin:
    method_grants = {"run": ["fs.workspace"]}
    def run(self, ctx=None, **params):
        return {"summary": "ok"}
"""

OVERREACH_LOGIC = """
class Plugin:
    # Khai xin model.connect nhưng manifest chỉ cho fs.workspace.
    method_grants = {"run": ["model.connect"]}
    def run(self, ctx=None, **params):
        return {"summary": "ok"}
"""


class TestSamplePluginsPass:
    @pytest.mark.parametrize("name", ["tool.fs-read", "tool.fs-write", "vivy.runtime"])
    def test_host_samples_are_graded_ok(self, name):
        checks = grade_plugin(SAMPLE_PLUGINS / name)
        assert all(c.ok for c in checks), format_report(checks)

    def test_assert_plugin_ok_is_silent_when_clean(self):
        assert_plugin_ok(SAMPLE_PLUGINS / "tool.fs-read")


class TestTestkitHasTeeth:
    def test_manifest_hole_is_caught(self, tmp_path):
        p = write_plugin(
            tmp_path,
            '[plugin]\nid = "tool.x"\nversion = "1.0.0"\napi = 2\nkind = "tool"\n'
            'organ = "eye"\n[entry]\nlogic = "logic/main.py"\n',
            OK_LOGIC,
        )
        checks = grade_plugin(p)
        assert fails(checks, "manifest hợp lệ"), format_report(checks)
        # Manifest hỏng thì không chấm tiếp phần runtime — không lặp lại một lỗi.
        assert not any(c.name.startswith("nạp được") for c in checks)

    def test_organ_rule_is_enforced(self, tmp_path):
        p = write_plugin(
            tmp_path,
            '[plugin]\nid = "tool.x"\nversion = "1.0.0"\napi = 1\nkind = "tool"\n'
            '[entry]\nlogic = "logic/main.py"\n',
            OK_LOGIC,
            name="no-organ",
        )
        checks = grade_plugin(p)
        assert fails(checks, "manifest hợp lệ"), format_report(checks)
        assert "BẮT BUỘC" in next(c.detail for c in checks if not c.ok)

    def test_missing_entry_file_is_caught(self, tmp_path):
        p = tmp_path / "ghost"
        p.mkdir()
        (p / "plugin.toml").write_text(
            '[plugin]\nid = "tool.ghost"\nversion = "1.0.0"\napi = 1\nkind = "tool"\n'
            'organ = "hand"\n[entry]\nlogic = "logic/main.py"\n',
            encoding="utf-8",
        )
        checks = grade_plugin(p)
        assert fails(checks, "file entry có mặt"), format_report(checks)

    def test_unknown_grant_is_caught(self, tmp_path):
        p = write_plugin(
            tmp_path,
            '[plugin]\nid = "tool.x"\nversion = "1.0.0"\napi = 1\nkind = "tool"\n'
            'organ = "eye"\n[entry]\nlogic = "logic/main.py"\n'
            '[permissions]\ngrant = ["fs.telepathy"]\n',
            OK_LOGIC,
            name="bad-grant",
        )
        checks = grade_plugin(p)
        assert fails(checks, "grant nằm trong bảng host biết"), format_report(checks)

    def test_method_grant_beyond_manifest_is_caught(self, tmp_path):
        p = write_plugin(
            tmp_path,
            '[plugin]\nid = "tool.x"\nversion = "1.0.0"\napi = 1\nkind = "tool"\n'
            'organ = "eye"\n[entry]\nlogic = "logic/main.py"\n'
            '[permissions]\ngrant = ["fs.workspace"]\n',
            OVERREACH_LOGIC,
            name="overreach",
        )
        checks = grade_plugin(p)
        assert passes(checks, "nạp được qua PluginRegistry"), format_report(checks)
        assert fails(checks, "method_grants nằm trong permissions.grant"), format_report(checks)
        detail = next(c.detail for c in checks if not c.ok)
        assert "model.connect" in detail

    def test_assert_plugin_ok_raises_with_report(self, tmp_path):
        p = write_plugin(
            tmp_path,
            '[plugin]\nid = "tool.x"\nversion = "1.0.0"\napi = 1\nkind = "tool"\n'
            'organ = "eye"\n[entry]\nlogic = "logic/khong-co.py"\n',
            OK_LOGIC,
            name="will-fail",
        )
        with pytest.raises(AssertionError) as exc:
            assert_plugin_ok(p)
        assert "trượt" in str(exc.value)
        assert "file entry có mặt" in str(exc.value)

    def test_missing_directory_is_a_fail_not_a_crash(self, tmp_path):
        checks = grade_plugin(tmp_path / "khong-ton-tai")
        assert len(checks) == 1
        assert not checks[0].ok
