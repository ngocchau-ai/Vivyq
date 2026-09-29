"""Bộ 1/5 — Contract test (spec §7.3.1).

Chốt: manifest schema, version, và bus từ chối lời gọi thiếu quyền.
Plugin bên thứ ba chấm bằng đúng bộ này qua `tests/testkit.py`.
"""

from __future__ import annotations

import pytest

from cautreo_host.manifest import (
    SUPPORTED_API,
    ContractError,
    parse_manifest,
    parse_manifest_dict,
)


def base_manifest(**over: object) -> dict:
    """Một manifest hợp lệ, ghi đè từng trường để dựng ca sai."""
    raw = {
        "plugin": {
            "id": "tool.fs-read",
            "version": "1.2.0",
            "api": SUPPORTED_API,
            "kind": "tool",
            "organ": "eye",
        },
        "entry": {"logic": "logic/main.py"},
        "permissions": {"grant": ["fs.workspace"]},
    }
    for key, value in over.items():
        if key in ("plugin", "entry", "permissions"):
            raw[key] = value  # type: ignore[assignment]
        else:
            raw["plugin"][key] = value  # type: ignore[index]
    return raw


class TestManifestHappyPath:
    def test_valid_tool_manifest_parses(self):
        m = parse_manifest_dict(base_manifest())
        assert m.id == "tool.fs-read"
        assert m.version == "1.2.0"
        assert m.kind == "tool"
        assert m.organ == "eye"
        assert m.entry_logic == "logic/main.py"
        assert m.grants == frozenset({"fs.workspace"})

    def test_ui_only_plugin_is_allowed(self):
        m = parse_manifest_dict(
            {
                "plugin": {"id": "panel.vitals", "version": "0.1.0", "api": 1, "kind": "panel"},
                "entry": {"ui": "dist/index.js"},
            }
        )
        assert m.entry_ui == "dist/index.js"
        assert m.entry_logic is None

    def test_workspace_panel_must_not_declare_organ(self):
        m = parse_manifest_dict(
            {
                "plugin": {"id": "workspace.he-thong", "version": "1.0.0", "api": 1, "kind": "workspace"},
                "entry": {"ui": "dist/index.js"},
            }
        )
        assert m.organ is None
        assert m.is_organ is False

    def test_grants_default_to_empty(self):
        m = parse_manifest_dict(
            {
                "plugin": {"id": "tool.t", "version": "1.0.0", "api": 1, "kind": "tool", "organ": "hand"},
                "entry": {"logic": "m.py"},
            }
        )
        assert m.grants == frozenset()
        assert m.needs_model is False

    def test_model_connect_marks_needs_model(self):
        m = parse_manifest_dict(base_manifest(permissions={"grant": ["model.connect"]}))
        assert m.needs_model is True


class TestManifestId:
    @pytest.mark.parametrize("bad", ["tool", "tool.", ".fs", "Tool.fs", "tool.fs read", ""])
    def test_id_must_be_namespaced(self, bad):
        with pytest.raises(ContractError):
            parse_manifest_dict(base_manifest(id=bad))

    def test_id_accepts_namespace_and_underscores(self):
        m = parse_manifest_dict(base_manifest(id="boot.model_loader"))
        assert m.id == "boot.model_loader"


class TestManifestVersion:
    @pytest.mark.parametrize("bad", ["1.2", "v1.2.0", "1.2.0.0", ""])
    def test_version_must_be_semver(self, bad):
        with pytest.raises(ContractError):
            parse_manifest_dict(base_manifest(version=bad))

    @pytest.mark.parametrize("ok", ["0.0.1", "1.2.0", "2.0.0-rc.1"])
    def test_semver_forms_accepted(self, ok):
        assert parse_manifest_dict(base_manifest(version=ok)).version == ok


class TestManifestApi:
    @pytest.mark.parametrize("bad", [2, 0, "1", None, 1.0])
    def test_wrong_api_rejected(self, bad):
        """Host không cố dịch phiên bản contract lạ — lệch api là từ chối."""
        with pytest.raises(ContractError) as exc:
            parse_manifest_dict(base_manifest(api=bad))
        assert "api" in str(exc.value)


class TestManifestOrgan:
    """Điểm chốt của spec §4.1: organ bắt buộc với tool/runtime, trống với workspace/panel."""

    @pytest.mark.parametrize("kind", ["tool", "runtime"])
    @pytest.mark.parametrize("missing", [None, "", "   ", "leg"])
    def test_tool_runtime_without_organ_fails_validation(self, kind, missing):
        with pytest.raises(ContractError) as exc:
            parse_manifest_dict(base_manifest(kind=kind, organ=missing))
        assert "BẮT BUỘC" in str(exc.value)

    @pytest.mark.parametrize("kind", ["workspace", "panel"])
    def test_workspace_panel_with_organ_is_rejected(self, kind):
        with pytest.raises(ContractError) as exc:
            parse_manifest_dict(base_manifest(kind=kind, organ="eye"))
        assert "phải trống" in str(exc.value)

    def test_organ_must_be_known(self):
        with pytest.raises(ContractError):
            parse_manifest_dict(base_manifest(organ="brain"))


class TestManifestKindAndEntry:
    @pytest.mark.parametrize("bad", ["plugin", "Plugin", "", "tool "])
    def test_kind_must_be_known(self, bad):
        with pytest.raises(ContractError):
            parse_manifest_dict(base_manifest(kind=bad))

    def test_missing_entry_table_fails(self):
        with pytest.raises(ContractError) as exc:
            parse_manifest_dict(base_manifest(entry={}))
        assert "entry" in str(exc.value).lower()

    def test_needs_at_least_one_face(self):
        with pytest.raises(ContractError) as exc:
            parse_manifest_dict(base_manifest(entry={"ui": "", "logic": "  "}))
        assert "ui hoặc logic" in str(exc.value)


class TestManifestGrants:
    def test_grant_must_be_string_list(self):
        with pytest.raises(ContractError):
            parse_manifest_dict(base_manifest(permissions={"grant": "fs.workspace"}))

    def test_grant_entries_are_trimmed(self):
        m = parse_manifest_dict(base_manifest(permissions={"grant": [" fs.workspace ", "model.connect"]}))
        assert m.grants == frozenset({"fs.workspace", "model.connect"})


class TestParseFromDisk:
    def test_missing_file_reports_path(self, tmp_path):
        with pytest.raises(ContractError) as exc:
            parse_manifest(tmp_path / "nope" / "plugin.toml")
        assert "không tìm thấy" in str(exc.value)

    def test_toml_syntax_error_is_contract_error(self, tmp_path):
        p = tmp_path / "plugin.toml"
        p.write_text("this is [not toml", encoding="utf-8")
        with pytest.raises(ContractError) as exc:
            parse_manifest(p)
        assert "TOML" in str(exc.value)

    def test_valid_file_on_disk_parses(self, tmp_path):
        p = tmp_path / "plugin.toml"
        p.write_text(
            "\n".join(
                [
                    "[plugin]",
                    'id = "tool.fs-read"',
                    'version = "1.2.0"',
                    "api = 1",
                    'kind = "tool"',
                    'organ = "both"',
                    "",
                    "[entry]",
                    'logic = "logic/main.py"',
                    "",
                    "[permissions]",
                    'grant = ["fs.workspace"]',
                ]
            ),
            encoding="utf-8",
        )
        m = parse_manifest(p)
        assert m.organ == "both"
        assert m.grants == frozenset({"fs.workspace"})
