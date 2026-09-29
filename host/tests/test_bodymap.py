"""Bản đồ thân thể — tự dựng, tự cập nhật, và nạp vào model.

Ba điều bộ này chốt:

1. **Bản đồ là bằng chứng, không phải văn mẫu.** Mọi id / method / grant trong
   bản đồ đều phải mọc lên từ registry. Cơ quan nào trống thì nói thẳng
   "chưa có", không bịa ra một tool nào cho đủ hình.
2. **Tự dựng lại khi có thay đổi.** Thêm plugin, gỡ plugin, hot-swap — bản đồ
   phải theo, **không ai phải nhớ gọi tay**.
3. **ViVy nhận ra chính mình.** System prompt nạp cho model đúng là bản đồ đó;
   nhờ vậy hỏi "bạn là ai" không còn ra "I am not Vivy".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from test_model_backend import StubModelServer

from cautreo_host.backends import ModelBackend
from cautreo_host.bodymap import (
    BODY_NAME,
    ORGAN_ORDER,
    SKILL_PREFIX,
    SOUL_NAME,
    body_prompt_for,
    build_body_map,
    render_body_prompt,
)
from cautreo_host.host import Host
from cautreo_host.registry import PluginRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]
CAUTREO_HOST_DIR = REPO_ROOT / "cautreo-host"
UI_DIR = REPO_ROOT / "cautreo-desktop-ui"
PLUGINS_DIR = CAUTREO_HOST_DIR / "plugins"


def _host(endpoint: str | None = "http://127.0.0.1:8080", *, offline: bool = False) -> Host:
    return Host(
        ui_dir=UI_DIR,
        plugins_dir=PLUGINS_DIR,
        workspace=REPO_ROOT,
        port=0,
        model_endpoint=endpoint,
        offline=offline,
    )


def _loaded_host(endpoint: str | None = "http://127.0.0.1:8080") -> Host:
    host = _host(endpoint)
    host.load_plugins()
    host.open_link()
    return host


def _ids(body_map: dict[str, Any]) -> set[str]:
    return {
        part["id"]
        for parts in body_map["organs"].values()
        for part in parts
    }


def _methods(body_map: dict[str, Any]) -> set[str]:
    names = {
        m["name"]
        for parts in body_map["organs"].values()
        for part in parts
        for m in part["methods"]
    }
    names |= {m["name"] for m in body_map["host_methods"]}
    return names


# ---------------------------------------------------------------- bằng chứng


class TestBodyMapIsEvidenceNotProse:
    """Bản đồ chỉ nói những gì registry nói. Không có dòng mô tả tự viết nào."""

    def test_map_is_built_from_the_real_registry(self):
        host = _loaded_host()
        body_map = host.bus.body_map
        assert _ids(body_map) == {"tool.fs-read", "tool.fs-write", "vivy.runtime"}

    def test_each_plugin_lands_under_the_organ_its_manifest_declares(self):
        body_map = _loaded_host().bus.body_map
        assert {p["id"] for p in body_map["organs"]["eye"]} == {"tool.fs-read"}
        assert {p["id"] for p in body_map["organs"]["hand"]} == {"tool.fs-write"}
        assert {p["id"] for p in body_map["organs"]["both"]} == {"vivy.runtime"}

    def test_every_registered_method_appears_in_the_map(self):
        host = _loaded_host()
        body_map = host.bus.body_map
        # Registry là nguồn sự thật — bản đồ phải chứa đúng chừng đó method.
        assert _methods(body_map) == set(host.registry.method_names()) | {
            "host.body-map",
            "host.knowledge-graph",
            "host.link-probe",
        }

    def test_grants_come_from_the_manifest_not_from_imagination(self):
        body_map = _loaded_host().bus.body_map
        by_id = {
            p["id"]: p
            for parts in body_map["organs"].values()
            for p in parts
        }
        assert by_id["tool.fs-read"]["grants"] == ["fs.workspace"]
        assert by_id["tool.fs-write"]["grants"] == ["fs.workspace"]
        assert set(by_id["vivy.runtime"]["grants"]) == {
            "model.connect",
            "cautreo.access",
        }

    def test_empty_registry_yields_an_empty_map_with_no_phantom_tool(self):
        body_map = build_body_map(())
        assert _ids(body_map) == set()
        assert body_map["counts"]["plugins"] == 0
        assert body_map["counts"]["methods"] == 0
        for organ in ORGAN_ORDER:
            assert body_map["organs"][organ] == []

    def test_a_broken_plugin_is_shown_with_its_error_not_hidden(self, tmp_path):
        """Plugin hỏng phải hiện ra cùng lý do — nhưng **không** bày như cơ quan."""
        bad = tmp_path / "tool.thieu-organ"
        bad.mkdir()
        (bad / "plugin.toml").write_text(
            '[plugin]\n'
            'id = "tool.thieu-organ"\n'
            'version = "1.0.0"\n'
            'api = 1\n'
            'kind = "tool"\n'
            '\n[entry]\nlogic = "logic/main.py"\n',
            encoding="utf-8",
        )
        reg = PluginRegistry()
        reg.discover(tmp_path)
        body_map = build_body_map(reg.all())
        # Manifest hỏng bị host thay bằng placeholder `invalid.*` — bản đồ giữ
        # đúng cái đó, không tự đặt lại tên cho giống manifest gốc.
        assert len(body_map["broken"]) == 1
        entry = body_map["broken"][0]
        assert entry["id"] == "invalid.tool.thieu-organ"
        assert entry["error"]
        assert entry["state"] == "discovered"
        # Nó KHÔNG nằm trong cơ quan nào — không có cơ quan nào mang tên này.
        assert _ids(body_map) == set()

    def test_a_load_failure_is_also_reported_not_swallowed(self, tmp_path):
        """Plugin manifest đúng nhưng code hỏng — vẫn phải hiện ra cùng lý do."""
        p = tmp_path / "tool.code-hong"
        (p / "logic").mkdir(parents=True)
        (p / "plugin.toml").write_text(
            '[plugin]\n'
            'id = "tool.code-hong"\n'
            'version = "1.0.0"\n'
            'api = 1\n'
            'kind = "tool"\n'
            'organ = "eye"\n'
            '\n[entry]\nlogic = "logic/main.py"\n',
            encoding="utf-8",
        )
        (p / "logic" / "main.py").write_text("raise RuntimeError('nổ')\n", encoding="utf-8")
        reg = PluginRegistry()
        reg.discover(tmp_path)
        rec = reg.record("tool.code-hong")
        assert rec is not None
        reg.validate("tool.code-hong")
        try:
            reg.load("tool.code-hong")
        except Exception:  # noqa: BLE001 — đúng là nó phải nổ
            pass
        body_map = build_body_map(reg.all())
        assert _ids(body_map) == set()
        assert body_map["broken"] and body_map["broken"][0]["id"] == "tool.code-hong"
        assert body_map["broken"][0]["error"]

    def test_skills_are_counted_by_namespace_and_none_exist_yet(self):
        """Contract `api=1` không có `kind = "skill"` — skill là cơ quan.

        Ta đếm theo namespace `skill.`. Hiện chưa có → bản đồ nói thẳng "chưa có",
        không bịa một con số nào cho đẹp.
        """
        body_map = _loaded_host().bus.body_map
        assert body_map["counts"]["skills"] == 0
        assert not any(i.startswith(SKILL_PREFIX) for i in _ids(body_map))

    def test_version_comes_from_the_manifest(self):
        body_map = _loaded_host().bus.body_map
        for parts in body_map["organs"].values():
            for part in parts:
                assert part["version"], f"{part['id']} thiếu version"
                assert part["kind"] in {"workspace", "panel", "tool", "runtime"}


# ---------------------------------------------------------------- tự dựng lại


class TestBodyMapRebuildsItself:
    """Thêm / bớt thành phần thì bản đồ theo — không ai gọi tay."""

    def test_load_plugins_alone_is_enough_to_build_the_map(self):
        host = _host()
        # Chưa làm gì ngoài load_plugins — không gọi sync_registry bằng tay.
        host.load_plugins()
        assert "tool.fs-read" in _ids(host.bus.body_map)

    def test_registry_on_change_is_wired_to_the_bus(self):
        host = _host()
        # Method bound của cùng instance thì `==`, không phải `is`.
        assert host.registry.on_change == host.bus.sync_registry

    def test_deactivate_hides_the_methods_because_the_bus_would_refuse_them(self):
        """Bản đồ **không** hứa điều bus sẽ từ chối.

        `_run_plugin` chặn khi plugin không `activated` (trả `plugin_unavailable`).
        Nói với model "có method này" lúc đó là bịa năng lực.
        """
        host = _loaded_host()
        assert "vivy.runtime/ask" in _methods(host.bus.body_map)
        host.registry.deactivate("vivy.runtime")
        by_id = {
            p["id"]: p
            for parts in host.bus.body_map["organs"].values()
            for p in parts
        }
        assert by_id["vivy.runtime"]["state"] == "deactivated"
        assert by_id["vivy.runtime"]["methods"] == []
        assert "vivy.runtime/ask" not in _methods(host.bus.body_map)

    def test_an_unloaded_plugin_stays_listed_with_its_true_state(self):
        """Tháo plugin ≠ xoá nó khỏi tồn kho. Bản đồ nói đúng trạng thái."""
        host = _loaded_host()
        host.registry.deactivate("tool.fs-read")
        host.registry.unload("tool.fs-read")
        by_id = {
            p["id"]: p
            for parts in host.bus.body_map["organs"].values()
            for p in parts
        }
        assert by_id["tool.fs-read"]["state"] == "unloaded"
        assert by_id["tool.fs-read"]["methods"] == []

    def test_the_map_never_lists_a_method_the_bus_would_refuse(self):
        """Bất biến chốt: method có trong bản đồ ⇒ gọi qua bus **thật sự** được."""
        host = _loaded_host()
        host.registry.deactivate("tool.fs-write")
        body_map = host.bus.body_map
        live = _methods(body_map)
        for name in sorted(live):
            if name in ("host.body-map", "host.knowledge-graph"):
                continue  # method host, dispatch nhánh khác
            msg = host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": f"chk-{name}", "method": name, "params": {},
            }))
            assert msg is not None
            assert "error" not in msg or msg["error"]["code"] not in (
                -32004,  # plugin_unavailable — nghĩa là bản đồ nói dối
            ), f"bản đồ liệt kê {name} nhưng bus từ chối: {msg}"

    def test_hot_swap_rebuilds_once_not_four_times(self):
        """Hot-swap đi qua 4 bước chuyển trạng thái — bản đồ chỉ dựng **một lần**.

        Dựng từng bước sẽ bắn 4 thông báo `registry.changed` vô nghĩa ra UI.
        """
        host = _loaded_host()
        seen: list[int] = []
        original = host.bus.sync_registry

        def counting() -> tuple[str, ...]:
            seen.append(1)
            return original()

        host.registry.on_change = counting
        host.registry.hot_swap("tool.fs-read")
        assert len(seen) == 1
        assert "tool.fs-read" in _ids(host.bus.body_map)

    def test_hot_swap_sees_the_new_code(self):
        """Bản đồ sau hot-swap phải là của bản nạp mới, không phải bản cũ."""
        host = _loaded_host()
        before = host.bus.body_map
        host.registry.hot_swap("tool.fs-read")
        after = host.bus.body_map
        # Cùng id, nhưng hai bản dựng khác nhau — bản đồ đã dựng lại.
        assert after is not before
        assert {p["id"] for p in after["organs"]["eye"]} == {"tool.fs-read"}


# ---------------------------------------------------------------- system prompt


class TestPromptIsTheMapNotAStory:
    """System prompt là **kết quả của bản đồ**, không phải văn mẫu viết tay."""

    def test_prompt_declares_the_identity_the_project_chose(self):
        prompt = body_prompt_for(())
        assert SOUL_NAME in prompt
        assert BODY_NAME in prompt
        assert f"Bạn là {SOUL_NAME}" in prompt

    def test_every_plugin_id_reaches_the_model(self):
        host = _loaded_host()
        prompt = host.bus.body_prompt
        for pid in _ids(host.bus.body_map):
            assert pid in prompt, f"{pid} không tới được model"

    def test_every_method_reaches_the_model(self):
        host = _loaded_host()
        prompt = host.bus.body_prompt
        for name in _methods(host.bus.body_map):
            assert name in prompt, f"method {name} không tới được model"

    def test_empty_body_says_so_instead_of_inventing_tools(self):
        prompt = render_body_prompt(build_body_map(()))
        assert "chưa có" in prompt
        # Không một tên tool nào của máy này lọt vào khi registry trống.
        for pid in ("tool.fs-read", "tool.fs-write", "vivy.runtime"):
            assert pid not in prompt

    def test_prompt_is_rendered_from_the_map_so_the_two_cannot_drift(self):
        """`body_prompt` phải bằng `render_body_prompt(body_map)` — cùng một nguồn."""
        host = _loaded_host()
        assert host.bus.body_prompt == render_body_prompt(host.bus.body_map)

    def test_prompt_tells_the_model_not_to_invent_capabilities(self):
        prompt = _loaded_host().bus.body_prompt
        assert "Không bịa" in prompt

    def test_prompt_reports_the_skill_vacuum_honestly(self):
        prompt = _loaded_host().bus.body_prompt
        assert "chưa có" in prompt
        assert f"skill (namespace `{SKILL_PREFIX}`)" in prompt or SKILL_PREFIX in prompt


# ---------------------------------------------------------------- nạp vào model


class TestModelReceivesTheBodyMap:
    """Đây là chỗ sửa lỗi "ViVy không nhận diện được bản thân"."""

    def test_system_prompt_travels_ahead_of_the_users_words(self):
        with StubModelServer() as stub:
            backend = ModelBackend(stub.endpoint, system="Bạn là ViVy.")
            backend.complete("bạn là ai")
        sent = stub.calls[-1]["payload"]["messages"]
        assert sent[0] == {"role": "system", "content": "Bạn là ViVy."}
        assert sent[1] == {"role": "user", "content": "bạn là ai"}

    def test_without_a_system_prompt_the_request_is_unchanged(self):
        """Không có bản đồ thì lời gọi đi y hệt như trước — không chèn gì thừa."""
        with StubModelServer() as stub:
            ModelBackend(stub.endpoint).complete("chào")
        sent = stub.calls[-1]["payload"]["messages"]
        assert sent == [{"role": "user", "content": "chào"}]

    def test_blank_system_is_dropped_not_sent_as_whitespace(self):
        with StubModelServer() as stub:
            backend = ModelBackend(stub.endpoint)
            backend.set_system("   ")
            backend.complete("chào")
        sent = stub.calls[-1]["payload"]["messages"]
        assert sent == [{"role": "user", "content": "chào"}]

    def test_ask_reaches_the_model_with_the_body_map_attached(self):
        """Hỏi thật qua `vivy.runtime/ask` — model phải thấy bản đồ cơ thể."""
        with StubModelServer(reply="Tôi là ViVy.") as stub:
            host = _loaded_host(stub.endpoint)
            msg = host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": "b-1", "method": "vivy.runtime/ask",
                "params": {"prompt": "bạn là ai"},
            }))
        assert msg is not None and "error" not in msg
        sent = stub.calls[-1]["payload"]["messages"]
        assert sent[0]["role"] == "system"
        system = sent[0]["content"]
        assert SOUL_NAME in system
        assert BODY_NAME in system
        # Năng lực trong prompt đúng là năng lực thật — không bịa.
        assert "tool.fs-read" in system
        assert "vivy.runtime/ask" in system
        assert sent[1] == {"role": "user", "content": "bạn là ai"}

    def test_the_system_prompt_is_the_live_map_not_a_frozen_string(self):
        """Đổi registry thì system prompt model thấy cũng đổi theo."""
        with StubModelServer() as stub:
            host = _loaded_host(stub.endpoint)
            host.registry.deactivate("tool.fs-write")
            host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": "b-2", "method": "vivy.runtime/ask",
                "params": {"prompt": "chào"},
            }))
        system = stub.calls[-1]["payload"]["messages"][0]["content"]
        by_state = host.bus.body_map["organs"]["hand"]
        assert by_state and by_state[0]["state"] == "deactivated"
        assert "deactivated" in system


# ---------------------------------------------------------------- hỏi bản đồ


class TestBodyMapIsQueryableWithoutAModel:
    """D9: lệnh không cần model vẫn chạy — kể cả khi DEGRADED."""

    def _call(self, host: Host, req_id: str = "b-9") -> dict[str, Any]:
        msg = host.bus.handle(json.dumps({
            "jsonrpc": "2.0", "id": req_id, "method": "host.body-map", "params": {},
        }))
        assert msg is not None
        return msg

    def test_body_map_returns_the_same_structure_the_model_sees(self):
        host = _loaded_host()
        msg = self._call(host)
        assert "error" not in msg
        assert msg["result"]["map"] == host.bus.body_map

    def test_body_map_works_when_the_model_is_down(self):
        host = Host(
            ui_dir=UI_DIR, plugins_dir=PLUGINS_DIR, workspace=REPO_ROOT,
            port=0, model_endpoint="http://127.0.0.1:9",
        )
        host.load_plugins()
        host.open_link()
        assert host.link.reason == "endpoint_unreachable"
        msg = self._call(host)
        assert "error" not in msg
        assert _ids(msg["result"]["map"]) == {"tool.fs-read", "tool.fs-write", "vivy.runtime"}

    def test_reading_the_map_is_not_model_work(self):
        """Xem bản đồ là việc cục bộ — nhãn là `tool-local`, không phải `model`."""
        host = _loaded_host()
        msg = self._call(host)
        assert msg["receipt"]["source"] == "tool-local"
        assert msg["receipt"]["organ"] == "host"

    def test_a_degraded_ask_still_refuses_rather_than_talking_from_the_map(self):
        """Có bản đồ **không** biến thành đường bịa trả lời khi mất model."""
        host = Host(
            ui_dir=UI_DIR, plugins_dir=PLUGINS_DIR, workspace=REPO_ROOT,
            port=0, model_endpoint="http://127.0.0.1:9",
        )
        host.load_plugins()
        host.open_link()
        msg = host.bus.handle(json.dumps({
            "jsonrpc": "2.0", "id": "b-10", "method": "vivy.runtime/ask",
            "params": {"prompt": "bạn là ai"},
        }))
        assert set(msg) == {"jsonrpc", "id", "error"}
        assert "result" not in msg
        assert msg["error"]["code"] == -32005
