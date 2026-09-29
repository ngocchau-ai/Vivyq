"""Host mảnh — đúng ba thứ (spec §3): cửa sổ · Plugin Registry · IPC Bus.

**Cửa sổ là trình duyệt.** Host phục vụ `cautreo-desktop-ui/` qua HTTP trên cùng
process với WebSocket của bus, rồi mở trình duyệt hệ thống. Không có webview native
nào ở đây (`pywebview` không cài được trong môi trường này) và host **không giả
vờ** có — xem README.

Single-instance bằng khóa file ở mức hệ điều hành: tiến trình chết thì khóa tự
nhả, không có khóa PID nào còn sót lại.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import mimetypes
import os
import sys
import tempfile
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, cast

from websockets.datastructures import Headers
from websockets.legacy.server import WebSocketServerProtocol, serve

from .backends import default_backends
from .bus import Bus
from .receipt import ReceiptLog
from .registry import PluginRegistry
from .state import LinkMachine

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UI_DIR = REPO_ROOT / "cautreo-desktop-ui"
DEFAULT_PLUGINS_DIR = REPO_ROOT / "cautreo-host" / "plugins"

# Các đường dẫn tĩnh host phục vụ. `/bus` dành riêng cho WebSocket.
BUS_PATH = "/bus"


def _model_name_from(raw: bytes) -> str | None:
    """Đọc tên model từ thân phản hồi của endpoint. Không đoán, không mặc định.

    `/v1/models` trả `{"models":[{"name": ...}]}`. `/health` thường chỉ trả
    `{"status":"ok"}` — khi đó kết quả là None, vì server chưa nói nó là ai.
    """
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    items = data.get("models")
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in ("name", "id", "model"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


class HostLockedError(Exception):
    """Đã có một host khác giữ cổng này. Không mở hai cửa sổ cho cùng một cơ thể."""


def _lock_fd(fd: int) -> None:
    """Khóa file ở mức OS. Nạp module bằng `__import__` vì `msvcrt`/`fcntl` chỉ
    có trên hệ điều hành tương ứng — mypy chạy trên Windows không có stub `fcntl`."""
    if os.name == "nt":
        msvcrt: Any = __import__("msvcrt")
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        fcntl: Any = __import__("fcntl")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_fd(fd: int) -> None:
    if os.name == "nt":
        msvcrt: Any = __import__("msvcrt")
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        fcntl: Any = __import__("fcntl")
        fcntl.flock(fd, fcntl.LOCK_UN)


class SingleInstance:
    """Khóa file ở mức OS. Process chết thì khóa tự nhả — không để khóa mồ côi."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
        try:
            _lock_fd(fd)
        except OSError as exc:
            os.close(fd)
            raise HostLockedError(
                f"đã có host khác đang giữ {self.path} — mở lại cửa sổ cũ, "
                "hoặc tắt host đó trước khi chạy host mới"
            ) from exc
        os.ftruncate(fd, 0)
        os.write(fd, f"{os.getpid()}\n".encode())
        self._fd = fd

    def release(self) -> None:
        if self._fd is None:
            return
        with contextlib.suppress(OSError):
            os.lseek(self._fd, 0, os.SEEK_SET)
            _unlock_fd(self._fd)
        os.close(self._fd)
        self._fd = None
        with contextlib.suppress(OSError):
            self.path.unlink()

    def __enter__(self) -> SingleInstance:
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()


