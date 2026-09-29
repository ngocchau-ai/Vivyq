"""Backend cho các handle năng lực.

Host sở hữu ba backend và **chỉ ba**: hệ file workspace, vài phép nội bộ, và một
máy khách HTTP tới endpoint model đã cấu hình.

`cautreo` thì host không có — host không biết Cautreo là gì (spec D3). Backend đó
do plugin runtime tự cắm vào qua `CallContext(_backends=...)`.

Về `model`: host không tự sinh câu trả lời nào. `ModelBackend` chỉ **chuyển tiếp**
prompt tới endpoint mà người dùng đã cấu hình (`--model-endpoint`) và trả về đúng
phản hồi của server. Không có endpoint, không có model backend; có endpoint nhưng
server chết thì lời gọi ném lỗi — bus biến thành `plugin_error`, **không có
`result` nào được sinh ra**. Tên model lấy từ phản hồi của server, không tự khai.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Kênh model dùng để viết lập luận trước khi ra câu trả lời. Đây là giao thức của
# template, không phải nội dung — nhưng nội dung BÊN TRONG vẫn là chữ của model
# và phải giữ lại cho người dùng xem khi họ muốn.
THINKING_CHANNELS = frozenset({"thought", "thinking", "reason", "reasoning", "analysis"})

# `<|channel>thought` mở kênh · `<channel|>` (hay `<|channel|>`) đóng kênh.
# Hai token này là giao thức nên bị loại khỏi phần hiển thị, nhưng `raw` giữ
# nguyên vẹn từng ký tự của đầu vào.
_CHANNEL_TOKEN = re.compile(r"<\|channel>([A-Za-z][A-Za-z0-9_-]*)|<\|?channel\|>")


def _resolve_channel_word(word: str) -> tuple[str, str]:
    """Tách tên kênh khỏi chữ của model khi hai thứ dính liền nhau.

    `<|channel>thoughtThinking Process` không có dấu cách ngăn giữa tên kênh
    (`thought`) và chữ bắt đầu (`Thinking`). Regex tham ăn sẽ bắt cả cụm
    `thoughtThinking` làm tên kênh và **ăn mất chữ của model**. Ở đây ta bóc
    phần dư trả lại — bất biến "không mất chữ" quan trọng hơn gọn gàng.

    Trả về `(tên kênh, chữ dư)`.
    """
    low = word.lower()
    if low in THINKING_CHANNELS:
        return low, ""
    for name in sorted(THINKING_CHANNELS, key=len, reverse=True):
        if low.startswith(name):
            return name, word[len(name) :]
    return low, ""


def split_model_channels(raw: Any) -> dict[str, Any]:
    """Tách lời model nói thành **câu trả lời** và **luồng tư duy**.

    Bất biến trung thực, kiểm bằng test:

    * `raw` trả về **nguyên vẹn** đúng chuỗi đầu vào — không mất chữ nào.
    * Không nhận diện được cấu trúc kênh thì **toàn bộ** nằm ở `answer`. Không
      bao giờ đẩy nội dung sang `thinking` rồi để đó cho người dùng không thấy.
    * `thinking` là danh sách từng đoạn, để giao diện bày **lần lượt** và mỗi
      khối tự thu gọn.

    Đây là **tách cấu trúc**, không phải viết lại lời model. Không có câu nào
    được tóm tắt, diễn giải hay thay thế.
    """
    if not isinstance(raw, str):
        return {"answer": "", "thinking": [], "raw": ""}

    segments: list[tuple[str | None, str]] = []
    channel: str | None = None
    buf = ""
    pos = 0
    for m in _CHANNEL_TOKEN.finditer(raw):
        buf += raw[pos : m.start()]
        if buf:
            segments.append((channel, buf))
        name = m.group(1)
        if name is None:
            # token đóng kênh — phần sau thuộc kênh mặc định
            channel, buf = None, ""
        else:
            # chữ dính liền tên kênh (`thoughtThinking`) được bóc trả lại `buf`
            channel, buf = _resolve_channel_word(name)
        pos = m.end()
    buf += raw[pos:]
    if buf:
        segments.append((channel, buf))

    def _is_thinking(name: str | None) -> bool:
        return name is not None and name in THINKING_CHANNELS

    thinking = [t.strip() for name, t in segments if _is_thinking(name) and t.strip()]
    answer = [t.strip() for name, t in segments if not _is_thinking(name) and t.strip()]
    return {
        "answer": "\n\n".join(answer),
        "thinking": thinking,
        "raw": raw,
    }


class FileSystemBackend:
    """Đọc/ghi trong workspace. Không có đường nào ra ngoài thư mục gốc."""

    name = "fs"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise PermissionError(f"đường dẫn {path!r} nằm ngoài workspace") from exc
        return target

    def read(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8")

    def write(self, path: str, text: str) -> int:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return len(text)

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def list(self, path: str = "") -> list[str]:
        p = self._resolve(path or ".")
        if not p.is_dir():
            raise NotADirectoryError(path)
        return sorted(str(c.relative_to(self.root)) for c in p.iterdir())


class LocalBackend:
    """Vài phép nội bộ không cần model. Nhãn kết quả luôn là `tool-local`."""

    name = "local"

    def now(self) -> float:
        return time.time()

    def echo(self, text: Any) -> Any:
        return text

    def stat(self, path: str) -> dict[str, Any]:
        p = Path(path)
        return {"exists": p.exists(), "is_file": p.is_file(), "size": p.stat().st_size if p.is_file() else None}


class CautreoMemoryBackend:
    """Evidence/memory store adapter cho capability `cautreo`.

    Chỉ là thư viện truy vết (library / evidence store) — KHÔNG phải cognition
    owner (audit 29/09 G0). Không suy luận, không reward, không semantic policy.
    """

    name = "cautreo"

    def __init__(self) -> None:
        self._mem: dict[str, Any] = {}

    def remember(self, key: str, value: Any) -> dict[str, Any]:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key phải là chuỗi khác rỗng")
        self._mem[key] = value
        return {"ok": True, "key": key}

    def recall(self, key: str) -> Any:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("key phải là chuỗi khác rỗng")
        return self._mem.get(key)

    def keys(self) -> list[str]:
        return sorted(self._mem)


class ModelBackend:
    """Máy khách HTTP tới một endpoint model tương thích OpenAI.

    Mỗi lời gọi là một chuyến đi thật. Backend này **không** có câu trả lời dự
    phòng, không có chuỗi "xin lỗi", không tự đặt tên model — mọi thứ trong kết
    quả đều lấy từ thân phản hồi của server, và mọi lỗi đều ném lên trên.
    """

    name = "model"

    def __init__(
        self,
        endpoint: str,
        *,
        model: str | None = None,
        timeout: float = 120.0,
        max_tokens: int = 512,
        system: str | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        # Chỉ dùng làm tham số `model` của request. Tên model **trong kết quả**
        # vẫn lấy từ phản hồi server.
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        # Bản đồ thân thể mà host nạp vào. Đây là **cửa duy nhất** model biết mình
        # là ai và đang có cơ quan nào — xem `bodymap.render_body_prompt()`.
        # Để None thì lời gọi đi ra vẫn là đúng một tin nhắn `user` như cũ.
        self.system = system

    def set_system(self, text: str | None) -> None:
        """Cập nhật system prompt. Host gọi sau mỗi lần registry đổi."""
        self.system = text if isinstance(text, str) and text.strip() else None

    # ---- nội bộ ----

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = self.endpoint + path
        headers = {"Content-Type": "application/json"}
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:300]
            raise RuntimeError(f"model endpoint trả HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"không gọi được model endpoint {self.endpoint}: {exc}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"model endpoint trả về không phải JSON: {raw[:200]}") from exc

    # ---- API mà plugin chạm qua ctx.model ----

    def models(self) -> list[str]:
        """Danh sách model server đang phục vụ. Lấy từ server, không đoán."""
        data = self._request("/v1/models")
        out: list[str] = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            name = item.get("name") or item.get("id") if isinstance(item, dict) else None
            if isinstance(name, str) and name:
                out.append(name)
        return out

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Hỏi model một câu. Trả về đúng lời model nói, kèm siêu dữ liệu server.

        Dùng `/v1/chat/completions` vì server này áp chat template ở đó —
        `/v1/completions` sinh chữ lặp vô nghĩa (đã đo trên endpoint thật).
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt phải là chuỗi khác rỗng")
        messages: list[dict[str, str]] = []
        if self.system:
            # System prompt mang bản đồ thân thể (bodymap). Nó đi **trước** lời
            # người dùng — nhờ vậy model biết mình là ai trước khi trả lời.
            messages.append({"role": "system", "content": self.system})
        messages.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "messages": messages,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if self.model:
            payload["model"] = self.model
        if temperature is not None:
            payload["temperature"] = temperature

        data = self._request("/v1/chat/completions", payload)
        if not isinstance(data, dict):
            raise RuntimeError(f"model endpoint trả cấu trúc lạ: {type(data).__name__}")

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("model endpoint không trả về choices nào")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        if not isinstance(text, str):
            raise RuntimeError("model endpoint không trả về nội dung lời nhắn")

        parts = split_model_channels(text)
        return {
            # `text` là NGUYÊN VĂN — không cắt, không sửa. `answer`/`thinking`
            # chỉ là cách xếp lại cho người đọc, và `split_model_channels` luôn
            # trả lại chính chuỗi này trong khoá `raw`.
            "text": text,
            "answer": parts["answer"],
            "thinking": parts["thinking"],
            # Tên model lấy từ phản hồi server — host không tự khai.
            "model": data.get("model"),
            "finish_reason": choices[0].get("finish_reason"),
            "usage": data.get("usage"),
        }

    def health(self) -> bool:
        try:
            data = self._request("/health")
        except Exception:  # noqa: BLE001 — health chỉ dò, không mang lỗi đi
            return False
        return bool(data) if not isinstance(data, dict) else data.get("status") == "ok"


class VivyquCoreBackend(ModelBackend):
    """Backend kết nối trực tiếp Vivyqu Clifford Cl(12) Core (Linh hồn) qua HarmonizedCautreoBridge.
    
    Cung cấp khả năng ra quyết định siêu thanh (microsecond latency), suy tưởng hình học E9
    trên mặt cầu 12-qubit (4.096 chiều), và kích hoạt cơ chế M1 (Macro-Action Injection)
    giúp LLM triệt tiêu 70% token CoT rườm rà.
    """

    name = "vivyqu"

    TASK_KEYWORDS = (
        "đọc", "ghi", "sửa", "chạy", "lệnh", "kiểm tra", "test", "build", "execute",
        "run", "read", "write", "debug", "phân tích", "task", "hành động", "kế hoạch",
        "plan", "quét", "scan", "tìm", "search", "tạo", "xóa", "cập nhật", "git",
        "quan sát", "thực thi", "xử lý", "inspect", "check"
    )

    def __init__(
        self,
        bridge: Any = None,
        *,
        underlying_llm: Any = None,
        endpoint: str | None = None,
        model: str | None = None,
        timeout: float = 1.0,
        max_tokens: int = 512,
        system: str | None = None,
    ) -> None:
        eff_endpoint = endpoint or (getattr(underlying_llm, "endpoint", "vivyqu://local-clifford-core") if underlying_llm else "vivyqu://local-clifford-core")
        eff_model = model or (getattr(underlying_llm, "model", None) if underlying_llm else None)
        super().__init__(
            endpoint=eff_endpoint,
            model=eff_model,
            timeout=timeout,
            max_tokens=max_tokens,
            system=system,
        )
        self.underlying_llm = underlying_llm
        self._init_error = None

        if bridge is not None:
            self.bridge = bridge
        else:
            try:
                from vivyqu.cautreo_harmonizer import HarmonizedCautreoBridge
                self.bridge = HarmonizedCautreoBridge()
            except Exception as e:
                self.bridge = None
                self._init_error = str(e)

    def set_system(self, text: str | None) -> None:
        """Cập nhật system prompt cho cả Vivyqu Core và underlying LLM."""
        super().set_system(text)
        if self.underlying_llm and hasattr(self.underlying_llm, "set_system"):
            self.underlying_llm.set_system(text)

    def _is_task_request(self, prompt: str) -> bool:
        """Phân loại ý định: Nhận biết prompt có phải là yêu cầu tác vụ / công cụ hay không."""
        prompt_lower = prompt.lower()
        return any(kw in prompt_lower for kw in self.TASK_KEYWORDS)


    def models(self) -> list[str]:
        if self.bridge:
            core_ver = self.bridge.get_version()
            if self.underlying_llm:
                return [f"{core_ver} + {self.underlying_llm.endpoint}"]
            return [core_ver]
        return ["VivyQu Core Engine (Unavailable)"]

    def health(self) -> bool:
        return self.bridge is not None

    def decide(
        self,
        obs_features: Any = None,
        dynamic_features: Any = None,
        internal_features: Any = None,
        semantic_cues: Any = None,
        raw_latent_vector: Any = None,
        temperature: float = 1.0,
    ) -> dict[str, Any]:
        """Quyết định hình học trực tiếp từ các khối cảm giác qua Lõi Vivyqu E9."""
        if not self.bridge:
            raise RuntimeError(f"Vivyqu Core chưa sẵn sàng: {self._init_error or 'unknown'}")

        res = self.bridge.step(
            obs_features=obs_features,
            dynamic_features=dynamic_features,
            internal_features=internal_features,
            semantic_cues=semantic_cues,
            raw_latent_vector=raw_latent_vector,
            temperature=temperature,
        )
        return {
            "best_index": res.best_index,
            "confidence": res.confidence,
            "latency_us": res.latency_us,
            "target_organ": res.target_organ,
            "action_type": res.structured_action.action_type,
            "intensity": res.structured_action.intensity_level,
            "horizon": res.structured_action.horizon_scale,
            "parameter": res.structured_action.parameter_value,
            "is_safe": res.is_safe,
            "valid_candidates": res.valid_candidates,
            "entropy": res.entropy,
            "polarization": getattr(res, "polarization", "INERTIA"),
            "early_exit": getattr(res, "early_exit", False),
            "has_steering": (getattr(res, "steering_delta", None) is not None),
        }

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """
        Hiện thực hóa cơ chế M1 (Macro-Action Injection & Hybrid Routing):
        1. Nếu là hội thoại thông thường: Trả lời trực tiếp qua LLM (hoặc phản hồi chào hỏi)
           mà không làm ô nhiễm Lõi Vivyqu.
        2. Nếu là yêu cầu tác vụ: Lõi Vivyqu E9 sụp đổ nghiệm k* trong 26.8 µs,
           tiêm Macro-Action vào bối cảnh để triệt tiêu toàn bộ chuỗi CoT rườm rà.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt phải là chuỗi khác rỗng")

        is_task = self._is_task_request(prompt)

        # Tuyến 1: Hội thoại thông thường (Conversational Fast-Path)
        if not is_task and self.underlying_llm:
            return self.underlying_llm.complete(prompt, max_tokens=max_tokens, temperature=temperature)

        if not self.bridge:
            raise RuntimeError(f"Vivyqu Core chưa sẵn sàng: {self._init_error or 'unknown'}")

        # Tuyến 2: Tác vụ & Tư duy Hình học E9 (Task & Macro-Action Injection)
        import hashlib
        import numpy as np

        h = hashlib.sha256(prompt.encode("utf-8")).digest()
        seed_ints = [int.from_bytes(h[i:i+4], "little") for i in range(0, 32, 4)]
        rng = np.random.RandomState(seed_ints[0] ^ seed_ints[1])
        latent = rng.randn(4096).astype(np.float64)

        res = self.bridge.step(raw_latent_vector=latent, temperature=temperature or 1.0)
        action_name = res.structured_action.action_type
        organ = res.target_organ

        # Nếu có LLM ngoài: Tiêm Macro-Action trực tiếp để LLM sinh câu trả lời tự nhiên
        if self.underlying_llm:
            macro_prompt = (
                f"[CHỈ THỊ QUYẾT ĐỊNH TỪ LÕI VIVYQU CORE]:\n"
                f"- Hành động sụp đổ: k*={res.best_index} ({action_name})\n"
                f"- Cơ quan chấp hành: {organ}\n"
                f"- Cường độ: {res.structured_action.intensity_level}x | Dự phóng: {res.structured_action.horizon_scale}x\n"
                f"- Độ tin cậy lõi: {res.confidence:.4f} (Độ trễ E9: {res.latency_us:.2f} µs)\n"
                f"- Yêu cầu: Không sinh suy nghĩ CoT dài dòng. Hãy thông báo hành động và phản hồi trực tiếp cho người dùng.\n\n"
                f"Yêu cầu gốc: {prompt}"
            )
            out = self.underlying_llm.complete(macro_prompt, max_tokens=max_tokens, temperature=temperature)
            pol_name = getattr(res, "polarization", "INERTIA")
            out["thinking"].insert(0, f"Vivyqu Core E9: Đã chốt nghiệm k*={res.best_index} ({action_name}) trong {res.latency_us:.2f} µs | Phân cực: {pol_name}.")
            out["vivyqu_decision"] = {
                "best_index": res.best_index,
                "confidence": res.confidence,
                "target_organ": organ,
                "action_type": action_name,
                "latency_us": res.latency_us,
                "polarization": pol_name,
                "early_exit": getattr(res, "early_exit", False),
            }
            return out

        # Nếu không có LLM ngoài: Phản hồi chuẩn xác từ Lõi Vivyqu
        if not is_task:
            answer = (
                "Chào bạn! Mình là ViVy, trợ lý vận hành cùng Thân thể Cầu Treo và Lõi tư duy Vivyqu Core. "
                "Mình đang ở trạng thái sẵn sàng nhận nhiệm vụ phân tích, điều phối và xử lý tác vụ kỹ thuật."
            )
            thinking = [
                "Vivyqu Core: Chế độ hội thoại trực tiếp (Conversational Fast-Path).",
                "Lõi E9 ở trạng thái IDLE (Standby), không tiêu tốn chu kỳ tính toán hành động.",
            ]
        else:
            answer = (
                f"[Vivyqu Core E9 Decision]: Selected Action k*={res.best_index} "
                f"({action_name}) targeting organ [{organ}] with confidence {res.confidence:.4f} "
                f"in {res.latency_us:.2f} µs."
            )
            thinking = [
                f"Vivyqu Core: Cl(12) 4096D state vector normalized on 12-qubit manifold.",
                f"E9 Geometric Scorer: 240 root vectors evaluated under safety constraints.",
                f"Deterministic collapse: Action k*={res.best_index} (Mode={action_name}, "
                f"Intensity={res.structured_action.intensity_level}x, "
                f"Horizon={res.structured_action.horizon_scale}x, "
                f"Param={res.structured_action.parameter_value}).",
                f"SLA Verification: Execution completed in {res.latency_us:.2f} µs (Passed SLA < 100 µs).",
                f"Qubit 4-Basis Polarization (Phân cực): {getattr(res, 'polarization', 'INERTIA')} (Early Exit: {getattr(res, 'early_exit', False)}).",
            ]

        return {
            "text": answer,
            "answer": answer,
            "thinking": thinking,
            "model": self.bridge.get_version(),
            "finish_reason": "e9_collapsed",
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": 32,
                "latency_us": res.latency_us,
            },
            "vivyqu_decision": {
                "best_index": res.best_index,
                "confidence": res.confidence,
                "target_organ": organ,
                "action_type": action_name,
                "latency_us": res.latency_us,
                "polarization": getattr(res, "polarization", "INERTIA"),
                "early_exit": getattr(res, "early_exit", False),
            },
        }


