"""Bộ 4/5 — Boot & DEGRADED test (spec §7.3.3).

Chốt: mất model → đúng lý do, và **không có câu trả lời nào được bịa ra**.

- Response khi DEGRADED **không có `result`**, chỉ có `error`.
- Không có receipt nào mang nhãn `model` khi link không ONLINE — receipt là đơn vị
  tin cậy, không sinh cho việc chưa xảy ra.
- `DEGRADED` không có đường sang `OFFLINE`.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from cautreo_host.bus import (
    MODEL_UNAVAILABLE,
    PERMISSION_DENIED,
    PLUGIN_UNAVAILABLE,
    Bus,
)
from cautreo_host.provenance import SOURCE_MODEL, SOURCE_TOOL_LOCAL
from cautreo_host.receipt import ReceiptLog
from cautreo_host.registry import PluginRegistry
from cautreo_host.state import REASONS, LinkError, LinkMachine, LinkState

# ---------------------------------------------------------------- mặt logic mẫu


MODEL_LOGIC = '''
import sys

LEDGER = sys.modules.setdefault("_cautreo_boot_ledger", type(sys)("x"))


def create_plugin():
    return Plugin()


class Plugin:
    """Tool cần model. Không có model thì bus phải chặn TRƯỚC khi chạy tới đây."""

    method_grants = {"run": ["model.connect"]}

    def run(self, ctx=None, **params):
        # Chỗ này là nơi model thật sự được gọi. Nếu bus để lọt vào đây khi
        # link đang DEGRADED thì nghĩa là cổng chặn đã thủng.
        LEDGER.reached_model = getattr(LEDGER, "reached_model", 0) + 1
        out = ctx.model.complete(params.get("prompt", ""))
        return {"summary": "đã hỏi model", "text": out}
'''

LOCAL_LOGIC = '''
import sys

LEDGER = sys.modules.setdefault("_cautreo_boot_ledger", type(sys)("x"))


def create_plugin():
    return Plugin()


class Plugin:
    """Tool không cần model — vẫn phải chạy khi DEGRADED."""

    method_grants = {"run": ["tool.local"]}

    def run(self, ctx=None, **params):
        LEDGER.local_runs = getattr(LEDGER, "local_runs", 0) + 1
        # Cố tình tự gắn nhãn "model" — bus phải gỡ nó và gán nhãn theo sổ.
        return {"summary": "đã làm việc cục bộ", "echo": params.get("echo"), "source": "model"}
'''

WANTS_MODEL_WITHOUT_GRANT = '''
def create_plugin():
    return Plugin()


class Plugin:
    """Tự ý khai method_grants có model.connect, nhưng manifest KHÔNG xin grant đó."""

    method_grants = {"run": ["model.connect"]}

    def run(self, ctx=None, **params):
        return {"text": "chưa bao giờ được chạy"}
'''


def write_plugin(root: Path, *, pid: str, logic: str, grants: tuple[str, ...]) -> Path:
    d = root / pid.replace(".", "_")
    (d / "logic").mkdir(parents=True, exist_ok=True)
    grant_items = ", ".join(f'"{g}"' for g in grants)
    (d / "plugin.toml").write_text(
        f"""[plugin]
id = "{pid}"
version = "1.0.0"
api = 1
kind = "tool"
organ = "hand"

[entry]
logic = "logic/main.py"

