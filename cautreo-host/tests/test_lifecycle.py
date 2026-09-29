"""Bộ 2/5 — Lifecycle test (spec §7.3.2).

Chốt: nạp/tháo/hot-swap 100 lần không rò handle ctypes, không sót surface,
lệnh đang bay nhận `plugin_reloading` chứ **không sập host**.

Sổ handle dùng chung sống ở `sys.modules["_cautreo_handle_ledger"]` để cả test lẫn
logic face của plugin đọc **cùng một** danh sách, kể cả khi hot-swap dựng lại module.
"""

from __future__ import annotations

import sys
import threading
import time
import types
from pathlib import Path

import pytest

from cautreo_host.registry import (
    PluginRegistry,
    PluginReloading,
    PluginState,
    RegistryError,
)

# ---------------------------------------------------------------- sổ handle chung


@pytest.fixture(autouse=True)
def ledger():
    """Một sổ handle sống qua các lần nạp module. Dọn sạch sau mỗi test."""
    mod = types.ModuleType("_cautreo_handle_ledger")
    mod.open = []  # type: ignore[attr-defined]
    mod.deactivate_calls = 0  # type: ignore[attr-defined]
    mod.release_gate = None  # type: ignore[attr-defined]
    sys.modules["_cautreo_handle_ledger"] = mod
    yield mod
    sys.modules.pop("_cautreo_handle_ledger", None)


# ---------------------------------------------------------------- mặt logic mẫu


GOOD_LOGIC = '''
import ctypes
import sys

LEDGER = sys.modules["_cautreo_handle_ledger"]


def create_plugin():
    return Plugin()


class Plugin:
    """Một tool giữ handle ctypes, và nhả nó trong deactivate()."""

    def activate(self, api=None):
        pass

    def deactivate(self):
        LEDGER.deactivate_calls += 1
        while LEDGER.open:
            LEDGER.open.pop()

    def run(self, ctx=None, **params):
        # Mở một handle ctypes thật — thứ sẽ rò nếu deactivate() quên nhả.
        handle = ctypes.create_string_buffer(32)
        LEDGER.open.append(handle)
        return {"echo": params.get("echo"), "handles": len(LEDGER.open)}
'''

LEAKY_LOGIC = '''
import ctypes
import sys

LEDGER = sys.modules["_cautreo_handle_ledger"]


def create_plugin():
    return Plugin()


class Plugin:
    """Cố tình KHÔNG nhả handle — để chứng minh bộ test nhìn thấy được chỗ rò."""

    def deactivate(self):
        LEDGER.deactivate_calls += 1
        # quên nhả — đúng lỗi mà §4.4 cấm

    def run(self, ctx=None, **params):
        handle = ctypes.create_string_buffer(32)
        LEDGER.open.append(handle)
        return {"handles": len(LEDGER.open)}
'''

BLOCKING_LOGIC = '''
import ctypes
import sys

LEDGER = sys.modules["_cautreo_handle_ledger"]


def create_plugin():
    return Plugin()


class Plugin:
    """deactivate() chặn lại, dựng kịch bản "đang tháo thì có lời gọi tới"."""

    def deactivate(self):
        LEDGER.deactivate_calls += 1
        gate = LEDGER.release_gate
        if gate is not None:
            gate.wait(timeout=5)
        while LEDGER.open:
            LEDGER.open.pop()

    def run(self, ctx=None, **params):
        handle = ctypes.create_string_buffer(32)
        LEDGER.open.append(handle)
        return {"ok": True}
'''


def write_plugin(
    root: Path,
    *,
    pid: str = "tool.probe",
    kind: str = "tool",
    organ: str | None = "hand",
    grants: tuple[str, ...] = (),
    logic: str = GOOD_LOGIC,
    version: str = "1.0.0",
) -> Path:
    """Ghi một plugin hoàn chỉnh ra đĩa. Trả về thư mục plugin."""
    d = root / pid.replace(".", "_")
    (d / "logic").mkdir(parents=True, exist_ok=True)
    organ_line = f'organ = "{organ}"\n' if organ else ""
    grant_items = ", ".join(f'"{g}"' for g in grants)
    (d / "plugin.toml").write_text(
        f"""[plugin]
id = "{pid}"
version = "{version}"
api = 1
kind = "{kind}"
{organ_line}
[entry]
logic = "logic/main.py"

[permissions]
grant = [{grant_items}]
""",
        encoding="utf-8",
    )
    (d / "logic" / "main.py").write_text(logic, encoding="utf-8")
    return d


