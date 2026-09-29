#!/usr/bin/env python3
"""
VivyQu Watchdog Circuit Breaker & Cầu Treo Dispatcher Integration Test
======================================================================
Kiểm định toàn diện Tường Lửa Bảo Vệ 3 Cấp Độ theo SOP_OPERATIONAL_RUNBOOK.md:
1. Giai đoạn 1: Khởi động & Vận hành bình thường qua IPC-P Shared Memory (CLOSED state).
2. Giai đoạn 2: Giả lập Sự cố Cấp 2 (Timeout > 500 µs) -> Circuit Breaker trip sang Baseline A2 (OPEN state).
3. Giai đoạn 3: Phục hồi Tự động (OPEN -> HALF_OPEN -> CLOSED).
4. Giai đoạn 4: Giả lập Sự cố Cấp 3 (Tiến trình Daemon bị tiêu diệt) -> Tự động hạ cấp sang C-ABI DLL.
5. Giai đoạn 5: Kiểm định Bộ đệm Nhật ký Bay Telemetry (Flight Recorder).
"""

import os
import sys
import time
import subprocess
import ctypes
import numpy as np

# Thêm thư mục python vào sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from vivyqu import (
    VivyquEngine,
    VivyquShmClient,
    WatchdogSupervisor,
    CircuitState,
    IncidentLevel,
    CautreoDispatcher,
    CL12_DIMENSION,
)