[permissions]
grant = [{grant_items}]
""",
        encoding="utf-8",
    )
    (d / "logic" / "main.py").write_text(logic, encoding="utf-8")
    return d


@pytest.fixture(autouse=True)
def boot_ledger():
    mod = types.ModuleType("_cautreo_boot_ledger")
    sys.modules["_cautreo_boot_ledger"] = mod
    yield mod
    sys.modules.pop("_cautreo_boot_ledger", None)


class FakeModelBackend:
    """Backend model giả. Host thật không có sẵn — đây là chỗ plugin runtime cắm vào."""

    def complete(self, prompt: str = "") -> dict[str, str]:
        return {"text": f"trả lời cho: {prompt}"}


def make_bus(tmp_path: Path, link: LinkMachine) -> Bus:
    """Registry có đúng hai tool: một cần model, một không."""
    write_plugin(tmp_path, pid="tool.ask-model", logic=MODEL_LOGIC,
                 grants=("model.connect",))
    write_plugin(tmp_path, pid="tool.local-job", logic=LOCAL_LOGIC,
                 grants=("tool.local",))
    reg = PluginRegistry()
    reg.discover(tmp_path)
    for pid in ("tool.ask-model", "tool.local-job"):
        reg.validate(pid)
        reg.load(pid)
        reg.activate(pid)
    bus = Bus(
        reg,
        receipts=ReceiptLog(),
        allows_model=lambda: link.allows_model,
        model_refusal=link.refuse_model,
        backends={"model": FakeModelBackend()},
    )
    bus.sync_registry()
    return bus


def call(bus: Bus, method: str, **params):
    return bus.handle({"jsonrpc": "2.0", "id": "c-1", "method": method, "params": params})


# ---------------------------------------------------------------- máy trạng thái


class TestLinkMachine:
    def test_boot_path_is_booting_to_linking_to_online(self):
        link = LinkMachine()
        assert link.state is LinkState.BOOTING
        link.boot()
        assert link.state is LinkState.LINKING
        link.come_online()
        assert link.state is LinkState.ONLINE
        assert link.allows_model is True
        assert link.reason is None

    def test_online_to_degraded_with_exact_reason(self):
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.lost("endpoint_unreachable")
        assert link.state is LinkState.DEGRADED
        assert link.reason == "endpoint_unreachable"
        assert link.reason_text == REASONS["endpoint_unreachable"]
        assert link.allows_model is False

    @pytest.mark.parametrize("reason", sorted(REASONS))
    def test_every_declared_reason_is_usable(self, reason):
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.lost(reason)
        assert link.reason == reason

    def test_unknown_reason_rejected(self):
        link = LinkMachine()
        link.boot()
        link.come_online()
        with pytest.raises(LinkError, match="không có trong bảng"):
            link.lost("thoi tiet xau")  # không phải lý do hợp lệ

    def test_degraded_cannot_go_offline(self):
        """Điểm chốt: DEGRADED ≠ OFFLINE, và không có đường DEGRADED → OFFLINE."""
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.lost("endpoint_unreachable")
        with pytest.raises(LinkError, match="không hợp lệ"):
            link.go_offline()

    def test_offline_is_user_choice_only_from_online(self):
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.go_offline()
        assert link.state is LinkState.OFFLINE
        assert link.reason is None  # OFFLINE là chọn, không phải hỏng
        link.come_back()
        assert link.state is LinkState.ONLINE

    def test_cannot_go_offline_before_online(self):
        link = LinkMachine()
        link.boot()
        with pytest.raises(LinkError, match="không hợp lệ"):
            link.go_offline()

    def test_degraded_heals_to_online(self):
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.lost("model_mismatch")
        link.healed()
        assert link.state is LinkState.ONLINE
        assert link.reason is None

    def test_snapshot_does_not_invent_fields(self):
        link = LinkMachine(model="gemma4-e4b")
        snap = link.snapshot()
        assert snap == {
            "link": "BOOTING",
            "reason": None,
            "reason_text": None,
            "model": "gemma4-e4b",
        }

    def test_snapshot_hides_model_when_offline(self):
        """OFFLINE thì không có model nào đang chạy — không được khai tên model."""
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.go_offline()
        assert link.snapshot()["model"] is None

    def test_refuse_model_states_a_real_reason(self):
        link = LinkMachine()
        link.boot()
        link.come_online()
        link.lost("endpoint_unreachable")
        assert link.refuse_model() == REASONS["endpoint_unreachable"]
        link.healed()
        with pytest.raises(LinkError):
            link.refuse_model()  # đang ONLINE thì không có gì để từ chối


# ---------------------------------------------------------------- boot & degraded


class TestBootSequence:
    def test_boot_to_online_happy_path(self, tmp_path):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        resp = call(bus, "tool.ask-model", prompt="xin chao")
        assert "error" not in resp
        assert resp["receipt"]["source"] == SOURCE_MODEL
        assert resp["result"]["summary"] == "đã hỏi model"

    def test_linking_state_refuses_model_before_online(self, tmp_path):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()  # còn LINKING
        resp = call(bus, "tool.ask-model", prompt="sớm quá")
        assert resp["error"]["code"] == MODEL_UNAVAILABLE
        assert "result" not in resp
        assert "receipt" not in resp


class TestDegradedRefusesModel:
    """Điểm chốt: khi degraded, lệnh cần model bị từ chối kèm lý do, không bịa trả lời."""

    def test_model_command_refused_with_exact_reason(self, tmp_path, boot_ledger):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        link.lost("endpoint_unreachable")

        resp = call(bus, "tool.ask-model", prompt="vẫn hỏi được chứ?")

        assert resp["error"]["code"] == MODEL_UNAVAILABLE
        assert resp["error"]["message"] == "model_unavailable"
        assert resp["error"]["data"]["reason"] == REASONS["endpoint_unreachable"]
        # Không có kết quả, không có biên nhận — chưa có việc nào xảy ra.
        assert "result" not in resp
        assert "receipt" not in resp
        # Model thật sự không bị gọi.
        assert getattr(boot_ledger, "reached_model", 0) == 0

    @pytest.mark.parametrize("reason", sorted(REASONS))
    def test_refusal_carries_whichever_real_reason(self, tmp_path, reason):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        link.lost(reason)
        resp = call(bus, "tool.ask-model", prompt="x")
        assert resp["error"]["data"]["reason"] == REASONS[reason]

    def test_no_model_receipt_is_minted_while_degraded(self, tmp_path):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        link.lost("model_mismatch")
        for _ in range(5):
            call(bus, "tool.ask-model", prompt="thử lại")
        assert bus.receipts.by_source(SOURCE_MODEL) == ()
        assert bus.receipts.all() == ()  # không có việc nào được ghi nhận

    def test_local_command_still_runs_while_degraded(self, tmp_path, boot_ledger):
        """DEGRADED nhận lệnh — chỉ lệnh cần model mới bị chặn (D9)."""
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        link.lost("endpoint_unreachable")

        resp = call(bus, "tool.local-job", echo="vẫn làm được")

        assert "error" not in resp
        assert resp["result"]["echo"] == "vẫn làm được"
        assert resp["receipt"]["source"] == SOURCE_TOOL_LOCAL
        assert boot_ledger.local_runs == 1

    def test_offline_also_refuses_model(self, tmp_path):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        link.go_offline()
        resp = call(bus, "tool.ask-model", prompt="x")
        assert resp["error"]["code"] == MODEL_UNAVAILABLE
        assert resp["error"]["data"]["reason"] == "người dùng đã ngắt model"
        assert "result" not in resp

    def test_healing_restores_model_commands(self, tmp_path):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        link.lost("engine_unavailable")
        assert call(bus, "tool.ask-model", prompt="x")["error"]["code"] == MODEL_UNAVAILABLE
        link.healed()
        resp = call(bus, "tool.ask-model", prompt="x")
        assert "error" not in resp
        assert resp["receipt"]["source"] == SOURCE_MODEL


class TestErrorsNeverClaimWork:
    """Lỗi không có `result`, không có receipt. Không có đường nào bịa việc đã làm."""

    @pytest.mark.parametrize(
        ("link_setup", "reason"),
        [
            ("degraded", "endpoint_unreachable"),
            ("degraded", "model_mismatch"),
            ("degraded", "engine_unavailable"),
            ("degraded", "permission_denied"),
            ("offline", None),
            ("linking", None),
        ],
    )
    def test_every_model_refusal_shape(self, tmp_path, link_setup, reason):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        if link_setup == "degraded":
            link.come_online()
            link.lost(reason)
        elif link_setup == "offline":
            link.come_online()
            link.go_offline()

        resp = call(bus, "tool.ask-model", prompt="x")
        assert set(resp) == {"jsonrpc", "id", "error"}
        assert "result" not in resp
        assert "receipt" not in resp
        assert bus.receipts.all() == ()

    def test_permission_denied_when_manifest_omits_grant(self, tmp_path):
        """Biên 1 — method: method xin grant mà manifest không xin → từ chối ngay."""
        write_plugin(tmp_path, pid="tool.overreach", logic=WANTS_MODEL_WITHOUT_GRANT,
                     grants=())
        reg = PluginRegistry()
        reg.discover(tmp_path)
        reg.validate("tool.overreach")
        reg.load("tool.overreach")
        reg.activate("tool.overreach")
        link = LinkMachine()
        link.boot()
        link.come_online()
        bus = Bus(reg, receipts=ReceiptLog(),
                  allows_model=lambda: link.allows_model,
                  model_refusal=link.refuse_model)
        bus.sync_registry()

        resp = call(bus, "tool.overreach")
        assert resp["error"]["code"] == PERMISSION_DENIED
        assert resp["error"]["message"] == "permission_denied"
        assert resp["error"]["data"]["need"] == ["model.connect"]
        assert "result" not in resp
        assert bus.receipts.all() == ()

    def test_unknown_method_is_unavailable(self, tmp_path):
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        resp = call(bus, "tool.khong-ton-tai")
        assert resp["error"]["code"] == PLUGIN_UNAVAILABLE
        assert "result" not in resp
        assert "receipt" not in resp

    def test_client_cannot_stamp_its_own_source(self, tmp_path):
        """Client gửi `source: "model"` thì bus bỏ đi — nhãn vẫn do sổ quyết định."""
        link = LinkMachine()
        bus = make_bus(tmp_path, link)
        link.boot()
        link.come_online()
        resp = bus.handle(
            {
                "jsonrpc": "2.0",
                "id": "c-9",
                "method": "tool.local-job",
                "params": {"echo": "x", "source": "model", "provenance_label": "derived"},
            }
        )
        assert resp["receipt"]["source"] == SOURCE_TOOL_LOCAL
        assert "source" not in resp["result"]
