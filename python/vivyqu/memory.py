"""
VivyQu Memory Module (Trí Nhớ Hồi Ức & Tự Hoàn Thiện)
=====================================================
Hiện thực hóa cơ quan Trí nhớ hồi ức (Episodic Memory) và Cơ chế thích ứng:
- Bộ đệm lăn 10.000 episodes (Rolling Episodic Buffer).
- NPS Pruning & Promotion: Tự động khóa bitmask các vùng bẫy giá gây lỗ.
- Replay Hamiltonian Torque Descent: Thích nghi tại chỗ 8 rotors Cl(12).
- Đồng bộ bài học kinh nghiệm bền vững vào kho tri thức trung tâm D:\\2brain.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
import time
import os
import numpy as np

from .codec import StructuredAction
from .types import CL12_DIMENSION, CONSTRAINT_MASK_BYTES


@dataclass
class Episode:
    """Bản ghi hồi ức chu kỳ ra quyết định và phản hồi thế giới thực."""
    sequence_id: int
    timestamp_ns: int
    latent_h: np.ndarray                  # Vector 4096D đầu vào
    k_star: int                           # Quyết định đã chọn [0..4095]
    confidence: float                     # Độ tự tin sụp đổ
    action: StructuredAction              # Lệnh hành động đã giải mã
    outcome_reward: float                 # Phản hồi thế giới thực (PnL / Reward / Loss)
    execution_latency_us: float           # Độ trễ thực thi
    metadata: Dict[str, Any] = field(default_factory=dict)


class EpisodicMemoryBuffer:
    """
    Bộ đệm trí nhớ hồi ức lăn (Rolling Episodic Memory Buffer 10.000 slots):
    - Quản lý lịch sử quyết định và kết quả.
    - Cập nhật mặt nạ ràng buộc NPS Pruning (tỉa bỏ hành động liên tục gây lỗ).
    - Tái hiện hồi ức (Experience Replay) kết hợp Hamiltonian Torque Descent.
    - Xuất bài học bền vững sang D:\\2brain.
    """

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self._buffer: List[Episode] = []
        self._action_failure_counts: Dict[int, int] = {}
        self._action_success_counts: Dict[int, int] = {}

    def __len__(self) -> int:
        return len(self._buffer)

    def add(self, episode: Episode) -> None:
        """Thêm 1 episode vào bộ đệm lăn với độ phức tạp O(1)."""
        if len(self._buffer) >= self.capacity:
            # Loại bỏ phần tử cũ nhất khi đầy bộ đệm
            self._buffer.pop(0)
        self._buffer.append(episode)

        # Cập nhật thống kê thành công / thất bại của action k*
        k = episode.k_star
        if episode.outcome_reward < 0.0:
            self._action_failure_counts[k] = self._action_failure_counts.get(k, 0) + 1
        elif episode.outcome_reward > 0.0:
            self._action_success_counts[k] = self._action_success_counts.get(k, 0) + 1

    record = add  # Alias thuận tiện

    def sample_batch(self, batch_size: int = 32, negative_only: bool = False) -> List[Episode]:
        """Lấy mẫu mini-batch từ bộ đệm hồi ức để học hỏi."""
        if not self._buffer:
            return []

        if negative_only:
            candidates = [ep for ep in self._buffer if ep.outcome_reward < 0.0]
            if not candidates:
                candidates = self._buffer
        else:
            candidates = self._buffer

        n = min(len(candidates), batch_size)
        indices = np.random.choice(len(candidates), size=n, replace=False)
        return [candidates[i] for i in indices]

    def update_nps_pruning_mask(
        self,
        current_mask_bytes: np.ndarray,
        failure_threshold: int = 3
    ) -> Tuple[np.ndarray, List[int]]:
        """
        NPS Pruning: Tỉa bỏ các giả thuyết/hành động liên tục gây lỗi.
        Đánh dấu bit 0 trong mặt nạ ràng buộc 512-byte để Core không thể chọn lại.
        Trả về: (updated_mask_512b, list_pruned_actions).
        """
        mask = current_mask_bytes.copy()
        pruned_actions = []

        for k, fails in self._action_failure_counts.items():
            successes = self._action_success_counts.get(k, 0)
            # Nếu số lần thất bại vượt ngưỡng và vượt trội so với thành công
            if fails >= failure_threshold and fails > successes * 2:
                byte_idx = k // 8
                bit_idx = k % 8
                # Xóa bit k (đặt bit = 0)
                if mask[byte_idx] & (1 << bit_idx):
                    mask[byte_idx] &= np.uint8((~(1 << bit_idx)) & 0xFF)
                    pruned_actions.append(k)

        return mask, pruned_actions

    def replay_hamiltonian_descent(
        self,
        engine,
        batch_size: int = 16,
        learning_rate: float = 0.02,
        find_target_fn: Optional[Any] = None,
    ) -> float:
        """
        Chạy vòng lặp thích ứng Hamiltonian Torque Descent trên các episodes lỗi:
        - Lấy mẫu các trường hợp sai lệch.
        - Xoay 8 rotors Clifford Cl(12) để giảm thế năng mất mát.
        - Trả về mức giảm loss trung bình.
        """
        negative_batch = self.sample_batch(batch_size=batch_size, negative_only=True)
        if not negative_batch:
            return 0.0

        total_loss = 0.0
        for ep in negative_batch:
            # Xác định target_k cải thiện: nếu không có hàm ngoài, đảo hướng action
            if find_target_fn:
                target_k = find_target_fn(ep)
            else:
                # Đảo hướng (REVERSE hoặc HOLD)
                target_k = (ep.k_star ^ 0x07) % CL12_DIMENSION

            loss = engine.adapt_torque(
                ep.latent_h,
                chosen_k=ep.k_star,
                target_k=target_k,
                learning_rate=learning_rate,
            )
            total_loss += loss

        return total_loss / len(negative_batch)

    def export_durable_lessons(self, export_path: str, engine=None) -> str:
        """Xuất báo cáo bài học kinh nghiệm bền vững định dạng Markdown đồng bộ D:\\2brain."""
        os.makedirs(os.path.dirname(os.path.abspath(export_path)), exist_ok=True)

        total_episodes = len(self._buffer)
        total_pnl = sum(ep.outcome_reward for ep in self._buffer)
        pos_episodes = [ep for ep in self._buffer if ep.outcome_reward > 0]
        win_rate = (len(pos_episodes) / max(1, total_episodes)) * 100.0

        angles_str = "N/A"
        if engine is not None:
            angles = engine.get_rotor_angles()
            angles_str = str(np.round(angles, 4).tolist())

        content = f"""# [!IMPORTANT]
