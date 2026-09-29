"""tool.fs-write — Tay. Ghi file trong workspace.

Plugin này là chỗ minh hoạ nhãn `derived`: truyền `based_on = "rc-0003"` thì
kết quả được coi là suy ra từ receipt đó, và host tự gắn nhãn `derived`. Plugin
không viết từ "derived" ra ở đâu cả — viết ra cũng bị gỡ.
"""

from __future__ import annotations

from typing import Any


def create_plugin() -> Plugin:
    return Plugin()


class Plugin:
    method_grants = {"run": ["fs.workspace"]}

    def run(self, ctx: Any = None, **params: Any) -> dict[str, Any]:
        path = params.get("path")
        if not isinstance(path, str) or not path.strip():
            return {"summary": "thiếu đường dẫn", "error": "cần tham số path"}
        text = params.get("text")
        if not isinstance(text, str):
            text = ""
        assert ctx is not None, "bus phải cấp ctx"

        based_on = params.get("based_on")
        if isinstance(based_on, str) and based_on.strip():
            ctx.derive_from(based_on.strip())

        written = ctx.fs.write(path, text)
        return {
            "summary": f"đã ghi {path} ({written} ký tự)",
            "path": path,
            "written": written,
        }
