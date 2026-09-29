"""Script chạy Cautreo Host nạp cấu hình Dual-Model từ D:\\models và lập Biểu đồ Tri thức.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

# Đảm bảo PYTHONPATH chứa host và python
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "host"))
sys.path.insert(0, str(REPO_ROOT / "python"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


from cautreo_host.host import Host
from cautreo_host.knowledge import export_and_sync_knowledge_graph, render_knowledge_graph_markdown

def main() -> int:
    print("=" * 80)
    print("  CAUTREO LIVING KNOWLEDGE GRAPH GENERATOR & DUAL-MODEL LOADER")
    print("=" * 80)

    gemma_path = Path("D:/models/gemma4-e4b/vivy-gemma-e4b-q4km.gguf")
    qwen_path = Path("D:/models/qwen2-vl-72b/Qwen2-VL-72B-Instruct-Q4_K_M.gguf")

    print(f"\n[1] Kiểm tra hiện diện các model trong D:\\models:")
    print(f"  * Gemma 4 E4B (Giao tiếp):     {gemma_path} -> {'TỒN TẠI (' + str(round(gemma_path.stat().st_size / (1024**3), 2)) + ' GB)' if gemma_path.exists() else 'CHƯA THẤY'}")
    print(f"  * Qwen 2 VL 72B (Phân rã):     {qwen_path} -> {'TỒN TẠI (' + str(round(qwen_path.stat().st_size / (1024**3), 2)) + ' GB)' if qwen_path.exists() else 'CHƯA THẤY'}")

    print(f"\n[2] Khởi tạo Thân Thể Cautreo Host với cấu hình Dual-Model...")
    host = Host(
        ui_dir=REPO_ROOT / "cautreo-desktop-ui",
        plugins_dir=REPO_ROOT / "host" / "plugins",
        workspace=REPO_ROOT,
        dual_models=True,
        gemma_path=gemma_path,
        qwen_path=qwen_path,
    )

    loaded = host.load_plugins()
    print(f"  * Đã nạp thành công {len(loaded)} plugins: {', '.join(loaded)}")

    host.open_link()
    print(f"  * Trạng thái liên kết Model: {host.link.state.value} (Model: {host.link.model})")


    print(f"\n[3] Lập và phân rã Biểu đồ Tri thức Cautreo & Vivyqu...")
    graph = host.bus.knowledge_graph
    stats = graph.get("stats", {})
    print(f"  * Tổng số Nodes tri thức: {stats.get('total_nodes')}")
    print(f"  * Tổng số Edges liên kết: {stats.get('total_edges')}")
    print(f"  * Các phân vùng cụm: {', '.join(stats.get('clusters', []))}")

    print(f"\n[4] Xuất tệp và đồng bộ hóa sang kho tri thức trung tâm D:\\2brain...")
    doc_path, json_path = export_and_sync_knowledge_graph(graph, workspace_root=REPO_ROOT, sync_2brain_root="D:/2brain")
    print(f"  * Đã xuất Markdown & Mermaid: {doc_path}")
    print(f"  * Đã xuất JSON Machine-readable: {json_path}")
    print(f"  * Đã đồng bộ sang D:\\2brain\\projects\\cautreo_knowledge_graph.md")
    print(f"  * Đã đồng bộ sang D:\\2brain\\projects\\cautreo_knowledge_graph.json")

    print("\n" + "=" * 80)
    print("  HOÀN THÀNH LẬP BIỂU ĐỒ TRI THỨC VÀ NẠP CẤU HÌNH CAUTREO DUAL-MODEL!")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
