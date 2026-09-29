"""Bộ 5/5 — UI smoke test (spec §7.3.5).

Chốt: 4 bề mặt mở được, và **Thanh Thân thể đọc đúng state thật**.

Cách kiểm: dựng host thật, tải `index.html` qua HTTP của host, nối WebSocket `/bus`,
nhận `host.state` do host phát, rồi **đọc DOM** bằng Chrome headless:
`data-link` trên Body Bar phải khớp state host, đủ 4 `data-surface`, và
`proto-switch` phải biến mất khi đã nối bus (không cho giả vờ state).
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from websockets.sync.client import connect as ws_connect

REPO_ROOT = Path(__file__).resolve().parents[2]
CAUTREO_HOST_DIR = REPO_ROOT / "cautreo-host"

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

SURFACES = {"giao-tiep", "nhiem-vu", "skill-plugin", "he-thong"}

# state.py REASONS["endpoint_unreachable"] — host không bịa chuỗi giải thích.
ENDPOINT_UNREACHABLE = "không nối được endpoint"


def _find_chrome() -> Path | None:
    for p in CHROME_CANDIDATES:
        if p.is_file():
            return p
    return None


CHROME = _find_chrome()
needs_chrome = pytest.mark.skipif(CHROME is None, reason="không có Chrome/Edge để đọc DOM")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.05)
    raise TimeoutError(f"cổng {port} chưa mở sau {timeout}s")


class HostProcess:
    """Một host thật chạy trong process con. Dùng cho kiểm chứng đầu-cuối."""

    def __init__(self, port: int, args: list[str]) -> None:
        self.port = port
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "cautreo_host", "--port", str(port), "--no-browser", *args],
            cwd=str(CAUTREO_HOST_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        _wait_for_port(port)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def ws_url(self) -> str:
        return f"ws://127.0.0.1:{self.port}/bus"

    def close(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


@pytest.fixture(scope="module")
def offline_host():
    """Host với `--offline`: state phải là OFFLINE, model phải là null."""
    h = HostProcess(_free_port(), ["--offline"])
    yield h
    h.close()


@pytest.fixture(scope="module")
def degraded_host():
    """Host với endpoint model chết: state phải là DEGRADED + lý do thật."""
    h = HostProcess(_free_port(), ["--model-endpoint", "http://127.0.0.1:9"])
    yield h
    h.close()


def http_get(url: str) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:  # noqa: S310
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, ""


def bus_call(host: HostProcess, method: str, params: dict, req_id: str = "c-1") -> dict:
    """Gọi một method qua bus thật, trả về đúng khung phản hồi cho id đó."""
    with ws_connect(host.ws_url) as ws:
        first = json.loads(ws.recv())  # host.state
        assert first["method"] == "host.state"
        ws.send(json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            msg = json.loads(ws.recv())
            if msg.get("id") == req_id:
                return msg
    raise AssertionError(f"không có phản hồi cho {method!r}")


def dump_dom(url: str, profile_tag: str) -> str:
    """Chạy Chrome headless và trả về DOM đã kết xuất. Không chụp ảnh — chỉ DOM."""
    assert CHROME is not None
    out_dir = Path.cwd() / "_pytest_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(CHROME),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={out_dir / ('chrome-profile-' + profile_tag)}",
        "--virtual-time-budget=6000",
        "--dump-dom",
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=90)
    assert res.returncode == 0, res.stderr.decode("utf-8", "replace")[:500]
    return res.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- hợp đồng host


class TestHostServesUi:
    def test_index_is_served(self, offline_host):
        status, body = http_get(offline_host.base + "/")
        assert status == 200
        assert "<title>Cautreo" in body
        assert 'id="bodyBar"' in body

    def test_static_assets_are_served(self, offline_host):
        for path, needle in [("styles.css", "--nerve"), ("app.js", "setBusMode")]:
            status, body = http_get(offline_host.base + "/" + path)
            assert status == 200, path
            assert needle in body

    def test_missing_file_is_404(self, offline_host):
        status, _ = http_get(offline_host.base + "/khong-co")
        assert status == 404

    def test_path_traversal_is_refused(self, offline_host):
        # Host không cho nhảy ra ngoài thư mục UI bằng ../
        status, _ = http_get(offline_host.base + "/%2e%2e/cautreo-host/pyproject.toml")
        assert status in (403, 404)


class TestBusContract:
    def test_first_message_is_real_host_state(self, offline_host):
        with ws_connect(offline_host.ws_url) as ws:
            msg = json.loads(ws.recv())
        assert msg["method"] == "host.state"
        params = msg["params"]
        assert params["link"] == "OFFLINE"
        assert params["model"] is None  # OFFLINE thì không có model nào đang chạy
        assert set(params) == {"link", "reason", "reason_text", "model"}

    def test_response_carries_receipt_with_host_label(self, offline_host):
        msg = bus_call(
            offline_host, "tool.fs-read",
            {"path": "cautreo-host/pyproject.toml"}, req_id="c-1",
        )
        assert "error" not in msg
        assert set(msg) == {"jsonrpc", "id", "result", "receipt"}
        receipt = msg["receipt"]
        assert set(receipt) == {"id", "organ", "command", "result", "at", "source"}
        assert receipt["organ"] == "eye"
        assert receipt["command"] == "tool.fs-read"
        # Nhãn đọc file là tool-local — đọc đĩa không phải việc của model.
        # Đây là nhãn HOST gán theo sổ năng lực, không phải plugin tự khai.
        assert receipt["source"] == "tool-local"

    def test_error_has_neither_result_nor_receipt(self, degraded_host):
        """Khi model mất, lệnh cần model bị từ chối — không bịa câu trả lời."""
        with ws_connect(degraded_host.ws_url) as ws:
            first = json.loads(ws.recv())
            assert first["params"]["link"] == "DEGRADED"
            assert first["params"]["reason"] == "endpoint_unreachable"
            assert first["params"]["reason_text"] == ENDPOINT_UNREACHABLE
            ws.send(json.dumps({
                "jsonrpc": "2.0", "id": "c-9", "method": "vivy.runtime/ask",
                "params": {"prompt": "vẫn trả lời được chứ"},
            }))
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                msg = json.loads(ws.recv())
                if msg.get("id") == "c-9":
                    break
            else:
                raise AssertionError("không có phản hồi")
        assert set(msg) == {"jsonrpc", "id", "error"}
        assert "result" not in msg
        assert "receipt" not in msg
        assert msg["error"]["code"] == -32005
        # Lý do từ chối lấy đúng chuỗi của state machine, không phải UI nghĩ ra.
        assert msg["error"]["data"]["reason"] == ENDPOINT_UNREACHABLE

    def test_client_cannot_stamp_source(self, offline_host):
        msg = bus_call(
            offline_host, "tool.fs-write",
            {"path": "scratch/_smoke_ui.txt", "text": "ok", "source": "model"},
            req_id="c-2",
        )
        assert "error" not in msg
        # Ghi file là tool-local. Client nói "model" cũng không đổi được nhãn.
        assert msg["receipt"]["source"] == "tool-local"
        assert "source" not in msg["result"]


# ---------------------------------------------------------------- nối UI vào bus


class TestUiWiring:
    def test_app_js_takes_label_from_receipt(self, offline_host):
        _, js = http_get(offline_host.base + "/app.js")
        # UI lấy nhãn từ receipt do host gán.
        assert "receipt.source" in js
        # UI không tự dán nhãn bằng chuỗi cố định.
        assert 'setAttribute("data-src", "' not in js
        # Nối được bus thì cất công tắc trạng thái mẫu.
        assert "setBusMode" in js
        assert "protoSwitch" in js

    def test_index_declares_four_surfaces(self, offline_host):
        _, html = http_get(offline_host.base + "/")
        found = {s for s in SURFACES if f'data-surface="{s}"' in html}
        assert found == SURFACES

    def test_thinking_is_collapsed_not_paraded(self, offline_host):
        """Luồng tư duy bày thu gọn, ai muốn xem thì bấm mở — không tràn màn hình."""
        _, js = http_get(offline_host.base + "/app.js")
        # Mỗi đoạn suy nghĩ là một khối `<details>`.
        assert 'document.createElement("details")' in js
        assert 'className = "thinking"' in js
        assert "thinking-stack" in js
        # TỰ ĐỘNG THU GỌN: không có đoạn nào gán `open` cho nó.
        assert 'setAttribute("open"' not in js
        assert "det.open" not in js
        assert ".open = true" not in js

    def test_thinking_lands_after_the_answer_not_inside_it(self, offline_host):
        _, js = http_get(offline_host.base + "/app.js")
        # Khối suy nghĩ được append vào entry-body, không phải nội dung body.
        assert "buildThinking" in js
        assert "bodyEl.appendChild(thinkingEl)" in js

    def test_model_that_only_thought_is_said_so_not_papered_over(self, offline_host):
        _, js = http_get(offline_host.base + "/app.js")
        # Model chỉ sinh suy nghĩ → nói thẳng, KHÔNG lấy summary giả làm câu trả lời.
        assert "không có câu trả lời cuối" in js

    def test_thinking_blocks_are_visually_disclosed(self, offline_host):
        _, css = http_get(offline_host.base + "/styles.css")
        assert ".thinking-summary" in css
        assert "cursor: pointer" in css


# ---------------------------------------------------------------- bản đồ thân thể


class TestBodyMapIsVisible:
    """Bản đồ phải **truy cập được** từ giao diện, không chỉ nằm trong module Python.

    Kiểm đúng cái người dùng bảo: "khả năng truy cập tree map, tool map, plugin,
    skill". Chưa thấy trên màn hình thì chưa gọi là truy cập được.
    """

    def test_the_plate_is_on_the_system_surface(self, offline_host):
        _, html = http_get(offline_host.base + "/")
        assert 'id="bodyMap"' in html
        assert "Bản đồ thân thể" in html
        # Tuyên bố đúng xuất xứ: bản đồ dựng từ registry, không phải mô tả viết tay.
        assert "PluginRegistry" in html

    def test_when_not_wired_the_ui_says_so_instead_of_showing_a_fake_map(self, offline_host):
        """Chưa nối bus → bảng nói thẳng là chưa có, không bày bản đồ mẫu."""
        _, html = http_get(offline_host.base + "/")
        seed = html.split('id="bodyMap"', 1)[1].split("</div>", 1)[0]
        assert "Chưa nối bus" in seed
        assert "không phải bản đồ mẫu" in seed
        # Trong trạng thái chờ không được rò tên plugin nào — đó sẽ là bịa năng lực.
        assert "tool.fs-read" not in seed
        assert "vivy.runtime" not in seed

    def test_the_map_is_fetched_from_the_host_not_hardcoded(self, offline_host):
        _, js = http_get(offline_host.base + "/app.js")
        assert "refreshBodyMap" in js
        assert 'callBus("host.body-map"' in js
        # Vẽ từ `map` do host trả về, không từ hằng số viết trong JS.
        assert "renderBodyMap(msg.result.map)" in js
        assert 'root.setAttribute("data-map", "live")' in js

    def test_registry_change_rebuilds_the_map_without_a_restart(self, offline_host):
        """Thêm/bớt tool, plugin, skill → bản đồ tự dựng lại, không chờ ai nhớ gọi tay."""
        _, js = http_get(offline_host.base + "/app.js")
        assert 'msg.method === "registry.changed"' in js
        # Cổng mở là nạp bản đồ ngay — đúng yêu cầu "ngay khi Cautreo được khởi động".
        assert "refreshBodyMap()" in js

    def test_body_map_renders_both_organs_and_refuses_to_invent_a_third(self, offline_host):
        _, js = http_get(offline_host.base + "/app.js")
        assert "Mắt · cơ quan nhận" in js
        assert "Tay · cơ quan làm" in js
        assert "Method của host" in js
        # Mục "Thứ đang hỏng" phải có — lỗi không được giấu đi như cơ quan khoẻ.
        assert "Thứ đang hỏng" in js

    def test_body_map_has_its_own_visual_language(self, offline_host):
        _, css = http_get(offline_host.base + "/styles.css")
        assert ".body-map" in css
        # Hai cơ quan hai màu, theo đúng palette của Body Bar.
        assert ".map-section:nth-child(1) h4 { color: var(--iris)" in css
        assert ".map-section:nth-child(2) h4 { color: var(--ochre)" in css
        assert ".map-section:nth-child(5) h4 { color: var(--clot)" in css

    def test_body_map_is_queryable_without_a_model(self, degraded_host):
        """Bản đồ là chuyện của host, không cần model — DEGRADED vẫn đọc được.

        Đây là cửa `host.body-map` nói riêng. Lệnh cần model khi DEGRADED vẫn
        bị từ chối (test trên đã giữ), nhưng bản đồ thì không được phép im lặng.
        """
        msg = bus_call(degraded_host, "host.body-map", {}, req_id="c-map")
        assert "error" not in msg, msg.get("error")
        body_map = msg["result"]["map"]
        assert body_map["body"] == "Cautreo"
        assert body_map["soul"] == "ViVy"
        # Bằng chứng thật từ registry: có ít nhất các plugin demo đang nạp.
        ids = {p["id"] for organ in body_map["organs"].values() for p in organ}
        assert "tool.fs-read" in ids
        assert "vivy.runtime" in ids
        assert body_map["counts"]["plugins"] >= 2
        # Khi chưa có skill nào thì đếm là 0 — không bịa ra một skill nào.
        assert body_map["counts"]["skills"] == 0
        assert not any(p["id"].startswith("skill.") for organ in body_map["organs"].values() for p in organ)
        # Khung phản hồi đúng hợp đồng: chỉ `summary` + `map`, không có nhãn tự gán.
        assert set(msg["result"]) == {"summary", "map"}
        assert "source" not in msg["result"]


@needs_chrome
class TestBodyBarReadsTrueState:
    """Đọc DOM thật bằng Chrome headless. Không có ảnh — chỉ dump DOM, cho chính xác."""

    def test_offline_state_reaches_body_bar(self, offline_host):
        dom = dump_dom(offline_host.base + "/", f"off-{offline_host.port}")
        assert 'id="bodyBar" data-link="OFFLINE"' in dom
        # Đã nối bus → công tắc trạng thái mẫu biến mất.
        assert 'data-bus="live"' in dom
        after = dom.split('id="protoSwitch"', 1)[1][:160]
        assert "hidden" in after
        for s in SURFACES:
            assert f'data-surface="{s}"' in dom

    def test_degraded_state_with_true_reason_reaches_body_bar(self, degraded_host):
        dom = dump_dom(degraded_host.base + "/", f"deg-{degraded_host.port}")
        assert 'id="bodyBar" data-link="DEGRADED"' in dom
        # Lý do đúng khóa hợp đồng mà host báo, không phải chuỗi UI tự nghĩ ra.
        assert "endpoint_unreachable" in dom
        assert ENDPOINT_UNREACHABLE in dom
        for s in SURFACES:
            assert f'data-surface="{s}"' in dom

    def test_deep_link_cannot_fake_state_against_live_host(self, offline_host):
        """Mở `?link=online` trên host đang OFFLINE — Body Bar vẫn phải là OFFLINE.

        Deep link phục vụ điều hướng màn hình, không phải công tắc giả state.
        Host đã nối thì host nói sự thật; UI không để deep link đè lên.
        """
        dom = dump_dom(offline_host.base + "/?link=online", f"dl-{offline_host.port}")
        assert 'id="bodyBar" data-link="ONLINE"' not in dom
        assert 'id="bodyBar" data-link="OFFLINE"' in dom

    def test_deep_link_opens_a_surface(self, offline_host):
        """Deep link bề mặt vẫn dùng được khi đang xem máy thật."""
        dom = dump_dom(offline_host.base + "/?surface=nhiem-vu", f"sf-{offline_host.port}")
        assert 'data-surface="nhiem-vu"' in dom
        assert 'id="bodyBar" data-link="OFFLINE"' in dom
