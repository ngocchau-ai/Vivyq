"""
VivyQu Cầu Treo Runtime & Actor Dispatcher Bridge
=================================================
Hiện thực hóa Tầng Điều Phối Thân Thể (Body Process) theo SOUL_BODY_DECOUPLING.md:
- Tiếp nhận vector ngữ cảnh 4096D từ LLM / Vision / Thị trường.
- Khử nhiễu số học, kẹp giá trị an toàn (NaN/Inf Sanitization).
- Tạo và áp dụng Mặt nạ ràng buộc an toàn (Safety Constraint Bitmask).
- Kết nối thông qua Tường Lửa Watchdog Supervisor (Zero Frame-Drop).
- Phát lệnh điều phối tức thì (Action Dispatch) tới hạ tầng thực thi.
"""

import os
import sys
import time
from typing import Optional, List, Callable, Dict, Any, Set
import numpy as np

from .types import (
    CL12_DIMENSION,
    CONSTRAINT_MASK_BYTES,
    DecisionResult,
)
from .watchdog import WatchdogSupervisor


class CautreoDispatcher:
    """Bộ điều phối runtime Cầu Treo kết nối VivyQu Core với thế giới bên ngoài."""

    def __init__(
        self,
        watchdog: WatchdogSupervisor,
        action_callback: Optional[Callable[[int, float, float], None]] = None,
    ):
        self.watchdog = watchdog
        self.action_callback = action_callback
        self.total_dispatched = 0
        self.total_dispatch_time_us = 0.0

    def dispatch(
        self,
        context_vector: np.ndarray,
        allowed_actions: Optional[List[int]] = None,
        constraint_mask_bytes: Optional[np.ndarray] = None,
    ) -> DecisionResult:
        """
        Tiếp nhận ngữ cảnh, lọc an toàn, ra quyết định và phát lệnh thực thi.
        Thời gian hoàn thành cam kết: < 15.0 µs.
        """
        t0 = time.perf_counter()

        # 1. Khử rác số học NaN / ±Inf
        if np.isnan(context_vector).any() or np.isinf(context_vector).any():
            context_vector = np.nan_to_num(context_vector, nan=0.0, posinf=10.0, neginf=-10.0)

        # 2. Xử lý mặt nạ ràng buộc an toàn
        mask_to_use = None
        if constraint_mask_bytes is not None:
            mask_to_use = constraint_mask_bytes
        elif allowed_actions is not None:
            mask_bool = np.zeros(CL12_DIMENSION, dtype=bool)
            for a in allowed_actions:
                if 0 <= a < CL12_DIMENSION:
                    mask_bool[a] = True
            mask_to_use = np.packbits(mask_bool, bitorder='little')

        # 3. Ra quyết định qua Tường Lửa Watchdog (Bảo đảm Zero Frame-Drop)
        res = self.watchdog.step(
            latent_vector=context_vector,
            constraint_mask=mask_to_use,
        )

        t_end = time.perf_counter()
        total_time_us = (t_end - t0) * 1e6
        self.total_dispatched += 1
        self.total_dispatch_time_us += total_time_us

        # 4. Kích hoạt Callback điều phối tới hạ tầng bên dưới (Godot / Actor / MT5 Hands)
        if self.action_callback is not None:
            self.action_callback(res.best_index, res.confidence, total_time_us)

        return res

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Trích xuất báo cáo giám sát SLA vận hành."""
        stats = self.watchdog.flight_recorder.get_stats()
        stats["total_dispatched_cautreo"] = self.total_dispatched
        stats["avg_dispatcher_latency_us"] = (
            self.total_dispatch_time_us / max(1, self.total_dispatched)
        )
        stats["circuit_breaker_current_state"] = self.watchdog.state.value
        return stats