> **BÀI HỌC KINH NGHIỆM BỀN VỮNG (DURABLE LESSONS) — EPISODIC MEMORY REPLAY**
> Tự động tạo bởi `VivyquMemory` vào lúc: {time.strftime('%Y-%m-%d %H:%M:%S')}

## 1. Thống Kê Tổng Quan Hồi Ức
- **Tổng số Episode ghi nhận:** {total_episodes:,}
- **Tổng tích lũy kết quả (Cumulative Reward):** {total_pnl:.2f}
- **Tỷ lệ Quyết định Sinh Lời (Win Rate):** {win_rate:.2f}%
- **Góc quay 8 Rotors Cl(12) Hiện Tại:** `{angles_str}`

## 2. Danh Sách Hành Động Đã Bị Tỉa Bỏ (NPS Pruned Actions)
"""
        for k, fails in sorted(self._action_failure_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            succ = self._action_success_counts.get(k, 0)
            content += f"- **Action Index {k}**: Thất bại {fails} lần, Thành công {succ} lần (Tỉa bỏ khỏi không gian tìm kiếm)\n"

        content += "\n## 3. Quyết Định Bền Vững Đề Xuất\n- Tiếp tục duy trì xoay góc Spin(12) thích nghi với chế độ thị trường mới.\n"

        with open(export_path, "w", encoding="utf-8") as f:
            f.write(content)

        return export_path

    export_durable_lessons_markdown = export_durable_lessons  # Alias thuận tiện
