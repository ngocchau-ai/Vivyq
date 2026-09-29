"""vivy.runtime — runtime plugin, mặt logic.

Đây là chỗ cơ chế "runtime được đăng ký method động" (D5) thành hiện thực:
`activate(api)` gọi `api.register_method(...)`, host ghi vào bảng bus.

**Không có model nào được cắm sẵn.** Host không biết model là gì (D3). Khi
`ctx.model.complete(...)` chạy mà chưa có backend, nó ném lỗi thật — và bus trả
`-32002 plugin_error` kèm lý do. Tuyệt đối không có câu trả lời giả nào được sinh
ra để lấp chỗ trống. Cắm model thật vào bằng cách cấp `CallContext(_backends={"model": ...})`.
"""

from __future__ import annotations

from typing import Any


def _text_of(out: Any) -> str:
    """Lấy đúng lời model nói ra khỏi phản hồi của backend.

    Backend trả `{"text": ..., "model": ...}`. Nếu shape khác thì **giữ nguyên
    bản in** của nó — không bịa một câu tóm tắt thay cho nội dung thật.
    """
    if isinstance(out, str):
        return out
    if isinstance(out, dict):
        for key in ("text", "answer", "content"):
            value = out.get(key)
            if isinstance(value, str):
                return value
    return repr(out)


def _parts_of(out: Any) -> tuple[str, list[str], str]:
    """Ba mặt của một lời model nói: `answer` · `thinking` · `raw`.

    Backend đã tách sẵn (`split_model_channels`). Plugin **không tự cắt xén**
    chữ của model ở đây — nếu backend trả shape khác thì nguyên khối rơi vào
    `answer`, phần suy nghĩ để rỗng. Thà bày hết ra còn hơn giấu mất chữ.
    """
    if isinstance(out, str):
        return out, [], out
    if not isinstance(out, dict):
        text = repr(out)
        return text, [], text

    raw = out.get("raw")
    if not isinstance(raw, str):
        raw = out.get("text") if isinstance(out.get("text"), str) else _text_of(out)

    answer = out.get("answer")
    if not isinstance(answer, str):
        answer = raw

    thinking = out.get("thinking")
    if not isinstance(thinking, list):
        thinking = []
    return answer, [t for t in thinking if isinstance(t, str)], raw


def create_plugin() -> Plugin:
    return Plugin()


class Plugin:
    # Khóa là tên method ngắn (phần sau `vivy.runtime/`).
    method_grants = {
        "ask": ["model.connect"],
        "recall": ["cautreo.access"],
        "digest": ["model.connect", "cautreo.access"],
    }

    def activate(self, api: Any = None) -> None:
        if api is None:
            return
        api.register_method("ask", self.ask)
        api.register_method("recall", self.recall)
        api.register_method("digest", self.digest)

    def deactivate(self) -> None:
        # Không giữ tài nguyên nào, nhưng hook phải có mặt để vòng đời trọn vẹn.
        return None

    def ask(self, ctx: Any = None, **params: Any) -> dict[str, Any]:
        prompt = params.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return {"summary": "thiếu lời hỏi", "error": "cần tham số prompt"}
        assert ctx is not None
        out = ctx.model.complete(prompt)
        answer, thinking, raw = _parts_of(out)
        return {
            "summary": "đã hỏi model",
            # `answer` là câu trả lời; `thinking` là các đoạn lập luận để giao
            # diện bày thu gọn. `raw` giữ nguyên vẹn — không chữ nào bị ném đi.
            "answer": answer,
            "thinking": thinking,
            "raw": raw,
            "detail": out if isinstance(out, dict) else None,
        }

    def recall(self, ctx: Any = None, **params: Any) -> dict[str, Any]:
        key = params.get("key")
        if not isinstance(key, str) or not key.strip():
            return {"summary": "thiếu khoá", "error": "cần tham số key"}
        assert ctx is not None
        memory = ctx.cautreo.recall(key)
        return {"summary": f"đã tra trí nhớ {key}", "memory": memory}

    def digest(self, ctx: Any = None, **params: Any) -> dict[str, Any]:
        """Đọc trí nhớ rồi hỏi model. Tiêu thụ receipt → host gắn nhãn `derived`."""
        key = params.get("key")
        if not isinstance(key, str) or not key.strip():
            return {"summary": "thiếu khoá", "error": "cần tham số key"}
        assert ctx is not None

        based_on = params.get("based_on")
        if isinstance(based_on, str) and based_on.strip():
            ctx.derive_from(based_on.strip())

        memory = ctx.cautreo.recall(key)
        out = ctx.model.complete(str(memory))
        answer, thinking, raw = _parts_of(out)
        return {
            "summary": f"đã tiêu hoá trí nhớ {key}",
            "memory": memory,
            "answer": answer,
            "thinking": thinking,
            "raw": raw,
            "detail": out if isinstance(out, dict) else None,
        }
