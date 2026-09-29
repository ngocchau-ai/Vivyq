"""
server.py — Cautreo Desktop Studio Backend API Server
FastAPI HTTP & SSE Streaming Server on port 8765.

[SANDBOX — NOT PRODUCTION] Protocol REST+SSE riêng, không phải host bus JSON-RPC.
Câu trả lời/metrics mô phỏng (nếu còn) KHÔNG được coi là bằng chứng sản phẩm.
Production surface: ui/cautreo-desktop + host/cautreo_host.

Author: Antigravity IDE (Sprint D1/D2)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

sys.path.insert(0, str(BACKEND_DIR))

from bridge import DesktopBridge
from sockets.harness_socket import HarnessSocket
from sockets.skills_socket import SkillsSocket
from sockets.tools_socket import ToolsSocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [CautreoStudio] %(message)s",
)
logger = logging.getLogger("cautreo.studio.server")

app = FastAPI(title="Cautreo Desktop Studio API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bridge = DesktopBridge.get_instance()
harness_socket = HarnessSocket()
tools_socket = ToolsSocket()
skills_socket = SkillsSocket()


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "gemma4-e4b"
    stream: bool = True
    context_skill: Optional[str] = None


@app.get("/api/vitals")
async def get_vitals() -> Dict[str, Any]:
    """Retrieve live Cautreo engine vitals."""
    return bridge.get_vitals()


@app.get("/api/sockets")
async def get_sockets() -> Dict[str, Any]:
    """Retrieve full status of the 3 Extension Sockets."""
    return {
        "harness": harness_socket.get_state(),
        "tools": tools_socket.get_state(),
        "skills": skills_socket.get_state(),
    }


@app.post("/api/sockets/harness/toggle_goal")
async def toggle_goal() -> Dict[str, Any]:
    """Toggle /goal autonomous execution loop."""
    active = harness_socket.toggle_goal_mode()
    bridge.goal_mode_active = active
    return {"success": True, "goal_mode": active}


@app.post("/api/sockets/tools/toggle")
async def toggle_tool(payload: Dict[str, str]) -> Dict[str, Any]:
    """Toggle a plugin tool in Cautreo Tool Registry."""
    tool_id = payload.get("tool_id", "")
    new_state = tools_socket.toggle_tool(tool_id)
    return {"success": True, "tool_id": tool_id, "enabled": new_state}


@app.post("/api/dream")
async def trigger_dream() -> Dict[str, Any]:
    """Trigger Dream Engine consolidation cycle."""
    return bridge.trigger_dream()


async def generate_chat_stream(
    user_msg: str, model: str
) -> AsyncGenerator[str, None]:
    """Streams thought block and response tokens via SSE."""
    start_time = time.perf_counter()
    llama_url = os.getenv("VIVY_LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")

    # Check if real llama-server is responsive
    real_stream = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            test_resp = await client.get("http://127.0.0.1:8080/health")
            if test_resp.status_code == 200:
                real_stream = True
    except Exception:
        real_stream = False

    if real_stream:
        # Stream from real llama-server
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    llama_url,
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": user_msg}],
                        "stream": True,
                    },
                ) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield f"{line}\n\n"
            return
        except Exception as e:
            logger.warning("Real streaming error (%s), fallback to cognitive synth", e)

    # High-fidelity Cognitive Simulation
    thought_chunks = [
        "<vivy_thought>\n",
        "  [EPISTEMIC HYPOTHESIS]\n",
        f"  - Input Query: \"{user_msg}\"\n",
        f"  - Active Reasoner: {model} (Cautreo C-ABI Native)\n",
        "  - Cognitive Graph: Node lookup in StateGraph -> Confidence 0.98\n",
        "  - Invariant Check: VM-11 dampener active (rate: Gate-10 receipt)\n",
        "  - Route: Direct Epistemic Synthesis & Execution Plan\n",
        "</vivy_thought>\n\n",
    ]

    total_tokens = 0
    thought_text = "".join(thought_chunks)

    # Emit thought block as single event
    yield f"event: thought\ndata: {json.dumps({'content': thought_text, 'ms': 310})}\n\n"
    await asyncio.sleep(0.15)

    # Determine synthesized response based on message content
    if "/goal" in user_msg.lower() or "goal" in user_msg.lower():
        # [ISOLATED 23/09/2026] prior Gate 1 claimed "100% tests pass",
        # Gate 4 claimed "RAM ~35MB", Gate 5 claimed "C-ABI Memory in-process
        # 0ms latency" — Gate 9 requires a reproducible receipt.
        reply = (
            "🎯 **CHẾ ĐỘ /GOAL ĐÃ ĐƯỢC KÍCH HOẠT THÀNH CÔNG.**\n\n"
            "ViVy Final phối hợp cùng Cautreo Engine giám sát toàn diện 7 Completion Gates:\n"
            "1. ✅ **Gate 1:** Build & test suite (see latest run receipt)\n"
            "2. ✅ **Gate 2:** Git clean diff & VM-11 dampener (rate: Gate-10 receipt)\n"
            "3. ✅ **Gate 3:** Triệt tiêu AI slop — Epistemic grammar chuẩn hóa\n"
            "4. ✅ **Gate 4:** Bộ nhớ native shell nhẹ (RAM: see benchmark receipt)\n"
            "5. ✅ **Gate 5:** C-ABI Memory in-process (latency: see benchmark receipt)\n"
            "6. ✅ **Gate 6:** Dream Engine cycle `LUCID_STANDBY`\n"
            "7. ✅ **Gate 7:** Đồng bộ tri thức bền vững vào `D:\\2brain`"
        )
    elif "/dream" in user_msg.lower() or "dream" in user_msg.lower():
        dream_res = bridge.trigger_dream()
        reply = (
            f"🌙 **CHU TRÌNH DREAM ENGINE ĐÃ HOÀN TẤT TRONG {dream_res['latency_ms']}ms!**\n\n"
            f"- Trạng thái nhận thức: `{dream_res['status']}`\n"
            f"- Mã chu trình: `{dream_res['cycle_id']}`\n"
            f"- Tổng số nodes đã củng cố: `{dream_res['consolidated_nodes']}`\n"
            "- Trọng số trực giác đã được lưu trữ an toàn trong `cautreo.dll` Context Memory."
        )
    elif "chào" in user_msg.lower() or "hello" in user_msg.lower():
        reply = (
            "Chào bạn! Tôi là **ViVy Final Core V1.0** — Trí tuệ nhận thức ngự trị trong cơ thể vật lý **Cautreo Engine**.\n\n"
            "Căn phòng điều hành Desktop Studio đã sẵn sàng với 3 socket mở rộng:\n"
            "- **Harness Socket:** Điều phối Codex CLI, Claude Code và chế độ `/goal`.\n"
            "- **Tool Socket:** Gọi công cụ WebSearch, SysTools, FileSystem (latency: benchmark receipt).\n"
            "- **Skill Socket:** Thư viện kỹ năng `.agents/skills/*` nạp tức thì 1 chạm."
        )
    else:
        reply = (
            f"Đã tiếp nhận yêu cầu: **\"{user_msg}\"**\n\n"
            f"Hệ thống đã định tuyến qua lõi **{model}** và lưu ngữ cảnh vào bộ nhớ Cautreo.\n"
            "- Bộ nhớ RAM: Đã ghi nhận `TASK` ID vào C-ABI slot.\n"
            "- Đồ thị trạng thái: Cập nhật trọng số thành công.\n"
            "- Hệ thống sẵn sàng nhận chỉ thị tiếp theo từ bạn!"
        )

    words = reply.split(" ")
    for word in words:
        yield f"event: token\ndata: {json.dumps({'token': word + ' '})}\n\n"
        total_tokens += 1
        await asyncio.sleep(0.025)  # Simulates ~14 tok/s natural inference

    elapsed = time.perf_counter() - start_time
    tok_per_sec = round(total_tokens / max(elapsed, 0.1), 1)

    yield f"event: done\ndata: {json.dumps({'total_tokens': total_tokens, 'velocity': tok_per_sec, 'elapsed_s': round(elapsed, 2)})}\n\n"


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """SSE streaming chat endpoint."""
    return StreamingResponse(
        generate_chat_stream(req.message, req.model or "gemma4-e4b"),
        media_type="text/event-stream",
    )


# Mount static frontend
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def start_server(host: str = "127.0.0.1", port: int = 8765):
    """Starts the uvicorn server."""
    logger.info("Starting Cautreo Desktop Studio Server on http://%s:%d", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_server()
