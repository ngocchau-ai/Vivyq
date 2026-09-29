"""Plugin Registry — vòng đời plugin, hot-swap, và lời gọi đang bay.

Vòng đời (spec §4.3):

    discovered → validated → loaded → activated ⇄ deactivated → unloaded

Hot-swap = `deactivated → unloaded → loaded → activated`. Lệnh đang bay (và lệnh
gửi tới trong lúc đang tháo/nạp) nhận `PluginReloading` — **host không sập**.

Quy tắc cứng (§4.4): `deactivate()` phải nhả mọi tài nguyên đang giữ (handle ctypes,
kết nối, timer). Python chạy in-process theo C-ABI, không có process boundary nào
cứu được nếu plugin quên nhả.
"""

from __future__ import annotations

import contextlib
import importlib.util
import itertools
import sys
import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

from .manifest import ContractError, Manifest, parse_manifest


class PluginState(StrEnum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    LOADED = "loaded"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    UNLOADED = "unloaded"


# Chuyển trạng thái được phép. Lệch là lỗi — không "cứ thử coi sao".
_TRANSITIONS: dict[PluginState, frozenset[PluginState]] = {
    PluginState.DISCOVERED: frozenset({PluginState.VALIDATED, PluginState.UNLOADED}),
    PluginState.VALIDATED: frozenset({PluginState.LOADED, PluginState.UNLOADED}),
    PluginState.LOADED: frozenset({PluginState.ACTIVATED, PluginState.UNLOADED}),
    PluginState.ACTIVATED: frozenset({PluginState.DEACTIVATED}),
    PluginState.DEACTIVATED: frozenset({PluginState.ACTIVATED, PluginState.UNLOADED}),
    PluginState.UNLOADED: frozenset({PluginState.LOADED, PluginState.DISCOVERED}),
}

# Hook vòng đời mà logic face có thể định nghĩa (tất cả đều tùy chọn trừ khi giữ tài nguyên).
_LIFECYCLE = frozenset({"activate", "deactivate", "run", "methods"})


class RegistryError(Exception):
    """Thao tác không hợp lệ trên vòng đời plugin."""


class PluginReloading(Exception):
    """Plugin đang hot-swap. Lời gọi bị từ chối kèm lý do — không trả kết quả bịa."""

    def __init__(self, plugin_id: str) -> None:
        self.plugin_id = plugin_id
        super().__init__(f"plugin {plugin_id} đang nạp lại; thử lại sau")


class PluginUnavailable(Exception):
    """Method chưa đăng ký, hoặc plugin chưa activated."""

    def __init__(self, plugin_id: str, reason: str) -> None:
        self.plugin_id = plugin_id
        self.reason = reason
        super().__init__(f"plugin {plugin_id}: {reason}")


class ActivateApi:
    """Thứ host trao cho `activate()`. Chỉ runtime được đăng ký method động."""

    def __init__(self, record: PluginRecord, *, allow_dynamic: bool) -> None:
        self._record = record
        self._allow_dynamic = allow_dynamic

    def register_method(self, name: str, fn: Callable[..., Any]) -> None:
        if not self._allow_dynamic:
            raise RegistryError(
                f"plugin {self._record.manifest.id} không phải runtime nên không được "
                "đăng ký method động"
            )
        if not name or "/" in name or name != name.strip():
            raise RegistryError(f"tên method {name!r} không hợp lệ")
        self._record.methods[f"{self._record.manifest.id}/{name}"] = fn


@dataclass(slots=True)
class PluginRecord:
    """Một plugin trong registry. Không ai sửa `state` trực tiếp — đi qua PluginRegistry."""

    manifest: Manifest
    path: Path
    state: PluginState = PluginState.DISCOVERED
    instance: Any = None
    module: ModuleType | None = None
    module_name: str | None = None
    methods: dict[str, Callable[..., Any]] = field(default_factory=dict)
    error: str | None = None
    in_flight: int = 0
    reloading: bool = False

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def is_active(self) -> bool:
        return self.state is PluginState.ACTIVATED


class PluginRegistry:
    """Nơi duy nhất giữ vòng đời plugin."""

    def __init__(self, *, backends: dict[str, Callable[..., Any]] | None = None) -> None:
        self._records: dict[str, PluginRecord] = {}
        self._lock = threading.RLock()
        self._swap_seq = itertools.count(1)
        self._backends = backends or {}
        # Được gọi sau **mỗi** lần bảng plugin đổi (discover/load/unload/
        # activate/deactivate/hot-swap). Bus cắm vào đây để dựng lại bảng method
        # **và bản đồ thân thể** — nhờ vậy bản đồ tự dựng lại khi thêm tool,
        # plugin, skill, chứ không phải chờ ai nhớ ra gọi tay. Hook chỉ là báo
        # hiệu, không ai đọc giá trị trả về.
        self.on_change: Callable[[], Any] | None = None
        self._mute = 0

    def _notify(self) -> None:
        if self._mute:
            return
        if self.on_change is not None:
            self.on_change()

    @contextlib.contextmanager
    def _quiet(self) -> Iterator[None]:
        """Gom nhiều thay đổi thành **một** lần báo — dùng cho hot-swap."""
        self._mute += 1
        try:
            yield
        finally:
            self._mute -= 1
            self._notify()

    # ---- đọc ----

    def record(self, plugin_id: str) -> PluginRecord | None:
        return self._records.get(plugin_id)

    def all(self) -> tuple[PluginRecord, ...]:
        return tuple(self._records.values())

    def method_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for rec in self._records.values():
            names.extend(rec.methods)
        return tuple(sorted(names))

    # ---- discover / validate ----

    def discover(self, root: str | Path) -> list[PluginRecord]:
        """Quét một thư mục: mọi thư mục con có `plugin.toml` là một ứng viên.

        Ứng viên hỏng contract không chặn các ứng viên khác — chúng được ghi nhận
        vào `error` và ở trạng thái `discovered`, không bao giờ `validated`.
        """
        root_path = Path(root)
        found: list[PluginRecord] = []
        if not root_path.is_dir():
            return found
        for child in sorted(root_path.iterdir()):
            manifest_path = child / "plugin.toml"
            if not manifest_path.is_file():
                continue
            try:
                manifest = parse_manifest(manifest_path)
            except ContractError as exc:
                rec = PluginRecord(
                    manifest=_broken_manifest(child.name),
                    path=child,
                    state=PluginState.DISCOVERED,
                    error=str(exc),
                )
                self._records[rec.id] = rec
                found.append(rec)
                continue
            if manifest.id in self._records:
                raise RegistryError(f"plugin id trùng: {manifest.id}")
            rec = PluginRecord(manifest=manifest, path=child, state=PluginState.DISCOVERED)
            self._records[rec.id] = rec
            found.append(rec)
        if found:
            self._notify()
        return found

    def validate(self, plugin_id: str) -> PluginRecord:
        """`discovered → validated`. Manifest sai thì không qua cửa này."""
        rec = self._get(plugin_id)
        self._require(rec, PluginState.DISCOVERED, "validate")
        if rec.error:
            raise RegistryError(f"plugin {plugin_id} vi phạm contract: {rec.error}")
        self._move(rec, PluginState.VALIDATED)
        return rec

    # ---- load / unload ----

    def load(self, plugin_id: str) -> PluginRecord:
        """Nạp logic face và dựng instance. `validated → loaded`."""
        rec = self._get(plugin_id)
        if rec.state is PluginState.UNLOADED:
            pass  # nạp lại sau unload là hợp lệ
        else:
            self._require(rec, PluginState.VALIDATED, "load")
        if rec.manifest.entry_logic is None:
            # Plugin một mặt UI: không có logic để nạp — vẫn được `loaded`.
            rec.instance = None
            rec.methods = {}
            self._move(rec, PluginState.LOADED)
            return rec

        module_name: str | None = None
        try:
            module, module_name = self._import_logic(rec)
            instance = self._instantiate(rec, module)
            methods = self._bind_methods(rec, instance)
        except Exception as exc:
            if module_name:
                sys.modules.pop(module_name, None)
            # Ném tiếp, nhưng **phải ghi lại lý do** — record mang lỗi thì bản đồ
            # thân thể mới nói được "thứ này hỏng vì…", thay vì im lặng biến mất.
            rec.error = rec.error or f"load(): {exc}"
            raise
        rec.module = module
        rec.module_name = module_name
        rec.instance = instance
        rec.methods = methods
        self._move(rec, PluginState.LOADED)
        return rec

    def unload(self, plugin_id: str) -> PluginRecord:
        """Gỡ instance. Phải đã `deactivated` — nếu không thì tự nhả trước.

        Tự gọi `deactivate()` khi còn `activated` là đường phòng thủ cuối: thà
        nhả hai lần còn hơn rò handle ctypes ra đời.
        """
        rec = self._get(plugin_id)
        if rec.state is PluginState.ACTIVATED:
            self._call_hook(rec, "deactivate")
            self._move(rec, PluginState.DEACTIVATED)
        if rec.state not in (
            PluginState.DISCOVERED,
            PluginState.VALIDATED,
            PluginState.LOADED,
            PluginState.DEACTIVATED,
        ):
            raise RegistryError(
                f"plugin {rec.id}: không thể unload khi đang ở trạng thái {rec.state}"
            )
        rec.methods = {}
        rec.instance = None
        rec.module = None
        if rec.module_name:
            sys.modules.pop(rec.module_name, None)
            rec.module_name = None
        self._move(rec, PluginState.UNLOADED)
        return rec

    # ---- activate / deactivate ----

    def activate(self, plugin_id: str) -> PluginRecord:
        rec = self._get(plugin_id)
        self._require(rec, PluginState.LOADED, "activate")
        api = ActivateApi(rec, allow_dynamic=rec.manifest.kind == "runtime")
        self._call_hook(rec, "activate", api)
        self._move(rec, PluginState.ACTIVATED)
        return rec

    def deactivate(self, plugin_id: str) -> PluginRecord:
        rec = self._get(plugin_id)
        self._require(rec, PluginState.ACTIVATED, "deactivate")
        self._call_hook(rec, "deactivate")
        self._move(rec, PluginState.DEACTIVATED)
        return rec

    # ---- hot-swap ----

    def hot_swap(self, plugin_id: str, new_root: str | Path | None = None) -> PluginRecord:
        """`deactivated → unloaded → loaded → activated`, có chặn lời gọi đang bay.

        `new_root` là thư mục plugin mới (mặc định: cùng thư mục cũ, tức là nạp lại
        code). Trong suốt phiên tháo/nạp, `rec.reloading = True` — mọi lời gọi tới
        plugin này nhận `PluginReloading`.
        """
        rec = self._get(plugin_id)
        with self._quiet():
            if rec.state is PluginState.ACTIVATED:
                # chặn lời gọi mới NGAY TRƯỚC khi deactivate để không có khe hở
                rec.reloading = True
                try:
                    self.deactivate(plugin_id)
                except Exception:
                    rec.reloading = False
                    raise
            else:
                rec.reloading = True

            try:
                if rec.state is PluginState.LOADED:
                    self._call_hook(rec, "deactivate")  # phòng thủ: nhả trước khi vứt
                if rec.state in (PluginState.DEACTIVATED, PluginState.LOADED):
                    self.unload(plugin_id)

                if new_root is not None:
                    new_path = Path(new_root)
                    new_manifest = parse_manifest(new_path / "plugin.toml")
                    if new_manifest.id != plugin_id:
                        raise RegistryError(
                            f"hot-swap phải giữ nguyên id: {plugin_id} → {new_manifest.id}"
                        )
                    rec.manifest = new_manifest
                    rec.path = new_path

                self.load(plugin_id)
                self.activate(plugin_id)
            finally:
                rec.reloading = False
        return rec

    # ---- lời gọi ----

    def invoke(self, method: str, params: dict[str, Any], *, context_factory: Any = None) -> Any:
        """Gọi một method đã đăng ký. Trả kết quả thô — bus sẽ gán nhãn nguồn.

        `context_factory` là hàm cấp `CallContext` cho lời gọi; nếu thiếu thì
        plugin nhận `None` (chỉ dùng cho method không cần năng lực).
        """
        with self._lock:
            owner = self._owner_of(method)
            if owner is None:
                raise PluginUnavailable(method, "method chưa đăng ký")
            if owner.reloading:
                raise PluginReloading(owner.id)
            if owner.state is not PluginState.ACTIVATED:
                raise PluginUnavailable(owner.id, f"trạng thái {owner.state}")
            fn = owner.methods[method]
            owner.in_flight += 1
        try:
            ctx = context_factory(owner.manifest) if context_factory else None
            return fn(ctx, **params) if ctx is not None else fn(**params)
        finally:
            with self._lock:
                owner.in_flight -= 1

    def assert_settled(self, plugin_id: str) -> None:
        """Không còn lời gọi nào đang bay. Dùng cho test rò tài nguyên."""
        rec = self._get(plugin_id)
        if rec.in_flight != 0:
            raise RegistryError(f"plugin {plugin_id} còn {rec.in_flight} lời gọi đang bay")

    # ---- nội bộ ----

    def _get(self, plugin_id: str) -> PluginRecord:
        rec = self._records.get(plugin_id)
        if rec is None:
            raise RegistryError(f"không có plugin {plugin_id}")
        return rec

    def _owner_of(self, method: str) -> PluginRecord | None:
        for rec in self._records.values():
            if method in rec.methods:
                return rec
        return None

    def _require(self, rec: PluginRecord, state: PluginState, action: str) -> None:
        if rec.state is not state:
            raise RegistryError(
                f"plugin {rec.id}: không thể {action} khi đang ở trạng thái {rec.state} "
                f"(cần {state})"
            )

    def _move(self, rec: PluginRecord, to: PluginState) -> None:
        allowed = _TRANSITIONS[rec.state]
        if to not in allowed:
            raise RegistryError(f"plugin {rec.id}: {rec.state} → {to} không hợp lệ")
        rec.state = to
        self._notify()

    def _call_hook(self, rec: PluginRecord, name: str, *args: Any) -> Any:
        fn = getattr(rec.instance, name, None)
        if fn is None:
            return None
        try:
            return fn(*args)
        except Exception as exc:  # noqa: BLE001 — lỗi plugin không được sập host
            rec.error = f"{name}(): {exc}"
            raise RegistryError(f"plugin {rec.id}: {name}() ném lỗi — {exc}") from exc

    def _import_logic(self, rec: PluginRecord) -> tuple[ModuleType, str]:
        assert rec.manifest.entry_logic is not None
        logic_path = (rec.path / rec.manifest.entry_logic).resolve()
        if not logic_path.is_file():
            raise RegistryError(f"plugin {rec.id}: thiếu entry logic {logic_path}")
        # Tên module riêng cho từng lần nạp để hot-swap đọc code mới.
        mod_name = f"_cautreo_plugin_{rec.id.replace('.', '_')}_{next(self._swap_seq)}"
        spec = importlib.util.spec_from_file_location(mod_name, logic_path)
        if spec is None or spec.loader is None:
            raise RegistryError(f"plugin {rec.id}: không nạp được {logic_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            sys.modules.pop(mod_name, None)
            raise RegistryError(f"plugin {rec.id}: lỗi khi import logic — {exc}") from exc
        return module, mod_name

    def _instantiate(self, rec: PluginRecord, module: ModuleType) -> Any:
        factory = getattr(module, "create_plugin", None)
        if callable(factory):
            return factory()
        cls = getattr(module, "Plugin", None)
        if isinstance(cls, type):
            return cls()
        raise RegistryError(
            f"plugin {rec.id}: logic face phải có `create_plugin()` hoặc class `Plugin`"
        )

    def _bind_methods(self, rec: PluginRecord, instance: Any) -> dict[str, Callable[..., Any]]:
        bound: dict[str, Callable[..., Any]] = {}
        run = getattr(instance, "run", None)
        if callable(run):
            bound[rec.id] = run
        declared = getattr(instance, "methods", None)
        if isinstance(declared, dict):
            for name, fn in declared.items():
                if not isinstance(name, str) or not callable(fn):
                    raise RegistryError(f"plugin {rec.id}: methods.{name!r} không hợp lệ")
                bound[f"{rec.id}/{name}"] = fn
        if not bound:
            if rec.manifest.kind == "runtime":
                # Runtime đăng ký method động trong `activate(api)` — chưa có gì
                # ở lúc load là bình thường.
                return bound
            raise RegistryError(
                f"plugin {rec.id}: logic face không expose method nào "
                f"(cần `run(ctx, **params)` hoặc `methods = {{...}}`)"
            )
        return bound


def _broken_manifest(name: str) -> Manifest:
    """Manifest giữ chỗ cho ứng viên sai contract — không bao giờ được nạp."""
    return Manifest(
        id=f"invalid.{name}",
        version="0.0.0",
        api=1,
        kind="tool",
        organ="hand",
        entry_ui=None,
        entry_logic=None,
        grants=frozenset(),
    )
