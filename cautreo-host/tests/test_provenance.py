"""Bộ 3/5 — Label provenance test (spec §7.3.4).

Chốt: mọi kết quả qua bus đều mang nhãn nguồn, và **plugin không tự gắn nhãn được**.
Điểm chốt: một plugin trả `{"source": "model"}` mà không hề chạm `ctx.model` thì
nhãn vẫn là `tool-local`. Bus không đọc lời khai của plugin để gán nhãn.
"""

from __future__ import annotations

import pytest

from cautreo_host.provenance import (
    ALL_SOURCES,
    SOURCE_CAUTREO,
    SOURCE_DERIVED,
    SOURCE_MODEL,
    SOURCE_TOOL_LOCAL,
    CallContext,
    Capability,
    PermissionDenied,
    source_for,
    strip_self_label,
)


class _FakeModel:
    """Backend model giả cho test. Host thật không có sẵn — plugin runtime tự cắm."""

    def complete(self, text: str = "") -> dict[str, str]:
        return {"echo": text}


class _FakeCautreo:
    def recall(self, key: str = "") -> dict[str, str]:
        return {"key": key}


def ctx(**grants: bool) -> CallContext:
    g: set[str] = set()
    if grants.get("model"):
        g.add("model.connect")
    if grants.get("cautreo"):
        g.add("cautreo.access")
    if grants.get("fs"):
        g.add("fs.workspace")
    if grants.get("local"):
        g.add("tool.local")
    return CallContext(
        grants=frozenset(g),
        _backends={"model": _FakeModel(), "cautreo": _FakeCautreo()},
    )


class TestSelfLabelIsImpossible:
    """Quy tắc §7.1: plugin không tự gắn nhãn được — không có đường nào."""

    def test_plugin_claiming_model_without_touching_gets_tool_local(self):
        c = ctx()
        # Plugin trả kết quả kèm lời tự nhận là model. Bus không đọc lời đó.
        plugin_payload = {"text": "câu trả lời", "source": "model"}
        label = source_for(c)
        assert label == SOURCE_TOOL_LOCAL
        assert plugin_payload["source"] != label  # lời khai ≠ nhãn thật

    def test_self_label_is_stripped_from_payload(self):
        out = strip_self_label({"text": "x", "source": "model", "provenance_label": "cautreo"})
        assert "source" not in out
        assert "provenance_label" not in out
        assert out["text"] == "x"

    def test_self_label_stripped_at_any_depth(self):
        out = strip_self_label({"steps": [{"source": "model"}, {"source": "derived"}], "source": "model"})
        assert "source" not in out
        assert all("source" not in s for s in out["steps"])

    @pytest.mark.parametrize("bogus", ["model", "cautreo", "tool-local", "derived"])
    def test_label_comes_only_from_ledger(self, bogus):
        c = ctx()
        # Ghi sổ rỗng → luôn tool-local, bất kể plugin muốn gì.
        assert source_for(c) == SOURCE_TOOL_LOCAL
        assert bogus in ALL_SOURCES  # bảng nhãn là cố định


class TestLedgerDrivesLabel:
    def test_touching_model_handle_labels_model(self):
        c = ctx(model=True)
        c.model.complete("hello")
        assert Capability.MODEL in c.used
        assert source_for(c) == SOURCE_MODEL

    def test_touching_cautreo_handle_labels_cautreo(self):
        c = ctx(cautreo=True)
        c.cautreo.recall("gate9")
        assert source_for(c) == SOURCE_CAUTREO

    def test_fs_alone_is_tool_local(self):
        c = ctx(fs=True)
        c.fs.read("preflight.py")
        assert source_for(c) == SOURCE_TOOL_LOCAL

    def test_model_wins_over_fs(self):
        """Chạm model + đọc file → vẫn là model, vì đó là chỗ kết quả sinh ra."""
        c = ctx(model=True, fs=True)
        c.fs.read("a.py")
        c.model.complete("tổng hợp")
        assert source_for(c) == SOURCE_MODEL

    def test_derive_from_beats_everything(self):
        c = ctx(model=True)
        c.model.complete("x")
        c.derive_from("rc-0001")
        assert source_for(c) == SOURCE_DERIVED
        assert c.derived_from == ("rc-0001",)

    def test_derive_from_dedupes_and_keeps_order(self):
        c = ctx()
        c.derive_from("rc-2", "rc-1", "rc-2")
        assert c.derived_from == ("rc-2", "rc-1")

    def test_local_handle_is_tool_local(self):
        c = ctx(local=True)
        c.local.exec("ls")
        assert source_for(c) == SOURCE_TOOL_LOCAL


class TestPermissionGateAtHandle:
    """Chặn quyền ở biên handle, không chỉ ở biên method."""

    def test_model_handle_requires_grant(self):
        c = ctx()
        with pytest.raises(PermissionDenied) as exc:
            _ = c.model
        assert "model.connect" in str(exc.value)

    def test_cautreo_handle_requires_grant(self):
        with pytest.raises(PermissionDenied):
            _ = ctx().cautreo

    def test_fs_handle_requires_grant(self):
        with pytest.raises(PermissionDenied):
            _ = ctx().fs

    def test_granted_handle_opens(self):
        c = ctx(model=True)
        handle = c.model
        assert handle.cap is Capability.MODEL

    def test_denied_open_leaves_ledger_clean(self):
        """Bị chặn thì không được ghi sổ — không có nhãn cho việc chưa xảy ra."""
        c = ctx()
        with pytest.raises(PermissionDenied):
            _ = c.model
        assert c.used == frozenset()
        assert source_for(c) == SOURCE_TOOL_LOCAL


class TestHandleTouchIsRecorded:
    def test_touch_recorded_on_call_not_on_open(self):
        c = ctx(model=True)
        _ = c.model  # mở handle, chưa dùng
        assert c.used == frozenset()
        c.model.complete("hi")  # dùng → mới ghi sổ
        assert c.used == frozenset({Capability.MODEL})

    def test_multiple_calls_touch_once(self):
        c = ctx(model=True)
        c.model.complete("a")
        c.model.complete("b")
        assert c.used == frozenset({Capability.MODEL})
        assert source_for(c) == SOURCE_MODEL


class TestSourceTable:
    def test_exactly_four_labels(self):
        assert set(ALL_SOURCES) == {"model", "cautreo", "tool-local", "derived"}

    def test_default_context_is_honest_tool_local(self):
        """Không chạm gì, không suy ra gì → tool-local. Không bịa model."""
        assert source_for(ctx()) == SOURCE_TOOL_LOCAL


class TestMissingBackendNeverFabricates:
    """Host không có sẵn model/Cautreo. Thiếu backend là lỗi thật, không phải kết quả giả."""

    def test_model_without_backend_raises(self):
        c = CallContext(grants=frozenset({"model.connect"}))
        with pytest.raises(RuntimeError, match="chưa cắm backend"):
            c.model.complete("x")

    def test_cautreo_without_backend_raises(self):
        c = CallContext(grants=frozenset({"cautreo.access"}))
        with pytest.raises(RuntimeError, match="chưa cắm backend"):
            c.cautreo.recall("k")

    def test_touch_is_still_recorded_before_the_raise(self):
        """Ghi sổ trước khi gọi — nên nhãn vẫn trung thực cả khi backend hỏng."""
        c = CallContext(grants=frozenset({"model.connect"}))
        with pytest.raises(RuntimeError):
            c.model.complete("x")
        assert Capability.MODEL in c.used
