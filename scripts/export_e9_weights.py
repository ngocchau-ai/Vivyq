"""
Export Branch C / E9 weights to high-performance binary format for C++ Core.
=============================================================================
Structure of e9_weights.bin:
- Magic: uint64 (0x564956595F453957 = "VIVY_E9W")
- Version: uint32 (1)
- cl12_dim: uint32 (4096)
- subspace_dim: uint32 (64)
- num_rotors: uint32 (8)
- topology_lambda: float32 (0.3)
- reserved: 40 bytes (align header to 64 bytes)
- rotors: 8 * RotorConfig (8 * 8 = 64 bytes)
  RotorConfig: uint8 plane_i, uint8 plane_j, uint16 reserved, float32 angle_theta
- W_c: 64 * 4096 * float32 (1,048,576 bytes)
- candidate_codebook: 4096 * 64 * float32 (1,048,576 bytes)
- topology_cost: 4096 * float32 (16,384 bytes)
- Total size: 64 + 64 + 1048576 + 1048576 + 16384 = 2,113,664 bytes (2.0157 MiB)
"""

import os
import struct
import numpy as np

def export_e9_weights():
    weights_path = os.path.join("results", "branch_c", "branch_c_weights.npz")
    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Missing weights file at {weights_path}")
    
    data = np.load(weights_path)
    W_c = np.ascontiguousarray(data["W_c"], dtype=np.float32) # (64, 4096)
    codebook = np.ascontiguousarray(data["candidate_codebook"], dtype=np.float32) # (4096, 64)
    cost = np.ascontiguousarray(data["topology_cost"], dtype=np.float32) # (4096,)
    rotors = data["rotors_config"] # (8, 3)
    
    assert W_c.shape == (64, 4096), f"Unexpected W_c shape: {W_c.shape}"
    assert codebook.shape == (4096, 64), f"Unexpected codebook shape: {codebook.shape}"
    assert cost.shape == (4096,), f"Unexpected cost shape: {cost.shape}"
    assert rotors.shape == (8, 3), f"Unexpected rotors shape: {rotors.shape}"
    
    out_dir = os.path.join("data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "e9_weights.bin")
    
    magic = 0x564956595F453957 # "VIVY_E9W"
    version = 1
    cl12_dim = 4096
    subspace_dim = 64
    num_rotors = len(rotors)
    topology_lambda = 0.3
    
    with open(out_path, "wb") as f:
        # Header (64 bytes)
        # Q: uint64 magic (8)
        # I: uint32 version (4)
        # I: uint32 cl12_dim (4)
        # I: uint32 subspace_dim (4)
        # I: uint32 num_rotors (4)
        # f: float32 topology_lambda (4)
        # 36x: padding (36) -> total 64 bytes
        header_bytes = struct.pack(
            "<QIIII f 36x",
            magic,
            version,
            cl12_dim,
            subspace_dim,
            num_rotors,
            topology_lambda
        )
        assert len(header_bytes) == 64, f"Header len {len(header_bytes)} != 64"
        f.write(header_bytes)
        
        # Rotors (8 * 8 = 64 bytes)
        for r in rotors:
            pi, pj, th = int(r[0]), int(r[1]), float(r[2])
            rotor_bytes = struct.pack("<BBHf", pi, pj, 0, th)
            assert len(rotor_bytes) == 8
            f.write(rotor_bytes)
            
        # W_c (1,048,576 bytes)
        f.write(W_c.tobytes())
        
        # Candidate codebook (1,048,576 bytes)
        f.write(codebook.tobytes())
        
        # Topology cost (16,384 bytes)
        f.write(cost.tobytes())
        
    total_size = os.path.getsize(out_path)
    print(f"Exported E9 binary weights to {out_path}")
    print(f"Total size: {total_size} bytes ({total_size / (1024*1024):.4f} MiB)")
    
    # Also save a copy in results/branch_c
    copy_path = os.path.join("results", "branch_c", "e9_weights.bin")
    with open(copy_path, "wb") as f_copy:
        with open(out_path, "rb") as f_src:
            f_copy.write(f_src.read())
    print(f"Copied to {copy_path}")

if __name__ == "__main__":
    export_e9_weights()
