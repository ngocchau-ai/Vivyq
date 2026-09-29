"""
VivyQu Types & Binary ABI Definitions (Python ctypes)
=====================================================
Khung dữ liệu nhị phân tương thích 100% với include/vivyqu/types.h và
đặc tả CAUTREO_CORE_INTERFACE_SPEC.md. Căn lề chuẩn 64-byte.
"""

import ctypes
from dataclasses import dataclass, field
from typing import List, Tuple

# Hằng số giao thức
CL12_DIMENSION = 4096
CONSTRAINT_MASK_BYTES = 512
MAX_ACTIVE_ROTORS = 16

MAGIC_INPUT_FRAME = 0x564956595155494E   # "VIVYQUIN"
MAGIC_OUTPUT_FRAME = 0x5649565951554F55  # "VIVYQUOU"
ABI_VERSION_1_0 = 0x00010000             # v1.0

# Chế độ hoạt động
MODE_DETERMINISTIC_ARGMAX = 1 << 0
MODE_CALIBRATED_BORN = 1 << 1
MODE_FALLBACK_LOWRANK = 1 << 2
FLAG_APPLY_SHADOW_ROTORS = 1 << 3
MODE_GEOMETRIC_E9 = 1 << 4

# Cờ trạng thái
STATUS_SUCCESS = 0
FLAG_IS_DETERMINISTIC = 1 << 0
FLAG_RENORMALIZED = 1 << 1
FLAG_FALLBACK_USED = 1 << 2
FLAG_ZERO_NORM_DETECTED = 1 << 3
FLAG_GEOMETRIC_E9 = 1 << 4

# Mã lỗi
ERR_NONE = 0
ERR_INPUT_NAN_INF = 1
ERR_CORE_TIMEOUT = 2
ERR_ALL_CONSTRAINTS_VIOLATED = 3
ERR_MATH_OVERFLOW = 4


class RotorConfig(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("plane_i", ctypes.c_uint8),
        ("plane_j", ctypes.c_uint8),
        ("reserved_r", ctypes.c_uint16),
        ("angle_theta", ctypes.c_float),
    ]


class CandidateScore(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("candidate_idx", ctypes.c_uint32),
        ("confidence", ctypes.c_float),
    ]


class VivyquInputFrame(ctypes.Structure):
    """Khung dữ liệu đầu vào (33.600 bytes = 525 Cachelines)"""
    _pack_ = 1
    _fields_ = [
        # Header (64 bytes)
        ("magic_header", ctypes.c_uint64),
        ("sequence_id", ctypes.c_uint64),
        ("version", ctypes.c_uint32),
        ("mode_flags", ctypes.c_uint32),
        ("timestamp_ns", ctypes.c_uint64),
        ("temperature", ctypes.c_float),
        ("active_rotors", ctypes.c_uint32),
        ("reserved_hdr", ctypes.c_uint8 * 24),

        # Mặt nạ ràng buộc (512 bytes = 4096 bits)
        ("constraint_bitmask", ctypes.c_uint8 * CONSTRAINT_MASK_BYTES),

        # Cấu hình rotor (256 bytes)
        ("rotors", RotorConfig * MAX_ACTIVE_ROTORS),
        ("reserved_rotors", ctypes.c_uint8 * 128),

        # Vector ngữ cảnh (32.768 bytes = 4096 float64)
        ("latent_vector", ctypes.c_double * CL12_DIMENSION),
    ]


class VivyquOutputFrame(ctypes.Structure):
    """Khung dữ liệu đầu ra (256 bytes = 4 Cachelines)"""
    _pack_ = 1
    _fields_ = [
        # Header (64 bytes)
        ("magic_reply", ctypes.c_uint64),
        ("sequence_id", ctypes.c_uint64),
        ("error_code", ctypes.c_uint32),
        ("status_flags", ctypes.c_uint32),
        ("latency_core_ns", ctypes.c_uint64),
        ("reserved_stat", ctypes.c_uint8 * 32),

        # Quyết định cốt lõi (64 bytes)
        ("best_decision_idx", ctypes.c_uint32),
        ("valid_candidates", ctypes.c_uint32),
        ("best_confidence", ctypes.c_double),
        ("norm_drift", ctypes.c_double),
        ("system_entropy", ctypes.c_double),
        ("reserved_decision", ctypes.c_uint8 * 32),

        # Top-8 ứng viên dự phòng (128 bytes)
        ("top_candidates", CandidateScore * 8),
        ("reserved_top_m", ctypes.c_uint8 * 64),
    ]


# Kiểm tra kích thước nhị phân bất biến
assert ctypes.sizeof(VivyquInputFrame) == 33600, f"VivyquInputFrame mismatch: {ctypes.sizeof(VivyquInputFrame)}"
assert ctypes.sizeof(VivyquOutputFrame) == 256, f"VivyquOutputFrame mismatch: {ctypes.sizeof(VivyquOutputFrame)}"


@dataclass
class DecisionResult:
    """Đối tượng kết quả thân thiện với Python developer."""
    best_index: int
    confidence: float
    valid_candidates: int
    latency_us: float
    norm_drift: float
    is_valid: bool
    sequence_id: int
    error_code: int
    top_candidates: List[Tuple[int, float]] = field(default_factory=list)
