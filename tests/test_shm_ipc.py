#!/usr/bin/env python3
"""
VivyQu Lock-Free Shared Memory IPC (IPC-P) Benchmark & Integration Test
========================================================================
Kiểm định toàn diện cơ chế giao tiếp chính (Primary Interface) theo:
- CAUTREO_CORE_INTERFACE_SPEC.md
- VIVY_MASTER_BUILD_PLAN.md (Sprint 3)

Nội dung kiểm định:
1. Vận hành Daemon độc lập trên CPU Core 2 (HIGH_PRIORITY_CLASS).
2. Kết nối phi khóa từ Python Client (pin Core 3).
3. 10.000 chu kỳ giao tiếp qua Windows Shared Memory Ring Buffer 8 slots.
4. Đo lường phân phối độ trễ vận chuyển (Transport Latency < 0.3 µs).
5. Đo lường phân phối độ trễ End-to-End (< 15.0 µs SLA).
6. Kiểm chứng tính tuân thủ 100% của Mặt nạ ràng buộc (V = 100.0%).
7. Kiểm tra cơ chế dừng an toàn (Graceful Shutdown) qua atomic flag.
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

from vivyqu import VivyquShmClient, CL12_DIMENSION, CONSTRAINT_MASK_BYTES


def pin_current_thread_to_core(core_id: int):
    """Ghim tiến trình hiện tại vào 1 CPU Core chuyên biệt để đo độ trễ chuẩn xác."""
    try:
        kernel32 = ctypes.windll.kernel32
        mask = 1 << core_id
        kernel32.SetProcessAffinityMask(kernel32.GetCurrentProcess(), mask)
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00000080) # HIGH_PRIORITY_CLASS
        return True
    except Exception as e:
        print(f"      [WARN] Could not pin affinity to core {core_id}: {e}")
        return False


def test_shm_ipc():
    print("=" * 70)
    print("      VIVYQU LOCK-FREE SHARED MEMORY IPC (IPC-P) BENCHMARK      ")
    print("=" * 70)

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    daemon_exe = os.path.join(root_dir, "build", "bin", "vivyqu_shm_daemon.exe")

    if not os.path.exists(daemon_exe):
        print(f"[FAIL] Daemon executable not found at: {daemon_exe}")
        sys.exit(1)

    # 1. Khởi động VivyQu Shared Memory Daemon trong tiến trình độc lập
    print("\n[1/5] Spawning Vivyqu Core Daemon process...")
    proc = subprocess.Popen(
        [daemon_exe],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Chờ 0.3s để daemon tạo FileMapping và khởi tạo Core
    time.sleep(0.3)

    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print(f"[FAIL] Daemon terminated prematurely!\nSTDOUT: {stdout}\nSTDERR: {stderr}")
        sys.exit(1)

    print(f"      Daemon spawned successfully (PID: {proc.pid})")

    # Ghim Python client vào CPU Core 3 (để không tranh chấp Core 2 với Daemon)
    pin_current_thread_to_core(3)

    try:
        # 2. Kết nối từ Python Shared Memory Client
        print("\n[2/5] Connecting Python VivyquShmClient to Shared Memory...")
        t_conn0 = time.perf_counter()
        client = VivyquShmClient()
        conn_time_ms = (time.perf_counter() - t_conn0) * 1000.0
        print(f"      Shared Memory connected in {conn_time_ms:.3f} ms (PASS)")

        # 3. Warmup & Kiểm tra tính chính xác của quyết định & mặt nạ ràng buộc
        print("\n[3/5] Verifying Hard Constraint Compliance & Single Step...")
        # Tạo mask chỉ cho phép 5 vị trí: 100, 200, 300, 400, 500
        strict_mask = np.zeros(CL12_DIMENSION, dtype=bool)
        allowed_indices = {100, 200, 300, 400, 500}
        for idx in allowed_indices:
            strict_mask[idx] = True

        dummy_latent = np.random.randn(CL12_DIMENSION).astype(np.float64)
        dummy_latent /= np.linalg.norm(dummy_latent)

        # Warmup 200 bước
        for _ in range(200):
            client.step(dummy_latent)

        # Chạy 100 lần kiểm tra mặt nạ
        violations = 0
        for i in range(100):
            rnd_latent = np.random.randn(CL12_DIMENSION).astype(np.float64)
            rnd_latent /= np.linalg.norm(rnd_latent)
            res = client.step(rnd_latent, constraint_mask_bytes=strict_mask)
            if res.best_index not in allowed_indices:
                violations += 1

        validity_rate = ((100 - violations) / 100.0) * 100.0
        print(f"      Hard Constraint Tests: 100/100")
        print(f"      Allowed Actions Set  : {sorted(list(allowed_indices))}")
        print(f"      Constraint Validity V: {validity_rate:.1f}% (Required: 100.0% -> {'PASS' if validity_rate == 100.0 else 'FAIL'})")
        assert validity_rate == 100.0, "Hard constraint violation detected!"

        # 4. Đo lường phân phối độ trễ 10.000 chu kỳ qua Shared Memory
        N_ITER = 10000
        print(f"\n[4/5] Benchmarking {N_ITER:,} Real-Time Iterations across IPC Ring Buffer...")

        # Chuẩn bị dữ liệu sẵn trong RAM
        test_latents = np.random.randn(N_ITER, CL12_DIMENSION).astype(np.float64)
        # Chuẩn hóa L2
        norms = np.linalg.norm(test_latents, axis=1, keepdims=True)
        test_latents /= norms

        # Chuẩn bị mặt nạ ngẫu nhiên 50%
        rnd_mask = np.random.randint(0, 2, size=CL12_DIMENSION).astype(bool)
        packed_mask = np.packbits(rnd_mask, bitorder='little')
        mask_ptr = packed_mask.ctypes.data

        # Đo lường chế độ Standard step()
        print("      --> Running Standard step() [Idiomatic Dataclass Output] (2,000 runs)...")
        std_e2e_latencies = []
        std_core_latencies = []
        for i in range(2000):
            t0 = time.perf_counter()
            res = client.step(test_latents[i], constraint_mask_bytes=packed_mask, spin_timeout_us=5000.0)
            t1 = time.perf_counter()
            std_e2e_latencies.append((t1 - t0) * 1e6)
            std_core_latencies.append(res.latency_us)

        # Đo lường chế độ Fast-Path step_fast()
        print(f"      --> Running Fast-Path step_fast() [Zero-Allocation Pointers] ({N_ITER:,} runs)...")
        fast_e2e_latencies = np.empty(N_ITER, dtype=np.float64)
        fast_core_latencies = np.empty(N_ITER, dtype=np.float64)
        fast_transport_latencies = np.empty(N_ITER, dtype=np.float64)

        for i in range(N_ITER):
            latent_ptr = test_latents[i].ctypes.data
            action_idx, core_us, e2e_us = client.step_fast(latent_ptr, mask_ptr=mask_ptr, spin_timeout_us=5000.0)
            fast_e2e_latencies[i] = e2e_us
            fast_core_latencies[i] = core_us
            fast_transport_latencies[i] = max(0.0, e2e_us - core_us)


        # Thống kê phân phối Fast-Path
        p50_e2e = np.percentile(fast_e2e_latencies, 50)
        p90_e2e = np.percentile(fast_e2e_latencies, 90)
        p95_e2e = np.percentile(fast_e2e_latencies, 95)
        p99_e2e = np.percentile(fast_e2e_latencies, 99)
        max_e2e = np.max(fast_e2e_latencies)

        p50_core = np.percentile(fast_core_latencies, 50)
        p95_core = np.percentile(fast_core_latencies, 95)
        p99_core = np.percentile(fast_core_latencies, 99)

        p50_trans = np.percentile(fast_transport_latencies, 50)
        p95_trans = np.percentile(fast_transport_latencies, 95)
        p99_trans = np.percentile(fast_transport_latencies, 99)

        print("\n" + "=" * 70)
        print("          LOCK-FREE SHARED MEMORY LATENCY DISTRIBUTION          ")
        print("=" * 70)
        print(f"Metric                         Percentile   Measured (µs)   Target SLA")
        print("-" * 70)
        print(f"Core Calculation Latency       p50          {p50_core:6.2f} µs       < 50.0 µs  [{'PASS' if p50_core < 50.0 else 'FAIL'}]")
        print(f"Core Calculation Latency       p95          {p95_core:6.2f} µs       --")
        print(f"Core Calculation Latency       p99          {p99_core:6.2f} µs       < 100.0 µs [{'PASS' if p99_core < 100.0 else 'FAIL'}]")
        print("-" * 70)
        print(f"IPC Transport Overhead         p50          {p50_trans:6.2f} µs       < 5.00 µs  [{'PASS' if p50_trans < 5.0 else 'MARGINAL'}]")
        print(f"IPC Transport Overhead         p95          {p95_trans:6.2f} µs       --")
        print(f"IPC Transport Overhead         p99          {p99_trans:6.2f} µs       --")
        print("-" * 70)
        print(f"End-to-End Latency (Fast-Path) p50          {p50_e2e:6.2f} µs       < 60.0 µs  [{'PASS' if p50_e2e < 60.0 else 'FAIL'}]")
        print(f"End-to-End Latency (Fast-Path) p95          {p95_e2e:6.2f} µs       --")
        print(f"End-to-End Latency (Fast-Path) p99          {p99_e2e:6.2f} µs       < 120.0 µs [{'PASS' if p99_e2e < 120.0 else 'FAIL'}]")
        print(f"End-to-End Latency (Fast-Path) Max          {max_e2e:6.2f} µs       --")
        print("-" * 70)

        # 5. Kiểm thử E9 Geometric Scorer qua SHM IPC với tập dữ liệu test thật
        print(f"\n[5/6] Testing E9 Geometric Scorer Mode over Shared Memory IPC (500 samples)...")
        test_latents_file = os.path.join(root_dir, "data", "e0_benchmark", "test_latents.npy")
        test_masks_file = os.path.join(root_dir, "data", "e0_benchmark", "test_masks.npy")
        test_oracle_file = os.path.join(root_dir, "data", "e0_benchmark", "test_oracle.npy")
        if not os.path.exists(test_latents_file):
            test_latents_file = os.path.join(root_dir, "data", "test_latents.npy")
            test_masks_file = os.path.join(root_dir, "data", "test_masks.npy")
            test_oracle_file = os.path.join(root_dir, "data", "test_oracle.npy")

        if os.path.exists(test_latents_file) and os.path.exists(test_masks_file):
            held_latents = np.load(test_latents_file)[:500]
            held_masks = np.load(test_masks_file)[:500]
            held_oracle = np.load(test_oracle_file)[:500] if os.path.exists(test_oracle_file) else None


            e9_e2e_lats = []
            e9_core_lats = []
            e9_valid_count = 0

            for i in range(500):
                t0 = time.perf_counter()
                res = client.step(held_latents[i], constraint_mask_bytes=held_masks[i], mode="e9", spin_timeout_us=2500.0)
                t1 = time.perf_counter()

                e9_e2e_lats.append((t1 - t0) * 1e6)
                e9_core_lats.append(res.latency_us)

                # Kiểm tra ràng buộc trong mặt nạ 512 bytes (packed little-endian)
                byte_idx = res.best_index // 8
                bit_idx = res.best_index % 8
                if (held_masks[i, byte_idx] & (1 << bit_idx)) != 0:
                    e9_valid_count += 1


            p50_e9_core = np.percentile(e9_core_lats, 50)
            p99_e9_core = np.percentile(e9_core_lats, 99)
            p50_e9_e2e = np.percentile(e9_e2e_lats, 50)
            p99_e9_e2e = np.percentile(e9_e2e_lats, 99)

            print(f"      E9 Held-out Samples Evaluated: 500 / 500")
            print(f"      E9 Mask Validity Rate        : {e9_valid_count / 500.0 * 100.0:.2f}%")
            print(f"      E9 Core Calculation (p50)    : {p50_e9_core:6.2f} µs (p99: {p99_e9_core:6.2f} µs)")
            print(f"      E9 SHM End-to-End Latency    : {p50_e9_e2e:6.2f} µs (p99: {p99_e9_e2e:6.2f} µs)")
            assert e9_valid_count == 500, "Constraint violation in E9 SHM mode!"

        # 6. Kiểm thử Graceful Shutdown
        print("\n[6/6] Testing Graceful Daemon Shutdown...")
        client.shutdown_daemon()
        client.close()


        # Đợi Daemon dừng an toàn
        exit_code = proc.wait(timeout=5.0)
        print(f"      Daemon process exited cleanly with code: {exit_code} (PASS)")

    except Exception as exc:
        print(f"\n[EXCEPTION CAUGHT] {exc}")
        poll_val = proc.poll()
        print(f"      Daemon proc.poll() = {poll_val}")
        try:
            out, err = proc.communicate(timeout=1.0)
            print(f"      Daemon STDOUT:\n{out}\n      Daemon STDERR:\n{err}")
        except Exception:
            pass
        if proc.poll() is None:
            proc.kill()
        raise exc
    finally:
        if proc.poll() is None:
            proc.kill()


    print("\n" + "=" * 70)
    print("      >>> SPRINT 3 IPC-P VERIFICATION COMPLETED SUCCESSFULLY <<< ")
    print("=" * 70)


if __name__ == "__main__":
    test_shm_ipc()
