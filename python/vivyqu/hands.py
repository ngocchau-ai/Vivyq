"""
VivyQu Hands Module (Tay Thực Thi & Điều Khiển Bộ Chấp Hành)
=============================================================
Hiện thực hóa cơ quan vận động / chấp hành của Vivy:
- Tiếp nhận quyết định k* ∈ [0, 4095] từ Não bộ Clifford Cl(12) qua OutputStitchingCodec.
- Bắn trực tiếp và tức thì hành động điều khiển cấu trúc tới Bộ chấp hành (Actuator, Control Interface, Robotic/Agent Environment).

[BẤT BIẾN KIẾN TRÚC]:
Tay là cơ quan chấp hành thuần túy: chuyển tiếp nguyên vẹn quyết định thô từ Não bộ tới môi trường,
tuyệt đối không can thiệp, không gác cổng lập trình cứng, không làm sai lệch ý chí quyết định của AI.
"""

from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, List
import time

from .codec import StructuredAction


@dataclass
class ExecutionReceipt:
    """Biên lai xác nhận thực thi lệnh điều khiển từ cơ quan Tay."""
    action_id: int
    action_type: str
    intensity_level: float
    horizon_scale: float
    parameter_value: float
    execution_latency_us: float
    success: bool
    status_message: str


class VivyquHands:
    """
    Cơ quan Tay thực thi của Vivy:
    - Tiếp nhận StructuredAction từ bộ giải mã quyết định 12-bit.
    - Điều phối trực tiếp tới bộ điều khiển môi trường (Actuator Dispatcher).
    - Bảo đảm zero-overhead, phản xạ tức thì dưới micro-giây.
    """

    def __init__(self, actuator_dispatcher: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None):
        self._dispatcher = actuator_dispatcher
        self._action_counter = 1000
        self._execution_history: List[ExecutionReceipt] = []

    def execute(
        self,
        action: StructuredAction,
        target_subsystem: str = "PRIMARY_ACTUATOR",
    ) -> ExecutionReceipt:
        """
        Thực thi lệnh hành động điều khiển tới bộ chấp hành mục tiêu.
        Tuyệt đối không có bộ lọc cản hay can thiệp logic cứng.
        """
        t0 = time.perf_counter()
        self._action_counter += 1
        action_id = self._action_counter

        # 1. Trạng thái IDLE: Giữ nguyên trạng thái quan sát
        if action.action_type == "IDLE":
            elapsed_us = (time.perf_counter() - t0) * 1e6
            receipt = ExecutionReceipt(
                action_id=action_id,
                action_type="IDLE",
                intensity_level=action.intensity_level,
                horizon_scale=action.horizon_scale,
                parameter_value=action.parameter_value,
                execution_latency_us=elapsed_us,
                success=True,
                status_message="IDLE state maintained as decided by Vivy Brain.",
            )
            self._execution_history.append(receipt)
            return receipt

        # 2. Đóng gói payload hành động điều khiển
        payload = {
            "action_id": action_id,
            "target": target_subsystem,
            "action_type": action.action_type,
            "intensity": action.intensity_level,
            "horizon": action.horizon_scale,
            "parameter": action.parameter_value,
            "confidence": action.confidence,
            "timestamp": time.time(),
        }

        # 3. Chuyển tiếp trực tiếp tới Actuator Dispatcher
        if self._dispatcher is not None:
            try:
                res = self._dispatcher(payload)
                success = res.get("status", 0) == 0
                msg = res.get("message", "Dispatched to Actuator successfully.")
            except Exception as e:
                success = False
                msg = f"Actuator Interface Error: {e}"
        else:
            success = True
            msg = "Dispatched directly to Local Actuator Loop (Zero-Latency Simulation)."

        elapsed_us = (time.perf_counter() - t0) * 1e6
        receipt = ExecutionReceipt(
            action_id=action_id,
            action_type=action.action_type,
            intensity_level=action.intensity_level,
            horizon_scale=action.horizon_scale,
            parameter_value=action.parameter_value,
            execution_latency_us=elapsed_us,
            success=success,
            status_message=msg,
        )

        self._execution_history.append(receipt)
        return receipt

    def clear_history(self):
        """Xóa lịch sử thực thi để giải phóng bộ nhớ."""
        self._execution_history.clear()
