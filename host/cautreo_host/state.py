"""Máy trạng thái liên kết — Thanh Thân thể đọc từ đây.

    BOOTING → LINKING → ONLINE ⇄ DEGRADED
                        ⇅
                      OFFLINE

Quy tắc cứng (spec D9 + Gate 9):
- `DEGRADED` **không** có đường sang `OFFLINE`. OFFLINE là lựa chọn của người dùng,
  đi thẳng từ ONLINE; DEGRADED là trạng thái hỏng — không phải trạng thái người chọn.
- Khi không phải ONLINE, lệnh cần model bị **từ chối kèm lý do**. Tuyệt đối không
  sinh ra câu trả lời thay cho model.
- `reason` phải thuộc bảng `REASONS` — không có "lý do khác" mơ hồ.
"""

from __future__ import annotations

from enum import StrEnum


class LinkState(StrEnum):
    BOOTING = "BOOTING"
    LINKING = "LINKING"
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


# Bảng lý do đóng. Khóa là hợp đồng (UI hiển thị khóa thu gọn), chuỗi là lời người.
REASONS: dict[str, str] = {
    "endpoint_unreachable": "không nối được endpoint",
    "model_mismatch": "model không khớp",
    "engine_unavailable": "engine chưa sẵn sàng",
    "permission_denied": "thiếu quyền",
}

# Chuyển trạng thái được phép.
_TRANSITIONS: dict[LinkState, frozenset[LinkState]] = {
    LinkState.BOOTING: frozenset({LinkState.LINKING}),
    LinkState.LINKING: frozenset({LinkState.ONLINE, LinkState.DEGRADED}),
    LinkState.ONLINE: frozenset({LinkState.DEGRADED, LinkState.OFFLINE}),
    LinkState.DEGRADED: frozenset({LinkState.ONLINE}),
    LinkState.OFFLINE: frozenset({LinkState.ONLINE}),
}


class LinkError(Exception):
    """Chuyển trạng thái không hợp lệ, hoặc lý do không có trong bảng."""


class LinkMachine:
    """Một đường liên kết tới model. Không sinh kết quả — chỉ nói đang sống hay không."""

    def __init__(self, *, model: str | None = None) -> None:
        # Tên model để `None` cho tới khi **đọc được từ server**. Không có giá trị
        # mặc định nào ở đây — host không được khai tên model mà nó chưa thấy.
        self._state = LinkState.BOOTING
        self._reason: str | None = None
        self._model = model

    # ---- đọc ----

    @property
    def state(self) -> LinkState:
        return self._state

    @property
    def reason(self) -> str | None:
        """Khóa lý do (vd `endpoint_unreachable`), hoặc None khi đang ONLINE/OFFLINE."""
        return self._reason

    @property
    def reason_text(self) -> str | None:
        return REASONS.get(self._reason) if self._reason else None

    @property
    def model(self) -> str | None:
        """Tên model **đã đọc được từ server**, hoặc None nếu chưa xác minh."""
        return self._model

    def set_model(self, name: str | None) -> None:
        """Ghi tên model khi đã đọc được từ server. `None` nghĩa là chưa biết."""
        self._model = name or None

    @property
    def is_online(self) -> bool:
        return self._state is LinkState.ONLINE

    @property
    def allows_model(self) -> bool:
        """Có được gọi model không. Chỉ ONLINE. Không có ngoại lệ."""
        return self._state is LinkState.ONLINE

    def snapshot(self) -> dict[str, str | None]:
        """Khối trạng thái gửi qua bus cho UI. Không bịa trường nào."""
        return {
            "link": self._state.value,
            "reason": self._reason,
            "reason_text": self.reason_text,
            "model": self._model if self._state is not LinkState.OFFLINE else None,
        }

    # ---- chuyển ----

    def boot(self) -> None:
        self._move(LinkState.LINKING)

    def come_online(self) -> None:
        self._move(LinkState.ONLINE, clear_reason=True)

    def lost(self, reason: str) -> None:
        """Rơi sang DEGRADED. Phải nêu đúng lý do trong bảng."""
        if reason not in REASONS:
            raise LinkError(
                f"lý do {reason!r} không có trong bảng {sorted(REASONS)}"
            )
        self._reason = reason
        self._move(LinkState.DEGRADED)

    def healed(self) -> None:
        """DEGRADED → ONLINE."""
        self._move(LinkState.ONLINE, clear_reason=True)

    def go_offline(self) -> None:
        """Người dùng ngắt. Chỉ đi từ ONLINE — không có DEGRADED → OFFLINE."""
        self._move(LinkState.OFFLINE, clear_reason=True)

    def come_back(self) -> None:
        self._move(LinkState.ONLINE, clear_reason=True)

    def refuse_model(self) -> str:
        """Lý do từ chối lệnh cần model, dành cho bus dựng thông báo lỗi.

        Phải trả đúng lý do thật. Không bịa lý do khi ta không biết.
        """
        if self._state is LinkState.ONLINE:
            raise LinkError("đang ONLINE, không có gì để từ chối")
        if self._state is LinkState.DEGRADED:
            return REASONS.get(self._reason or "", "đang degraded")
        if self._state is LinkState.OFFLINE:
            return "người dùng đã ngắt model"
        return f"link đang ở {self._state.value}"

    # ---- nội bộ ----

    def _move(self, to: LinkState, *, clear_reason: bool = False) -> None:
        if to not in _TRANSITIONS[self._state]:
            raise LinkError(f"{self._state.value} → {to.value} không hợp lệ")
        self._state = to
        if clear_reason:
            self._reason = None
