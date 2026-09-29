"""
Integration Test: Cautreo Host <-> Vivyqu Core (Linh hồn & Thân thể)
===================================================================
Kiểm tra liên thông hoàn chỉnh:
1. Host khởi động với model_endpoint="vivyqu" -> LinkMachine chuyển sang ONLINE.
2. Nạp toàn bộ danh mục plugin (Bodymap) từ cautreo-host/plugins.
3. Gửi lệnh qua IPC Bus -> vivy.runtime/ask kích hoạt Lõi Vivyqu E9 Scorer.
4. Kiểm tra phản hồi mang bản sắc Vivyqu Core và độ trễ siêu thanh.
"""

import os
import sys
from pathlib import Path
import pytest

# Windows cp1252 console safety
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thêm đường dẫn cho cautreo-host và vivyqu python
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "python"))
sys.path.insert(0, str(REPO_ROOT / "cautreo-host"))

from cautreo_host.host import Host
from cautreo_host.state import LinkState


@pytest.fixture
def vivyqu_host():
    """Khởi tạo một instance Host độc lập liên kết với Vivyqu Core."""
    ui_dir = REPO_ROOT / "cautreo-desktop-ui"
    plugins_dir = REPO_ROOT / "cautreo-host" / "plugins"
    workspace = REPO_ROOT / ".tmp_test"
    workspace.mkdir(parents=True, exist_ok=True)

    h = Host(
        ui_dir=ui_dir,
        plugins_dir=plugins_dir,
        workspace=workspace,
        port=8759,
        model_endpoint="vivyqu",
        offline=False,
    )
    yield h
    import shutil
    shutil.rmtree(workspace, ignore_errors=True)



def test_host_boots_online_with_vivyqu_core(vivyqu_host):
    """Kiểm tra Host nhận diện được Vivyqu Core và lên trạng thái ONLINE."""
    # 1. Nạp plugins
    loaded = vivyqu_host.load_plugins()
    assert "vivy.runtime" in loaded
    assert "tool.fs-read" in loaded
    assert "tool.fs-write" in loaded

    # 2. Dò tìm model link
    vivyqu_host.open_link()
    assert vivyqu_host.link.state == LinkState.ONLINE
    model_name = vivyqu_host.link.model
    assert "VivyQu" in model_name and "1.2.0" in model_name


def test_bus_routes_ask_to_vivyqu_core_e9(vivyqu_host):
    """Kiểm tra gọi RPC vivy.runtime/ask qua IPC Bus nhận được phán quyết từ Lõi E9."""
    vivyqu_host.load_plugins()
    vivyqu_host.open_link()

    # Gửi lệnh ask qua Bus
    call = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "vivy.runtime/ask",
        "params": {"prompt": "Quan sát trạng thái hệ thống và lập kế hoạch thực thi."},
    }

    reply = vivyqu_host.bus.handle(call)
    assert reply.get("jsonrpc") == "2.0"
    assert reply.get("id") == 1
    assert "error" not in reply, f"RPC call bị lỗi: {reply.get('error')}"

    result = reply.get("result", {})
    assert "answer" in result
    assert "[Vivyqu Core E9 Decision]" in result["answer"]
    assert len(result.get("thinking", [])) >= 3
    print(f"\n[EVIDENCE] Vivyqu Host Answer: {result['answer']}")


def test_native_vivyqu_backend_decide(vivyqu_host):
    """Kiểm tra gọi trực tiếp backend vivyqu.decide từ bus backends."""
    backend = vivyqu_host.bus.backends.get("vivyqu")
    assert backend is not None
    assert backend.health() is True

    # Warm-up call
    _ = backend.decide(temperature=1.0)

    # Đo đạc
    decision = backend.decide(temperature=1.0)
    assert 0 <= decision["best_index"] < 4096
    assert decision["is_safe"] is True
    assert decision["target_organ"] in ("eye", "hand", "both")
    assert decision["latency_us"] < 500.0
    print(f"\n[EVIDENCE] Native Vivyqu Decision Latency: {decision['latency_us']:.2f} µs")


def test_conversational_chitchat_fast_path(vivyqu_host):
    """Kiểm tra lời chào hỏi thông thường đi qua Fast-Path, không ép Lõi Vivyqu sụp đổ hành động."""
    vivyqu_host.load_plugins()
    vivyqu_host.open_link()

    call = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "vivy.runtime/ask",
        "params": {"prompt": "Chào bạn, bạn có khỏe không?"},
    }

    reply = vivyqu_host.bus.handle(call)
    assert "error" not in reply
    result = reply.get("result", {})
    assert "ViVy" in result["answer"]
    assert any("IDLE" in t or "Fast-Path" in t for t in result.get("thinking", []))
    print(f"\n[EVIDENCE] Chitchat Fast-Path Answer: {result['answer']}")


def test_macro_action_injection_with_underlying_llm(vivyqu_host):
    """Kiểm tra cơ chế M1 Macro-Action Injection tiêm quyết định E9 vào LLM ngoài."""
    vivyqu_host.load_plugins()
    vivyqu_host.open_link()

    captured_prompts = []

    class MockLLM:
        endpoint = "mock://gemma4-local"
        def complete(self, prompt, **kwargs):
            captured_prompts.append(prompt)
            return {
                "answer": "Đã tiến hành đọc file và kiểm tra theo chỉ thị tối ưu.",
                "thinking": ["LLM: Sinh câu trả lời trực tiếp mà không cần CoT."],
                "text": "Đã tiến hành đọc file và kiểm tra theo chỉ thị tối ưu.",
                "raw": "Đã tiến hành đọc file và kiểm tra theo chỉ thị tối ưu.",
            }

    # Gắn MockLLM làm underlying_llm của VivyquCoreBackend
    backend = vivyqu_host.bus.backends.get("model")
    backend.underlying_llm = MockLLM()

    call = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "vivy.runtime/ask",
        "params": {"prompt": "Hãy đọc file mã nguồn và kiểm tra các lỗi tiềm ẩn."},
    }

    reply = vivyqu_host.bus.handle(call)
    assert "error" not in reply
    result = reply.get("result", {})
    assert len(captured_prompts) == 1
    injected_prompt = captured_prompts[0]

    # Xác thực rằng Lõi Vivyqu đã tiêm Macro-Action vào prompt của LLM
    assert "[CHỈ THỊ QUYẾT ĐỊNH TỪ LÕI VIVYQU CORE]" in injected_prompt
    assert "k*=" in injected_prompt
    assert "Không sinh suy nghĩ CoT dài dòng" in injected_prompt
    print(f"\n[EVIDENCE] Injected Macro-Action Prompt Header:\n{injected_prompt[:250]}...")

