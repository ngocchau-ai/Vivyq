"""Receipt — đơn vị tin cậy của hệ thống.

"Đo bằng receipt, không đo bằng lời." Không có receipt thì không được nói đã làm.
Mỗi lời gọi đi qua bus sinh đúng một receipt: id, cơ quan, lệnh, kết quả, thời
gian, nhãn nguồn — nhãn nguồn do host gán, xem `provenance.py`.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .provenance import ALL_SOURCES, SOURCE_TOOL_LOCAL


class ReceiptError(Exception):
    """Receipt không hợp lệ — ví dụ nhãn nguồn không có trong bảng."""


@dataclass(frozen=True, slots=True)
class Receipt:
    """Một biên nhận. Bất biến sau khi sinh — không ai sửa được nhãn nguồn."""

    id: str
    organ: str
    command: str
    result: str
    at: str
    source: str

    def __post_init__(self) -> None:
        if self.source not in ALL_SOURCES:
            raise ReceiptError(
                f"nhãn nguồn {self.source!r} không có trong bảng {list(ALL_SOURCES)}"
            )
        if not self.id:
            raise ReceiptError("receipt thiếu id")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class ReceiptLog:
    """Nhật ký receipt. Nơi duy nhất lưu kết quả đã được chứng nhận."""

    def __init__(self) -> None:
        self._items: list[Receipt] = []
        self._seq = itertools.count(1)

    def record(
        self,
        *,
        organ: str,
        command: str,
        result: str,
        source: str = SOURCE_TOOL_LOCAL,
    ) -> Receipt:
        receipt = Receipt(
            id=f"rc-{next(self._seq):04d}",
            organ=organ,
            command=command,
            result=result,
            at=datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            source=source,
        )
        self._items.append(receipt)
        return receipt

    def all(self) -> tuple[Receipt, ...]:
        return tuple(self._items)

    def by_source(self, source: str) -> tuple[Receipt, ...]:
        return tuple(r for r in self._items if r.source == source)

    def get(self, receipt_id: str) -> Receipt | None:
        for r in self._items:
            if r.id == receipt_id:
                return r
        return None

    def clear(self) -> None:
        self._items.clear()


def now_ms() -> int:
    """Thời gian thật, tính bằng mili giây. Không bịa timestamp."""
    return int(time.time() * 1000)
