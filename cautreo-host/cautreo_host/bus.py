"""IPC Bus — JSON-RPC 2.0 nối JS ↔ host ↔ Python.

Bốn điều bus này không làm:
1. **Không nhận nhãn nguồn từ client.** Client gửi `source` thì bỏ đi, không đọc.
2. **Không sinh `result` khi lỗi.** Lỗi chỉ có `error`. Không có receipt nào tự nhận
   đã làm việc gì — receipt là đơn vị tin cậy, chỉ sinh khi việc **thật sự xảy ra**.
3. **Không bịa câu trả lời thay model.** Khi link không ONLINE, lệnh cần model bị
   từ chối kèm lý do thật.
4. **Không nuốt lỗi plugin.** Lỗi trả `-32002` kèm `plugin_id` và `method`.

Mã lỗi (spec §5):
    -32001  permission_denied    thiếu grant
    -32002  plugin_error         plugin ném lỗi
    -32003  plugin_reloading     lệnh gửi tới khi đang hot-swap
    -32004  plugin_unavailable   method chưa đăng ký / plugin chưa activated
    -32005  model_unavailable    cần model nhưng link không phải ONLINE
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .bodymap import build_body_map, render_body_prompt
from .provenance import CallContext, PermissionDenied, source_for, strip_self_label
from .receipt import Receipt, ReceiptLog
from .registry import PluginRecord, PluginRegistry, PluginReloading, PluginUnavailable

# --- mã lỗi ---
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
PERMISSION_DENIED = -32001
PLUGIN_ERROR = -32002
PLUGIN_RELOADING = -32003
PLUGIN_UNAVAILABLE = -32004
MODEL_UNAVAILABLE = -32005

# Trường client được phép gửi. `source` / `nhãn nguồn` không có trong đây —
# nên có gửi cũng bị bỏ, và bị gỡ khỏi params trước khi chạm plugin.
_CLIENT_FIELDS = frozenset({"jsonrpc", "id", "method", "params"})


@dataclass(slots=True)
class MethodSpec:
    """Một method đã đăng ký trên bus. `grants` là những gì method này cần."""

    name: str
    plugin_id: str
    organ: str
    fn: Callable[..., Any]
    grants: frozenset[str]
    needs_model: bool


class Bus:
    """Cổng duy nhất giữa UI và logic. Mọi lời gọi đi qua đây đều sinh receipt."""

    def __init__(
        self,
        registry: PluginRegistry,
        *,
        receipts: ReceiptLog | None = None,
        allows_model: Callable[[], bool] | None = None,
        model_refusal: Callable[[], str] | None = None,
        backends: dict[str, Callable[..., Any]] | None = None,
    ) -> None:
        self._registry = registry
        self.receipts = receipts if receipts is not None else ReceiptLog()
        self._allows_model = allows_model or (lambda: True)
        self._model_refusal = model_refusal or (lambda: "model chưa sẵn sàng")
        self._backends = backends or {}
        self._methods: dict[str, MethodSpec] = {}
        self._host_methods: dict[str, tuple[Callable[..., Any], frozenset[str], bool]] = {}
        self.outbox: list[dict[str, Any]] = []
        # `host.body-map` là cửa hỏi "cơ thể có gì". **Không cần model** — hỏi
        # được cả khi DEGRADED, đúng tinh thần D9: lệnh không cần model vẫn chạy.
        self.register_host_method(
            "host.body-map",
            lambda **_: {"summary": "bản đồ thân thể", "map": self.body_map},
        )
        self.register_host_method(
            "host.knowledge-graph",
            lambda **_: {"summary": "biểu đồ tri thức", "graph": self.knowledge_graph},
        )
        self.register_host_method(
            "host.link-probe",
            lambda **_: {
                "summary": "thăm dò liên kết",
                "link": getattr(self, "_link_probe", lambda: {"state": "unknown"})(),
            },
        )
        # Bản đồ thân thể — dựng từ registry, không viết tay. Cập nhật trong
        # `sync_registry()`, và **đẩy thẳng vào system prompt của model backend**
        # để ViVy biết mình là ai ngay từ đầu mỗi câu hỏi.
        self._body_map: dict[str, Any] = build_body_map(self._registry.all(), self._host_methods)
        self._body_prompt: str = render_body_prompt(self._body_map)
        self._push_system_prompt()
        # Registry đổi thì bảng method + bản đồ tự dựng lại. Đây là chỗ khiến
        # "tự dựng lại khi thêm tool/plugin/skill" thành sự thật, không phải lời hứa.
        registry.on_change = self.sync_registry

    @property
    def knowledge_graph(self) -> dict[str, Any]:
        """Biểu đồ tri thức hiện tại tích hợp mô hình kép Gemma 4B & Qwen 72B."""
        from .knowledge import build_knowledge_graph
        return build_knowledge_graph(self._registry.all(), self._host_methods)


    @property
    def backends(self) -> dict[str, Any]:
        return self._backends

    # ---- đăng ký ----


    def sync_registry(self) -> tuple[str, ...]:
        """Dựng lại bảng method **và bản đồ thân thể** từ registry.

        Gọi sau mỗi lần discover/load/unload/activate/deactivate/hot-swap —
        registry tự gọi qua `on_change`, không ai phải nhớ gọi tay.
        """
        self._methods.clear()
        for rec in self._registry.all():
            for name, fn in rec.methods.items():
                grants = self._method_grants(rec, name)
                self._methods[name] = MethodSpec(
                    name=name,
                    plugin_id=rec.id,
                    organ=rec.manifest.organ or rec.manifest.kind,
                    fn=fn,
                    grants=grants,
                    needs_model="model.connect" in grants,
                )
        self._body_map = build_body_map(self._registry.all(), self._host_methods)
        self._body_prompt = render_body_prompt(self._body_map)
        self._push_system_prompt()
        self._emit_registry_changed()
        return tuple(sorted(self._methods))

    def _push_system_prompt(self) -> None:
        """Nạp bản đồ vào model backend. Backend không có `system` thì bỏ qua.

        Đây là **cửa duy nhất** model biết cơ thể mình có gì. Không có đường nào
        khác chèn lời "bạn là ViVy" vào — và nội dung năng lực thì lấy từ registry.
        """
        backend = self._backends.get("model")
        setter = getattr(backend, "set_system", None)
        if callable(setter):
            setter(self._body_prompt)

    @property
    def body_map(self) -> dict[str, Any]:
        """Bản đồ thân thể hiện tại. Đọc được cả khi DEGRADED — không cần model."""
        return self._body_map

    @property
    def body_prompt(self) -> str:
        """System prompt đang nạp cho model — đúng chuỗi model đang thấy."""
        return self._body_prompt

    def register_host_method(
        self,
        name: str,
        fn: Callable[..., Any],
        *,
        grants: frozenset[str] | set[str] = frozenset(),
        needs_model: bool = False,
    ) -> None:
        """Method của host (`host.*`) — không phải plugin, receipt mang organ `host`."""
        self._host_methods[name] = (fn, frozenset(grants), needs_model)

    def method_names(self) -> tuple[str, ...]:
        return tuple(sorted(set(self._methods) | set(self._host_methods)))

    # ---- phục vụ lời gọi ----

    def handle(self, message: Any) -> dict[str, Any] | None:
        """Điều khiển một tin nhắn tới. Trả response, hoặc None nếu là notification."""
        if isinstance(message, (bytes, str)):
            try:
                message = json.loads(message)
            except (ValueError, TypeError):
                return _error(None, PARSE_ERROR, "không phải JSON hợp lệ")
        if not isinstance(message, dict):
            return _error(None, INVALID_REQUEST, "phải là object JSON-RPC")

        msg_id = message.get("id")
        method = message.get("method")
        if not isinstance(method, str) or not method:
            if msg_id is None:
                return None  # notification rỗng — không phản hồi
            return _error(msg_id, INVALID_REQUEST, "thiếu method")

        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _error(msg_id, INVALID_REQUEST, "params phải là object")
        params = _drop_self_labels(params)

        try:
            payload = self._dispatch(method, params)
        except _BusError as exc:
            return _error(msg_id, exc.code, exc.message, data=exc.data)
        except Exception as exc:  # noqa: BLE001 — host không sập vì lỗi client
            return _error(msg_id, PLUGIN_ERROR, f"{type(exc).__name__}: {exc}")

        if msg_id is None:
            return None  # notification: chạy rồi nhưng không có gì để đáp
        return {"jsonrpc": "2.0", "id": msg_id, "result": payload["result"],
                "receipt": payload["receipt"].to_dict()}

    def publish(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Phát một notification ra ngoài. Không có `id` — không ai chờ trả lời."""
        note = {"jsonrpc": "2.0", "method": method, "params": params}
        self.outbox.append(note)
        return note

    def drain(self) -> list[dict[str, Any]]:
        out = list(self.outbox)
        self.outbox.clear()
        return out

    # ---- nội bộ ----

    def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method in self._host_methods:
            return self._run_host(method, params)
        spec = self._methods.get(method)
        if spec is None:
            raise _BusError(
                PLUGIN_UNAVAILABLE,
                "plugin_unavailable",
                {"method": method},
            )
        return self._run_plugin(spec, params)

    def _run_host(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        fn, grants, needs_model = self._host_methods[method]
        if needs_model and not self._allows_model():
            raise _BusError(
                MODEL_UNAVAILABLE,
                "model_unavailable",
                {"method": method, "reason": self._model_refusal()},
            )
        ctx = CallContext(grants=frozenset(grants), _backends=self._backends)
        try:
            raw = fn(ctx, **params) if _wants_ctx(fn) else fn(**params)
        except PermissionDenied as exc:
            raise _BusError(
                PERMISSION_DENIED, "permission_denied", {"need": exc.need}
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise _BusError(
                PLUGIN_ERROR,
                "plugin_error",
                {"method": method, "error": str(exc)},
            ) from exc
        return self._stamp(method, "host", raw, ctx)

    def _run_plugin(self, spec: MethodSpec, params: dict[str, Any]) -> dict[str, Any]:
        rec = self._registry.record(spec.plugin_id)
        if rec is None:
            raise _BusError(
                PLUGIN_UNAVAILABLE, "plugin_unavailable", {"plugin_id": spec.plugin_id}
            )
        if rec.reloading:
            raise _BusError(
                PLUGIN_RELOADING, "plugin_reloading", {"plugin_id": spec.plugin_id}
            )
        if not rec.is_active:
            raise _BusError(
                PLUGIN_UNAVAILABLE,
                "plugin_unavailable",
                {"plugin_id": spec.plugin_id, "state": rec.state.value},
            )

        # Biên 1 — method: method này cần grant mà manifest không xin thì từ chối
        # ngay, không đợi plugin chui vào tới handle mới nổ.
        missing = sorted(spec.grants - rec.manifest.grants)
        if missing:
            raise _BusError(
                PERMISSION_DENIED,
                "permission_denied",
                {"plugin_id": spec.plugin_id, "need": missing,
                 "have": sorted(rec.manifest.grants)},
            )
        if spec.needs_model and not self._allows_model():
            # Không có result, không có receipt — tuyệt đối không bịa trả lời.
            raise _BusError(
                MODEL_UNAVAILABLE,
                "model_unavailable",
                {"plugin_id": spec.plugin_id, "method": spec.name,
                 "reason": self._model_refusal()},
            )

        ctx = CallContext(grants=rec.manifest.grants, _backends=self._backends)
        try:
            raw = self._registry.invoke(
                spec.name, params, context_factory=lambda _m: ctx
            )
        except PluginReloading as exc:
            raise _BusError(
                PLUGIN_RELOADING, "plugin_reloading", {"plugin_id": spec.plugin_id},
            ) from exc
        except PluginUnavailable as exc:
            raise _BusError(
                PLUGIN_UNAVAILABLE, "plugin_unavailable",
                {"plugin_id": spec.plugin_id, "reason": exc.reason},
            ) from exc
        except PermissionDenied as exc:
            # Biên 2 — handle: plugin thiếu quyền thì sổ không ghi, nhãn vẫn trung thực.
            raise _BusError(
                PERMISSION_DENIED, "permission_denied",
                {"plugin_id": spec.plugin_id, "need": exc.need},
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise _BusError(
                PLUGIN_ERROR, "plugin_error",
                {"plugin_id": spec.plugin_id, "method": spec.name,
                 "error": f"{type(exc).__name__}: {exc}"},
            ) from exc
        return self._stamp(spec.name, spec.organ, raw, ctx)

    def _stamp(
        self, command: str, organ: str, raw: Any, ctx: CallContext
    ) -> dict[str, Any]:
        """Gắn nhãn nguồn từ sổ lời gọi, rồi mới sinh receipt. Không đọc lời plugin."""
        clean = strip_self_label(raw)
        source = source_for(ctx)
        receipt = self.receipts.record(
            organ=organ,
            command=command,
            result=_summarize(clean),
            source=source,
        )
        # Receipt nằm trong response cho request/response. Chỉ publish
        # host.receipt cho notification/async — không emit kép (UI sẽ render 2 lần).
        return {"result": clean, "receipt": receipt}

    def _method_grants(self, rec: PluginRecord, method: str) -> frozenset[str]:
        """Grant mà method này cần.

        Logic face khai qua `method_grants = {"run": ["model.connect"]}`. Không khai
        gì thì giả định **cả plugin** cần đúng những gì manifest xin — nghĩa là plugin
        nào có `model.connect` thì mọi method của nó đều cần model, cho tới khi plugin
        chứng minh ngược lại bằng `method_grants`.
        """
        declared = getattr(rec.instance, "method_grants", None)
        if isinstance(declared, dict):
            need = declared.get(_short_name(rec.id, method))
            if isinstance(need, (list, tuple, set, frozenset)):
                return frozenset(str(g) for g in need)
            return frozenset()
        return rec.manifest.grants

    def _emit_receipt(self, receipt: Receipt) -> None:
        self.publish("host.receipt", receipt.to_dict())

    def _emit_registry_changed(self) -> None:
        self.publish(
            "registry.changed",
            {
                "methods": list(self.method_names()),
                "plugins": [
                    {"id": r.id, "state": r.state.value, "kind": r.manifest.kind}
                    for r in self._registry.all()
                ],
            },
        )


def _short_name(plugin_id: str, method: str) -> str:
    """`tool.fs-read` → `run`; `tool.fs-read/preview` → `preview`.

    Đó là khóa mà logic face dùng trong `method_grants`.
    """
    if method == plugin_id:
        return "run"
    prefix = plugin_id + "/"
    return method[len(prefix):] if method.startswith(prefix) else method


class _BusError(Exception):
    def __init__(self, code: int, message: str, data: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def _error(
    msg_id: Any, code: int, message: str, *, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Response lỗi. **Không có `result`. Không có `receipt`.**"""
    err: dict[str, Any] = {"code": code, "message": message}
    if data:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": msg_id, "error": err}


def _drop_self_labels(params: dict[str, Any]) -> dict[str, Any]:
    """Bỏ mọi trường client cố tình gửi kèm để tự gắn nhãn nguồn."""
    return {
        k: _drop_self_labels(v) if isinstance(v, dict) else v
        for k, v in params.items()
        if k not in {"source", "nhãn nguồn", "provenance_label", "source_label"}
    }


def _summarize(payload: Any) -> str:
    """Mô tả ngắn cho receipt. Ưu tiên lời plugin tự nói (`summary`/`note`),
    còn không thì mô tả đúng dạng kết quả — **không bịa nội dung**."""
    if isinstance(payload, dict):
        for key in ("summary", "note"):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()[:200]
    text = payload if isinstance(payload, str) else repr(payload)
    return text if len(text) <= 200 else text[:197] + "…"


def _wants_ctx(fn: Callable[..., Any]) -> bool:
    """Method host có tham số `ctx` thì nhận CallContext; không thì gọi trần."""
    import inspect

    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return "ctx" in sig.parameters