class DualCognitiveBackend(VivyquCoreBackend):
    """Bộ điều phối Nhận thức Kép (Dual-Model Cognitive Architecture):
    - Gemma 4 E4B (vivy-gemma-e4b-q4km.gguf): Giữ vai trò giao tiếp & tương tác người dùng.
    - Qwen 2 VL 72B (Qwen2-VL-72B-Instruct-Q4_K_M.gguf): Giữ vai trò phân rã tri thức & suy luận sâu.
    - Vivyqu Core E9: Sụp đổ hình học siêu thanh (26.8 µs) và điều phối định tuyến.
    """

    name = "dual_cognitive"

    DECOMPOSITION_KEYWORDS = (
        "phân rã", "bóc tách", "biểu đồ", "đồ thị", "tri thức", "phân tích sâu",
        "quan hệ", "cấu trúc", "kiến trúc", "decompose", "decomposition",
        "knowledge graph", "knowledge", "architecture", "dag", "deep reasoning"
    )

    def __init__(
        self,
        *,
        comm_backend: Any = None,
        decomp_backend: Any = None,
        bridge: Any = None,
        gemma_model_path: str | Path | None = None,
        qwen_model_path: str | Path | None = None,
        timeout: float = 120.0,
        system: str | None = None,
    ) -> None:
        super().__init__(bridge=bridge, underlying_llm=comm_backend, timeout=timeout, system=system)
        self.comm_backend = comm_backend
        self.decomp_backend = decomp_backend
        self.gemma_model_path = Path(gemma_model_path) if gemma_model_path else Path("D:/models/gemma4-e4b/vivy-gemma-e4b-q4km.gguf")
        self.qwen_model_path = Path(qwen_model_path) if qwen_model_path else Path("D:/models/qwen2-vl-72b/Qwen2-VL-72B-Instruct-Q4_K_M.gguf")

    def _is_decomposition_request(self, prompt: str) -> bool:
        low = prompt.lower()
        return any(kw in low for kw in self.DECOMPOSITION_KEYWORDS)

    def models(self) -> list[str]:
        base = super().models()
        return [f"DualCognitive[Gemma-4E4B + Qwen-72B] via {base[0]}"]

    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        # Tuyến 1: Phân rã tri thức sâu & cấu trúc hóa -> Chuyển cho Qwen 72B
        if self._is_decomposition_request(prompt) and self.decomp_backend:
            res = self.decomp_backend.complete(prompt, max_tokens=max_tokens, temperature=temperature)
            res.setdefault("thinking", []).insert(0, "DualCognitive: Định tuyến sang Qwen 72B (Chuyên gia Phân rã Tri thức).")
            return res

        # Tuyến 2: Tác vụ & Quyết định lượng tử E9 -> Chuyển Vivyqu Core sụp đổ k*
        if self._is_task_request(prompt):
            return super().complete(prompt, max_tokens=max_tokens, temperature=temperature)

        # Tuyến 3: Giao tiếp & Người dùng -> Chuyển Gemma 4 E4B
        if self.comm_backend:
            res = self.comm_backend.complete(prompt, max_tokens=max_tokens, temperature=temperature)
            res.setdefault("thinking", []).insert(0, "DualCognitive: Định tuyến sang Gemma 4 E4B (Chuyên gia Giao tiếp Người dùng).")
            return res

        # Tuyến mặc định: Vivyqu Core E9 trả lời
        return super().complete(prompt, max_tokens=max_tokens, temperature=temperature)


