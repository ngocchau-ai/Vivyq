"""
VivyQu Sensory & Action Codecs
==============================
Hiện thực hóa 2 codec cốt lõi cho kiến trúc nhận thức tổng quát của Vivy:
1. InputSplittingCodec: Phân tách và chuẩn hóa không gian đặc trưng 4x1024D = 4096D (12-qubit manifold).
2. OutputStitchingCodec: Giải mã quyết định 12-bit (k* ∈ [0, 4095]) thành lệnh hành động cấu trúc (Motor Action).

[GHI CHÚ KIẾN TRÚC]: Hoàn toàn độc lập với mọi domain cụ thể, không gắn với bất kỳ nền tảng tài chính nào.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np

from .types import CL12_DIMENSION


@dataclass(frozen=True)
class StructuredAction:
    """Lệnh hành động cấu trúc tổng quát được giải mã từ chỉ số k* 12-bit."""
    best_index: int              # Chỉ số k* gốc [0..4095]
    confidence: float            # Biên độ xác suất sụp đổ
    action_intent_id: int        # Bits 0..2 (0..7)
    action_type: str             # Tên chế độ hành động (IDLE, ENGAGE, PIVOT, ...)
    intensity_tier_id: int       # Bits 3..5 (0..7)
    intensity_level: float       # Mức năng lượng / cường độ điều khiển [0.125 .. 1.0]
    horizon_tier_id: int         # Bits 6..8 (0..7)
    horizon_scale: float         # Thang thời gian / độ dài dự phóng [0.5x .. 5.0x]
    parameter_tier_id: int       # Bits 9..11 (0..7)
    parameter_value: float       # Hệ số tinh chỉnh không gian [0.5 .. 4.0]
    is_valid: bool = True        # Tính hợp lệ


class OutputStitchingCodec:
    """
    Bộ giải mã quyết định 12-bit (Output Stitching Codec).
    Giải mã k* ∈ [0, 4095] thành 4 trường tham số điều khiển 3-bit:
    - Bits 0..2: Action Mode (8 chế độ vận động)
    - Bits 3..5: Intensity Tier (8 cấp độ cường độ tác động)
    - Bits 6..8: Horizon Scale Tier (8 thang thời gian dự phóng)
    - Bits 9..11: Spatial Parameter Tier (8 mức tinh chỉnh không gian)
    """
    ACTION_NAMES = [
        "IDLE",               # 0: Giữ nguyên trạng thái / quan sát
        "ENGAGE_PRIMARY",     # 1: Tác động trực diện chế độ 1
        "ENGAGE_SECONDARY",   # 2: Tác động phụ trợ chế độ 2
        "PIVOT_STATE",        # 3: Chuyển hướng trạng thái vận động
        "RECALIBRATE",        # 4: Tự hiệu chuẩn lại tham số
        "PARTIAL_RELEASE",    # 5: Nhả bớt tải điều khiển
        "FULL_RESET",         # 6: Đặt lại trạng thái ban đầu
        "ADAPTIVE_EXPEDITE",  # 7: Tăng tốc đáp ứng thích ứng
    ]

    INTENSITY_TIERS = [0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 0.875, 1.000]
    HORIZON_TIERS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    PARAMETER_TIERS = [0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]

    @classmethod
    def decode(cls, k_star: int, confidence: float = 1.0, is_valid: bool = True) -> StructuredAction:
        """Giải mã chỉ số 12-bit sang đối tượng StructuredAction tổng quát."""
        k = int(k_star) & 0x0FFF

        action_id = k & 0x07
        intensity_id = (k >> 3) & 0x07
        horizon_id = (k >> 6) & 0x07
        param_id = (k >> 9) & 0x07

        return StructuredAction(
            best_index=k,
            confidence=float(confidence),
            action_intent_id=action_id,
            action_type=cls.ACTION_NAMES[action_id],
            intensity_tier_id=intensity_id,
            intensity_level=cls.INTENSITY_TIERS[intensity_id],
            horizon_tier_id=horizon_id,
            horizon_scale=cls.HORIZON_TIERS[horizon_id],
            parameter_tier_id=param_id,
            parameter_value=cls.PARAMETER_TIERS[param_id],
            is_valid=is_valid,
        )

    @classmethod
    def encode(cls, action_id: int, intensity_id: int, horizon_id: int, param_id: int) -> int:
        """Đóng gói 4 tham số 3-bit thành 1 chỉ số 12-bit duy nhất."""
        return ((param_id & 0x07) << 9) | ((horizon_id & 0x07) << 6) | ((intensity_id & 0x07) << 3) | (action_id & 0x07)


class InputSplittingCodec:
    """
    Bộ mã hóa phân tách không gian đặc trưng 4096D (Input Splitting Codec).
    Ghép 4 khối nhận thức 1024D thành 1 vector thống nhất:
    - Khối 1 (0..1023):    Không gian quan sát môi trường / Thực tại vật lý (Spatial Perception)
    - Khối 2 (1024..2047): Động lượng & Biến thiên đa thang đo (Dynamic Features)
    - Khối 3 (2048..3071): Trạng thái nội tại & Tài nguyên tác nhân (Internal Agent State)
    - Khối 4 (3072..4095): Tín hiệu ngữ nghĩa & Âm học đa phương thức (Semantic & Acoustic Cues)
    """
    DIM_TOTAL = CL12_DIMENSION  # 4096
    DIM_BLOCK = 1024

    def __init__(self):
        self._buffer = np.zeros(self.DIM_TOTAL, dtype=np.float64)

    def encode(
        self,
        block1_spatial: np.ndarray,
        block2_dynamics: np.ndarray,
        block3_internal: np.ndarray,
        block4_semantic: np.ndarray,
        normalize_l2: bool = True,
    ) -> np.ndarray:
        """Ghép 4 khối 1024D, khử NaN/Inf, kẹp biên [-10.0, 10.0] và chuẩn hóa an toàn."""
        for idx, block in enumerate((block1_spatial, block2_dynamics, block3_internal, block4_semantic)):
            start = idx * self.DIM_BLOCK
            end = start + self.DIM_BLOCK
            if block is not None and len(block) == self.DIM_BLOCK:
                self._buffer[start:end] = block
            else:
                self._buffer[start:end] = 0.0

        # Xử lý an toàn số học: Triệt tiêu NaN, Inf và kẹp biên
        np.nan_to_num(self._buffer, copy=False, nan=0.0, posinf=10.0, neginf=-10.0)
        np.clip(self._buffer, -10.0, 10.0, out=self._buffer)

        # Chuẩn hóa L2 về mặt cầu đơn vị
        if normalize_l2:
            norm = np.linalg.norm(self._buffer)
            if norm > 1e-12:
                self._buffer /= norm
            else:
                self._buffer[0] = 1.0

        return self._buffer.copy()
