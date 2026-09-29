"""
test_desktop_studio.py — End-to-End Smoke Tests for Cautreo Desktop Studio
Tests FastAPI backend, C-ABI vitals, 3 Sockets, Dream Engine, and SSE Chat Streaming.

Author: Antigravity IDE (Verification Phase)
"""

import json
import sys
import time
from pathlib import Path

DESKTOP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = DESKTOP_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient
from server import app


def test_desktop_studio():
    client = TestClient(app)
    passed = 0
    total = 6

    print("\n=======================================================")
    print("  RUNNING CAUTREO DESKTOP STUDIO E2E INTEGRATION TESTS")
    print("=======================================================\n")

    # 1. Test Static Root
    print("[TEST 1/6] Testing Static UI Delivery (GET /)...")
    resp = client.get("/")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "Cautreo Desktop Studio" in resp.text, "index.html title missing"
    assert "pane-ecosystem" in resp.text, "Ecosystem pane missing"
    print("  -> PASS: Frontend index.html served cleanly.")
    passed += 1

    # 2. Test Vitals Endpoint
    print("[TEST 2/6] Testing Engine Vitals (GET /api/vitals)...")
    resp = client.get("/api/vitals")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    vitals = resp.json()
    assert vitals["status"] == "ONLINE"
    assert "scores" in vitals
    assert "context_memory" in vitals
    assert vitals["scores"]["task_progress"] > 0
    assert vitals["scores"]["context_efficiency"] > 0
    assert vitals["scores"]["memory_quality"] > 0
    print(f"  -> PASS: Vitals online. Task Progress: {vitals['scores']['task_progress']}%, Slots: {vitals['context_memory']['used_slots']}/2048.")
    passed += 1

    # 3. Test 3 Sockets Endpoint
    print("[TEST 3/6] Testing 3 Sockets Extensibility (GET /api/sockets)...")
    resp = client.get("/api/sockets")
    assert resp.status_code == 200
    sockets = resp.json()
    assert "harness" in sockets
    assert "tools" in sockets
    assert "skills" in sockets
    assert len(sockets["harness"]["workers"]) >= 3
    assert len(sockets["tools"]["plugins"]) >= 3
    assert len(sockets["skills"]["skills"]) >= 3
    print(f"  -> PASS: 3 Sockets online. Workers: {len(sockets['harness']['workers'])}, Plugins: {len(sockets['tools']['plugins'])}, Skills: {len(sockets['skills']['skills'])}.")
    passed += 1

    # 4. Test Harness Goal Toggle
    print("[TEST 4/6] Testing Harness /goal Toggle (POST /api/sockets/harness/toggle_goal)...")
    resp = client.post("/api/sockets/harness/toggle_goal")
    assert resp.status_code == 200
    res = resp.json()
    assert "goal_mode" in res
    assert res["goal_mode"] is True
    # Toggle back
    client.post("/api/sockets/harness/toggle_goal")
    print("  -> PASS: /goal mode toggle verified.")
    passed += 1

    # 5. Test Dream Engine Trigger
    print("[TEST 5/6] Testing Dream Engine Cycle (POST /api/dream)...")
    resp = client.post("/api/dream")
    assert resp.status_code == 200
    dream = resp.json()
    assert dream["success"] is True
    assert dream["status"] == "LUCID_STANDBY"
    assert dream["latency_ms"] > 0
    print(f"  -> PASS: Dream Cycle completed in {dream['latency_ms']}ms. State: {dream['status']}.")
    passed += 1

    # 6. Test Chat Streaming
    print("[TEST 6/6] Testing SSE Chat Streaming with <vivy_thought> (POST /api/chat)...")
    with client.stream("POST", "/api/chat", json={"message": "Xin chào ViVy", "model": "gemma4-e4b"}) as stream:
        assert stream.status_code == 200
        content = ""
        has_thought = False
        has_token = False
        has_done = False
        for line in stream.iter_lines():
            content += line + "\n"
            if "event: thought" in line:
                has_thought = True
            if "event: token" in line:
                has_token = True
            if "event: done" in line:
                has_done = True
        assert has_thought, "Missing event: thought"
        assert has_token, "Missing event: token"
        assert has_done, "Missing event: done"
    print("  -> PASS: SSE Streaming received thought, token, and done events.")
    passed += 1

    print("\n=======================================================")
    print(f"  ALL {passed}/{total} DESKTOP STUDIO TESTS PASSED 100%!")
    print("=======================================================\n")
    return True


if __name__ == "__main__":
    test_desktop_studio()
