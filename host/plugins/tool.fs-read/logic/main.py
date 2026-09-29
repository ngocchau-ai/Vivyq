"""tool.fs-read — Mắt. Đọc file trong workspace.

Nhãn nguồn của kết quả là `tool-local`: đọc đĩa không phải là việc của model.
Nếu mai này plugin này hỏi model để tóm tắt, chỉ cần chạm `ctx.model` — nhãn
tự đổi theo sổ, không phải sửa một dòng nào ở đây.
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
        assert ctx is not None, "bus phải cấp ctx"
        text = ctx.fs.read(path)
        return {
            "summary": f"đã đọc {path} ({len(text)} ký tự)",
            "path": path,
            "text": text,
        }