class Host:
    """Ghép ba thứ lại. Không có business logic nào ở đây — mọi việc là của plugin."""

    def __init__(
        self,
        *,
        ui_dir: Path,
        plugins_dir: Path,
        workspace: Path | None = None,
        port: int = 8751,
        host: str = "127.0.0.1",
        model_endpoint: str | None = "http://127.0.0.1:8080",
        offline: bool = False,
        dual_models: bool = False,
        gemma_path: Path | str | None = None,
        qwen_path: Path | str | None = None,
    ) -> None:
        self.ui_dir = Path(ui_dir)
        self.plugins_dir = Path(plugins_dir)
        self.workspace = Path(workspace) if workspace else REPO_ROOT
        self.port = port
        self.host = host
        self.model_endpoint = model_endpoint
        self.offline = offline
        self.dual_models = dual_models
        self.gemma_path = gemma_path
        self.qwen_path = qwen_path

        self.link = LinkMachine()
        self.registry = PluginRegistry()
        # Host cắm fs, local, và **máy khách HTTP** tới endpoint model đã cấu hình.
        # Không tự sinh câu trả lời nào — chỉ chuyển tiếp. Cautreo thì host không
        # có, do plugin runtime tự cắm (D3).
        model_backend = None if self.offline else self.model_endpoint
        self.bus = Bus(
            self.registry,
            receipts=ReceiptLog(),
            allows_model=lambda: self.link.allows_model,
            model_refusal=self.link.refuse_model,
            backends=default_backends(
                self.workspace,
                model_backend,
                dual_models=self.dual_models,
                gemma_path=self.gemma_path,
                qwen_path=self.qwen_path,
            ),
        )
        # host.link-probe: thăm dò lại endpoint thật rồi trả state do LinkMachine quyết.
        # UI không được tự bịa ONLINE — chỉ render kết quả này.
        def _link_probe() -> dict[str, Any]:
            self.open_link()
            return {
                "link": self.link.state.value,
                "reason": self.link.reason,
                "model": self.link.model,
            }

        self.bus._link_probe = _link_probe
        self._clients: set[WebSocketServerProtocol] = set()
        self._server: Any = None

    # ---- URL ----

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    @property
    def bus_url(self) -> str:
        return f"ws://{self.host}:{self.port}{BUS_PATH}"

    # ---- nạp plugin ----

    def load_plugins(self) -> list[str]:
        """discover → validate → load → activate. Plugin hỏng không chặn plugin khác."""
        self.registry.discover(self.plugins_dir)
        loaded: list[str] = []
        for rec in self.registry.all():
            if rec.error:
                continue
            try:
                self.registry.validate(rec.id)
                self.registry.load(rec.id)
                self.registry.activate(rec.id)
            except Exception as exc:  # noqa: BLE001 — một plugin hỏng không sập host
                rec.error = str(exc)
                continue
            loaded.append(rec.id)
        self.bus.sync_registry()
        return loaded

    # ---- liên kết model ----

    def open_link(self) -> None:
        """D1 — "load online": thử model thật ngay khi boot. Thất bại thì DEGRADED
        kèm lý do thật, **không** bịa là đang dùng model."""
        self.link.boot()
        if self.offline:
            # OFFLINE là lựa chọn của người dùng — đi thẳng từ BOOTING là sai máy
            # trạng thái, nên ta đi qua ONLINE rồi mới ngắt, đúng như hợp đồng.
            self.link.come_online()
            self.link.go_offline()
            return
        if not self.model_endpoint:
            self.link.lost("endpoint_unreachable")
            return
        reason, model_name = self._probe_model()
        if reason is None:
            # Tên model chỉ được ghi khi **đọc được từ server**. Server không nói
            # tên thì để None — không bịa một chuỗi nào lên Thanh Thân thể.
            self.link.set_model(model_name)
            self.link.come_online()
        else:
            self.link.lost(reason)

    def _probe_model(self) -> tuple[str | None, str | None]:
        """Thử endpoint thật. Trả về `(lý do hỏng, tên model đọc được)`.

        Thử `/v1/models` **trước**: nó vừa chứng minh server sống, vừa nói server
        là model nào. `/health` chỉ là bằng chứng sống — không có tên thì để
        `None`, không bịa.

        Ba kết cục, ba lý do trung thực — không gộp, không đoán.
        """
        assert self.model_endpoint is not None
        if self.dual_models:
            backend = self.bus.backends.get("dual_cognitive") or self.bus.backends.get("vivyqu")
            if backend and backend.health():
                models = backend.models()
                return None, models[0] if models else "DualCognitive[Gemma-4E4B + Qwen-72B]"
            return "engine_unavailable", None

        if self.model_endpoint == "vivyqu":
            backend = self.bus.backends.get("vivyqu")
            if backend and backend.health():
                models = backend.models()
                return None, models[0] if models else "VivyQu Core"
            return "engine_unavailable", None

        base = self.model_endpoint.rstrip("/")
        for path in ("/v1/models", "/health"):
            try:
                with urllib.request.urlopen(base + path, timeout=1.5) as resp:  # noqa: S310
                    if 200 <= resp.status < 300:
                        return None, _model_name_from(resp.read())
            except urllib.error.HTTPError as exc:
                # Nối được nhưng engine trả lỗi — khác với không nối được.
                if exc.code in (401, 403, 404):
                    continue
                return "engine_unavailable", None
            except (urllib.error.URLError, OSError, TimeoutError):
                return "endpoint_unreachable", None
        return "engine_unavailable", None


    # ---- WebSocket /bus ----

    async def _ws_handler(self, ws: WebSocketServerProtocol) -> None:
        self._clients.add(ws)
        try:
            # Gửi trạng thái thật ngay khi nối — UI không phải đoán.
            await ws.send(json.dumps(self._state_message(), ensure_ascii=False))
            async for raw in ws:
                response = self.bus.handle(raw)
                # Đáp trước, thông báo sau: client gửi id thì nhận đúng response
                # của mình ngay, không phải lách qua notification.
                if response is not None:
                    await ws.send(json.dumps(response, ensure_ascii=False))
                for note in self.bus.drain():
                    await ws.send(json.dumps(note, ensure_ascii=False))
        finally:
            self._clients.discard(ws)

    def _state_message(self) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "method": "host.state",
            "params": self.link.snapshot(),
        }

    async def broadcast(self, message: dict[str, Any]) -> None:
        text = json.dumps(message, ensure_ascii=False)
        for ws in list(self._clients):
            with contextlib.suppress(Exception):
                await ws.send(text)

    # ---- HTTP tĩnh ----

    def _serve_static(self, path: str) -> tuple[int, Headers, bytes]:
        """Đưa file ra. Không có path traversal, không có listing thư mục."""
        raw = path.split("?", 1)[0].split("#", 1)[0]
        rel = raw.lstrip("/")
        if not rel:
            rel = "index.html"
        target = (self.ui_dir / rel).resolve()
        try:
            target.relative_to(self.ui_dir.resolve())
        except ValueError:
            return _html_error(403, "403 — đường dẫn nằm ngoài thư mục UI")
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            return _html_error(404, f"404 — không tìm thấy {rel}")
        body = target.read_bytes()
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        headers = Headers(
            [
                ("Content-Type", ctype),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ]
        )
        return 200, headers, body

    async def _process_request(self, path: str, _headers: Headers) -> tuple[int, Headers, bytes] | None:
        if path.split("?", 1)[0] in (BUS_PATH, BUS_PATH + "/"):
            return None  # để websockets bắt tay
        return self._serve_static(path)

    # ---- chạy ----

    async def _serve(self, *, open_browser: bool) -> None:
        async with serve(
            self._ws_handler,
            self.host,
            self.port,
            process_request=self._process_request,
            ping_interval=20,
            ping_timeout=20,
        ) as server:
            self._server = server
            if open_browser:
                webbrowser.open(self.url)
            await asyncio.Future()  # chạy cho tới khi bị hủy

    def run(self, *, open_browser: bool = True, lock: Path | None = None) -> int:
        """Chạy host. Trả về exit code."""
        lock_path = lock or Path(tempfile.gettempdir()) / f"cautreo-host-{self.port}.lock"
        try:
            instance = SingleInstance(lock_path)
            instance.acquire()
        except HostLockedError as exc:
            print(f"cautreo-host: {exc}", file=sys.stderr)
            return 2

        try:
            self.load_plugins()
            self.open_link()

            # KHÔNG auto-write knowledge khi host boot (audit sync 29/09 — host boot
            # từng rewrite 3–4 bản copy, stamp generated_at mỗi lần). Chỉ export khi
            # operator bật CAUTREO_SYNC_KNOWLEDGE=1 hoặc chạy scripts/generate_and_sync_knowledge_graph.py.
            if os.environ.get("CAUTREO_SYNC_KNOWLEDGE", "").strip() in {"1", "true", "yes"}:
                try:
                    from .knowledge import export_and_sync_knowledge_graph
                    doc_p, json_p = export_and_sync_knowledge_graph(self.bus.knowledge_graph, workspace_root=self.workspace)
                    print(f"cautreo-host: biểu đồ tri thức → {doc_p}")
                except Exception as e:
                    print(f"cautreo-host: [cảnh báo] không thể xuất biểu đồ tri thức: {e}", file=sys.stderr)

            print(f"cautreo-host: cửa sổ → {self.url}")
            print(f"cautreo-host: bus    → {self.bus_url}")
            print(f"cautreo-host: link   → {self.link.state.value}"
                  + (f" / {self.link.reason}" if self.link.reason else ""))
            try:
                asyncio.run(self._serve(open_browser=open_browser))
            except KeyboardInterrupt:
                print("\ncautreo-host: đã ngắt.")
            return 0
        finally:
            instance.release()


