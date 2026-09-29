"""Nhãn nguồn — host gán, plugin không tự gắn được.

Cơ chế: host trao cho plugin một `ctx` có các **handle năng lực**. Handle nào được
chạm trong lúc chạy method thì host ghi vào sổ. Nhãn suy ra từ sổ đó, **không bao
giờ** bằng cách bóc kết quả plugin trả về để tìm nhãn.

Đây là cách duy nhất để quy tắc §7.1 ("plugin không tự gắn nhãn được") thành điều
kiểm chứng được thay vì một lời quy ước. Plugin có trả `{"source": "model"}` đi
chăng nữa thì bus vẫn gán nhãn theo sổ — và `test_provenance.py` khẳng định đúng
điều đó.

Bốn nhãn (spec §7.1):
    model      — kết quả sinh ra từ model
    cautreo    — kết quả từ bộ nhớ / C-ABI Cautreo
    tool-local — kết quả từ tool cục bộ (đọc file, tra cứu…) không qua model
    derived    — suy ra từ receipt khác
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# Thứ tự ưu tiên khi một lời gọi chạm nhiều năng lực.
# derived thắng vì đã tiêu thụ receipt khác; sau đó mới tới chỗ phát sinh kết quả.
SOURCE_MODEL = "model"
SOURCE_CAUTREO = "cautreo"
SOURCE_TOOL_LOCAL = "tool-local"
SOURCE_DERIVED = "derived"

ALL_SOURCES = (SOURCE_MODEL, SOURCE_CAUTREO, SOURCE_TOOL_LOCAL, SOURCE_DERIVED)


class Capability(StrEnum):
    """Năng lực mà plugin có thể chạm qua handle. Không có đường nào khác."""

    MODEL = "model"
    CAUTREO = "cautreo"
    FS = "fs"
    LOCAL = "local"


# Grant cần có để mở từng handle. Chặn quyền ở biên handle, không chỉ ở biên method.
CAPABILITY_GRANTS: dict[Capability, str] = {
    Capability.MODEL: "model.connect",
    Capability.CAUTREO: "cautreo.access",
    Capability.FS: "fs.workspace",
    Capability.LOCAL: "tool.local",
}


class PermissionDenied(Exception):
    """Plugin thiếu quyền để mở một năng lực."""

    def __init__(self, need: str, have: frozenset[str]) -> None:
        self.need = need
        self.have = sorted(have)
        super().__init__(f"cần quyền {need}; plugin đang có {self.have}")


@dataclass(slots=True)
class Handle:
    """Một năng lực đã được phép mở. Dùng nó là tự ghi sổ."""

    cap: Capability
    _touch: Callable[[], None]
    _invoke: Callable[..., Any]

    def __getattr__(self, name: str) -> Callable[..., Any]:
        # Mọi thao tác trên handle đều đi qua đây: ghi sổ trước, rồi mới chạy.
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            self._touch()
            return self._invoke(name, *args, **kwargs)

        return _wrapped


@dataclass(slots=True)
class CallContext:
    """Ngữ cảnh một lời gọi. Sổ tay ở đây là nguồn duy nhất để gán nhãn.

    Plugin nhận `ctx` khi method được gọi. Chỉ host tạo được — không có đường
    dựng một CallContext đã "khai sẵn" nhãn.
    """

    grants: frozenset[str]
    _used: set[Capability] = field(default_factory=set)
    _derived_from: list[str] = field(default_factory=list)
    # Backend khoá theo TÊN năng lực ("model", "cautreo", "fs", "local") — trùng
    # với `Capability.value`. Khớp với `default_backends()` và với chỗ plugin runtime
    # tự cắm model/Cautreo vào, nên caller không phải import Capability chỉ để khoá.
    _backends: Mapping[str, Callable[..., Any]] = field(default_factory=dict)

    # ---- ghi sổ ----

    def _touch(self, cap: Capability) -> None:
        self._used.add(cap)

    def derive_from(self, *receipt_ids: str) -> None:
        """Khai rằng kết quả này suy ra từ receipt khác."""
        for rid in receipt_ids:
            if rid and rid not in self._derived_from:
                self._derived_from.append(rid)

    # ---- mở handle ----

    def _open(self, cap: Capability) -> Handle:
        need = CAPABILITY_GRANTS[cap]
        if need not in self.grants:
            raise PermissionDenied(need, self.grants)
        backend = self._backends.get(cap.value)
        return Handle(
            cap=cap,
            _touch=lambda: self._touch(cap),
            _invoke=_default_invoke(backend, cap),
        )

    @property
    def model(self) -> Handle:
        """Cửa vào model. Cần grant `model.connect`."""
        return self._open(Capability.MODEL)

    @property
    def cautreo(self) -> Handle:
        """Cửa vào bộ nhớ / C-ABI Cautreo. Cần grant `cautreo.access`."""
        return self._open(Capability.CAUTREO)

    @property
    def fs(self) -> Handle:
        """Cửa vào workspace (đọc và ghi). Cần grant `fs.workspace`."""
        return self._open(Capability.FS)

    @property
    def local(self) -> Handle:
        """Tool cục bộ không cần model. Cần grant `tool.local`."""
        return self._open(Capability.LOCAL)

    # ---- đọc sổ (chỉ host dùng) ----

    @property
    def used(self) -> frozenset[Capability]:
        return frozenset(self._used)

    @property
    def derived_from(self) -> tuple[str, ...]:
        return tuple(self._derived_from)


def _default_invoke(
    backend: Callable[..., Any] | None, cap: Capability
) -> Callable[..., Any]:
    if backend is None:
        if cap is Capability.MODEL or cap is Capability.CAUTREO:
            # Host không có sẵn model hay Cautreo (spec D3) — và **không bao giờ**
            # dựng một kết quả giả để thay. Thiếu backend là lỗi thật, ném thật.
            def _missing(name: str, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError(
                    f"chưa cắm backend cho năng lực {cap.value!r} — host không tự có "
                    "model hay Cautreo; plugin runtime phải cắm vào qua CallContext"
                )

            return _missing

        # fs / local: ghi sổ vẫn xảy ra (vì _touch chạy trước), và trả về một
        # giá trị đánh dấu rõ là chưa có backend — không phải kết quả của việc gì.
        def _empty(name: str, *args: Any, **kwargs: Any) -> Any:
            return {"ok": True, "op": name, "args": len(args)}

        return _empty

    def _bound(name: str, *args: Any, **kwargs: Any) -> Any:
        return getattr(backend, name)(*args, **kwargs)

    return _bound


def source_for(ctx: CallContext) -> str:
    """Gán nhãn nguồn từ sổ của một lời gọi. **Không nhận nhãn từ plugin.**

    Ưu tiên: derived > model > cautreo > tool-local.
    """
    if ctx.derived_from:
        return SOURCE_DERIVED
    used = ctx.used
    if Capability.MODEL in used:
        return SOURCE_MODEL
    if Capability.CAUTREO in used:
        return SOURCE_CAUTREO
    return SOURCE_TOOL_LOCAL


def strip_self_label(payload: Any) -> Any:
    """Gỡ mọi trường tự nhận nhãn nguồn ra khỏi kết quả plugin trả về.

    Host không đọc những trường này để gán nhãn — nhưng cũng không cho chúng
    lọt ra ngoài UI, để không ai đọc nhầm lời tự nhận thành nhãn thật.
    """
    if isinstance(payload, dict):
        return {
            k: strip_self_label(v)
            for k, v in payload.items()
            if k not in {"source", "nhãn nguồn", "provenance_label", "source_label"}
        }
    if isinstance(payload, list):
        return [strip_self_label(v) for v in payload]
    return payload
