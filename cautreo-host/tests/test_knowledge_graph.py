"""Kiểm thử Biểu đồ Tri thức Cautreo & Kiến trúc Dual-Model (Gemma 4B & Qwen 72B).

Bảo đảm tính xác thực (Evidence-based):
1. Biểu đồ tri thức dựng đúng các node thực thể và quan hệ.
2. Bus JSON-RPC `host.knowledge-graph` trả về biểu đồ tri thức hợp lệ mà không cần model.
3. DualCognitiveBackend định tuyến chính xác giữa giao tiếp (Gemma) và phân rã tri thức (Qwen).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cautreo_host.backends import DualCognitiveBackend, default_backends
from cautreo_host.bus import Bus
from cautreo_host.knowledge import build_knowledge_graph, render_knowledge_graph_markdown
from cautreo_host.receipt import ReceiptLog
from cautreo_host.registry import PluginRegistry


class MockModelBackend:
    """Mock backend để đo định tuyến cuộc gọi mà không cần server mạng thật."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[str] = []

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(prompt)
        return {
            "text": f"[{self.name} Response]: {prompt[:50]}",
            "answer": f"[{self.name} Response]: {prompt[:50]}",
            "thinking": [f"Processed by {self.name}"],
            "model": self.name,
            "raw": f"[{self.name} Response]: {prompt[:50]}",
        }


class TestKnowledgeGraphConstruction:
    def test_build_knowledge_graph_structure(self):
        graph = build_knowledge_graph()
        assert "title" in graph
        assert "models" in graph
        assert "nodes" in graph
        assert "edges" in graph

        # Kiểm tra sự hiện diện của cặp model nhận thức
        comm_model = graph["models"]["communication"]
        assert comm_model["id"] == "gemma4-e4b"
        assert "gemma4-e4b" in comm_model["path"].lower()

        decomp_model = graph["models"]["decomposition"]
        assert decomp_model["id"] == "qwen2-vl-72b"
        assert "qwen2-vl-72b" in decomp_model["path"].lower()

        # Kiểm tra node Lõi Lượng tử
        node_ids = {n["id"] for n in graph["nodes"]}
        assert "soul.vivyqu_core" in node_ids
        assert "model.gemma_4eb" in node_ids
        assert "model.qwen_72b" in node_ids
        assert "bridge.harmonizer" in node_ids
        assert "memory.episodic" in node_ids

        # Kiểm tra 4 trạng thái qubit
        assert "qubit.ground" in node_ids
        assert "qubit.superposition" in node_ids
        assert "qubit.entanglement" in node_ids
        assert "qubit.decay" in node_ids

    def test_render_knowledge_graph_markdown(self):
        graph = build_knowledge_graph()
        md = render_knowledge_graph_markdown(graph)
        assert "# Biểu Đồ Tri Thức Cautreo & Vivyqu" in md
        assert "Gemma 4 E4B" in md
        assert "Qwen 2 VL 72B" in md
        assert "```mermaid" in md
        assert "VivyCore" in md


class TestKnowledgeGraphViaBus:
    def test_bus_exposes_knowledge_graph_method(self, tmp_path: Path):
        registry = PluginRegistry()
        bus = Bus(registry, backends=default_backends(tmp_path))

        assert "host.knowledge-graph" in bus.method_names()

        # Gọi qua giao thức Bus JSON-RPC
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": "test-kg-1",
            "method": "host.knowledge-graph",
            "params": {},
        })
        resp = bus.handle(req)
        assert resp is not None
        assert "result" in resp
        result = resp["result"]
        assert result["summary"] == "biểu đồ tri thức"
        assert "graph" in result
        assert "models" in result["graph"]


class TestDualCognitiveRouting:
    def test_routes_decomposition_to_qwen(self):
        qwen_mock = MockModelBackend("Qwen-72B")
        gemma_mock = MockModelBackend("Gemma-4B")

        dual = DualCognitiveBackend(
            comm_backend=gemma_mock,
            decomp_backend=qwen_mock,
        )

        # Lời hỏi yêu cầu phân rã tri thức / đồ thị
        res = dual.complete("Hãy phân rã cấu trúc kiến trúc của hệ thống thành biểu đồ tri thức.")
        assert len(qwen_mock.calls) == 1
        assert len(gemma_mock.calls) == 0
        assert "Qwen-72B" in res["answer"]
        assert any("Qwen 72B" in t for t in res["thinking"])

    def test_routes_user_dialogue_to_gemma(self):
        qwen_mock = MockModelBackend("Qwen-72B")
        gemma_mock = MockModelBackend("Gemma-4B")

        dual = DualCognitiveBackend(
            comm_backend=gemma_mock,
            decomp_backend=qwen_mock,
        )

        # Lời hỏi hội thoại thông thường của người dùng
        res = dual.complete("Chào bạn, hôm nay thời tiết thế nào?")
        assert len(gemma_mock.calls) == 1
        assert len(qwen_mock.calls) == 0
        assert "Gemma-4B" in res["answer"]
        assert any("Gemma 4 E4B" in t for t in res["thinking"])

    def test_routes_task_to_vivyqu_core(self):
        qwen_mock = MockModelBackend("Qwen-72B")
        gemma_mock = MockModelBackend("Gemma-4B")

        dual = DualCognitiveBackend(
            comm_backend=gemma_mock,
            decomp_backend=qwen_mock,
        )

        # Lời hỏi yêu cầu tác vụ thực thi
        res = dual.complete("Hãy đọc file và kiểm tra trạng thái git.")
        # Với tác vụ, Lõi Vivyqu E9 sụp đổ k* và tiêm macro-action vào LLM
        assert len(gemma_mock.calls) == 1  # tiêm macro-action cho Gemma nói
        assert "CHỈ THỊ QUYẾT ĐỊNH TỪ LÕI VIVYQU CORE" in gemma_mock.calls[0]
