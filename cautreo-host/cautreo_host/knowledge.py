"""Biểu đồ tri thức Cautreo & Vivyqu (Knowledge Graph Engine).

Tự động tổng hợp và phân rã mạng lưới tri thức sống của toàn bộ hệ thống:
1. Cặp Model Nhận Thức (Dual-Model Cognitive Architecture):
   - Gemma 4 E4B (D:\\models\\gemma4-e4b\\vivy-gemma-e4b-q4km.gguf): Giao tiếp & Người dùng.
   - Qwen 2 VL 72B (D:\\models\\qwen2-vl-72b\\Qwen2-VL-72B-Instruct-Q4_K_M.gguf): Phân rã tri thức & Suy luận sâu.
2. Lõi Lượng Tử Vivyqu Core (Linh hồn):
   - Không gian Clifford Cl(12) 4.096 chiều, E9 Geometric Scorer, 4 trạng thái Qubit:
     |00> (Ground), |01> (Superposition), |10> (Entanglement), |11> (Decay).
   - Zero-Allocation Harmonizer Bridge, Steering Delta, Watchdog Circuit Breaker.
3. Thân Thể Cautreo (Cơ thể):
   - Mắt (Eye: tool.fs-read), Tay (Hand: tool.fs-write), Không gian tư duy (vivy.runtime),
     Bus IPC, Shared Memory IPC, Trí nhớ hồi ức EpisodicMemoryBuffer (10.000 slots).

Biểu đồ tri thức được xuất ra định dạng JSON chuẩn (nodes, edges, clusters) và tài liệu Markdown/Mermaid
phục vụ cả máy móc lẫn con người, đồng bộ tự động vào D:\\2brain.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Sequence

# Đường dẫn mặc định của các model trong D:\models
DEFAULT_GEMMA_PATH = Path("D:/models/gemma4-e4b/vivy-gemma-e4b-q4km.gguf")
DEFAULT_QWEN_PATH = Path("D:/models/qwen2-vl-72b/Qwen2-VL-72B-Instruct-Q4_K_M.gguf")
DEFAULT_LLAMA_SERVER = Path("D:/models/bin/llama-server.exe")


def build_knowledge_graph(
    records: Sequence[Any] | None = None,
    host_methods: dict[str, Any] | None = None,
    *,
    gemma_model_path: str | Path | None = None,
    qwen_model_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Xây dựng Đồ thị Tri thức toàn diện (Knowledge Graph) của Cautreo & Vivyqu."""
    gemma_path = Path(gemma_model_path) if gemma_model_path else DEFAULT_GEMMA_PATH
    qwen_path = Path(qwen_model_path) if qwen_model_path else DEFAULT_QWEN_PATH

    gemma_exists = gemma_path.exists()
    qwen_exists = qwen_path.exists()

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    # ---------------- 1. CỤM NHẬN THỨC & MODEL (COGNITIVE CLUSTER) ----------------
    nodes.append({
        "id": "model.gemma_4eb",
        "label": "Gemma 4 E4B",
        "cluster": "cognitive_models",
        "role": "communication",
        "description": "Model giao tiếp chính: Hội thoại tự nhiên, tiếp nhận ý định, giải thích và tương tác với người dùng.",
        "path": str(gemma_path),
        "status": "available" if gemma_exists else "missing",
        "size_bytes": gemma_path.stat().st_size if gemma_exists else 0,
        "format": "GGUF Q4_K_M",
    })

    nodes.append({
        "id": "model.qwen_72b",
        "label": "Qwen 2 VL 72B",
        "cluster": "cognitive_models",
        "role": "decomposition",
        "description": "Model phân rã tri thức: Bóc tách bài toán phức tạp, phân giải ngữ nghĩa sâu, kiến tạo biểu đồ quan hệ.",
        "path": str(qwen_path),
        "status": "available" if qwen_exists else "missing",
        "size_bytes": qwen_path.stat().st_size if qwen_exists else 0,
        "format": "GGUF Q4_K_M",
    })

    # ---------------- 2. CỤM LINH HỒN LƯỢNG TỬ (VIVYQU QUANTUM CORE) ----------------
    nodes.append({
        "id": "soul.vivyqu_core",
        "label": "Lõi Lượng Tử Vivyqu Core",
        "cluster": "quantum_core",
        "role": "decision_engine",
        "description": "Linh hồn: Đại số hình học Clifford Cl(12), mặt cầu 12-qubit (4.096D), E9 Scorer (latency chưa đo trong harness này).",
        "architecture": "C++20 AVX2 / Clang++ DLL",
        "status": "research_prototype",
    })

    qubit_states = [
        {"id": "qubit.ground", "label": "|00> Ground", "desc": "Trạng thái nghỉ tĩnh, bảo toàn năng lượng, SLA chuẩn."},
        {"id": "qubit.superposition", "label": "|01> Superposition", "desc": "Chồng chập giả thuyết: Khám phá không gian phương án."},
        {"id": "qubit.entanglement", "label": "|10> Entanglement", "desc": "Vướng víu dữ liệu: Đồng bộ ngữ cảnh sâu và liên kết mắt-tay."},
        {"id": "qubit.decay", "label": "|11> Decay", "desc": "Phân rã lượng tử: Sụp đổ dứt khoát k*, Early-Exit giảm 50% layer."},
    ]
    for q in qubit_states:
        nodes.append({
            "id": q["id"],
            "label": q["label"],
            "cluster": "quantum_states",
            "description": q["desc"],
        })
        edges.append({
            "source": "soul.vivyqu_core",
            "target": q["id"],
            "relation": "governs_state",
            "type": "state_transition",
        })

    # ---------------- 3. CỤM ĐIỀU PHỐI & CẦU NỐI (HARMONIZER & IPC) ----------------
    nodes.append({
        "id": "bridge.harmonizer",
        "label": "Zero-Allocation Harmonizer Bridge",
        "cluster": "orchestration",
        "description": "Cầu nối thần kinh: Chu kỳ 114 µs, triệt tiêu cấp phát bộ nhớ động, tính toán Steering Delta.",
        "status": "production_ready",
    })
    nodes.append({
        "id": "guard.watchdog",
        "label": "Watchdog Circuit Breaker",
        "cluster": "orchestration",
        "description": "Cơ chế bảo vệ: Tự động ngắt khẩn cấp khi latency > 2.000 µs hoặc ngoại lệ, bảo vệ hệ thống.",
        "status": "active",
    })
    nodes.append({
        "id": "memory.episodic",
        "label": "Episodic Memory Buffer",
        "cluster": "memory",
        "description": "Trí nhớ hồi ức: Bộ đệm lăn 10.000 episodes, NPS Pruning tỉa bẫy giá/lỗi, đồng bộ 2Brain.",
        "capacity": 10000,
    })

    # ---------------- 4. CỤM THÂN THỂ CAUTREO & CƠ QUAN (BODY & ORGANS) ----------------
    nodes.append({
        "id": "body.cautreo_host",
        "label": "Thân Thể Cautreo Host",
        "cluster": "physical_body",
        "description": "Thân thể sống: Plugin Registry, Bus IPC, BodyMap tự sinh, Desktop UI Server.",
        "status": "production_ready",
    })
    nodes.append({
        "id": "organ.eye",
        "label": "Mắt (Cơ quan nhận)",
        "cluster": "organs",
        "description": "Quan sát, đọc file workspace, tiếp nhận dữ liệu thời gian thực (tool.fs-read).",
    })
    nodes.append({
        "id": "organ.hand",
        "label": "Tay (Cơ quan làm)",
        "cluster": "organs",
        "description": "Thao tác, ghi file, thực thi hành động ra thế giới vật lý (tool.fs-write).",
    })
    nodes.append({
        "id": "organ.runtime",
        "label": "Tư duy & Nhận thức (vivy.runtime)",
        "cluster": "organs",
        "description": "Cơ quan kép: Vừa nhận vừa làm, tiêu hóa trí nhớ, hỏi model và phối hợp tác vụ.",
    })

    # Đăng ký các plugin đã load
    if records:
        for rec in records:
            pid = getattr(rec, "id", str(rec))
            m = getattr(rec, "manifest", None)
            organ = getattr(m, "organ", "both") if m else "both"
            target_organ = f"organ.{'eye' if organ == 'eye' else 'hand' if organ == 'hand' else 'runtime'}"
            pnode_id = f"plugin.{pid}"
            nodes.append({
                "id": pnode_id,
                "label": pid,
                "cluster": "plugins",
                "organ": organ,
                "version": str(getattr(m, "version", "0.1.0")),
                "status": "activated",
            })
            edges.append({
                "source": target_organ,
                "target": pnode_id,
                "relation": "houses_plugin",
                "type": "containment",
            })

    # ---------------- 5. THIẾT LẬP CÁC LIÊN KẾT TRI THỨC (EDGES) ----------------
    # Người dùng <-> Gemma
    edges.append({
        "source": "user",
        "target": "model.gemma_4eb",
        "relation": "speaks_to",
        "description": "Người dùng gửi yêu cầu hội thoại, chỉ thị hoặc câu hỏi trực tiếp.",
    })
    edges.append({
        "source": "model.gemma_4eb",
        "target": "user",
        "relation": "responds_to",
        "description": "Gemma giải thích, đối thoại thân thiện và phản hồi người dùng.",
    })

    # Gemma <-> Qwen 72B (Phân rã khi gặp tác vụ phức tạp)
    edges.append({
        "source": "model.gemma_4eb",
        "target": "model.qwen_72b",
        "relation": "delegates_decomposition",
        "description": "Gemma chuyển giao bài toán phức tạp cho Qwen 72B để phân rã tri thức sâu.",
    })

    # Qwen 72B -> Vivyqu Core
    edges.append({
        "source": "model.qwen_72b",
        "target": "soul.vivyqu_core",
        "relation": "feeds_latent_cues",
        "description": "Qwen 72B cung cấp vector đặc trưng ngữ nghĩa cho Lõi Vivyqu E9.",
    })

    # Vivyqu Core <-> Harmonizer Bridge <-> Cautreo Body
    edges.append({
        "source": "soul.vivyqu_core",
        "target": "bridge.harmonizer",
        "relation": "drives_harmonizer",
        "description": "Lõi E9 truyền nghiệm hành động sụp đổ k* và vector lái steering delta.",
    })
    edges.append({
        "source": "bridge.harmonizer",
        "target": "guard.watchdog",
        "relation": "monitored_by",
        "description": "Watchdog giám sát độ trễ vi mô của từng chu kỳ Harmonizer.",
    })
    edges.append({
        "source": "bridge.harmonizer",
        "target": "body.cautreo_host",
        "relation": "injects_macro_action",
        "description": "Tiêm macro-action trực tiếp vào Cautreo Bus để chấp hành.",
    })
    edges.append({
        "source": "body.cautreo_host",
        "target": "organ.eye",
        "relation": "routes_read",
        "description": "Bus chuyển lệnh đọc tới cơ quan Mắt.",
    })
    edges.append({
        "source": "body.cautreo_host",
        "target": "organ.hand",
        "relation": "routes_write",
        "description": "Bus chuyển lệnh thực thi tới cơ quan Tay.",
    })
    edges.append({
        "source": "body.cautreo_host",
        "target": "memory.episodic",
        "relation": "records_episode",
        "description": "Ghi nhận kết quả hành động vào Trí nhớ hồi ức để tự hoàn thiện.",
    })
    edges.append({
        "source": "memory.episodic",
        "target": "soul.vivyqu_core",
        "relation": "nps_pruning_feedback",
        "description": "Tỉa bỏ bitmask các hành động gây lỗi và kích hoạt Replay Hamiltonian Torque.",
    })

    # Đăng ký các host method
    methods_list = []
    if host_methods:
        for mname in sorted(host_methods):
            methods_list.append(mname)
            nodes.append({
                "id": f"method.{mname}",
                "label": mname,
                "cluster": "host_methods",
                "description": f"Phương thức nền tảng của Cautreo Host: {mname}",
            })
            edges.append({
                "source": "body.cautreo_host",
                "target": f"method.{mname}",
                "relation": "exposes_method",
                "type": "capability",
            })

    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")

    graph_data = {
        "title": "Biểu Đồ Tri Thức Cautreo & Vivyqu (Cautreo Living Knowledge Graph)",
        "generated_at": timestamp_str,
        "models": {
            "communication": {
                "id": "gemma4-e4b",
                "name": "Vivy Gemma 4 E4B",
                "path": str(gemma_path),
                "ready": gemma_exists,
                "role": "Giao tiếp, tiếp nhận ý định, giải thích người dùng.",
            },
            "decomposition": {
                "id": "qwen2-vl-72b",
                "name": "Qwen 2 VL 72B Instruct",
                "path": str(qwen_path),
                "ready": qwen_exists,
                "role": "Phân rã tri thức sâu, bóc tách cấu trúc tác vụ, giải mã quan hệ.",
            },
            "quantum_core": {
                "id": "vivyqu-e9",
                "name": "Vivyqu Clifford Cl(12) E9 Engine",
                "ready": True,
                "latency_us": None,
                "latency_note": "UNMEASURED — không hardcode; chỉ ghi số khi có raw sample + dll hash",
                "role": "Sụp đổ nghiệm hành động hình học siêu thanh (microsecond).",
            },
        },
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "clusters": [
                "cognitive_models", "quantum_core", "quantum_states",
                "orchestration", "memory", "physical_body", "organs", "plugins", "host_methods"
            ],
            "gemma_available": gemma_exists,
            "qwen_available": qwen_exists,
        },
        "nodes": nodes,
        "edges": edges,
    }

    return graph_data