def test_watchdog_integration():
    print("=" * 75)
    print("      VIVYQU SPRINT 5: WATCHDOG CIRCUIT BREAKER & CAUTREO TEST      ")
    print("=" * 75)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    daemon_exe = os.path.join(root_dir, "build", "bin", "vivyqu_shm_daemon.exe")

    # 1. Khởi động Core Daemon
    print("\n[1/5] Booting Core Daemon & Establishing Dual-Tier Interfaces...")
    proc = subprocess.Popen([daemon_exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.3)

    assert proc.poll() is None, "Daemon failed to start!"
    print(f"      Core Daemon PID: {proc.pid}")

    shm_client = VivyquShmClient()
    dll_engine = VivyquEngine()

    watchdog = WatchdogSupervisor(
        shm_client=shm_client,
        dll_engine=dll_engine,
        timeout_us=1500.0,
        max_consecutive_failures=3,
        half_open_probe_interval=20,
    )

    dispatched_actions = []

    def action_callback(action_idx: int, confidence: float, latency_us: float):
        dispatched_actions.append(action_idx)

    dispatcher = CautreoDispatcher(watchdog=watchdog, action_callback=action_callback)
    print("      Dual-Tier Watchdog & CautreoDispatcher initialized successfully (PASS)")

    try:
        # Giai đoạn 1: Vận hành bình thường (CLOSED)
        print("\n[2/5] Testing Normal Operation (Circuit CLOSED, Primary IPC-P)...")
        # Chuẩn bị mặt nạ ràng buộc an toàn (cho phép 50 actions)
        allowed_set = list(range(100, 150))
        mask_bool = np.zeros(CL12_DIMENSION, dtype=bool)
        mask_bool[allowed_set] = True
        packed_mask = np.packbits(mask_bool, bitorder='little')

        for i in range(200):
            latent = np.random.randn(CL12_DIMENSION).astype(np.float64)
            res = dispatcher.dispatch(latent, constraint_mask_bytes=packed_mask)
            assert res.best_index in allowed_set, "Constraint violation in normal operation!"
            assert res.is_valid, "Decision must be valid!"

        assert watchdog.state == CircuitState.CLOSED, "State should be CLOSED!"
        print(f"      200/200 cycles executed via IPC-P Shared Memory")
        print(f"      Circuit State: {watchdog.state.value} (PASS)")
        print(f"      Constraint Validity: 100.0% (PASS)")

        # Giai đoạn 2: Giả lập Sự cố Cấp 2 (Timeout > 500 µs & Circuit Breaker Trip)
        print("\n[3/5] Simulating Incident Level 2 (Timeout & Circuit Breaker Trip)...")
        # Fault injection xác định: TimeoutError nhân tạo (không dựa wall-clock —
        # SHM có thể trả về ngay nên timeout_us nhỏ không chắc kích OPEN).
        class _InjectedTimeoutShm:
            def __init__(self, real, fail_times):
                self._real = real
                self.fail_times = fail_times

            def step(self, *args, **kwargs):
                if self.fail_times > 0:
                    self.fail_times -= 1
                    raise TimeoutError("injected Level 2 Core Timeout")
                return self._real.step(*args, **kwargs)

        real_shm = watchdog.shm_client
        watchdog.shm_client = _InjectedTimeoutShm(real_shm, fail_times=5)

        fallback_results = []
        for i in range(10):
            latent = np.random.randn(CL12_DIMENSION).astype(np.float64)
            t_call0 = time.perf_counter()
            res = dispatcher.dispatch(latent, constraint_mask_bytes=packed_mask)
            t_call_us = (time.perf_counter() - t_call0) * 1e6

            fallback_results.append(res)
            # Khi mạch đã OPEN: bảo đảm trả về tức thì < 1000 µs (1 ms Windows scheduler SLA)
            if watchdog.state == CircuitState.OPEN:
                assert t_call_us < 1000.0, f"Call latency too high when OPEN: {t_call_us} µs"
            assert res.best_index in allowed_set, f"Fallback constraint violation: {res.best_index}"

        # Sau 3 lần timeout liên tiếp, Circuit Breaker phải chuyển sang OPEN
        assert watchdog.state == CircuitState.OPEN, f"Circuit should be OPEN, got {watchdog.state.value}"
        print(f"      Circuit Breaker successfully tripped to: {watchdog.state.value} (PASS)")
        print(f"      Zero Frame-Drop Confirmed: Fallback decisions completed in < 1000 µs when OPEN")

        print(f"      Fallback Validity Rate: 100.0% (PASS)")

        # Giai đoạn 3: Kiểm tra Phục hồi Tự động (Auto-Recovery)
        print("\n[4/5] Testing Auto-Recovery Protocol (OPEN -> HALF_OPEN -> CLOSED)...")
        # Khôi phục SHM thật + timeout bình thường
        watchdog.shm_client = real_shm
        watchdog.timeout_us = 1500.0

        # Chạy 30 chu kỳ (vượt qua half_open_probe_interval = 20)
        for i in range(30):
            latent = np.random.randn(CL12_DIMENSION).astype(np.float64)
            dispatcher.dispatch(latent, constraint_mask_bytes=packed_mask)

        assert watchdog.state == CircuitState.CLOSED, f"Circuit should auto-recover to CLOSED, got {watchdog.state.value}"
        print(f"      Auto-Recovery Confirmed: State restored to {watchdog.state.value} (PASS)")

        # Giai đoạn 4: Giả lập Sự cố Cấp 3 (Process Crash / Daemon Termination)
        print("\n[5/5] Simulating Incident Level 3 (Core Crash & Auto-Downgrade to C-ABI DLL)...")
        # Tiêu diệt tiến trình Daemon
        proc.kill()
        proc.wait(timeout=2.0)
        print(f"      Daemon process terminated (PID: {proc.pid})")

        # Cầu Treo gửi tiếp lệnh: Watchdog phải tự động bắt exception và chuyển sang C-ABI DLL
        dll_fallback_count = 0
        for i in range(50):
            latent = np.random.randn(CL12_DIMENSION).astype(np.float64)
            res = dispatcher.dispatch(latent, constraint_mask_bytes=packed_mask)
            assert res.best_index in allowed_set, "Level 3 constraint violation!"
            assert res.is_valid, "Decision must be valid!"
            dll_fallback_count += 1

        print(f"      Level 3 Auto-Downgrade Successful: 50/50 decisions handled without crash (PASS)")

        # Kiểm tra Telemetry Flight Recorder
        telemetry = dispatcher.get_telemetry_summary()
        print("\n" + "=" * 75)
        print("                 FLIGHT RECORDER TELEMETRY SUMMARY               ")
        print("=" * 75)
        print(f"Total Dispatched Frames  : {telemetry['total_dispatched_cautreo']}")
        print(f"Fallback Executions      : {telemetry['fallback_count']}")
        print(f"Level 2 Incidents        : {telemetry['incident_level2_count']}")
        print(f"Level 3 Incidents        : {telemetry['incident_level3_count']}")
        print(f"Latency p50              : {telemetry['latency_p50_us']:.2f} µs")
        print(f"Latency p95              : {telemetry['latency_p95_us']:.2f} µs")
        print(f"Latency p99              : {telemetry['latency_p99_us']:.2f} µs")
        print(f"Avg Dispatcher Overhead  : {telemetry['avg_dispatcher_latency_us']:.2f} µs")
        print("=" * 75)

    finally:
        if proc.poll() is None:
            proc.kill()

    print("\n>>> SPRINT 5: WATCHDOG & CAUTREO INTEGRATION ACCEPTED WITH 100% PASS <<<")


if __name__ == "__main__":
    test_watchdog_integration()
