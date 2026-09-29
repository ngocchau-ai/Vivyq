"""Bộ chấm dùng chung — plugin bên thứ ba chấm bằng đúng bộ này (spec §7.3.1).

Plugin bên thứ ba không phải chép test của host. Chỉ cần trỏ testkit vào thư mục
plugin, nó sẽ chấm đúng những điều host tự chấm mình:

  1. manifest hợp lệ theo contract (`api = 1`, `organ` đúng luật, có mặt logic/ui)
  2. file entry khai trong manifest **thật sự tồn tại**
  3. `permissions.grant` phải nằm trong bảng host có năng lực tương ứng
  4. plugin nạp được qua đúng đường `PluginRegistry` của host
  5. `method_grants` mà instance khai phải nằm trọn trong `permissions.grant`
     của manifest — thiếu là fail, vì host sẽ chặn ở biên method

Không có mục nào "chấm cảm tính". Mỗi mục trả về `ok` và một câu `detail` nói
rõ vì sao hỏng, để tác giả plugin biết phải sửa gì.

Cách dùng trong test của plugin bạn:

    from pathlib import Path
    from testkit import assert_plugin_ok

    def test_contract():
        assert_plugin_ok(Path(__file__).parent / "my-plugin")
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cautreo_host.manifest import ContractError, parse_manifest
from cautreo_host.registry import PluginRegistry

# Host chỉ có chừng này năng lực. Bảng lặp lại CAPABILITY_GRANTS của provenance
# để testkit không đòi plugin phải hiểu sâu nội bộ host.
KNOWN_GRANTS = frozenset(
    {"model.connect", "cautreo.access", "fs.workspace", "tool.local"}
)


@dataclass(frozen=True)
class Check:
    """Một mục chấm. `detail` luôn nói được tại sao `ok` là False."""

    name: str
    ok: bool
    detail: str = ""

    def __str__(self) -> str:
        mark = "OK  " if self.ok else "FAIL"
        tail = f" — {self.detail}" if self.detail else ""
        return f"[{mark}] {self.name}{tail}"


def _check_manifest(plugin_dir: Path) -> tuple[list[Check], bool]:
    """Mục 1–3. Trả về (các mục, manifest có đọc được không)."""
    out: list[Check] = []
    try:
        m = parse_manifest(plugin_dir / "plugin.toml")
    except ContractError as exc:
        return (
            [
                Check("manifest hợp lệ", False, str(exc)),
                Check("file entry có mặt", False, "manifest hỏng nên chưa kiểm"),
                Check("grant nằm trong bảng host biết", False, "manifest hỏng nên chưa kiểm"),
            ],
            False,
        )

    out.append(Check("manifest hợp lệ", True, f"{m.id} v{m.version} · {m.kind}/{m.organ or '-'}"))

    missing = [
        face
        for face, rel in (("ui", m.entry_ui), ("logic", m.entry_logic))
        if rel and not (plugin_dir / rel).is_file()
    ]
    if missing:
        out.append(
            Check("file entry có mặt", False, f"thiếu file cho mặt {', '.join(missing)}")
        )
    else:
        faces = [f for f, rel in (("ui", m.entry_ui), ("logic", m.entry_logic)) if rel]
        out.append(Check("file entry có mặt", True, f"đủ mặt {', '.join(faces)}"))

    unknown = sorted(m.grants - KNOWN_GRANTS)
    if unknown:
        out.append(
            Check(
                "grant nằm trong bảng host biết",
                False,
                f"host không có năng lực nào tương ứng với {unknown}",
            )
        )
    else:
        listed = ", ".join(sorted(m.grants)) or "(không xin quyền nào)"
        out.append(Check("grant nằm trong bảng host biết", True, listed))
    return out, True


def _check_runtime(plugin_dir: Path) -> list[Check]:
    """Mục 4 + 5. Nạp qua đúng đường registry, rồi soi `method_grants`."""
    checks: list[Check] = []
    root = plugin_dir.parent
    want = plugin_dir.resolve()

    reg = PluginRegistry()
    try:
        recs = reg.discover(root)
    except Exception as exc:
        msg = f"không quét được {root}: {type(exc).__name__}: {exc}"
        return [
            Check("nạp được qua PluginRegistry", False, msg),
            Check("method_grants nằm trong permissions.grant", False, msg),
        ]

    rec = next((r for r in recs if r.path.resolve() == want), None)
    if rec is None:
        msg = f"không tìm thấy manifest hợp lệ trong {plugin_dir}"
        return [
            Check("nạp được qua PluginRegistry", False, msg),
            Check("method_grants nằm trong permissions.grant", False, msg),
        ]
    if rec.error:
        msg = f"vi phạm contract: {rec.error}"
        return [
            Check("nạp được qua PluginRegistry", False, msg),
            Check("method_grants nằm trong permissions.grant", False, msg),
        ]

    try:
        reg.validate(rec.id)
        reg.load(rec.id)
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        return [
            Check("nạp được qua PluginRegistry", False, msg),
            Check("method_grants nằm trong permissions.grant", False, msg),
        ]

    checks.append(
        Check("nạp được qua PluginRegistry", True, f"state = {rec.state.name}, id = {rec.id}")
    )

    # Plugin một mặt UI không có instance — không có gì để vượt quyền.
    declared = getattr(rec.instance, "method_grants", None) or {}
    over = [
        f"{method} cần {need!r}"
        for method, needs in declared.items()
        for need in needs
        if need not in rec.manifest.grants
    ]
    name = "method_grants nằm trong permissions.grant"
    if over:
        checks.append(Check(name, False, "vượt manifest: " + "; ".join(over)))
    else:
        total = sum(len(v) for v in declared.values())
        checks.append(
            Check(name, True, f"{len(declared)} method / {total} grant đã khai, không vượt")
        )
    return checks


def grade_plugin(plugin_dir: Path | str) -> list[Check]:
    """Chấm một plugin. Trả về từng mục — không ném, để gọi được từ CI."""
    plugin_dir = Path(plugin_dir)
    if not plugin_dir.is_dir():
        return [Check("plugin là thư mục", False, f"{plugin_dir} không tồn tại")]

    out = [Check("plugin là thư mục", True, str(plugin_dir))]
    manifest_checks, ok = _check_manifest(plugin_dir)
    out += manifest_checks
    if ok:
        out += _check_runtime(plugin_dir)
    return out


def format_report(checks: list[Check]) -> str:
    return "\n".join(str(c) for c in checks)


def assert_plugin_ok(plugin_dir: Path | str) -> None:
    """Chấm và ném `AssertionError` liệt kê mục hỏng. Dùng thẳng trong pytest."""
    checks = grade_plugin(plugin_dir)
    bad = [c for c in checks if not c.ok]
    if bad:
        raise AssertionError(
            f"plugin {plugin_dir} trượt {len(bad)}/{len(checks)} mục:\n" + format_report(bad)
        )