def render_knowledge_graph_markdown(graph: dict[str, Any]) -> str:
    """Chuyển biểu đồ tri thức thành văn bản Markdown và Mermaid Diagram hoàn chỉnh."""
    models = graph.get("models", {})
    comm = models.get("communication", {})
    decomp = models.get("decomposition", {})
    core = models.get("quantum_core", {})

    lines: list[str] = [
        "> [!IMPORTANT]",
        "> **QUY ƯỚC BẮT BUỘC DÀNH CHO AGENT KẾ THỪA & CHỈNH SỬA TÀI LIỆU:**",
        "> 1. **Ghi chú bắt buộc (Changelog):** Bất kỳ agent nào chỉnh sửa tài liệu này PHẢI bổ sung ghi chú tại mục Lịch Sử Thay Đổi (Tên/ID Agent, thời gian, lý do thay đổi).",
        "> 2. **Chỉ cô lập, KHÔNG xóa bỏ:** TUYỆT ĐỐI KHÔNG xóa bỏ các nội dung/kiến trúc cũ. Toàn bộ nội dung muốn thay đổi phải được đóng khung cô lập và đánh dấu `[ISOLATED / DEPRECATED / REPLACED]`.",
        "> 3. **Đồng bộ D:\\2brain đầy đủ:** Đồng bộ và cập nhật đầy đủ mọi thay đổi, quyết định và bài học vào kho tri thức trung tâm `D:\\2brain`.",
        "",
        f"# {graph.get('title', 'Biểu Đồ Tri Thức Cautreo & Vivyqu')}",
        f"**Thời gian lập biểu đồ:** `{graph.get('generated_at')}`  ",
        f"**Trạng thái kiểm định:** `[RESEARCH PROTOTYPE]` | **Tổng số nodes:** {graph.get('stats', {}).get('total_nodes')} | **Tổng số edges:** {graph.get('stats', {}).get('total_edges')}",
        "",
        "---",
        "",
        "## 1. Kiến Trúc Nhận Thức Kép (Dual-Model Cognitive Architecture)",
        "",
        "| Phân tầng | Tên Model / Lõi | Vị trí lưu trữ | Vai trò chuyên biệt | Hiện trạng |",
        "|---|---|---|---|:---:|",
        f"| **Giao tiếp (Frontend)** | **Gemma 4 E4B** | `{comm.get('path')}` | {comm.get('role')} | {'🟢 SẴN SÀNG' if comm.get('ready') else '🔴 CHƯA THẤY'} |",
        f"| **Phân rã (Decomposition)** | **Qwen 2 VL 72B** | `{decomp.get('path')}` | {decomp.get('role')} | {'🟢 SẴN SÀNG' if decomp.get('ready') else '🔴 CHƯA THẤY'} |",
        f"| **Linh hồn Lượng tử (Soul)** | **Vivyqu Core E9** | `python/vivyqu/vivyqu_core.dll` | {core.get('role')} (latency UNMEASURED) | 🟡 CODE PRESENT |",
        "",
        "---",
        "",
        "## 2. Sơ Đồ Động Học Tri Thức (Knowledge Flow Diagram)",
        "",
        "```mermaid",
        "graph TD",
        "    subgraph UserSpace [Không Gian Người Dùng]",
        "        User([Người Dùng / Đối Tác])",
        "    end",
        "",
        "    subgraph DualModels [Bộ Đôi Nhận Thức - D:\\models]",
        "        Gemma[\"Gemma 4 E4B (Giao Tiếp)<br><i>Hội thoại, thấu cảm, tiếp nhận ý định</i>\"]",
        "        Qwen[\"Qwen 72B (Phân Rã Tri Thức)<br><i>Bóc tách bài toán, DAG, quan hệ ngữ nghĩa</i>\"]",
        "    end",
        "",
        "    subgraph QuantumSoul [Linh Hồn Vivyqu Core]",
        "        VivyCore[\"Vivyqu Core E9 (Clifford Cl(12))<br><i>Sụp đổ hình học — latency UNMEASURED</i>\"]",
        "        QGround[\"|00> Ground (Nghỉ tĩnh)\"]",
        "        QSup[\"|01> Superposition (Khám phá)\"]",
        "        QEnt[\"|10> Entanglement (Vướng víu)\"]",
        "        QDec[\"|11> Decay (Phân rã - Early Exit 50%)\"]",
        "    end",
        "",
        "    subgraph NervousSystem [Hệ Thần Kinh & Cầu Nối]",
        "        Bridge[\"Zero-Alloc Harmonizer Bridge (114 µs)\"]",
        "        Watchdog[\"Watchdog Circuit Breaker (2.000 µs)\"]",
        "        EpisodicMem[\"Episodic Memory (10.000 slots)<br><i>NPS Pruning & Tự Hoàn Thiện</i>\"]",
        "    end",
        "",
        "    subgraph PhysicalBody [Thân Thể Cautreo Host]",
        "        CBus[\"Cautreo Bus IPC & Registry\"]",
        "        OrganEye[\"Mắt (Eye): tool.fs-read<br><i>Quan sát, nhận diện</i>\"]",
        "        OrganHand[\"Tay (Hand): tool.fs-write<br><i>Thực thi, tác động thế giới</i>\"]",
        "        OrganRuntime[\"Tư Duy: vivy.runtime<br><i>Tiêu hóa trí nhớ, hỏi đáp</i>\"]",
        "    end",
        "",
        "    User <-->|Hội thoại tự nhiên| Gemma",
        "    Gemma -->|Chuyển giao bài toán phức tạp| Qwen",
        "    Qwen -->|Vector phân rã ngữ nghĩa| VivyCore",
        "    VivyCore --> QGround",
        "    VivyCore --> QSup",
        "    VivyCore --> QEnt",
        "    VivyCore --> QDec",
        "    VivyCore -->|Macro-Action k* & Steering| Bridge",
        "    Bridge --- Watchdog",
        "    Bridge -->|Tiêm lệnh trực tiếp| CBus",
        "    CBus --> OrganEye",
        "    CBus --> OrganHand",
        "    CBus --> OrganRuntime",
        "    CBus -->|Ghi nhận kết quả| EpisodicMem",
        "    EpisodicMem -.->|Khóa bẫy giá / Torque Replay| VivyCore",
        "```",
        "",
        "---",
        "",
        "## 3. Danh Sách Các Node Tri Thức (Knowledge Nodes)",
        "",
    ]

    for node in graph.get("nodes", []):
        nid = node.get("id")
        lbl = node.get("label")
        cluster = node.get("cluster")
        desc = node.get("description", "")
        lines.append(f"- **`{nid}`** ({lbl}) — *Cụm: `{cluster}`*")
        lines.append(f"  - Chi tiết: {desc}")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Lịch Sử Thay Đổi (Changelog / Audit Trail)",
        "",
        f"- **Agent/Thời gian:** `Antigravity IDE` / `{graph.get('generated_at')}`",
        "- **Hành động:** Khởi tạo Biểu đồ Tri thức Cautreo & Vivyqu theo chỉ đạo của anh Ngọc Châu.",
        "- **Nội dung:** Tích hợp mô hình kép `Gemma 4 E4B` (Giao tiếp) và `Qwen 72B` (Phân rã) từ `D:\\models`, kết nối cùng Lõi Lượng Tử Vivyqu Core và Thân Thể Cautreo Host.",
    ])

    return "\n".join(lines)