def boot(root: Path, *, pid: str = "tool.probe") -> PluginRegistry:
    """discover → validate → load → activate, trả registry đã sẵn sàng."""
    reg = PluginRegistry()
    reg.discover(root)
    reg.validate(pid)
    reg.load(pid)
    reg.activate(pid)
    return reg


# ---------------------------------------------------------------- test


class TestLifecycleHappyPath:
    def test_full_lifecycle_state_machine(self, tmp_path, ledger):
        write_plugin(tmp_path)
        reg = PluginRegistry()
        rec = reg.discover(tmp_path)[0]
        assert rec.state is PluginState.DISCOVERED
        reg.validate(rec.id)
        assert rec.state is PluginState.VALIDATED
        reg.load(rec.id)
        assert rec.state is PluginState.LOADED
        reg.activate(rec.id)
        assert rec.state is PluginState.ACTIVATED
        reg.deactivate(rec.id)
        assert rec.state is PluginState.DEACTIVATED
        reg.unload(rec.id)
        assert rec.state is PluginState.UNLOADED

    def test_invoke_runs_and_opens_handle(self, tmp_path, ledger):
        write_plugin(tmp_path)
        reg = boot(tmp_path)
        out = reg.invoke("tool.probe", {"echo": "xin chao"})
        assert out["echo"] == "xin chao"
        assert len(ledger.open) == 1

    def test_illegal_transition_rejected(self, tmp_path):
        write_plugin(tmp_path)
        reg = PluginRegistry()
        rec = reg.discover(tmp_path)[0]
        with pytest.raises(RegistryError, match="trạng thái"):
            reg.activate(rec.id)  # chưa load

    def test_unload_from_discovered_is_allowed(self, tmp_path):
        write_plugin(tmp_path)
        reg = PluginRegistry()
        rec = reg.discover(tmp_path)[0]
        reg.unload(rec.id)
        assert rec.state is PluginState.UNLOADED

    def test_contract_violation_never_validates(self, tmp_path):
        """tool thiếu organ → không qua cửa validate, không bao giờ activated."""
        d = write_plugin(tmp_path, pid="tool.no-organ", organ=None)
        (d / "plugin.toml").write_text(
            "[plugin]\n"
            'id = "tool.no-organ"\n'
            'version = "1.0.0"\n'
            "api = 1\n"
            'kind = "tool"\n'
            "\n"
            "[entry]\n"
            'logic = "logic/main.py"\n',
            encoding="utf-8",
        )
        reg = PluginRegistry()
        rec = reg.discover(tmp_path)[0]
        assert rec.error is not None
        with pytest.raises(RegistryError, match="vi phạm contract"):
            reg.validate(rec.id)
        assert rec.state is PluginState.DISCOVERED


class TestHandleLeak:
    def test_100_hot_swaps_release_every_handle(self, tmp_path, ledger):
        """Điểm chốt của §4.4: 100 vòng hot-swap, bộ đếm handle về 0."""
        d = write_plugin(tmp_path / "a")
        reg = boot(tmp_path / "a")
        for _ in range(100):
            reg.hot_swap("tool.probe", d)
        assert len(ledger.open) == 0
        assert ledger.deactivate_calls >= 100
        reg.assert_settled("tool.probe")

    def test_100_full_load_unload_cycles(self, tmp_path, ledger):
        write_plugin(tmp_path / "a")
        for _ in range(100):
            reg = PluginRegistry()
            reg.discover(tmp_path / "a")
            reg.validate("tool.probe")
            reg.load("tool.probe")
            reg.activate("tool.probe")
            reg.deactivate("tool.probe")
            reg.unload("tool.probe")
        assert len(ledger.open) == 0

    def test_deactivate_called_on_defensive_unload(self, tmp_path, ledger):
        """unload() khi còn activated phải tự nhả — không có đường quên."""
        write_plugin(tmp_path)
        reg = boot(tmp_path)
        reg.unload("tool.probe")  # bỏ qua deactivate() tường minh
        assert ledger.deactivate_calls == 1
        assert len(ledger.open) == 0

    def test_leak_is_visible_when_deactivate_skips_release(self, tmp_path, ledger):
        """Bộ test có răng: plugin không nhả handle thì sổ KHÔNG về 0.

        Nếu test trước (vòng tốt) là xanh mà test này cũng khẳng định được chỗ
        rò, thì vòng tốt không phải đang chấm cho có.
        """
        write_plugin(tmp_path / "a", pid="tool.leaky", logic=LEAKY_LOGIC)
        reg = boot(tmp_path / "a", pid="tool.leaky")
        reg.invoke("tool.leaky", {})  # mở 1 handle
        assert len(ledger.open) == 1
        reg.deactivate("tool.leaky")  # deactivate() quên nhả
        reg.unload("tool.leaky")
        assert len(ledger.open) == 1, "phải nhìn thấy chỗ rò — nếu không test này vô nghĩa"


