"""
Vivyqu & Cầu Treo Harmonization Bridge (Python 3.11 Runtime)
============================================================
Cầu nối kiến trúc lưỡng tốc (Two-Speed Harmonization Bridge):
- Tầng 1 (ABI): Zero-copy ctypes binding kết nối C++20 vivyqu_core.dll và C11 cautreo.dll.
- Tầng 2 (Dual Codec):
    + Ingest: Chuyển hóa CCE Context + Score Graph + Memory thành Vector Cl(12) 4096D (InputSplittingCodec).
    + Action: Giải mã k* 12-bit thành StructuredAction và ánh xạ Cautreo Bodymap Organ (OutputStitchingCodec).
- Tầng 3 (Cognitive Graph): Đồng bộ trạng thái FALSIFIED sang Constraint Bitmask 512-byte (Zero Repeated Blunder).
- Tầng 4 (Temporal Decoupler): Phối hợp nhịp µs (Core) và nhịp ms (Cautreo Host / Bus / UI) qua Watchdog Supervisor.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np

from .codec import InputSplittingCodec, OutputStitchingCodec, StructuredAction
from .types import (
    CL12_DIMENSION,
    CONSTRAINT_MASK_BYTES,
    MAGIC_INPUT_FRAME,
    MAGIC_OUTPUT_FRAME,
    MODE_GEOMETRIC_E9,
    VivyquInputFrame,
    VivyquOutputFrame,
    DecisionResult,
)
from .watchdog import WatchdogSupervisor


# Ánh xạ 8 Action Type sang Cautreo Bodymap Organ
ACTION_TO_ORGAN: Dict[str, str] = {
    "IDLE": "eye",                # Quan sát, lắng nghe
    "ENGAGE_PRIMARY": "hand",      # Thao tác chính (tool execute)
    "ENGAGE_SECONDARY": "both",    # Vừa quan sát vừa thao tác phụ
    "PIVOT_STATE": "both",         # Chuyển hướng suy tưởng
    "RECALIBRATE": "both",         # Tự hiệu chuẩn nội tại
    "PARTIAL_RELEASE": "hand",     # Nhả bớt tải bộ nhớ
    "FULL_RESET": "both",          # Đặt lại trạng thái an toàn
    "ADAPTIVE_EXPEDITE": "both",   # Tăng tốc thích ứng
}


@dataclass
class HarmonizedDecision:
    """Quyết định hợp nhất đầy đủ giữa Linh hồn Vivyqu và Thân thể Cầu Treo."""
    best_index: int
    confidence: float
    latency_us: float
    structured_action: StructuredAction
    target_organ: str              # 'eye' | 'hand' | 'both'
    valid_candidates: int
    sequence_id: int
    is_safe: bool
    entropy: float
    polarization: str = "INERTIA"  # 'INERTIA' | 'SENSORY' | 'ACTION' | 'SUPERVISION'
    early_exit: bool = False
    steering_delta: Optional[np.ndarray] = None


class HarmonizedCautreoBridge:
    """
    Cầu nối cấu trúc tối ưu hóa kết nối Cầu Treo và Vivyqu Core.
    """

    def __init__(
        self,
        core_dll_path: Optional[str] = None,
        weights_path: Optional[str] = None,
        cautreo_dll_path: Optional[str] = None,
        watchdog: Optional[WatchdogSupervisor] = None,
    ):
        self.repo_root = Path(__file__).resolve().parents[2]

        # 1. Đường dẫn DLL và Weights
        if core_dll_path is None:
            cand1 = self.repo_root / "build" / "bin" / "vivyqu_core.dll"
            cand2 = Path(__file__).parent / "vivyqu_core.dll"
            core_dll_path = str(cand1 if cand1.exists() else cand2)

        if weights_path is None:
            weights_path = str(self.repo_root / "data" / "e9_weights.bin")

        if cautreo_dll_path is None:
            cautreo_dll = self.repo_root / "engine" / "bin" / "cautreo.dll"
            cautreo_dll_path = str(cautreo_dll) if cautreo_dll.exists() else None

        self.core_dll_path = core_dll_path
        self.weights_path = weights_path
        self.cautreo_dll_path = cautreo_dll_path

        # 2. Watchdog Supervisor
        self.watchdog = watchdog or WatchdogSupervisor()

        # 3. Codecs
        self.input_codec = InputSplittingCodec()
        self.output_codec = OutputStitchingCodec()

        # 4. Trạng thái ràng buộc nhận thức (Cognitive Constraints)
        self.prohibited_actions: Set[int] = set()

        # 5. Khung dữ liệu nhị phân Zero-Allocation (Cấp phát 1 lần cố định)
        self._in_frame = VivyquInputFrame()
        self._out_frame = VivyquOutputFrame()
        self._sequence_counter = 0

        # Preallocated buffers cho Phân cực Qubit & Steering (Zero Python Allocation)
        self._pol_buf = np.zeros(CL12_DIMENSION, dtype=np.float32)
        self._out_pol = ctypes.c_uint32()
        self._out_conf = ctypes.c_float()
        self._delta_buf = np.zeros(CL12_DIMENSION, dtype=np.float32)

        # 6. Nạp C++20 Core DLL
        self._core_lib = None
        self._cautreo_lib = None
        self._init_libraries()

    def _init_libraries(self) -> None:
        """Nạp thư viện nhị phân C++20 và C11 C-ABI."""
        if not os.path.exists(self.core_dll_path):
            raise FileNotFoundError(f"Vivyqu Core DLL không tồn tại tại: {self.core_dll_path}")

        self._core_lib = ctypes.CDLL(self.core_dll_path)

        # Định nghĩa chữ ký hàm C-API
        self._core_lib.vivyqu_core_init.restype = ctypes.c_int32
        self._core_lib.vivyqu_core_load_e9_weights.argtypes = [ctypes.c_char_p]
        self._core_lib.vivyqu_core_load_e9_weights.restype = ctypes.c_int32

        self._core_lib.vivyqu_core_step_e9.argtypes = [
            ctypes.POINTER(VivyquInputFrame),
            ctypes.POINTER(VivyquOutputFrame),
        ]
        self._core_lib.vivyqu_core_step_e9.restype = ctypes.c_int32

        self._core_lib.vivyqu_core_version.restype = ctypes.c_char_p

        # Khai báo chữ ký hàm Phân cực Qubit & Activation Steering
        if hasattr(self._core_lib, "vivyqu_core_classify_polarization"):
            self._core_lib.vivyqu_core_classify_polarization.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_float),
            ]
            self._core_lib.vivyqu_core_classify_polarization.restype = ctypes.c_int32

        if hasattr(self._core_lib, "vivyqu_core_compute_steering"):
            self._core_lib.vivyqu_core_compute_steering.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_size_t,
                ctypes.c_float,
            ]
            self._core_lib.vivyqu_core_compute_steering.restype = ctypes.c_int32

        # Khởi tạo core
        ret = self._core_lib.vivyqu_core_init()
        if ret != 0:
            raise RuntimeError(f"Lỗi khởi tạo Vivyqu Core: {ret}")

        # Nạp trọng số E9
        if os.path.exists(self.weights_path):
            ret_w = self._core_lib.vivyqu_core_load_e9_weights(self.weights_path.encode("utf-8"))
            if ret_w != 0:
                print(f"[CẢNH BÁO] Không thể nạp trọng số E9 từ {self.weights_path}, mã lỗi: {ret_w}")

        # Thử nạp C11 cautreo.dll nếu có
        if self.cautreo_dll_path and os.path.exists(self.cautreo_dll_path):
            try:
                self._cautreo_lib = ctypes.CDLL(self.cautreo_dll_path)
            except Exception as e:
                # Không bắt buộc nếu chỉ cần Vivyqu Core tính toán
                self._cautreo_lib = None

    def get_version(self) -> str:
        """Đọc phiên bản Lõi Vivyqu Core C++."""
        if self._core_lib:
            return self._core_lib.vivyqu_core_version().decode("utf-8")
        return "UNKNOWN"

    def ban_action(self, action_index: int) -> None:
        """
        Đánh dấu một hành động bị cấm vĩnh viễn trong phiên (do falsified hoặc vi phạm an toàn).
        Tầng 3 Cognitive Graph Synchronization.
        """
        if 0 <= action_index < CL12_DIMENSION:
            self.prohibited_actions.add(action_index)

    def unban_action(self, action_index: int) -> None:
        """Gỡ bỏ cấm nếu có bằng chứng phục hồi."""
        self.prohibited_actions.discard(action_index)

    def _build_constraint_mask(self) -> np.ndarray:
        """Dựng mặt nạ ràng buộc 512 bytes (4096 bits): 1 = cho phép, 0 = cấm."""
        mask_bool = np.ones(CL12_DIMENSION, dtype=bool)
        for a in self.prohibited_actions:
            mask_bool[a] = False
        return np.packbits(mask_bool, bitorder="little")

    def step(
        self,
        obs_features: Optional[np.ndarray] = None,
        dynamic_features: Optional[np.ndarray] = None,
        internal_features: Optional[np.ndarray] = None,
        semantic_cues: Optional[np.ndarray] = None,
        raw_latent_vector: Optional[np.ndarray] = None,
        temperature: float = 1.0,
        compute_steering: bool = False,
    ) -> HarmonizedDecision:
        """
        Thực hiện một chu kỳ suy tưởng và điều phối hoàn chỉnh (Ingest -> Think -> Act).
        Bảo đảm thời gian thực thi: < 35.0 µs.
        """
        t0 = time.perf_counter()
        self._sequence_counter += 1
        seq_id = self._sequence_counter

        # 1. Tầng 2: Gom tụ vector nhận thức 4096D qua InputSplittingCodec
        if raw_latent_vector is not None:
            latent_4096 = raw_latent_vector
            if np.isnan(latent_4096).any() or np.isinf(latent_4096).any():
                latent_4096 = np.nan_to_num(latent_4096, nan=0.0, posinf=1.0, neginf=-1.0)
            norm = np.linalg.norm(latent_4096)
            if norm > 1e-9:
                latent_4096 = latent_4096 / norm
            else:
                latent_4096 = np.zeros(CL12_DIMENSION, dtype=np.float64)
                latent_4096[0] = 1.0
        else:
            latent_4096 = self.input_codec.encode(
                block1_spatial=obs_features,
                block2_dynamics=dynamic_features,
                block3_internal=internal_features,
                block4_semantic=semantic_cues,
                normalize_l2=True,
            )

        # 2. Điền dữ liệu trực tiếp vào InputFrame cố định (Zero-copy in hot path)
        self._in_frame.magic_header = MAGIC_INPUT_FRAME
        self._in_frame.sequence_id = seq_id
        self._in_frame.version = 0x00010000
        self._in_frame.mode_flags = MODE_GEOMETRIC_E9
        self._in_frame.timestamp_ns = int(time.time_ns())
        self._in_frame.temperature = float(temperature)
        self._in_frame.active_rotors = 0

        # Cập nhật mặt nạ ràng buộc (Tầng 3)
        mask_bytes = self._build_constraint_mask()
        ctypes.memmove(
            ctypes.byref(self._in_frame.constraint_bitmask),
            mask_bytes.ctypes.data,
            CONSTRAINT_MASK_BYTES,
        )

        # ABI boundary (audit 29/09 P0): ép float64 + contiguous trước copy.
        # Đây là preallocated copy, KHÔNG phải zero-copy shared buffer.
        latent_4096 = np.ascontiguousarray(latent_4096, dtype=np.float64).reshape(-1)
        if latent_4096.shape[0] != CL12_DIMENSION:
            raise ValueError(
                f"latent_4096 must have {CL12_DIMENSION} float64 elements, "
                f"got shape={latent_4096.shape} dtype={latent_4096.dtype}"
            )
        ctypes.memmove(
            ctypes.byref(self._in_frame.latent_vector),
            latent_4096.ctypes.data,
            CL12_DIMENSION * 8,
        )

        # 3. Kích hoạt Lõi Vivyqu E9 Scorer (C++20 AVX2)
        t_core_start = time.perf_counter()
        ret = self._core_lib.vivyqu_core_step_e9(
            ctypes.byref(self._in_frame),
            ctypes.byref(self._out_frame),
        )
        t_core_end = time.perf_counter()
        core_latency_us = (t_core_end - t_core_start) * 1e6

        used_watchdog = False
        if ret != 0 or self._out_frame.magic_reply != MAGIC_OUTPUT_FRAME:
            # Chuyển qua Watchdog fallback nếu có sự cố
            used_watchdog = True
            watchdog_res = self.watchdog.step(latent_4096, mask_bytes)
            best_idx = watchdog_res.best_index
            conf = watchdog_res.confidence
            entropy = 0.0
            valid_cand = watchdog_res.valid_candidates
            # Validity phải lấy từ kết quả fallback, không đọc frame Core cũ.
            decode_valid = bool(watchdog_res.is_valid)
        else:
            best_idx = int(self._out_frame.best_decision_idx)
            conf = float(self._out_frame.best_confidence)
            entropy = float(self._out_frame.system_entropy)
            valid_cand = int(self._out_frame.valid_candidates)
            decode_valid = (int(self._out_frame.error_code) == 0)

        # 4. Tầng 2 Action Path: Giải mã StructuredAction
        structured_act = self.output_codec.decode(
            k_star=best_idx,
            confidence=conf,
            is_valid=decode_valid,
        )

        # Ánh xạ sang Cautreo Bodymap Organ
        target_organ = ACTION_TO_ORGAN.get(structured_act.action_type, "both")

        # 5. Phân tích 4 Phân cực Qubit & Tính toán Steering / Early Exit
        pol_code, pol_name, pol_conf = self.classify_polarization(latent_4096)
        early_exit = (pol_name in ("INERTIA", "ACTION"))
        steering_vec = (
            self.compute_steering_delta(latent_4096, max_scale=0.10)
            if (compute_steering and pol_name == "ACTION")
            else None
        )

        t_total_end = time.perf_counter()
        total_latency_us = (t_total_end - t0) * 1e6

        return HarmonizedDecision(
            best_index=best_idx,
            confidence=conf,
            latency_us=total_latency_us,
            structured_action=structured_act,
            target_organ=target_organ,
            valid_candidates=valid_cand,
            sequence_id=seq_id,
            is_safe=(best_idx not in self.prohibited_actions),
            entropy=entropy,
            polarization=pol_name,
            early_exit=early_exit,
            steering_delta=steering_vec,
        )

    POLARIZATION_MAP = {
        0: "INERTIA",
        1: "SENSORY",
        2: "ACTION",
        3: "SUPERVISION",
    }

    def classify_polarization(self, state_4096: np.ndarray) -> Tuple[int, str, float]:
        """Phân loại 4 phân cực Qubit từ vector 4096D (|00>, |01>, |10>, |11>)."""
        dim = len(state_4096)
        if dim != CL12_DIMENSION:
            return 0, "INERTIA", 0.5

        if self._core_lib and hasattr(self._core_lib, "vivyqu_core_classify_polarization"):
            np.copyto(self._pol_buf, state_4096, casting="unsafe")
            arr_ct = self._pol_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            ret = self._core_lib.vivyqu_core_classify_polarization(
                arr_ct, ctypes.c_size_t(dim), ctypes.byref(self._out_pol), ctypes.byref(self._out_conf)
            )
            if ret == 0:
                pol_code = int(self._out_pol.value)
                return pol_code, self.POLARIZATION_MAP.get(pol_code, "INERTIA"), float(self._out_conf.value)

        # Fallback numpy thuần
        total_sq = float(np.sum(state_4096 ** 2))
        if total_sq < 1e-6 or abs(np.sqrt(total_sq) - 1.0) > 0.40:
            return 3, "SUPERVISION", 0.90

        q_size = dim // 4
        e_action = float(np.sum(state_4096[q_size:2*q_size] ** 2)) / (total_sq + 1e-8)
        e_sensory = float(np.sum(state_4096[:q_size] ** 2) + np.sum(state_4096[2*q_size:3*q_size] ** 2)) / (total_sq + 1e-8)
        peak = float(np.max(state_4096 ** 2)) / (total_sq + 1e-8)

        if e_action > 0.35 or peak > 0.04:
            return 2, "ACTION", min(1.0, e_action * 2.0)
        elif e_sensory > 0.55:
            return 1, "SENSORY", min(1.0, e_sensory)
        else:
            return 0, "INERTIA", 0.85

    def compute_steering_delta(self, state_4096: np.ndarray, max_scale: float = 0.10) -> np.ndarray:
        """Tính toán vector điều hướng hoạt hóa Δh (Activation Steering Delta)."""
        dim = len(state_4096)
        if self._core_lib and hasattr(self._core_lib, "vivyqu_core_compute_steering"):
            np.copyto(self._pol_buf, state_4096, casting="unsafe")
            arr_ct = self._pol_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            out_ct = self._delta_buf.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
            ret = self._core_lib.vivyqu_core_compute_steering(
                arr_ct, out_ct, ctypes.c_size_t(dim), ctypes.c_float(max_scale)
            )
            if ret == 0:
                return self._delta_buf.copy()

        # Fallback numpy thuần
        effective_scale = min(max_scale, 0.10)
        if effective_scale <= 0.0:
            return np.zeros(dim, dtype=np.float32)
        norm_in = float(np.linalg.norm(state_4096))
        shifted = np.roll(state_4096, -1)
        diff = shifted - state_4096
        diff_norm = float(np.linalg.norm(diff))
        if diff_norm > 1e-7:
            target_norm = effective_scale * (norm_in if norm_in > 1e-6 else 1.0)
            return ((diff / diff_norm) * target_norm).astype(np.float32)
        return np.zeros(dim, dtype=np.float32)
