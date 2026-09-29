"""
VivyQu Eyes Module (Mắt Nhận Thức)
==================================
Hiện thực hóa cơ quan quan sát / thị giác của Vivy:
- Thu nhận không gian quan sát từ môi trường thế giới (World Environment Observation).
- Chuyển đổi thành 2 khối nhận thức trực giao:
  * Khối 1: Quan sát không gian & Trạng thái bề mặt thế giới (Spatial Perception - 1024 chiều).
  * Khối 2: Động lượng, Gia tốc & Biến thiên đa thang đo (Dynamic Features - 1024 chiều).

[BẤT BIẾN KIẾN TRÚC]:
Mắt là cơ quan thu nhận cảm giác thuần túy, phản ánh trung thực trạng thái khách quan của môi trường,
tuyệt đối không gắn bất kỳ bộ lọc cản tĩnh nào làm sai lệch nhận thức của Não bộ.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class WorldSensoryFeed:
    """Gói dữ liệu cảm giác quan sát từ môi trường thế giới của tác nhân."""
    timestamp_ns: int = 0
    spatial_state: Optional[np.ndarray] = None       # Vector trạng thái không gian (vị trí, địa hình, đối tượng)
    environmental_signals: Optional[np.ndarray] = None # Tín hiệu trường vật lý / môi trường
    temporal_dynamics: Optional[np.ndarray] = None   # Chuỗi biến thiên thời gian gần nhất
    scale_factor: float = 1.0


class VivyquEyes:
    """
    Cơ quan Mắt nhận thức của Vivy:
    - Thu nhận dữ liệu quan sát từ môi trường thế giới.
    - Đóng gói và chuẩn hóa thành 2 khối 1024D trực giao: Khối 1 (Spatial) & Khối 2 (Dynamics).
    """

    def __init__(self):
        self._block1_cache = np.zeros(1024, dtype=np.float64)
        self._block2_cache = np.zeros(1024, dtype=np.float64)

    def perceive_spatial(self, feed: WorldSensoryFeed) -> np.ndarray:
        """Trích xuất và chuẩn hóa Khối 1 (1024D) từ trạng thái không gian và môi trường."""
        self._block1_cache.fill(0.0)

        offset = 0
        if feed.spatial_state is not None:
            spatial_flat = feed.spatial_state.flatten()
            n_sp = min(len(spatial_flat), 512)
            self._block1_cache[offset:offset + n_sp] = spatial_flat[:n_sp]
            offset += n_sp

        if feed.environmental_signals is not None:
            env_flat = feed.environmental_signals.flatten()
            rem = 1024 - offset
            n_env = min(len(env_flat), rem)
            self._block1_cache[offset:offset + n_env] = env_flat[:n_env]

        norm1 = np.linalg.norm(self._block1_cache)
        if norm1 > 1e-12:
            self._block1_cache /= norm1

        return self._block1_cache.copy()

    def perceive_dynamics(self, feed: WorldSensoryFeed) -> np.ndarray:
        """Trích xuất và chuẩn hóa Khối 2 (1024D) từ động lượng và biến thiên đa thang đo."""
        self._block2_cache.fill(0.0)

        if feed.temporal_dynamics is not None:
            dyn_flat = feed.temporal_dynamics.flatten()
            n_dyn = min(len(dyn_flat), 1024)
            self._block2_cache[:n_dyn] = dyn_flat[:n_dyn]
        else:
            self._block2_cache[0] = feed.scale_factor

        norm2 = np.linalg.norm(self._block2_cache)
        if norm2 > 1e-12:
            self._block2_cache /= norm2

        return self._block2_cache.copy()