class TestHotSwap:
    def test_hot_swap_keeps_plugin_alive(self, tmp_path, ledger):
        d = write_plugin(tmp_path / "a")
        reg = boot(tmp_path / "a")
        for _ in range(20):
            rec = reg.hot_swap("tool.probe", d)
            assert rec.state is PluginState.ACTIVATED
            assert reg.invoke("tool.probe", {"echo": "v"})["echo"] == "v"

    def test_hot_swap_mismatched_id_rejected(self, tmp_path):
        write_plugin(tmp_path / "a", pid="tool.probe")
        other = write_plugin(tmp_path / "b", pid="tool.other")
        reg = boot(tmp_path / "a")
        with pytest.raises(RegistryError, match="giữ nguyên id"):
            reg.hot_swap("tool.probe", other)

    def test_hot_swap_frees_module_names(self, tmp_path, ledger):
        d = write_plugin(tmp_path / "a")
        reg = boot(tmp_path / "a")
        before = [n for n in sys.modules if n.startswith("_cautreo_plugin_")]
        for _ in range(10):
            reg.hot_swap("tool.probe", d)
        after = [n for n in sys.modules if n.startswith("_cautreo_plugin_")]
        # Module cũ bị gỡ khi unload — không phình sys.modules theo số vòng.
        assert len(after) <= len(before) + 1


class TestInFlightGetsReloading:
    def test_call_during_hot_swap_is_rejected_not_fatal(self, tmp_path, ledger):
        """Lệnh đang bay khi hot-swap nhận `plugin_reloading`, host không sập."""
        d = write_plugin(tmp_path, logic=BLOCKING_LOGIC)
        reg = boot(tmp_path)
        gate = threading.Event()
        ledger.release_gate = gate  # type: ignore[attr-defined]

        errors: list[BaseException] = []

        def swap() -> None:
            try:
                reg.hot_swap("tool.probe", d)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        t = threading.Thread(target=swap, name="hot-swap")
        t.start()
        # Chờ tới khi hot-swap thật sự đi vào đoạn tháo.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not reg.record("tool.probe").reloading:
            time.sleep(0.005)
        assert reg.record("tool.probe").reloading is True

        # Lệnh gửi tới trong lúc đang tháo → PluginReloading, không nổ host.
        with pytest.raises(PluginReloading):
            reg.invoke("tool.probe", {"echo": "dang bay"})

        gate.set()
        t.join(timeout=5)
        assert not t.is_alive()
        assert errors == []
        assert reg.record("tool.probe").state is PluginState.ACTIVATED
        # Sau khi tháo xong thì gọi lại bình thường.
        assert reg.invoke("tool.probe", {}) == {"ok": True}

    def test_host_survives_a_hundred_swaps_with_a_call_each(self, tmp_path, ledger):
        d = write_plugin(tmp_path / "a")
        reg = boot(tmp_path / "a")
        for _ in range(100):
            reg.hot_swap("tool.probe", d)
            reg.invoke("tool.probe", {"echo": "sống"})
        assert reg.record("tool.probe").state is PluginState.ACTIVATED
        # Mỗi hot-swap nhả handle của vòng trước → chỉ còn 1 của lần gọi cuối.
        assert len(ledger.open) == 1
        assert ledger.deactivate_calls == 100
        reg.deactivate("tool.probe")
        assert len(ledger.open) == 0