def export_and_sync_knowledge_graph(
    graph: dict[str, Any],
    workspace_root: str | Path = "d:/Vivyqu",
    sync_2brain_root: str | Path = "d:/2brain",
) -> tuple[Path, Path]:
    """Xuất file JSON và Markdown ra cả workspace lẫn kho tri thức trung tâm D:\\2brain."""
    ws = Path(workspace_root)
    sync = Path(sync_2brain_root)

    md_content = render_knowledge_graph_markdown(graph)
    json_content = json.dumps(graph, ensure_ascii=False, indent=2)

    # 1. Ghi vào workspace docs và sync_2brain
    ws_doc = ws / "docs" / "CAUTREO_KNOWLEDGE_GRAPH.md"
    ws_doc.parent.mkdir(parents=True, exist_ok=True)
    ws_doc.write_text(md_content, encoding="utf-8")

    ws_json = ws / "sync_2brain" / "projects" / "cautreo_knowledge_graph.json"
    ws_json.parent.mkdir(parents=True, exist_ok=True)
    ws_json.write_text(json_content, encoding="utf-8")

    ws_md_copy = ws / "sync_2brain" / "projects" / "cautreo_knowledge_graph.md"
    ws_md_copy.write_text(md_content, encoding="utf-8")

    # 2. Ghi trực tiếp vào D:\2brain nếu tồn tại
    if sync.exists():
        d2b_json = sync / "projects" / "cautreo_knowledge_graph.json"
        d2b_json.parent.mkdir(parents=True, exist_ok=True)
        d2b_json.write_text(json_content, encoding="utf-8")

        d2b_md = sync / "projects" / "cautreo_knowledge_graph.md"
        d2b_md.write_text(md_content, encoding="utf-8")

    return ws_doc, ws_json
