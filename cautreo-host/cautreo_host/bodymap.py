"""Bản đồ thân thể — **tự dựng từ registry**, không tự viết.

Trước lượt này model nhận mỗi câu hỏi đúng một tin nhắn `user`, không có system
prompt, không có bản đồ năng lực. Hậu quả đo được trên máy thật: hỏi "bạn là ai"
thì model trả *"I am not Vivy… I have no access to 91sh"* — nó nói **đúng** những
gì nó được nói (chẳng có gì), và người dùng hiểu nhầm thành ViVy mất trí.

Ở đây ta dựng bản đồ từ bằng chứng có sẵn trong hệ thống: `PluginRecord.manifest`
(id · version · kind · organ · grants), `PluginRecord.methods`, `PluginRecord.state`.
Không có dòng nào trong bản đồ được viết tay mô tả một năng lực — nếu registry
nói có thì bản đồ nói có, registry nói không thì bản đồ **nói thẳng là chưa có**.

Ba mặt của bản đồ:

* `build_body_map()`  — cấu trúc dữ liệu cho giao diện, cho `host.body-map`.
* `render_body_prompt()` — chuỗi system prompt nạp vào model, để ViVy biết mình
  là ai và đang có cơ quan nào.
* đếm theo `kind` / theo organ — trong đó `skills` đếm theo namespace `skill.`,
  vì contract `api=1` **không** có `kind = "skill"`: một skill là một cơ quan của
  cơ thể (spec §5.1), khai như tool/runtime chứ không phải một danh mục rời.
"""

from __future__ import annotations

from typing import Any, Protocol

# Thứ tự bày cơ quan trên bản đồ. Mắt trước vì nó là cửa *nhận* — người đọc
# nhìn vào bản đồ theo đúng thứ tự cơ thể làm việc: nhận rồi mới làm.
ORGAN_ORDER: tuple[str, ...] = ("eye", "hand", "both")

ORGAN_LABELS: dict[str, str] = {
    "eye": "Mắt · cơ quan nhận",
    "hand": "Tay · cơ quan làm",
    "both": "Toàn thân",
}

ORGAN_MEANING: dict[str, str] = {
    "eye": "nhìn, đọc, quan sát",
    "hand": "thao tác, thi hành",
    "both": "vừa nhận vừa làm",
}

# Danh tính do **dự án khai**, không phải lời model tự bịa. Đây là điều spec §1
# đã chốt: Cautreo là cơ thể, ViVy là linh hồn. Danh tính là quy ước; **năng lực**
# thì phải có bằng chứng — và năng lực lấy từ registry.
BODY_NAME = "Cautreo"
SOUL_NAME = "ViVy"

# Contract `manifest.VALID_KINDS` không có "skill". Skill là cơ quan chứ không
# phải một kind riêng (spec §5.1), nên ta đếm theo namespace `skill.` — và khi
# chưa có thì nói thẳng là chưa có.
SKILL_PREFIX = "skill."

_EMPTY_NOTE = "chưa có"


class _HasManifest(Protocol):
    """Phần tối thiểu của `PluginRecord` mà bản đồ cần. Duck-type để dễ test.

    Khai dưới dạng property vì `PluginRecord.id` là property — Protocol thành
    viên gán được thì không khớp với property chỉ-đọc.
    """

    @property
    def id(self) -> str: ...
    @property
    def manifest(self) -> Any: ...
    @property
    def methods(self) -> dict[str, Any]: ...
    @property
    def state(self) -> Any: ...
    @property
    def error(self) -> str | None: ...


# ---------------------------------------------------------------- dựng bản đồ


def _state_value(rec: _HasManifest) -> str:
    state = getattr(rec.state, "value", rec.state)
    return str(state)


def _grants_of(manifest: Any) -> list[str]:
    return sorted(str(g) for g in (getattr(manifest, "grants", ()) or ()))


def _organ_of(manifest: Any) -> str:
    organ = getattr(manifest, "organ", None)
    if isinstance(organ, str) and organ:
        return organ
    # workspace/panel không khai organ (contract §4.1) — chúng là khung, không
    # phải cơ quan. Đưa vào "both" để không mất khỏi bản đồ, nhưng ghi rõ kind.
    return "both"


