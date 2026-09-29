#!/usr/bin/env python3
"""
Test Suite: Vivy 4-Organ Architecture Integration Test
======================================================
Kiểm định toàn diện kiến trúc 4 thành phần nhận thức tổng quát của Vivy:
1. Mắt (VivyquEyes): Ingestion thị giác & trạng thái thế giới (WorldSensoryFeed) -> Khối 1 & Khối 2.
2. Tai (VivyquEars): Ingestion ngữ nghĩa & âm học đa phương thức (AcousticSemanticFeed) -> Khối 4.
3. Tay (VivyquHands): Điều khiển trực tiếp bộ chấp hành (Actuator Dispatcher) từ StructuredAction 12-bit.
4. Memory (EpisodicMemoryBuffer): Lưu vết 10k episodes, NPS Pruning đào thải giả thuyết, Replay Hamiltonian Torque Descent.
5. Vòng lặp đóng kín (Closed-Loop Autonomous Cycle) từ quan sát -> suy luận Core -> hành động -> tự học.
"""

import os
import sys
import time
import pytest
import numpy as np

# Thêm thư mục python vào sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

from vivyqu import (
    VivyquEngine,
    VivyquEyes,
    WorldSensoryFeed,
    VivyquEars,
    AcousticSemanticFeed,
    VivyquHands,
    ExecutionReceipt,
    EpisodicMemoryBuffer,
    Episode,
    InputSplittingCodec,
    OutputStitchingCodec,
    StructuredAction,
    CL12_DIMENSION,
    CONSTRAINT_MASK_BYTES,
)


@pytest.fixture(scope="module")
def engine():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_path = os.path.join(root_dir, "data", "e9_weights.bin")
    eng = VivyquEngine()
    eng.load_e9_weights(weights_path)
    return eng


def test_codec_output_stitching_exhaustiveness():
    """Kiểm chứng tính toàn vẹn 100% của OutputStitchingCodec trên toàn bộ 4.096 mã nhị phân 12-bit."""
    print("\n[TEST CODEC] Verifying 4,096 distinct 12-bit action states...")

    for k in range(4096):
        action = OutputStitchingCodec.decode(k, confidence=0.95)
        assert action.best_index == k
        assert 0 <= action.action_intent_id < 8
        assert 0 <= action.intensity_tier_id < 8
        assert 0 <= action.horizon_tier_id < 8
        assert 0 <= action.parameter_tier_id < 8

        # Khôi phục ngược lại
        k_reconstructed = OutputStitchingCodec.encode(
            action.action_intent_id,
            action.intensity_tier_id,
            action.horizon_tier_id,
            action.parameter_tier_id,
        )
        assert k_reconstructed == k, f"Codec mismatch: {k} != {k_reconstructed}"

    print("      PASSED: 4,096 / 4,096 12-bit action configurations verified bitwise-exact!")


def test_eyes_sensory_ingestion():
    """Kiểm tra Mắt (Eyes): Ingestion trạng thái quan sát thế giới thành Khối 1 & 2."""
    eyes = VivyquEyes()

    feed = WorldSensoryFeed(
        timestamp_ns=time.time_ns(),
        spatial_state=np.random.randn(256),
        environmental_signals=np.random.randn(128),
        temporal_dynamics=np.random.randn(512),
        scale_factor=1.0,
    )

    block1 = eyes.perceive_spatial(feed)
    block2 = eyes.perceive_dynamics(feed)

    assert block1.shape == (1024,)
    assert block2.shape == (1024,)
    assert not np.isnan(block1).any()
    assert not np.isnan(block2).any()
    assert np.isclose(np.linalg.norm(block1), 1.0, atol=1e-5)
    assert np.isclose(np.linalg.norm(block2), 1.0, atol=1e-5)
    print("\n[TEST EYES] Block 1 (Spatial Perception) & Block 2 (Dynamics) generated cleanly.")


def test_ears_macro_audio_ingestion():
    """Kiểm tra Tai (Ears): Ingestion ngữ nghĩa & âm học đa phương thức thành Khối 4."""
    ears = VivyquEars()

    feed = AcousticSemanticFeed(
        timestamp_ns=time.time_ns(),
        signal_intensity=1.5,
        sentiment_valence=0.4,
        semantic_prompt_embedding=np.random.randn(1024),
        acoustic_feature_vector=np.random.randn(64),
        urgency_weight=1.2,
    )

    block4 = ears.listen_and_encode(feed)

    assert block4.shape == (1024,)
    assert not np.isnan(block4).any()
    assert np.isclose(np.linalg.norm(block4), 1.0, atol=1e-5)
    print("[TEST EARS] Block 4 (Semantic & Acoustic Perception) generated cleanly.")


