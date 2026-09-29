#!/usr/bin/env python3
"""
VivyQu E0 Benchmark Dataset Generator
====================================
Kịch bản sinh bộ dữ liệu thực nghiệm E0 chuẩn mực theo đặc tả EXPERIMENT_E0_BENCHMARK_SPEC.md.

Thông số quy chuẩn:
- Số chiều: 4.096
- Tổng số mẫu: 10.000 (Train: 7.000, Val: 1.500, Test: 1.500)
- Hạt giống cố định:
    * SEED_LATENT    = 20260927
    * SEED_LANDSCAPE = 42
    * SEED_SPLIT     = 1337
- Đầu ra lưu tại: data/e0_benchmark/
"""

import os
import sys
import json
import hashlib
import time
import numpy as np

# --- CẤU HÌNH HẰNG SỐ QUY CHUẨN ---
CL12_DIMENSION = 4096
CONSTRAINT_BYTES = 512 # 4096 bits
TOTAL_SAMPLES = 10000

SEED_LATENT = 20260927
SEED_LANDSCAPE = 42
SEED_SPLIT = 1337

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "e0_benchmark")


def compute_sha256(filepath):
    """Tính mã băm SHA-256 của file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_e0_dataset():
    start_time = time.time()
    print("=" * 65)
    print("       VIVYQU E0 BENCHMARK DATASET GENERATION PIPELINE       ")
    print("=" * 65)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Sinh ma trận thế năng và vector đặc trưng ứng viên (Oracle Ground Truth Reference)
    print("\n[1/5] Synthesizing Energy Landscape & Candidate Codebook (Seed = {})...".format(SEED_LANDSCAPE))
    rng_landscape = np.random.default_rng(SEED_LANDSCAPE)
    
    # 4096 vector đặc trưng cơ sở u_k ∈ R^4096 (chuẩn hóa trên mặt cầu đơn vị)
    # Dùng ma trận đường chéo phân rã rank thấp để tính toán nhanh
    candidate_codebook = rng_landscape.standard_normal((CL12_DIMENSION, 64), dtype=np.float32)
    candidate_codebook /= np.linalg.norm(candidate_codebook, axis=1, keepdims=True) + 1e-12

    # Chi phí tô-pô nội tại của từng cấu hình
    topology_cost = rng_landscape.uniform(0.0, 1.0, size=CL12_DIMENSION).astype(np.float32)

    # 2. Sinh 10.000 vector ngữ cảnh đầu vào h ∈ R^4096
    print("[2/5] Generating {} Context Vectors (Seed = {})...".format(TOTAL_SAMPLES, SEED_LATENT))
    rng_latent = np.random.default_rng(SEED_LATENT)
    
    # Sinh phân phối chuẩn đa biến mô phỏng kích hoạt tầng ẩn LLM
    latents = rng_latent.standard_normal((TOTAL_SAMPLES, CL12_DIMENSION), dtype=np.float32)
    # Chuẩn hóa L2
    latents /= np.linalg.norm(latents, axis=1, keepdims=True) + 1e-12

    # Chèn 5% Outliers và 5% Mẫu tiệm cận biên
    num_outliers = int(TOTAL_SAMPLES * 0.05)
    outlier_idx = rng_latent.choice(TOTAL_SAMPLES, size=num_outliers, replace=False)
    latents[outlier_idx] *= rng_latent.uniform(5.0, 10.0, size=(num_outliers, 1))

    # 3. Sinh mặt nạ ràng buộc cứng (512 bytes / 4096 bits mỗi mẫu)
    print("[3/5] Generating Hard Constraint Bitmasks (Target Valid Ratio: 15% - 25%)...")
    masks_packed = np.zeros((TOTAL_SAMPLES, CONSTRAINT_BYTES), dtype=np.uint8)
    oracle_best_idx = np.zeros(TOTAL_SAMPLES, dtype=np.uint32)
    oracle_min_energy = np.zeros(TOTAL_SAMPLES, dtype=np.float32)

    # Chiếu latents về không gian rank 64 để tính điểm alignment nhanh
    # Project: proj_h = latents @ W_proj
    proj_matrix = rng_landscape.standard_normal((CL12_DIMENSION, 64), dtype=np.float32) * 0.1
    latents_proj = latents @ proj_matrix # Shape (10000, 64)

    # 4. Tính toán Oracle Chân Lý cho từng mẫu
    print("[4/5] Computing Ground-Truth Oracle Solutions (Batch Evaluation)...")
    for i in range(TOTAL_SAMPLES):
        # Sinh bitmask ngẫu nhiên với xác suất hợp lệ p ≈ 0.20
        valid_prob = rng_latent.uniform(0.12, 0.28)
        mask_bool = rng_latent.random(CL12_DIMENSION) < valid_prob
        # Đảm bảo có ít nhất 10 ứng viên hợp lệ
        if np.sum(mask_bool) < 10:
            mask_bool[:100] = True
        
        # Nén 4096 booleans thành 512 bytes (chuẩn hóa bitorder='little' đồng bộ C++ _tzcnt_u64)
        masks_packed[i] = np.packbits(mask_bool, bitorder='little')

        # Tính toán thế năng: V(k) = - <u_k, proj_h> + 0.3 * topology_cost
        h_p = latents_proj[i] # (64,)
        alignment = candidate_codebook @ h_p # (4096,)
        energy = -alignment + 0.3 * topology_cost # (4096,)

        # Áp dụng mặt nạ ràng buộc: gán infinity cho ứng viên vi phạm
        energy[~mask_bool] = np.inf

        best_k = np.argmin(energy)
        oracle_best_idx[i] = best_k
        oracle_min_energy[i] = energy[best_k]

        if (i + 1) % 2000 == 0:
            print("      Processed {} / {} samples...".format(i + 1, TOTAL_SAMPLES))

    # 5. Phân chia Train / Val / Test theo tỷ lệ 70 / 15 / 15
    print("\n[5/5] Splitting Dataset (70% Train, 15% Val, 15% Test) with Seed = {}...".format(SEED_SPLIT))
    rng_split = np.random.default_rng(SEED_SPLIT)
    indices = np.arange(TOTAL_SAMPLES)
    rng_split.shuffle(indices)

    train_idx = indices[:7000]
    val_idx = indices[7000:8500]
    test_idx = indices[8500:]

    dataset_dict = {
        "train": (latents[train_idx], masks_packed[train_idx], oracle_best_idx[train_idx]),
        "val": (latents[val_idx], masks_packed[val_idx], oracle_best_idx[val_idx]),
        "test": (latents[test_idx], masks_packed[test_idx], oracle_best_idx[test_idx]),
    }

    checksums = {}

    for split_name, (sub_latent, sub_masks, sub_oracle) in dataset_dict.items():
        latent_path = os.path.join(OUTPUT_DIR, f"{split_name}_latents.npy")
        masks_path = os.path.join(OUTPUT_DIR, f"{split_name}_masks.npy")
        oracle_path = os.path.join(OUTPUT_DIR, f"{split_name}_oracle.npy")

        np.save(latent_path, sub_latent)
        np.save(masks_path, sub_masks)
        np.save(oracle_path, sub_oracle)

        checksums[f"{split_name}_latents.npy"] = compute_sha256(latent_path)
        checksums[f"{split_name}_masks.npy"] = compute_sha256(masks_path)
        checksums[f"{split_name}_oracle.npy"] = compute_sha256(oracle_path)

        print(f"      Saved {split_name.upper():5s} | Latents: {sub_latent.shape} | Masks: {sub_masks.shape} | Oracle: {sub_oracle.shape}")

    # Ghi nhận metadata và SHA-256
    metadata = {
        "dataset_name": "Vivyqu_E0_Benchmark_Dataset",
        "version": "1.0-Locked",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dimension": CL12_DIMENSION,
        "total_samples": TOTAL_SAMPLES,
        "splits": {"train": len(train_idx), "val": len(val_idx), "test": len(test_idx)},
        "seeds": {
            "SEED_LATENT": SEED_LATENT,
            "SEED_LANDSCAPE": SEED_LANDSCAPE,
            "SEED_SPLIT": SEED_SPLIT
        },
        "checksums": checksums
    }

    metadata_path = os.path.join(OUTPUT_DIR, "dataset_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    sha_manifest_path = os.path.join(OUTPUT_DIR, "checksums.sha256")
    with open(sha_manifest_path, "w", encoding="utf-8") as f:
        for fname, sha in checksums.items():
            f.write(f"{sha}  {fname}\n")

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print("SUCCESS: E0 Dataset generated in {:.2f}s".format(elapsed))
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Checksums Manifest: {sha_manifest_path}")
    print("=" * 65)


if __name__ == "__main__":
    generate_e0_dataset()