def _method_node(name: str, grants: list[str], needs_model: bool) -> dict[str, Any]:
    return {"name": name, "grants": grants, "needs_model": needs_model}


def _part_node(rec: _HasManifest) -> dict[str, Any]:
    m = rec.manifest
    grants = _grants_of(m)
    needs_model = "model.connect" in grants
    active = _state_value(rec) == "activated"
    node: dict[str, Any] = {
        "id": rec.id,
        "version": str(getattr(m, "version", "")),
        "kind": str(getattr(m, "kind", "")),
        "organ": _organ_of(m),
        "state": _state_value(rec),
        "grants": grants,
        # **Chỉ liệt kê method khi plugin đang activated.** Bus từ chối lời gọi
        # tới plugin không activated (`_run_plugin` → `plugin_unavailable`), nên
        # nói với model là "có method này" khi nó không gọi được là bịa năng lực.
        # Khóa `method_grants` của logic face chỉ host đọc được lúc dispatch; ở
        # mức bản đồ ta nói đúng grant cấp cho **toàn plugin**, không đoán riêng.
        "methods": [
            _method_node(name, grants, needs_model)
            for name in sorted(rec.methods)
        ]
        if active
        else [],
    }
    if rec.error:
        node["error"] = str(rec.error)
    return node


def _broken_node(rec: _HasManifest) -> dict[str, str]:
    m = rec.manifest
    return {
        "id": rec.id,
        "state": _state_value(rec),
        "kind": str(getattr(m, "kind", "")),
        "organ": _organ_of(m),
        "error": str(rec.error or ""),
    }