def test_hands_actuator_dispatch():
    """Kiểm tra Tay (Hands): Thực thi trực tiếp tới bộ chấp hành, không có bộ lọc cản tĩnh."""
    dispatched_actions = []

    def mock_actuator_dispatcher(action_payload):
        dispatched_actions.append(action_payload)
        return {"status": 0, "message": "Command executed on physical actuator"}

    hands = VivyquHands(actuator_dispatcher=mock_actuator_dispatcher)

    # 1. Test hành động chủ động
    action = OutputStitchingCodec.decode(0b001_010_011_001, confidence=0.88)
    assert action.action_type == "ENGAGE_PRIMARY"

    receipt = hands.execute(action, target_subsystem="ARM_MANIPULATOR")
    assert receipt.success is True
    assert len(dispatched_actions) == 1
    assert dispatched_actions[0]["action_type"] == "ENGAGE_PRIMARY"
    assert dispatched_actions[0]["target"] == "ARM_MANIPULATOR"

    # 2. Test IDLE
    action_idle = OutputStitchingCodec.decode(0b000_000_000_000)
    receipt_idle = hands.execute(action_idle)
    assert receipt_idle.action_type == "IDLE"
    assert receipt_idle.success is True
    assert len(dispatched_actions) == 1  # Không bắn tới actuator khi IDLE

    print("[TEST HANDS] Executed directly without any programmatic filters.")


def test_memory_buffer_nps_pruning_and_replay(engine):
    """Kiểm tra Bộ Nhớ (Memory): Lưu trữ hồi ức lăn, cắt tỉa NPS Pruning và replay Hamiltonian Torque."""
    memory = EpisodicMemoryBuffer(capacity=100)

    # 1. Ghi nhận 10 episodes thành công và 5 episodes thất bại
    dummy_context = np.random.randn(CL12_DIMENSION)
    dummy_context /= np.linalg.norm(dummy_context)

    action_success = OutputStitchingCodec.decode(100)
    action_fail = OutputStitchingCodec.decode(777)

    for i in range(10):
        ep = Episode(
            sequence_id=i,
            timestamp_ns=time.time_ns(),
            latent_h=dummy_context,
            k_star=100,
            confidence=0.9,
            action=action_success,
            outcome_reward=1.0,
            execution_latency_us=50.0,
        )
        memory.record(ep)

    for i in range(10, 15):
        ep = Episode(
            sequence_id=i,
            timestamp_ns=time.time_ns(),
            latent_h=dummy_context,
            k_star=777,
            confidence=0.7,
            action=action_fail,
            outcome_reward=-1.0,
            execution_latency_us=50.0,
        )
        memory.record(ep)

    assert len(memory) == 15

    # 2. Kiểm tra NPS Pruning: action 777 bị trừ bitmask
    initial_mask = np.full(CONSTRAINT_MASK_BYTES, 0xFF, dtype=np.uint8)
    updated_mask, pruned_actions = memory.update_nps_pruning_mask(initial_mask, failure_threshold=3)

    assert 777 in pruned_actions
    byte_idx = 777 // 8
    bit_idx = 777 % 8
    assert (updated_mask[byte_idx] & (1 << bit_idx)) == 0, "Action 777 bit must be cleared!"
    print(f"\n[TEST MEMORY] NPS Pruning successfully pruned trapped actions: {pruned_actions}")

    # 3. Kiểm tra Replay Hamiltonian Torque Descent
    avg_loss = memory.replay_hamiltonian_descent(engine, batch_size=4, learning_rate=0.01)
    print(f"[TEST MEMORY] Replay Hamiltonian Torque Descent Loss: {avg_loss:.4f}")

    # 4. Xuất bài học markdown bền vững
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    os.makedirs(results_dir, exist_ok=True)
    export_path = os.path.join(results_dir, "memory_lessons_test.md")
    memory.export_durable_lessons_markdown(export_path)
    assert os.path.exists(export_path)
    print(f"[TEST MEMORY] Durable lessons exported to: {export_path}")