def _html_error(status: int, message: str) -> tuple[int, Headers, bytes]:
    body = (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{status}</title>"
        "<body style='font:16px/1.6 system-ui;padding:2rem;background:#151b1e;color:#dfe6e9'>"
        f"<h1 style='font-size:1.1rem;font-weight:600'>{message}</h1>"
        "<p style='opacity:.7'>cautreo-host — cửa sổ là trình duyệt.</p>"
        "</body>"
    ).encode()
    headers = Headers(
        [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))]
    )
    return status, headers, body


def main(argv: list[str] | None = None) -> int:
    # Console Windows mặc định là cp1252 — không gõ được tiếng Việt. Chuẩn hoá
    # stdout/stderr sang UTF-8 để thông báo không chết giữa chừng.
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            # `reconfigure` là của TextIOWrapper, không có trên giao thức TextIO.
            cast(Any, stream).reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="cautreo_host",
        description="Host mảnh cho Cautreo Desktop UI — cửa sổ, Plugin Registry, IPC Bus.",
    )
    parser.add_argument("--port", type=int, default=8751)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ui", type=Path, default=DEFAULT_UI_DIR,
                        help=f"thư mục UI tĩnh (mặc định {DEFAULT_UI_DIR})")
    parser.add_argument("--plugins", type=Path, default=DEFAULT_PLUGINS_DIR,
                        help=f"thư mục plugin (mặc định {DEFAULT_PLUGINS_DIR})")
    parser.add_argument("--model-endpoint", default="vivyqu",
                        help="endpoint model để dò khi boot (mặc định 'vivyqu' cho Vivyqu Core E9; để trống để luôn DEGRADED)")
    parser.add_argument("--dual-models", action="store_true",
                        help="kích hoạt kiến trúc nhận thức kép: Gemma 4B (giao tiếp) + Qwen 72B (phân rã) từ D:\\models")
    parser.add_argument("--gemma-path", type=Path, default=Path("D:/models/gemma4-e4b/vivy-gemma-e4b-q4km.gguf"),
                        help="đường dẫn model Gemma giao tiếp")
    parser.add_argument("--qwen-path", type=Path, default=Path("D:/models/qwen2-vl-72b/Qwen2-VL-72B-Instruct-Q4_K_M.gguf"),
                        help="đường dẫn model Qwen phân rã")

    parser.add_argument("--offline", action="store_true",
                        help="chạy OFFLINE ngay từ đầu (lựa chọn của người dùng)")
    parser.add_argument("--no-browser", action="store_true",
                        help="không mở trình duyệt — chỉ phục vụ")
    args = parser.parse_args(argv)

    host = Host(
        ui_dir=args.ui,
        plugins_dir=args.plugins,
        port=args.port,
        host=args.host,
        model_endpoint=args.model_endpoint or None,
        offline=args.offline,
        dual_models=args.dual_models,
        gemma_path=args.gemma_path,
        qwen_path=args.qwen_path,
    )
    return host.run(open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
