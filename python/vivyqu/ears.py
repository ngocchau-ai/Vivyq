"""
VivyQu Ears Module (Tai Lắng Nghe & Tín Hiệu Đa Phương Thức)
=============================================================
Hiện thực hóa cơ quan thính giác / ngữ nghĩa của Vivy:
- Lắng nghe và tiếp nhận các tín hiệu âm thanh môi trường (Acoustic Waveforms & Cues).
- Tiếp nhận các chỉ dẫn ngôn ngữ tự nhiên, vector prompt embeddings đa phương thức (Multimodal Semantic Prompts).
- Chuyển đổi thành Khối 4: Ngữ nghĩa & Âm học (1024 chiều) trong vector nhận thức h ∈ ℝ⁴⁰⁹⁶.

[BẤT BIẾN KIẾN TRÚC]:
Tai tiếp nhận trung thực tín hiệu chỉ dẫn và sóng âm từ thế giới khách quan gửi tới Não bộ,
tuyệt đối không can thiệp logic hay lọc bỏ tín hiệu.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class AcousticSemanticFeed:
    """Gói dữ liệu thính giác và ngữ nghĩa từ môi trường hoặc chỉ đạo của người dùng."""
    timestamp_ns: int = 0
    signal_intensity: float = 1.0                # Cường độ tín hiệu kích hoạt
    sentiment_valence: float = 0.0               # Mức độ tích cực/tiêu cực của ngữ cảnh [-1.0, 1.0]
    semantic_prompt_embedding: Optional[np.ndarray] = None # Vector ngữ nghĩa 1024D từ Local LLM / Encoder
    acoustic_feature_vector: Optional[np.ndarray] = None   # Vector đặc trưng âm học (MFCC, Audio Tone)
    urgency_weight: float = 1.0


class VivyquEars:
    """
    Cơ quan Tai lắng nghe của Vivy:
    - Thu nhận chỉ dẫn ngôn ngữ, vector ngữ nghĩa và tín hiệu âm học từ môi trường.
    - Chuyển đổi và chuẩn hóa thành Khối 4 (Semantic & Acoustic - 1024 chiều).
    """

    def __init__(self):
        self._block4_cache = np.zeros(1024, dtype=np.float64)

    def listen_and_encode(self, feed: AcousticSemanticFeed) -> np.ndarray:
        """Chuyển đổi tín hiệu ngữ nghĩa và âm học thành Khối 4 (1024D)."""
        self._block4_cache.fill(0.0)

        offset = 0

        # 1. Nạp vector ngữ nghĩa embedding nếu có
        if feed.semantic_prompt_embedding is not None:
            emb_flat = feed.semantic_prompt_embedding.flatten()
            n_emb = min(len(emb_flat), 1024)
            self._block4_cache[:n_emb] = emb_flat[:n_emb]
            offset = n_emb
        else:
            # Khởi tạo từ các đặc trưng ngữ cảnh cơ bản
            self._block4_cache[0] = feed.signal_intensity
            self._block4_cache[1] = feed.sentiment_valence
            self._block4_cache[2] = feed.urgency_weight
            offset = 3

        # 2. Bổ sung vector âm học nếu có
        if feed.acoustic_feature_vector is not None and offset < 1024:
            audio_flat = feed.acoustic_feature_vector.flatten()
            rem = 1024 - offset
            n_aud = min(len(audio_flat), rem)
            self._block4_cache[offset:offset + n_aud] = audio_flat[:n_aud]

        # 3. Chuẩn hóa L2 về mặt cầu đơn vị
        norm = np.linalg.norm(self._block4_cache)
        if norm > 1e-12:
            self._block4_cache /= norm
        else:
            self._block4_cache[0] = 1.0

        return self._block4_cache.copy()