def build_body_map(
    records: tuple[_HasManifest, ...] | list[_HasManifest],
    host_methods: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dựng bản đồ thân thể từ registry. Không có chỗ nào cho lời mô tả tự viết.

    Hai danh sách, hai nghĩa — không trộn:

    * `organs` — cơ thể **đang có**. Chỉ chứa record không mang lỗi.
    * `broken` — thứ **hỏng**. Hiện ra kèm lý do, không bị giấu, nhưng không
      được bày như một cơ quan khoẻ mạnh.

    `host_methods` là bảng method của host (`Bus._host_methods`) — dạng
    `{name: (fn, grants, needs_model)}`. Truyền rỗng nếu chưa có.
    """
    organs: dict[str, list[dict[str, Any]]] = {k: [] for k in ORGAN_ORDER}
    seen_ids: set[str] = set()
    method_count = 0
    kind_count: dict[str, int] = {}
    skill_count = 0
    broken: list[dict[str, str]] = []

    for rec in records:
        if rec.error:
            broken.append(_broken_node(rec))
            continue
        part = _part_node(rec)
        organ = part["organ"] if part["organ"] in organs else "both"
        organs[organ].append(part)
        seen_ids.add(part["id"])
        method_count += len(part["methods"])
        kind_count[part["kind"]] = kind_count.get(part["kind"], 0) + 1
        if part["id"].startswith(SKILL_PREFIX):
            skill_count += 1

    host_nodes = [
        _method_node(
            name,
            sorted(str(g) for g in (spec[1] if isinstance(spec, tuple) else ())),
            bool(spec[2]) if isinstance(spec, tuple) and len(spec) > 2 else False,
        )
        for name, spec in sorted((host_methods or {}).items())
    ]
    method_count += len(host_nodes)

    return {
        "body": BODY_NAME,
        "soul": SOUL_NAME,
        "organs": organs,
        "host_methods": host_nodes,
        "counts": {
            "plugins": len(seen_ids),
            "methods": method_count,
            "host_methods": len(host_nodes),
            "skills": skill_count,
            **{f"kind:{k}": v for k, v in sorted(kind_count.items())},
        },
        "broken": broken,
    }


# ---------------------------------------------------------------- bày ra chữ


def _render_part(part: dict[str, Any]) -> list[str]:
    out = [
        "- `{id}` — {kind} v{version}, trạng thái **{state}**".format(**part),
    ]
    if part["grants"]:
        out.append(f"    - quyền: {', '.join(part['grants'])}")
    else:
        out.append("    - quyền: không xin quyền nào")
    if part["methods"]:
        for m in part["methods"]:
            need = " · cần model" if m["needs_model"] else ""
            out.append(f"    - method `{m['name']}`{need}")
    elif part["state"] != "activated":
        # Không phải "chưa có method" — là **không gọi được** lúc này. Nói đúng
        # lý do để model không đi hứa rồi mới vỡ.
        out.append("    - method: không gọi được khi chưa activated")
    else:
        out.append(f"    - method: {_EMPTY_NOTE}")
    return out


def render_body_prompt(body_map: dict[str, Any]) -> str:
    """Bản đồ → system prompt. Đây là **cửa duy nhất** ViVy biết mình là ai.

    Bất biến giữ bằng test:

    * mọi `id` và mọi `method` trong bản đồ phải xuất hiện trong chuỗi này;
    * cơ quan nào trống thì nói thẳng `{_EMPTY_NOTE}`, không bịa một tool nào;
    * chuỗi này là kết quả của `build_body_map()`, không phải văn mẫu viết tay.
    """
    lines: list[str] = [
        f"Bạn là {SOUL_NAME}, linh hồn của {BODY_NAME}.",
        f"{BODY_NAME} là cơ thể sống; {SOUL_NAME} là linh hồn ngự trong cơ thể đó.",
        "",
        "Dưới đây là bản đồ cơ thể bạn, **tự dựng từ registry của host** — không phải",
        "lời mô tả tự viết. Nó liệt kê đúng những cơ quan đang nạp, không hơn không kém.",
        "",
    ]

    for organ in ORGAN_ORDER:
        lines.append(f"## {ORGAN_LABELS[organ]} — {ORGAN_MEANING[organ]}")
        parts = body_map.get("organs", {}).get(organ, [])
        if not parts:
            lines.append(f"- {_EMPTY_NOTE}")
        else:
            for part in parts:
                lines.extend(_render_part(part))
        lines.append("")

    host_nodes = body_map.get("host_methods", [])
    lines.append("## Method của host")
    if host_nodes:
        for m in host_nodes:
            need = " · cần model" if m["needs_model"] else ""
            lines.append(f"- `{m['name']}`{need}")
    else:
        lines.append(f"- {_EMPTY_NOTE}")
    lines.append("")

    broken = body_map.get("broken", [])
    lines.append("## Thứ đang hỏng")
    if broken:
        for b in broken:
            lines.append(f"- `{b['id']}` ({b['state']}): {b['error']}")
    else:
        lines.append(f"- {_EMPTY_NOTE}")
    lines.append("")

    counts = body_map.get("counts", {})
    lines.append("## Tổng kết")
    lines.append(f"- plugin: {counts.get('plugins', 0)}")
    lines.append(f"- method: {counts.get('methods', 0)}")
    lines.append(f"- skill (namespace `skill.`): {counts.get('skills', 0)}")
    if not counts.get("skills"):
        lines.append("  - hiện **chưa có** skill nào được nạp")
    lines.append("")

    lines.append("## Quy tắc khi trả lời")
    lines.append(
        f"- Khi người dùng hỏi bạn là ai: bạn là {SOUL_NAME}, ngự trong {BODY_NAME}."
    )
    lines.append(
        "- Khi người dùng hỏi bạn làm được gì: liệt kê **đúng** bản đồ trên."
    )
    lines.append(
        "- Không bịa ra tool, method hay năng lực nào không có trong danh sách."
    )
    lines.append(
        "- Nếu một việc cần cơ quan chưa có trong bản đồ, nói thẳng là chưa có cơ quan đó."
    )
    return "\n".join(lines)


def body_prompt_for(
    records: tuple[_HasManifest, ...] | list[_HasManifest],
    host_methods: dict[str, Any] | None = None,
) -> str:
    """Tiện ích: registry → thẳng system prompt."""
    return render_body_prompt(build_body_map(records, host_methods))