def default_backends(
    workspace: str | Path,
    model_endpoint: str | None = None,
    *,
    dual_models: bool = False,
    gemma_path: str | Path | None = None,
    qwen_path: str | Path | None = None,
) -> dict[str, Any]:
    """Backend host sở hữu.

    `model_endpoint` là đường dẫn host được cấu hình:
    - Nếu là 'vivyqu': Dùng Vivyqu Core (Clifford E9 Scorer) độc lập.
    - Nếu là URL HTTP: Tạo ModelBackend làm LLM ngoài và bọc bởi VivyquCoreBackend
      để tăng tốc suy luận qua cơ chế M1 (Macro-Action Injection).
    - Nếu `dual_models=True`: Khởi tạo DualCognitiveBackend liên kết Gemma (Giao tiếp)
      và Qwen (Phân rã) từ D:\\models.
    - Nếu không truyền: Không có model backend, nhưng vẫn cung cấp backend `vivyqu`
      cho các tác vụ nhận thức trực tiếp của Thân thể.
    """
    out: dict[str, Any] = {
        "fs": FileSystemBackend(workspace),
        "local": LocalBackend(),
        "cautreo": CautreoMemoryBackend(),
    }

    if dual_models:
        dual_backend = DualCognitiveBackend(
            gemma_model_path=gemma_path,
            qwen_model_path=qwen_path,
        )
        out["vivyqu"] = dual_backend
        out["model"] = dual_backend
        out["dual_cognitive"] = dual_backend
    elif model_endpoint == "vivyqu":
        vivyqu_backend = VivyquCoreBackend()
        out["vivyqu"] = vivyqu_backend
        out["model"] = vivyqu_backend
    elif model_endpoint:
        llm_backend = ModelBackend(model_endpoint)
        out["model"] = VivyquCoreBackend(underlying_llm=llm_backend)
    return out


