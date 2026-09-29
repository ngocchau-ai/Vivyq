"""
VivyQu Lock-Free Shared Memory IPC Client (Python)
==================================================
Hiện thực hóa Kế hoạch Chính (IPC-P) theo đặc tả CAUTREO_CORE_INTERFACE_SPEC.md:
- Giao tiếp qua Windows File Mapping (Shared Memory).
- Circular SPSC Ring Buffer 8 slots.
- Đồng bộ phi khóa bằng atomic sequence IDs (seq_in / seq_out).
- Đo lường độ trễ vận chuyển vi mô (< 0.3 µs).
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
    MODE_GEOMETRIC_E9,
    ERR_NONE,
    VivyquInputFrame,
    VivyquOutputFrame,
    DecisionResult,
)


SHM_REGION_NAME = "Local\\VivyquSharedMemory_v1"
RING_BUFFER_SLOTS = 8
MAGIC_SHM_HEADER = 0x564956595155534D


class ShmSlot(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("seq_in", ctypes.c_uint64),
        ("pad0", ctypes.c_uint8 * 56),
        ("in_frame", VivyquInputFrame),
        ("seq_out", ctypes.c_uint64),
        ("pad1", ctypes.c_uint8 * 56),
        ("out_frame", VivyquOutputFrame),
    ]


class ShmRingBuffer(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("magic_header", ctypes.c_uint64),
        ("version", ctypes.c_uint32),
        ("shutdown_flag", ctypes.c_uint32),
        ("pad_hdr", ctypes.c_uint8 * 48),
        ("slots", ShmSlot * RING_BUFFER_SLOTS),
    ]


class VivyquShmClient:
    """Client giao tiếp Shared Memory Ring Buffer với VivyQu Core Daemon."""

    def __init__(self, region_name: str = SHM_REGION_NAME):
        self._region_name = region_name
        self._kernel32 = ctypes.windll.kernel32

        # Cấu hình kiểu dữ liệu Win32 64-bit chuẩn xác
        self._kernel32.OpenFileMappingA.restype = ctypes.c_void_p
        self._kernel32.OpenFileMappingA.argtypes = [
            ctypes.c_uint32,
            ctypes.c_bool,
            ctypes.c_char_p,
        ]

        self._kernel32.MapViewOfFile.restype = ctypes.c_void_p
        self._kernel32.MapViewOfFile.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_size_t,
        ]

        self._kernel32.UnmapViewOfFile.restype = ctypes.c_bool
        self._kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]

        self._kernel32.CloseHandle.restype = ctypes.c_bool
        self._kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

        # 1. Mở File Mapping đã được tạo bởi shm_daemon.exe
        self._hMap = self._kernel32.OpenFileMappingA(
            0x0002 | 0x0004, # FILE_MAP_WRITE | FILE_MAP_READ
            False,
            region_name.encode("utf-8")
        )
        if not self._hMap:
            err = self._kernel32.GetLastError()
            raise ConnectionError(f"Cannot open Shared Memory mapping '{region_name}' (Error: {err}). Ensure vivyqu_shm_daemon.exe is running!")

        # 2. Map view of file
        self._pBuf = self._kernel32.MapViewOfFile(
            self._hMap,
            0x0002 | 0x0004,
            0,
            0,
            ctypes.sizeof(ShmRingBuffer)
        )
        if not self._pBuf:
            err = self._kernel32.GetLastError()
            self._kernel32.CloseHandle(self._hMap)
            raise RuntimeError(f"MapViewOfFile failed (Error: {err})")

        self._shm = ShmRingBuffer.from_address(self._pBuf)
        if self._shm.magic_header != MAGIC_SHM_HEADER:
            raise ValueError(f"Invalid SHM Magic Header: 0x{self._shm.magic_header:X}")

        # Handshake: seq_in is monotonic starting at 1 (matches daemon expected_seq=1).
        # The daemon resyncs expected_seq if it observes a new client (seq gap / restart).
        self._seq_id = 1

    def step(
        self,
        latent_vector: np.ndarray,
        constraint_mask_bytes: Optional[np.ndarray] = None,
        spin_timeout_us: float = 500.0,
        mode: str = "e9",
    ) -> DecisionResult:
        """Gửi 1 frame vào Ring Buffer qua Shared Memory và chờ phản hồi phi khóa."""
        seq = self._seq_id
        self._seq_id += 1
        slot_idx = seq % RING_BUFFER_SLOTS
        slot = self._shm.slots[slot_idx]

        t_send_start = time.perf_counter()

        # 1. Điền dữ liệu vào in_frame của slot
        in_f = slot.in_frame
        in_f.magic_header = MAGIC_INPUT_FRAME
        in_f.sequence_id = seq
        in_f.version = ABI_VERSION_1_0
        if mode == "e9":
            in_f.mode_flags = MODE_GEOMETRIC_E9
        elif mode == "born":
            in_f.mode_flags = MODE_CALIBRATED_BORN
        else:
            in_f.mode_flags = MODE_DETERMINISTIC_ARGMAX
        in_f.active_rotors = 0
        in_f.temperature = 1.0

        if constraint_mask_bytes is not None:
            if constraint_mask_bytes.dtype == bool and constraint_mask_bytes.size == CL12_DIMENSION:
                packed = np.packbits(constraint_mask_bytes, bitorder='little')
                ctypes.memmove(ctypes.addressof(in_f.constraint_bitmask), packed.ctypes.data, 512)
            elif constraint_mask_bytes.dtype == np.uint8 and constraint_mask_bytes.size == CONSTRAINT_MASK_BYTES:
                ctypes.memmove(ctypes.addressof(in_f.constraint_bitmask), constraint_mask_bytes.ctypes.data, 512)
            else:
                packed = np.ascontiguousarray(constraint_mask_bytes, dtype=np.uint8)
                ctypes.memmove(ctypes.addressof(in_f.constraint_bitmask), packed.ctypes.data, 512)
        else:
            ctypes.memset(ctypes.addressof(in_f.constraint_bitmask), 0xFF, 512)

        if latent_vector.dtype != np.float64 or not latent_vector.flags.c_contiguous:
            latent_vector = np.ascontiguousarray(latent_vector, dtype=np.float64)

        ctypes.memmove(ctypes.addressof(in_f.latent_vector), latent_vector.ctypes.data, 32768)

        # 2. Phát lệnh ghi (Release store) thông báo cho Core Daemon
        slot.seq_in = seq

        # 3. Spin-wait phi khóa nhận phản hồi từ Core Daemon
        t_spin_start = time.perf_counter()
        while slot.seq_out != seq:
            if (time.perf_counter() - t_spin_start) * 1e6 > spin_timeout_us:
                raise TimeoutError(f"VivyQu Core SHM timeout ({spin_timeout_us} µs) on seq {seq}")

        t_recv_end = time.perf_counter()
        total_transport_us = (t_recv_end - t_send_start) * 1e6

        out_f = slot.out_frame
        return DecisionResult(
            best_index=int(out_f.best_decision_idx),
            confidence=float(out_f.best_confidence),
            valid_candidates=int(out_f.valid_candidates),
            latency_us=float(out_f.latency_core_ns) / 1000.0,
            norm_drift=float(out_f.norm_drift),
            is_valid=(out_f.error_code == ERR_NONE),
            sequence_id=int(out_f.sequence_id),
            error_code=int(out_f.error_code),
        )

    def step_fast(
        self,
        latent_ptr: int,
        mask_ptr: Optional[int] = None,
        spin_timeout_us: float = 500.0,
        mode_flags: int = MODE_GEOMETRIC_E9,
    ) -> Tuple[int, float, float]:
        """
        Fast-path qua Shared Memory loại bỏ hoàn toàn Python object allocation.
        Nhận con trỏ bộ nhớ trực tiếp (ctypes.data).
        Trả về: (best_index, core_latency_us, total_transport_us).
        """
        seq = self._seq_id
        self._seq_id += 1
        slot_idx = seq % RING_BUFFER_SLOTS
        slot = self._shm.slots[slot_idx]

        t_send_start = time.perf_counter()

        in_f = slot.in_frame
        in_f.magic_header = MAGIC_INPUT_FRAME
        in_f.sequence_id = seq
        in_f.version = ABI_VERSION_1_0
        in_f.mode_flags = mode_flags

        in_f.active_rotors = 0
        in_f.temperature = 1.0

        if mask_ptr is not None:
            ctypes.memmove(ctypes.addressof(in_f.constraint_bitmask), mask_ptr, 512)
        else:
            ctypes.memset(ctypes.addressof(in_f.constraint_bitmask), 0xFF, 512)

        ctypes.memmove(ctypes.addressof(in_f.latent_vector), latent_ptr, 32768)
        slot.seq_in = seq

        t_spin_start = time.perf_counter()
        while slot.seq_out != seq:
            if (time.perf_counter() - t_spin_start) * 1e6 > spin_timeout_us:
                raise TimeoutError(f"VivyQu Core SHM timeout ({spin_timeout_us} µs) on seq {seq}")

        t_recv_end = time.perf_counter()
        total_us = (t_recv_end - t_send_start) * 1e6
        out_f = slot.out_frame

        return int(out_f.best_decision_idx), float(out_f.latency_core_ns) / 1000.0, total_us

    def shutdown_daemon(self):
        """Ra lệnh đóng Core Daemon một cách an toàn."""
        self._shm.shutdown_flag = 1

    def close(self):
        if hasattr(self, "_pBuf") and self._pBuf:
            self._kernel32.UnmapViewOfFile(self._pBuf)
            self._pBuf = None
        if hasattr(self, "_hMap") and self._hMap:
            self._kernel32.CloseHandle(self._hMap)
            self._hMap = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
