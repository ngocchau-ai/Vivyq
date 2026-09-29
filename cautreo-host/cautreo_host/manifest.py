"""Đọc và kiểm `plugin.toml` — contract của mọi plugin.

Đây là cửa thứ nhất của host: manifest sai thì không có chuyện nạp.
Mọi lỗi trả về `ContractError` kèm lý do cụ thể, không nuốt lỗi im lặng.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# api mà host này hiểu. Lệch là từ chối — không cố dịch, không đoán.
SUPPORTED_API = 1

VALID_KINDS = frozenset({"workspace", "panel", "tool", "runtime"})
VALID_ORGANS = frozenset({"eye", "hand", "both"})

# tool/runtime là cơ quan của cơ thể nên phải khai organ (spec §4.1).
# workspace/panel là khung/mặt phẳng, không phải cơ quan — để trống.
KINDS_REQUIRING_ORGAN = frozenset({"tool", "runtime"})

_ID_RE = re.compile(r"^[a-z0-9_][a-z0-9_\-]*\.[a-z0-9_][a-z0-9_\-]*$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")


class ContractError(Exception):
    """Manifest vi phạm contract. Plugin mang lỗi này không được nạp."""

    def __init__(self, plugin_id: str, reason: str) -> None:
        self.plugin_id = plugin_id
        self.reason = reason
        super().__init__(f"plugin {plugin_id or '?'}: {reason}")


@dataclass(frozen=True, slots=True)
class Manifest:
    """Manifest đã qua kiểm. Không có cách dựng một cái sai — dùng `parse_manifest`."""

    id: str
    version: str
    api: int
    kind: str
    organ: str | None
    entry_ui: str | None
    entry_logic: str | None
    grants: frozenset[str] = field(default_factory=frozenset)

    @property
    def needs_model(self) -> bool:
        """Method nào của plugin này cần model thì bus phải chặn khi link không ONLINE."""
        return "model.connect" in self.grants

    @property
    def is_organ(self) -> bool:
        """Có phải cơ quan (Tay/Mắt) của cơ thể không — chỉ tool/runtime."""
        return self.kind in KINDS_REQUIRING_ORGAN


def _require_str(table: dict[str, Any], key: str, where: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(str(table.get("id", "")), f"{where}.{key} thiếu hoặc rỗng")
    return value.strip()


def parse_manifest(path: str | Path) -> Manifest:
    """Đọc một `plugin.toml` và kiểm contract. Ném `ContractError` nếu sai."""
    p = Path(path)
    if not p.is_file():
        raise ContractError(p.parent.name, f"không tìm thấy manifest: {p}")

    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ContractError(p.parent.name, f"plugin.toml không phải TOML hợp lệ: {exc}") from exc

    return parse_manifest_dict(raw, source=str(p))


def parse_manifest_dict(raw: dict[str, Any], *, source: str = "<dict>") -> Manifest:
    """Kiểm một manifest đã parse sẵn. Dùng cho test và cho manifest sinh động."""
    plugin = raw.get("plugin")
    if not isinstance(plugin, dict):
        raise ContractError("", f"{source}: thiếu mục [plugin]")

    pid = plugin.get("id")
    if not isinstance(pid, str) or not _ID_RE.match(pid):
        raise ContractError(
            str(pid),
            f"{source}: id phải có dạng namespace.tên (chữ thường, gạch dưới/gạch ngang)",
        )

    version = plugin.get("version")
    if not isinstance(version, str) or not _VERSION_RE.match(version):
        raise ContractError(pid, f"{source}: version phải là semver (vd 1.2.0), nhận {version!r}")

    api = plugin.get("api")
    # Phải là số nguyên đúng bằng 1. `1.0` hay `True` cũng bị từ chối:
    # trong Python `1.0 == 1` và `True == 1`, nên so sánh bằng không đủ.
    if not isinstance(api, int) or isinstance(api, bool) or api != SUPPORTED_API:
        raise ContractError(
            pid,
            f"{source}: api phải bằng {SUPPORTED_API}, nhận {api!r}. "
            "Host không cố dịch phiên bản contract lạ.",
        )

    kind = plugin.get("kind")
    if kind not in VALID_KINDS:
        raise ContractError(pid, f"{source}: kind phải thuộc {sorted(VALID_KINDS)}, nhận {kind!r}")

    organ = plugin.get("organ")
    if organ is not None and not isinstance(organ, str):
        raise ContractError(pid, f"{source}: organ phải là chuỗi hoặc bỏ trống")
    organ = organ.strip() if isinstance(organ, str) and organ.strip() else None

    if kind in KINDS_REQUIRING_ORGAN:
        if organ not in VALID_ORGANS:
            raise ContractError(
                pid,
                f"{source}: kind={kind} là cơ quan của cơ thể nên BẮT BUỘC khai "
                f"organ thuộc {sorted(VALID_ORGANS)}; nhận {organ!r}. "
                "Thiếu organ → validated thất bại, không nạp.",
            )
    else:
        if organ is not None:
            raise ContractError(
                pid,
                f"{source}: kind={kind} không phải cơ quan nên organ phải trống; "
                f"nhận {organ!r}.",
            )

    entry = raw.get("entry")
    if not isinstance(entry, dict):
        raise ContractError(pid, f"{source}: thiếu mục [entry]")
    entry_ui = entry.get("ui")
    entry_logic = entry.get("logic")
    if not isinstance(entry_ui, str) or not entry_ui.strip():
        entry_ui = None
    else:
        entry_ui = entry_ui.strip()
    if not isinstance(entry_logic, str) or not entry_logic.strip():
        entry_logic = None
    else:
        entry_logic = entry_logic.strip()
    if entry_ui is None and entry_logic is None:
        raise ContractError(
            pid, f"{source}: [entry] phải có ít nhất ui hoặc logic — plugin một mặt cũng được, không mặt nào thì không"
        )

    perms = raw.get("permissions", {})
    if perms is None:
        perms = {}
    if not isinstance(perms, dict):
        raise ContractError(pid, f"{source}: [permissions] phải là bảng")
    grant_raw = perms.get("grant", [])
    if grant_raw is None:
        grant_raw = []
    if not isinstance(grant_raw, list) or any(not isinstance(g, str) for g in grant_raw):
        raise ContractError(pid, f"{source}: permissions.grant phải là danh sách chuỗi")
    grants = frozenset(g.strip() for g in grant_raw if g.strip())

    return Manifest(
        id=pid,
        version=version,
        api=SUPPORTED_API,
        kind=kind,
        organ=organ,
        entry_ui=entry_ui,
        entry_logic=entry_logic,
        grants=grants,
    )
