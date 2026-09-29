"""
VivyQu Engine Python Wrapper
============================
Cung cấp giao diện lập trình Python chuẩn mực theo đặc tả VIVY_MASTER_BUILD_PLAN.md:
- Time-to-Hello-World < 3 phút.
- Giao tiếp C-ABI tốc độ cao (0 µs overhead).
- Tích hợp sẵn Tường lửa Kiểm tra Lỗi và Watchdog Circuit Breaker (500 µs fallback).
"""

import os
import sys
import time
import ctypes
import numpy as np
from typing import Optional, List, Tuple

from .types import (
    CL12_DIMENSION,
    CONSTRAINT_MASK_BYTES,
    MAX_ACTIVE_ROTORS,
    MAGIC_INPUT_FRAME,
    MAGIC_OUTPUT_FRAME,
    ABI_VERSION_1_0,
    MODE_DETERMINISTIC_ARGMAX,
    MODE_CALIBRATED_BORN,
    MODE_FALLBACK_LOWRANK,
    MODE_GEOMETRIC_E9,
    ERR_NONE,
    ERR_ALL_CONSTRAINTS_VIOLATED,
    VivyquInputFrame,
    VivyquOutputFrame,
    DecisionResult,
)


class VivyquEngine:
    """Động cơ ra quyết định lượng tử VivyQu Core."""

    def __init__(self, dll_path: Optional[str] = None):
        self._dll_path = dll_path or self._find_dll()
        if not os.path.exists(self._dll_path):
            raise FileNotFoundError(f"Vivyqu Core DLL not found at: {self._dll_path}")

        # Thêm thư mục chứa DLL vào danh sách tìm kiếm trên Windows
        dll_dir = os.path.dirname(os.path.abspath(self._dll_path))
        if hasattr(os, "add_dll_directory") and os.path.isdir(dll_dir):
            try:
                os.add_dll_directory(dll_dir)
            except Exception:
                pass

        # Nạp DLL
        self._lib = ctypes.CDLL(self._dll_path)
        self._setup_c_api()

        # Khởi tạo trạng thái nội bộ
        init_res = self._lib.vivyqu_core_init()
        if init_res != ERR_NONE:
            raise RuntimeError(f"Failed to initialize Vivyqu Core (Error: {init_res})")

        self._seq_id = 0
        self._version_str = self._lib.vivyqu_core_version().decode("utf-8")

        # Cấp phát sẵn 1 cặp Input/Output Frame căn lề 64-byte để tái sử dụng (Zero-allocation)
        self._in_frame = VivyquInputFrame()
        self._out_frame = VivyquOutputFrame()

        # Cache các con trỏ địa chỉ để giảm thiểu overhead của ctypes
        self._p_in = ctypes.byref(self._in_frame)
        self._p_out = ctypes.byref(self._out_frame)
        self._in_mask_ptr = ctypes.addressof(self._in_frame.constraint_bitmask)
        self._in_latent_ptr = ctypes.addressof(self._in_frame.latent_vector)

        # Bộ đệm Baseline A2 cho cứu nguy (Lazy loading)
        self._baseline_a2_weights = None
        # Single timeout threshold: matches Watchdog T_max = 500 µs (SOP).
        self._timeout_us = 500.0


    def _find_dll(self) -> str:
        """Tự động tìm kiếm file DLL trong cây thư mục dự án."""
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(curr_dir))
        candidate_paths = [
            os.path.join(root_dir, "build", "bin", "vivyqu_core.dll"),
            os.path.join(root_dir, "build", "vivyqu_core.dll"),
            os.path.join(curr_dir, "vivyqu_core.dll"),
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                return p
        return candidate_paths[0]

    def _setup_c_api(self):
        """Khởi tạo prototype cho các hàm C-ABI."""
        self._lib.vivyqu_core_init.argtypes = []
        self._lib.vivyqu_core_init.restype = ctypes.c_int32

        self._lib.vivyqu_core_cleanup.argtypes = []
        self._lib.vivyqu_core_cleanup.restype = ctypes.c_int32

        self._lib.vivyqu_core_version.argtypes = []
        self._lib.vivyqu_core_version.restype = ctypes.c_char_p

        self._lib.vivyqu_core_step.argtypes = [
            ctypes.POINTER(VivyquInputFrame),
            ctypes.POINTER(VivyquOutputFrame),
        ]
        self._lib.vivyqu_core_step.restype = ctypes.c_int32

        if hasattr(self._lib, "vivyqu_core_load_e9_weights"):
            self._lib.vivyqu_core_load_e9_weights.argtypes = [ctypes.c_char_p]
            self._lib.vivyqu_core_load_e9_weights.restype = ctypes.c_int32

        if hasattr(self._lib, "vivyqu_core_step_e9"):
            self._lib.vivyqu_core_step_e9.argtypes = [
                ctypes.POINTER(VivyquInputFrame),
                ctypes.POINTER(VivyquOutputFrame),
            ]
            self._lib.vivyqu_core_step_e9.restype = ctypes.c_int32

        if hasattr(self._lib, "vivyqu_core_adapt_torque"):
            self._lib.vivyqu_core_adapt_torque.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_float,
                ctypes.c_void_p,
            ]
            self._lib.vivyqu_core_adapt_torque.restype = ctypes.c_float

        if hasattr(self._lib, "vivyqu_core_get_rotor_angle"):
            self._lib.vivyqu_core_get_rotor_angle.argtypes = [
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_float),
            ]
            self._lib.vivyqu_core_get_rotor_angle.restype = ctypes.c_int32

        if hasattr(self._lib, "vivyqu_core_set_rotor_angle"):
            self._lib.vivyqu_core_set_rotor_angle.argtypes = [
                ctypes.c_size_t,
                ctypes.c_float,
            ]
            self._lib.vivyqu_core_set_rotor_angle.restype = ctypes.c_int32

    def load_e9_weights(self, weights_bin_path: str) -> bool:
        """Nạp trọng số mô hình E9 Geometric Scorer từ file nhị phân."""
        if hasattr(self._lib, "vivyqu_core_load_e9_weights"):
            b_path = weights_bin_path.encode("utf-8")
            rc = self._lib.vivyqu_core_load_e9_weights(b_path)
            return rc == ERR_NONE
        return False

    def adapt_torque(
        self,
        latent_vector: np.ndarray,
        chosen_k: int,
        target_k: int,
        learning_rate: float = 0.01,
        return_torques: bool = False,
    ):
        """
        Thích nghi trực tuyến bằng Hamiltonian Torque Descent qua 8 rotors Cl(12).
        Cập nhật tại chỗ góc quay rotor vi phân theo moment lực bivector.
        """
        if not hasattr(self._lib, "vivyqu_core_adapt_torque"):
            raise NotImplementedError("vivyqu_core_adapt_torque not found in library")

        if latent_vector.dtype != np.float64 or not latent_vector.flags.c_contiguous:
            latent_vector = np.ascontiguousarray(latent_vector, dtype=np.float64)

        torques_arr = (ctypes.c_float * 8)()
        torques_ptr = ctypes.cast(torques_arr, ctypes.c_void_p)

        loss = self._lib.vivyqu_core_adapt_torque(
            latent_vector.ctypes.data,
            ctypes.c_uint32(chosen_k),
            ctypes.c_uint32(target_k),
            ctypes.c_float(learning_rate),
            torques_ptr,
        )

        if return_torques:
            return float(loss), np.ctypeslib.as_array(torques_arr).copy()
        return float(loss)

    def get_rotor_angles(self) -> np.ndarray:
        """Lấy 8 góc quay hiện tại của các rotors Cl(12)."""
        angles = np.zeros(8, dtype=np.float32)
        val = ctypes.c_float()
        for i in range(8):
            self._lib.vivyqu_core_get_rotor_angle(ctypes.c_size_t(i), ctypes.byref(val))
            angles[i] = val.value
        return angles

    def set_rotor_angle(self, rotor_idx: int, angle: float) -> bool:
        """Đặt trực tiếp góc quay cho rotor rotor_idx."""
        rc = self._lib.vivyqu_core_set_rotor_angle(ctypes.c_size_t(rotor_idx), ctypes.c_float(angle))
        return rc == ERR_NONE


    @property
    def version(self) -> str:
        return self._version_str

    def step(
        self,
        latent_vector: np.ndarray,
        constraint_mask: Optional[np.ndarray] = None,
        mode: str = "argmax",
        temperature: float = 1.0,
        rotors: Optional[List[Tuple[int, int, float]]] = None,
        return_top_m: bool = False,
    ) -> DecisionResult:
        """
        Thực thi 1 chu kỳ quyết định từ vector ngữ cảnh latent_vector.

        Tham số:
            latent_vector: np.ndarray shape (4096,), float32 hoặc float64.
            constraint_mask: np.ndarray (512 bytes uint8 hoặc 4096 bool).
            mode: "argmax" (Born xác định), "born" (lấy mẫu Born), hoặc "e9" / "geometric" (E9 Geometric Scorer).
            temperature: Nhiệt độ khi mode="born".
            rotors: Danh sách các rotor [(plane_i, plane_j, angle_rad), ...] (M <= 16).
            return_top_m: Có trích xuất mảng Top-8 ứng viên hay không.
        """
        self._seq_id += 1
        t_call_start = time.perf_counter()

        # 1. Điền Header
        self._in_frame.magic_header = MAGIC_INPUT_FRAME
        self._in_frame.sequence_id = self._seq_id
        self._in_frame.version = ABI_VERSION_1_0
        self._in_frame.timestamp_ns = 0  # Bỏ qua time.time_ns() trong hot loop
        self._in_frame.temperature = float(temperature)

        if mode == "born":
            self._in_frame.mode_flags = MODE_CALIBRATED_BORN
        elif mode in ("e9", "geometric"):
            self._in_frame.mode_flags = MODE_GEOMETRIC_E9
        else:
            self._in_frame.mode_flags = MODE_DETERMINISTIC_ARGMAX

        # 2. Xử lý Mặt nạ ràng buộc (512 bytes)
        if constraint_mask is not None:
            if constraint_mask.dtype == np.uint8 and constraint_mask.size == CONSTRAINT_MASK_BYTES:
                ctypes.memmove(self._in_mask_ptr, constraint_mask.ctypes.data, 512)
            elif constraint_mask.dtype == bool and constraint_mask.size == CL12_DIMENSION:
                packed = np.packbits(constraint_mask, bitorder='little')
                ctypes.memmove(self._in_mask_ptr, packed.ctypes.data, 512)
            else:
                mask_u8 = np.ascontiguousarray(constraint_mask, dtype=np.uint8)
                ctypes.memmove(self._in_mask_ptr, mask_u8.ctypes.data, 512)
        else:
            ctypes.memset(self._in_mask_ptr, 0xFF, 512)

        # 3. Xử lý cấu hình Rotor
        num_rotors = 0
        if rotors:
            num_rotors = min(len(rotors), MAX_ACTIVE_ROTORS)
            for idx in range(num_rotors):
                pi, pj, th = rotors[idx]
                self._in_frame.rotors[idx].plane_i = int(pi)
                self._in_frame.rotors[idx].plane_j = int(pj)
                self._in_frame.rotors[idx].angle_theta = float(th)
        self._in_frame.active_rotors = num_rotors

        # 4. Sao chép vector ngữ cảnh vào bộ nhớ đệm C
        if latent_vector.dtype == np.float64 and latent_vector.flags.c_contiguous:
            ctypes.memmove(self._in_latent_ptr, latent_vector.ctypes.data, 32768)
        else:
            vec_f64 = np.ascontiguousarray(latent_vector, dtype=np.float64)
            ctypes.memmove(self._in_latent_ptr, vec_f64.ctypes.data, 32768)

        # 5. Gọi thực thi C-ABI Lõi (Core Step)
        res_code = self._lib.vivyqu_core_step(self._p_in, self._p_out)

        t_call_end = time.perf_counter()
        total_latency_us = (t_call_end - t_call_start) * 1e6

        # 6. Kiểm tra Watchdog Circuit Breaker (timeout cấu hình hoặc lỗi nghiêm trọng)
        if total_latency_us > self._timeout_us or res_code != ERR_NONE or self._out_frame.error_code != ERR_NONE:
            return self._execute_fallback(latent_vector, constraint_mask, total_latency_us)

        # Fail-closed mask trên kết quả Core (kể cả DLL path Level 3).
        if constraint_mask is not None:
            if constraint_mask.dtype == bool and constraint_mask.size == CL12_DIMENSION:
                mask_bool = constraint_mask
            elif constraint_mask.dtype == np.uint8 and constraint_mask.size == CONSTRAINT_MASK_BYTES:
                mask_bool = np.unpackbits(
                    np.ascontiguousarray(constraint_mask, dtype=np.uint8),
                    bitorder="little",
                )[:CL12_DIMENSION].astype(bool)
            else:
                mask_bool = None
            if mask_bool is not None:
                k_chk = int(self._out_frame.best_decision_idx)
                valid_cnt = int(np.sum(mask_bool))
                if valid_cnt == 0 or k_chk < 0 or k_chk >= CL12_DIMENSION or not bool(mask_bool[k_chk]):
                    return DecisionResult(
                        best_index=0,
                        confidence=0.0,
                        valid_candidates=valid_cnt,
                        latency_us=total_latency_us,
                        norm_drift=0.0,
                        is_valid=False,
                        sequence_id=self._seq_id,
                        error_code=ERR_ALL_CONSTRAINTS_VIOLATED,
                    )


        # Trích xuất danh sách Top-M ứng viên nếu yêu cầu
        top_candidates = []
        if return_top_m:
            for i in range(8):
                cand_idx = self._out_frame.top_candidates[i].candidate_idx
                conf = self._out_frame.top_candidates[i].confidence
                if conf > 0.0 or i == 0:
                    top_candidates.append((int(cand_idx), float(conf)))

        return DecisionResult(
            best_index=int(self._out_frame.best_decision_idx),
            confidence=float(self._out_frame.best_confidence),
            valid_candidates=int(self._out_frame.valid_candidates),
            latency_us=float(self._out_frame.latency_core_ns) / 1000.0,
            norm_drift=float(self._out_frame.norm_drift),
            is_valid=(self._out_frame.error_code == ERR_NONE),
            sequence_id=int(self._out_frame.sequence_id),
            error_code=int(self._out_frame.error_code),
            top_candidates=top_candidates
        )

    def step_fast(self, latent_vector: np.ndarray, constraint_mask_bytes: Optional[np.ndarray] = None) -> int:
        """
        Đường dẫn thực thi siêu tốc (Sub-10µs End-to-End) dành cho Cầu Treo & Game Loop.
        Trả về trực tiếp chỉ số quyết định k* mà không tạo dataclass trung gian.
        """
        self._seq_id += 1
        self._in_frame.magic_header = MAGIC_INPUT_FRAME
        self._in_frame.sequence_id = self._seq_id
        self._in_frame.version = ABI_VERSION_1_0
        self._in_frame.mode_flags = MODE_DETERMINISTIC_ARGMAX
        self._in_frame.active_rotors = 0

        if constraint_mask_bytes is not None:
            ctypes.memmove(self._in_mask_ptr, constraint_mask_bytes.ctypes.data, 512)
        else:
            ctypes.memset(self._in_mask_ptr, 0xFF, 512)

        ctypes.memmove(self._in_latent_ptr, latent_vector.ctypes.data, 32768)
        self._lib.vivyqu_core_step(self._p_in, self._p_out)
        return self._out_frame.best_decision_idx

    def _execute_fallback(
        self,
        latent_vector: np.ndarray,
        constraint_mask: Optional[np.ndarray],
        measured_latency_us: float
    ) -> DecisionResult:
        """Kế hoạch cứu nguy Watchdog: Chuyển sang Baseline A2 khi Core vượt ngưỡng SLA."""
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        weights_file = os.path.join(root_dir, "results", "baseline_a2", "baseline_a2_weights.npz")

        if self._baseline_a2_weights is None and os.path.exists(weights_file):
            self._baseline_a2_weights = np.load(weights_file)

        if self._baseline_a2_weights is not None:
            w = self._baseline_a2_weights
            W_l, W_r, b = w["W_l"], w["W_r"], w["bias"]
            # s = W_r @ (W_l @ h) + b
            s = W_r @ (W_l @ latent_vector.astype(np.float32)) + b
            valid_cnt = CL12_DIMENSION
            if constraint_mask is not None:
                if constraint_mask.dtype == bool:
                    s[~constraint_mask] = -np.inf
                    valid_cnt = int(np.sum(constraint_mask))
                else:
                    unpacked = np.unpackbits(constraint_mask, bitorder='little')[:CL12_DIMENSION].astype(bool)
                    s[~unpacked] = -np.inf
                    valid_cnt = int(np.sum(unpacked))
            best_k = int(np.argmax(s))
            # Fail-closed: mask rỗng hoặc argmax rơi ngoài mask → invalid.
            if valid_cnt == 0:
                return DecisionResult(
                    best_index=0,
                    confidence=0.0,
                    valid_candidates=0,
                    latency_us=measured_latency_us,
                    norm_drift=0.0,
                    is_valid=False,
                    sequence_id=self._seq_id,
                    error_code=ERR_ALL_CONSTRAINTS_VIOLATED,
                )
            if constraint_mask is not None:
                if constraint_mask.dtype == bool:
                    ok = bool(constraint_mask[best_k])
                else:
                    unpacked = np.unpackbits(
                        np.ascontiguousarray(constraint_mask, dtype=np.uint8),
                        bitorder="little",
                    )[:CL12_DIMENSION].astype(bool)
                    ok = bool(unpacked[best_k]) if 0 <= best_k < CL12_DIMENSION else False
                if not ok:
                    return DecisionResult(
                        best_index=0,
                        confidence=0.0,
                        valid_candidates=valid_cnt,
                        latency_us=measured_latency_us,
                        norm_drift=0.0,
                        is_valid=False,
                        sequence_id=self._seq_id,
                        error_code=ERR_ALL_CONSTRAINTS_VIOLATED,
                    )
            return DecisionResult(
                best_index=best_k,
                confidence=1.0,
                valid_candidates=valid_cnt,
                latency_us=measured_latency_us,
                norm_drift=0.0,
                is_valid=True,
                sequence_id=self._seq_id,
                error_code=ERR_NONE
            )


        # Fallback tối thiểu nếu không có file weights
        return DecisionResult(
            best_index=0,
            confidence=0.0,
            valid_candidates=0,
            latency_us=measured_latency_us,
            norm_drift=0.0,
            is_valid=False,
            sequence_id=self._seq_id,
            error_code=ERR_CORE_TIMEOUT
        )

    def step_e9(
        self,
        latent_vector: np.ndarray,
        constraint_mask: Optional[np.ndarray] = None,
    ) -> Tuple[int, float, int, int]:
        """Thực thi nhanh chế độ E9 Geometric Scorer và trả về (best_k, conf, rc, latency_ns)."""
        res = self.step(latent_vector, constraint_mask=constraint_mask, mode="e9")
        return res.best_index, res.confidence, res.error_code, int(res.latency_us * 1000.0)

    def close(self):
        """Dọn dẹp và giải phóng tài nguyên engine."""
        if hasattr(self, "_lib") and self._lib:
            self._lib.vivyqu_core_cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
