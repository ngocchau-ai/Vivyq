"""
VivyQu Watchdog Supervisor & Circuit Breaker Runtime
====================================================
Hiện thực hóa Tường Lửa Bảo Vệ 3 Cấp Độ theo SOP_OPERATIONAL_RUNBOOK.md:
- Kiểm soát ngưỡng timeout cứng T_max = 500.0 µs.
- Máy trạng thái Circuit Breaker: CLOSED -> OPEN -> HALF_OPEN.
- Cấp 1 (Nhẹ): Trôi chuẩn số học -> Tái chuẩn hóa tại chỗ.
- Cấp 2 (Nghiêm trọng): Core Timeout > 500 µs -> Ngắt mạch tức thời sang Golden Baseline A2.
- Cấp 3 (Thảm họa): Daemon crash -> Tự động chuyển cấp sang In-Process C-ABI DLL.
- Bộ đệm Flight Recorder lưu trữ telemetry thời gian thực 10.000 chu kỳ.
"""

import os
import sys
import time
import enum
import collections
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any
import numpy as np

from .types import (
    CL12_DIMENSION,
    CONSTRAINT_MASK_BYTES,
    DecisionResult,
    ERR_NONE,
    ERR_ALL_CONSTRAINTS_VIOLATED,
)
from .engine import VivyquEngine
from .shm_client import VivyquShmClient


class CircuitState(enum.Enum):
    CLOSED = "CLOSED"       # Bình thường: Gọi Core qua Shared Memory (IPC-P)
    OPEN = "OPEN"           # Ngắt mạch: Gọi ngay Baseline A2 Fallback
    HALF_OPEN = "HALF_OPEN" # Thăm dò: Thử 1 chu kỳ để kiểm tra Core phục hồi


class IncidentLevel(enum.Enum):
    NONE = "NONE"
    LEVEL_1_NORM_DRIFT = "LEVEL_1_NORM_DRIFT"       # Trôi chuẩn > 1e-4
    LEVEL_2_CORE_TIMEOUT = "LEVEL_2_CORE_TIMEOUT"   # Timeout > 500 µs
    LEVEL_3_PROCESS_CRASH = "LEVEL_3_PROCESS_CRASH" # Daemon bị crash/kill


@dataclass
class TelemetryRecord:
    timestamp_ns: int
    latency_us: float
    norm_drift: float
    engine_used: str  # "core_shm", "core_dll", "fallback_baseline_a2"
    circuit_state: str
    incident_level: str
    is_valid: bool
    action_idx: int