def test_vivy_four_organs_closed_loop(engine):
    """
    KIỂM THỬ TÍCH HỢP TOÀN DIỆN VÒNG LẶP ĐÓNG KÍN (FULL CLOSED-LOOP AUTONOMOUS CYCLE)
    Chu trình khép kín:
    1. MẮT (Eyes): Quan sát thế giới -> Khối 1 & 2 (2048D).
    2. TAI (Ears): Lắng nghe ngữ cảnh & âm thanh -> Khối 4 (1024D).
    3. CODEC: Ghép nối 4 khối -> vector h ∈ ℝ⁴⁰⁹⁶.
    4. NÃO (Core): Clifford Cl(12) suy luận sụp đổ hàm sóng xác định k* ∈ [0, 4095].
    5. TAY (Hands): Giải mã 12-bit và điều phối actuator.
    6. BỘ NHỚ (Memory): Ghi nhận hồi ức, NPS Pruning, và thích ứng qua Hamiltonian Torque Descent.
    """
    codec = InputSplittingCodec()
    eyes = VivyquEyes()
    ears = VivyquEars()
    hands = VivyquHands()
    memory = EpisodicMemoryBuffer(capacity=500)

    # Mặt nạ ràng buộc hợp lệ 512 bytes (mặc định tất cả cho phép)
    active_mask = np.full(CONSTRAINT_MASK_BYTES, 0xFF, dtype=np.uint8)

    num_cycles = 50
    cycle_latencies = []

    print("\n=========================================================")
    print("      VIVY 4-ORGAN FULL CLOSED-LOOP INTEGRATION TEST     ")
    print("=========================================================")

    for step in range(num_cycles):
        t_start = time.perf_counter_ns()

        # 1. Mắt thu nhận quan sát
        world_feed = WorldSensoryFeed(
            timestamp_ns=time.time_ns(),
            spatial_state=np.random.randn(256),
            environmental_signals=np.random.randn(128),
            temporal_dynamics=np.random.randn(512),
        )
        block1 = eyes.perceive_spatial(world_feed)
        block2 = eyes.perceive_dynamics(world_feed)

        # Khối 3: Trạng thái nội tại của tác nhân (1024D)
        block3 = np.zeros(1024, dtype=np.float64)
        block3[0] = 1.0  # Normalized vitality
        block3[1] = 0.5  # Battery / Resource

        # 2. Tai lắng nghe ngữ cảnh
        acoustic_feed = AcousticSemanticFeed(
            timestamp_ns=time.time_ns(),
            signal_intensity=1.0,
            sentiment_valence=0.2,
            semantic_prompt_embedding=np.random.randn(1024),
        )
        block4 = ears.listen_and_encode(acoustic_feed)

        # 3. Ghép nối cảm giác thành vector h ∈ ℝ⁴⁰⁹⁶
        h_state = codec.encode(block1, block2, block3, block4)

        # 4. Não bộ tính toán (VivyquEngine step_e9)
        best_k, conf, rc, latency_ns = engine.step_e9(h_state, active_mask)
        assert rc == 0
        assert 0 <= best_k < 4096

        # 5. Giải mã 12-bit và Tay bắn hành động tới bộ chấp hành
        action = OutputStitchingCodec.decode(best_k, confidence=conf)
        receipt = hands.execute(action, target_subsystem="PRIMARY_ACTUATOR")
        assert receipt.success is True

        # 6. Giả lập phản hồi từ môi trường
        synthetic_outcome = 1.0 if (best_k % 2 == 0) else -1.0
        synthetic_reward = 10.0 * synthetic_outcome

        # 7. Bộ nhớ lưu vết hồi ức chu kỳ
        episode = Episode(
            sequence_id=step,
            timestamp_ns=time.time_ns(),
            latent_h=h_state,
            k_star=best_k,
            confidence=conf,
            action=action,
            outcome_reward=synthetic_outcome,
            execution_latency_us=receipt.execution_latency_us,
        )
        memory.record(episode)

        t_end = time.perf_counter_ns()
        cycle_latencies.append((t_end - t_start) / 1000.0)  # Micro-seconds

    # Cập nhật NPS Pruning
    active_mask, pruned = memory.update_nps_pruning_mask(active_mask, failure_threshold=5)

    # Chạy Replay Hamiltonian Torque Descent
    replay_loss = memory.replay_hamiltonian_descent(engine, batch_size=8, learning_rate=0.02)

    p50 = np.percentile(cycle_latencies, 50)
    p95 = np.percentile(cycle_latencies, 95)
    p99 = np.percentile(cycle_latencies, 99)

    print(f"  Closed-Loop Iterations : {num_cycles} cycles")
    print(f"  Memory Episodes Stored : {len(memory)}")
    print(f"  NPS Actions Pruned     : {len(pruned)} actions")
    print(f"  Torque Descent Replay  : Avg Loss = {replay_loss:.4f}")
    print("---------------------------------------------------------")
    print(f"  End-to-End Cycle p50   : {p50:.2f} µs")
    print(f"  End-to-End Cycle p95   : {p95:.2f} µs")
    print(f"  End-to-End Cycle p99   : {p99:.2f} µs")
    print("=========================================================")
    print(">>> 4-ORGAN VIVY ARCHITECTURE IS OFFICIALLY OPERATIONAL! <<<\n")

    assert p50 < 1000.0, f"End-to-End latency p50 ({p50} µs) must be < 1000 µs (1 ms)!"


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_path = os.path.join(root_dir, "data", "e9_weights.bin")
    eng = VivyquEngine()
    eng.load_e9_weights(weights_path)
    test_codec_output_stitching_exhaustiveness()
    test_eyes_sensory_ingestion()
    test_ears_macro_audio_ingestion()
    test_hands_actuator_dispatch()
    test_memory_buffer_nps_pruning_and_replay(eng)
    test_vivy_four_organs_closed_loop(eng)