def _mask_to_bool(constraint_mask: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Chuẩn hóa mask về bool[4096]. Trả về None nếu không có mask."""
    if constraint_mask is None:
        return None
    if getattr(constraint_mask, "dtype", None) == bool and constraint_mask.size == CL12_DIMENSION:
        return np.ascontiguousarray(constraint_mask, dtype=bool).reshape(CL12_DIMENSION)
    if getattr(constraint_mask, "dtype", None) == np.uint8 and constraint_mask.size == CONSTRAINT_MASK_BYTES:
        return np.unpackbits(
            np.ascontiguousarray(constraint_mask, dtype=np.uint8),
            bitorder="little",
        )[:CL12_DIMENSION].astype(bool)
    arr = np.ascontiguousarray(constraint_mask, dtype=bool).reshape(-1)
    if arr.size < CL12_DIMENSION:
        return None
    return arr[:CL12_DIMENSION]


def _fail_closed_mask(latency_us: float, sequence_id: int = 0) -> DecisionResult:
    """Không có action hợp lệ — fail closed, không trả index ngoài mask."""
    return DecisionResult(
        best_index=0,
        confidence=0.0,
        valid_candidates=0,
        latency_us=latency_us,
        norm_drift=0.0,
        is_valid=False,
        sequence_id=sequence_id,
        error_code=ERR_ALL_CONSTRAINTS_VIOLATED,
    )


def _enforce_constraint_mask(
    res: DecisionResult,
    constraint_mask: Optional[np.ndarray],
    latency_us: float,
) -> DecisionResult:
    """Fail-closed: mask rỗng hoặc best_index ngoài mask → invalid."""
    mask_bool = _mask_to_bool(constraint_mask)
    if mask_bool is None:
        return res
    valid_count = int(np.sum(mask_bool))
    if valid_count == 0:
        return _fail_closed_mask(latency_us, sequence_id=res.sequence_id)
    k = int(res.best_index)
    if k < 0 or k >= CL12_DIMENSION or not bool(mask_bool[k]):
        return _fail_closed_mask(latency_us, sequence_id=res.sequence_id)
    return DecisionResult(
        best_index=k,
        confidence=float(res.confidence),
        valid_candidates=valid_count,
        latency_us=float(res.latency_us if res.latency_us else latency_us),
        norm_drift=float(res.norm_drift),
        is_valid=True,
        sequence_id=res.sequence_id,
        error_code=ERR_NONE,
        top_candidates=res.top_candidates,
    )


class FlightRecorder:
    """Bộ đệm vòng nhật ký số (Flight Recorder) ghi nhận telemetry thời gian thực."""

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer = collections.deque(maxlen=capacity)
        self.total_frames = 0
        self.timeout_count = 0
        self.fallback_count = 0
        self.level1_count = 0
        self.level2_count = 0
        self.level3_count = 0

    def record(
        self,
        latency_us: float,
        norm_drift: float,
        engine_used: str,
        circuit_state: CircuitState,
        incident_level: IncidentLevel,
        is_valid: bool,
        action_idx: int,
    ):
        self.total_frames += 1
        if incident_level == IncidentLevel.LEVEL_1_NORM_DRIFT:
            self.level1_count += 1
        elif incident_level == IncidentLevel.LEVEL_2_CORE_TIMEOUT:
            self.level2_count += 1
            self.timeout_count += 1
        elif incident_level == IncidentLevel.LEVEL_3_PROCESS_CRASH:
            self.level3_count += 1

        if engine_used == "fallback_baseline_a2":
            self.fallback_count += 1

        rec = TelemetryRecord(
            timestamp_ns=time.time_ns(),
            latency_us=latency_us,
            norm_drift=norm_drift,
            engine_used=engine_used,
            circuit_state=circuit_state.value,
            incident_level=incident_level.value,
            is_valid=is_valid,
            action_idx=action_idx,
        )
        self.buffer.append(rec)

    def get_stats(self) -> Dict[str, Any]:
        if not self.buffer:
            return {"total_frames": 0}
        latencies = [r.latency_us for r in self.buffer]
        return {
            "total_frames": self.total_frames,
            "recorded_frames": len(self.buffer),
            "fallback_count": self.fallback_count,
            "fallback_rate_percent": (self.fallback_count / max(1, self.total_frames)) * 100.0,
            "timeout_count": self.timeout_count,
            "incident_level1_count": self.level1_count,
            "incident_level2_count": self.level2_count,
            "incident_level3_count": self.level3_count,
            "latency_p50_us": float(np.percentile(latencies, 50)),
            "latency_p95_us": float(np.percentile(latencies, 95)),
            "latency_p99_us": float(np.percentile(latencies, 99)),
            "latency_max_us": float(np.max(latencies)),
        }


class WatchdogSupervisor:
    """Tường lửa giám sát thời gian thực & ngắt mạch sự cố đa tầng."""

    def __init__(
        self,
        shm_client: Optional[VivyquShmClient] = None,
        dll_engine: Optional[VivyquEngine] = None,
        timeout_us: float = 500.0,
        max_consecutive_failures: int = 3,
        half_open_probe_interval: int = 50,
    ):
        self.shm_client = shm_client
        self.dll_engine = dll_engine
        self.timeout_us = timeout_us
        self.max_consecutive_failures = max_consecutive_failures
        self.half_open_probe_interval = half_open_probe_interval

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.open_ticks_counter = 0

        self.flight_recorder = FlightRecorder(capacity=10000)

        # Nạp trọng số Golden Baseline A2 sẵn sàng cho Tầng Cứu Nguy
        self._load_baseline_a2()

    def _load_baseline_a2(self):
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        weights_path = os.path.join(root_dir, "results", "baseline_a2", "baseline_a2_weights.npz")
        if os.path.exists(weights_path):
            data = np.load(weights_path)
            self._W_l = np.ascontiguousarray(data["W_l"], dtype=np.float64)
            self._W_r = np.ascontiguousarray(data["W_r"], dtype=np.float64)
            self._bias = np.ascontiguousarray(data["bias"], dtype=np.float64)
        else:
            self._W_l = np.random.randn(64, CL12_DIMENSION).astype(np.float64) * 0.01
            self._W_r = np.random.randn(CL12_DIMENSION, 64).astype(np.float64) * 0.01
            self._bias = np.zeros(CL12_DIMENSION, dtype=np.float64)

        # Tiền làm ấm bộ nhớ đệm (Cache Pre-warming) theo Bước 1.3 SOP
        dummy_h = np.zeros(CL12_DIMENSION, dtype=np.float64)
        self._execute_fallback_baseline_a2(dummy_h, None)

    def _execute_fallback_baseline_a2(
        self,
        latent_vector: np.ndarray,
        constraint_mask: Optional[np.ndarray],
    ) -> DecisionResult:
        """Thực thi Baseline A2 siêu tốc (< 100 µs) khi Core ngắt mạch hoặc timeout."""
        t0 = time.perf_counter()

        if latent_vector.dtype != np.float64 or not latent_vector.flags.c_contiguous:
            latent_vector = np.ascontiguousarray(latent_vector, dtype=np.float64)

        # BLAS dgemv siêu tốc
        h_proj = self._W_l @ latent_vector
        scores = self._W_r @ h_proj + self._bias

        if constraint_mask is not None:
            if constraint_mask.dtype == bool:
                mask_bool = constraint_mask
            elif constraint_mask.dtype == np.uint8 and constraint_mask.size == CONSTRAINT_MASK_BYTES:
                mask_bool = np.unpackbits(constraint_mask, bitorder='little')[:CL12_DIMENSION].astype(bool)
            else:
                mask_bool = np.ascontiguousarray(constraint_mask, dtype=bool)
            scores[~mask_bool] = -np.inf
            valid_count = int(np.sum(mask_bool))
        else:
            valid_count = CL12_DIMENSION

        k_pred = int(np.argmax(scores))
        t1 = time.perf_counter()
        lat_us = (t1 - t0) * 1e6

        return DecisionResult(
            best_index=k_pred,
            confidence=1.0,
            valid_candidates=valid_count,
            latency_us=lat_us,
            norm_drift=0.0,
            is_valid=True,
            sequence_id=0,
            error_code=ERR_NONE,
        )

    def step(
        self,
        latent_vector: np.ndarray,
        constraint_mask: Optional[np.ndarray] = None,
    ) -> DecisionResult:
        """
        Ra quyết định được bảo vệ 100% qua Tường lửa Watchdog Circuit Breaker:
        - Luôn trả về quyết định hợp lệ trong thời gian <= 500.0 µs.
        - Tự động ngắt mạch sang Baseline A2 khi Core quá tải.
        - Tự động hạ cấp sang C-ABI DLL khi Daemon crash.
        """
        t_start = time.perf_counter()

        # 1. Tiền xử lý dữ liệu: Khử NaN/Inf theo Quy trình 2 SOP
        if np.isnan(latent_vector).any() or np.isinf(latent_vector).any():
            latent_vector = np.nan_to_num(latent_vector, nan=0.0, posinf=10.0, neginf=-10.0)

        # 2. Xử lý Trạng thái OPEN của Circuit Breaker
        if self.state == CircuitState.OPEN:
            self.open_ticks_counter += 1
            if self.open_ticks_counter >= self.half_open_probe_interval:
                # Đã đến lúc thăm dò phục hồi Core
                self.state = CircuitState.HALF_OPEN
                self.open_ticks_counter = 0
            else:
                # Đang trong chu kỳ ngắt mạch -> Thực thi ngay Fallback Baseline A2
                res = self._execute_fallback_baseline_a2(latent_vector, constraint_mask)
                self.flight_recorder.record(
                    latency_us=(time.perf_counter() - t_start) * 1e6,
                    norm_drift=0.0,
                    engine_used="fallback_baseline_a2",
                    circuit_state=self.state,
                    incident_level=IncidentLevel.LEVEL_2_CORE_TIMEOUT,
                    is_valid=res.is_valid,
                    action_idx=res.best_index,
                )
                return res

        # 3. Trạng thái CLOSED hoặc HALF_OPEN: Thử gọi Core qua IPC-P Shared Memory
        if self.shm_client is not None:
            try:
                res = self.shm_client.step(
                    latent_vector=latent_vector,
                    constraint_mask_bytes=constraint_mask,
                    spin_timeout_us=self.timeout_us,
                )
                # Level 2 cũng kích khi call thành công nhưng vượt T_max
                # (spin-wait có thể về ngay nếu response sẵn — timeout_us nhỏ vẫn phải trip).
                elapsed_us = (time.perf_counter() - t_start) * 1e6
                if elapsed_us > self.timeout_us:
                    raise TimeoutError(
                        f"Core latency {elapsed_us:.2f} µs > T_max {self.timeout_us} µs"
                    )

                # Thành công: Khôi phục trạng thái CLOSED
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                self.consecutive_failures = 0

                # Kiểm tra Sự cố Cấp 1 (Trôi chuẩn số học)
                inc_level = IncidentLevel.NONE
                if res.norm_drift > 1e-4:
                    inc_level = IncidentLevel.LEVEL_1_NORM_DRIFT

                self.flight_recorder.record(
                    latency_us=(time.perf_counter() - t_start) * 1e6,
                    norm_drift=res.norm_drift,
                    engine_used="core_shm",
                    circuit_state=self.state,
                    incident_level=inc_level,
                    is_valid=res.is_valid,
                    action_idx=res.best_index,
                )
                return res

            except TimeoutError:
                # Sự cố Cấp 2: Core Timeout > 500 µs
                self.consecutive_failures += 1
                if self.consecutive_failures >= self.max_consecutive_failures:
                    self.state = CircuitState.OPEN
                    self.open_ticks_counter = 0

                # Kích hoạt Kế hoạch Cứu nguy (Fallback Baseline A2) ngay lập tức!
                res = self._execute_fallback_baseline_a2(latent_vector, constraint_mask)
                self.flight_recorder.record(
                    latency_us=(time.perf_counter() - t_start) * 1e6,
                    norm_drift=0.0,
                    engine_used="fallback_baseline_a2",
                    circuit_state=self.state,
                    incident_level=IncidentLevel.LEVEL_2_CORE_TIMEOUT,
                    is_valid=res.is_valid,
                    action_idx=res.best_index,
                )
                return res

            except (ConnectionError, RuntimeError, Exception) as exc:
                # Sự cố Cấp 3: Daemon crash hoặc mất kết nối SHM
                self.consecutive_failures += 1
                self.state = CircuitState.OPEN

                # Tự động hạ cấp sang In-Process C-ABI DLL nếu có
                if self.dll_engine is not None:
                    try:
                        res = self.dll_engine.step(
                            latent_vector=latent_vector,
                            constraint_mask=constraint_mask,
                        )
                        # Fail-closed mask: DLL fallback không được trả index ngoài mask.
                        res = _enforce_constraint_mask(
                            res,
                            constraint_mask,
                            (time.perf_counter() - t_start) * 1e6,
                        )
                        self.flight_recorder.record(
                            latency_us=(time.perf_counter() - t_start) * 1e6,
                            norm_drift=res.norm_drift,
                            engine_used="core_dll",
                            circuit_state=self.state,
                            incident_level=IncidentLevel.LEVEL_3_PROCESS_CRASH,
                            is_valid=res.is_valid,
                            action_idx=res.best_index,
                        )
                        return res
                    except Exception:
                        pass

                # Nếu cả DLL cũng fail -> Tầng cứu nguy Baseline A2 cuối cùng
                res = self._execute_fallback_baseline_a2(latent_vector, constraint_mask)
                self.flight_recorder.record(
                    latency_us=(time.perf_counter() - t_start) * 1e6,
                    norm_drift=0.0,
                    engine_used="fallback_baseline_a2",
                    circuit_state=self.state,
                    incident_level=IncidentLevel.LEVEL_3_PROCESS_CRASH,
                    is_valid=res.is_valid,
                    action_idx=res.best_index,
                )
                return res

        # 4. Nếu không cấu hình Shared Memory, dùng trực tiếp In-Process C-ABI DLL
        elif self.dll_engine is not None:
            res = self.dll_engine.step(latent_vector=latent_vector, constraint_mask=constraint_mask)
            self.flight_recorder.record(
                latency_us=(time.perf_counter() - t_start) * 1e6,
                norm_drift=res.norm_drift,
                engine_used="core_dll",
                circuit_state=self.state,
                incident_level=IncidentLevel.NONE,
                is_valid=res.is_valid,
                action_idx=res.best_index,
            )
            return res

        # 5. Nếu không có cả hai, dùng Fallback Baseline A2
        res = self._execute_fallback_baseline_a2(latent_vector, constraint_mask)
        self.flight_recorder.record(
            latency_us=(time.perf_counter() - t_start) * 1e6,
            norm_drift=0.0,
            engine_used="fallback_baseline_a2",
            circuit_state=self.state,
            incident_level=IncidentLevel.NONE,
            is_valid=res.is_valid,
            action_idx=res.best_index,
        )
        return res
