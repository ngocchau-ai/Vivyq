"""Model backend — D1 "load online" cho đủ.

Hai điều phải đúng:

1. **Host đọc tên model từ server.** Không có chuỗi tên nào được hardcode —
   trước đây `LinkMachine` mặc định `"gemma4-e4b"` là một lời khai không có
   bằng chứng. Server không nói tên thì để `None`.
2. **Backend không bịa câu trả lời.** Mọi lỗi HTTP / JSON / shape lạ đều ném
   lên trên, bus biến thành `plugin_error`, **không có `result`** nào được sinh
   ra để lấp chỗ trống.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from cautreo_host.backends import (
    ModelBackend,
    default_backends,
    split_model_channels,
)
from cautreo_host.host import Host, _model_name_from
from cautreo_host.state import LinkMachine

REPO_ROOT = Path(__file__).resolve().parents[2]
CAUTREO_HOST_DIR = REPO_ROOT / "cautreo-host"
UI_DIR = REPO_ROOT / "cautreo-desktop-ui"
PLUGINS_DIR = CAUTREO_HOST_DIR / "plugins"


class StubModelServer:
    """Một endpoint model giả. Ghi lại request để kiểm client gửi gì đi."""

    def __init__(
        self,
        *,
        names: tuple[str, ...] = ("gemma4-e4b",),
        reply: str = "chào bạn, tôi là ViVy",
        fail_with: int | None = None,
        malformed: bool = False,
        empty_choices: bool = False,
        health_only: bool = False,
    ) -> None:
        self.names = names
        self.reply = reply
        self.fail_with = fail_with
        self.malformed = malformed
        self.empty_choices = empty_choices
        self.health_only = health_only
        self.calls: list[dict[str, Any]] = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # im lặng khi test
                return None

            def _send(self, code: int, body: Any) -> None:
                raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:  # noqa: N802
                if self.path.startswith("/health"):
                    self._send(200, {"status": "ok"})
                    return
                if self.path.startswith("/v1/models"):
                    if stub.health_only:
                        self._send(404, {"error": "no models route"})
                        return
                    self._send(200, {
                        "models": [{"name": n, "id": n} for n in stub.names],
                    })
                    return
                self._send(404, {"error": "not found"})

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    payload = {"_unparsed": raw.decode("utf-8", "replace")}
                stub.calls.append({"path": self.path, "payload": payload})

                if not self.path.startswith("/v1/chat/completions"):
                    self._send(404, {"error": "not found"})
                    return
                if stub.fail_with is not None:
                    self._send(stub.fail_with, {"error": "server said no"})
                    return
                if stub.malformed:
                    self._send(200, b"this is not json at all")
                    return
                if stub.empty_choices:
                    self._send(200, {"model": stub.names[0], "choices": []})
                    return
                self._send(200, {
                    "model": stub.names[0],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": stub.reply},
                        }
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 5},
                })

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> StubModelServer:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"


# ---------------------------------------------------------------- ModelBackend


class TestModelBackendSpeaksOnlyWhatTheServerSaid:
    def test_complete_returns_server_text_and_server_model_name(self):
        with StubModelServer(names=("qwen3-4b",), reply="xin chào") as stub:
            out = ModelBackend(stub.endpoint).complete("chào")
        assert out["text"] == "xin chào"
        assert out["model"] == "qwen3-4b"  # từ server, không phải từ client
        assert out["finish_reason"] == "stop"
        assert out["usage"] == {"prompt_tokens": 3, "completion_tokens": 5}

    def test_configured_model_name_does_not_leak_into_result(self):
        """Cấu hình một tên, server nói tên khác — kết quả phải theo server."""
        with StubModelServer(names=("server-named",)) as stub:
            out = ModelBackend(stub.endpoint, model="client-claimed").complete("hi")
        assert out["model"] == "server-named"

    def test_request_carries_prompt_and_limits(self):
        with StubModelServer() as stub:
            ModelBackend(stub.endpoint, model="gemma4-e4b", max_tokens=77).complete("nói gì đi")
        sent = stub.calls[-1]["payload"]
        assert sent["messages"] == [{"role": "user", "content": "nói gì đi"}]
        assert sent["max_tokens"] == 77
        assert sent["model"] == "gemma4-e4b"

    def test_models_list_comes_from_server(self):
        with StubModelServer(names=("a", "b")) as stub:
            assert ModelBackend(stub.endpoint).models() == ["a", "b"]

    def test_health_reports_server_status(self):
        with StubModelServer() as stub:
            assert ModelBackend(stub.endpoint).health() is True


class TestModelBackendNeverFabricates:
    def test_http_error_raises_and_yields_no_placeholder(self):
        with StubModelServer(fail_with=500) as stub:
            backend = ModelBackend(stub.endpoint)
            with pytest.raises(RuntimeError) as exc:
                backend.complete("chào")
        assert "500" in str(exc.value)
        # Không có câu trả lời dự phòng nào được trả ra ngoài.
        assert "xin lỗi" not in str(exc.value).lower()

    def test_unreachable_endpoint_raises(self):
        with StubModelServer() as stub:
            dead = stub.endpoint
        with pytest.raises(RuntimeError) as exc:
            ModelBackend(dead, timeout=1.0).complete("chào")
        assert "không gọi được" in str(exc.value)

    def test_non_json_body_raises(self):
        with StubModelServer(malformed=True) as stub:
            with pytest.raises(RuntimeError) as exc:
                ModelBackend(stub.endpoint).complete("chào")
        assert "không phải JSON" in str(exc.value)

    def test_empty_choices_raises(self):
        with StubModelServer(empty_choices=True) as stub:
            with pytest.raises(RuntimeError) as exc:
                ModelBackend(stub.endpoint).complete("chào")
        assert "choices" in str(exc.value)

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_blank_prompt_is_refused(self, bad):
        with pytest.raises(ValueError):
            ModelBackend("http://127.0.0.1:1").complete(bad)


class TestDefaultBackends:
    def test_no_endpoint_means_no_model_backend(self):
        out = default_backends(CAUTREO_HOST_DIR)
        assert "model" not in out
        assert set(out) == {"cautreo", "fs", "local"}

    def test_endpoint_binds_model_backend(self):
        out = default_backends(CAUTREO_HOST_DIR, "http://127.0.0.1:8080")
        assert isinstance(out["model"], ModelBackend)
        assert set(out) == {"cautreo", "fs", "local", "model"}


# ---------------------------------------------------------------- tên model


class TestModelNameIsNeverInvented:
    def test_link_machine_starts_with_unknown_model(self):
        # Trước đây mặc định là "gemma4-e4b" — một lời khai không có bằng chứng.
        assert LinkMachine().model is None

    def test_set_model_accepts_none(self):
        link = LinkMachine(model="đã biết")
        link.set_model(None)
        assert link.model is None

    def test_snapshot_omits_model_when_never_verified(self):
        snap = LinkMachine().snapshot()
        assert snap["model"] is None

    @pytest.mark.parametrize(
        ("raw", "want"),
        [
            (b'{"models":[{"name":"gemma4-e4b"}]}', "gemma4-e4b"),
            (b'{"models":[{"id":"qwen3"}]}', "qwen3"),
            (b'{"status":"ok"}', None),
            (b"not json", None),
            (b"[1,2,3]", None),
            (b'{"models":[]}', None),
            (b'{"models":[{"name":"  spaced  "}]}', "spaced"),
        ],
    )
    def test_model_name_parser(self, raw, want):
        assert _model_name_from(raw) == want


class TestHostReadsModelNameFromServer:
    def _host(self, endpoint: str) -> Host:
        return Host(
            ui_dir=UI_DIR,
            plugins_dir=PLUGINS_DIR,
            workspace=REPO_ROOT,
            port=0,
            model_endpoint=endpoint,
        )

    def test_probe_reads_name_and_comes_online(self):
        with StubModelServer(names=("thật-sự-tên-này",)) as stub:
            host = self._host(stub.endpoint)
            host.open_link()
        assert host.link.is_online
        assert host.link.model == "thật-sự-tên-này"
        assert host.link.snapshot()["model"] == "thật-sự-tên-này"

    def test_health_only_still_online_but_model_unknown(self):
        """Server sống nhưng không hé lộ tên — để None, không bịa."""
        with StubModelServer(health_only=True) as stub:
            host = self._host(stub.endpoint)
            host.open_link()
        assert host.link.is_online
        assert host.link.model is None

    def test_dead_endpoint_is_degraded_with_no_model_name(self):
        host = self._host("http://127.0.0.1:9")
        host.open_link()
        assert host.link.reason == "endpoint_unreachable"
        assert host.link.model is None


# ---------------------------------------------------------------- hỏi model


class TestAskGoesToTheRealModel:
    def _bus_with_stub(self, stub: StubModelServer) -> Host:
        host = Host(
            ui_dir=UI_DIR,
            plugins_dir=PLUGINS_DIR,
            workspace=REPO_ROOT,
            port=0,
            model_endpoint=stub.endpoint,
        )
        host.load_plugins()
        host.open_link()
        return host

    def test_ask_returns_the_models_words_and_a_model_label(self):
        with StubModelServer(reply="tôi là ViVy, linh hồn của Cautreo") as stub:
            host = self._bus_with_stub(stub)
            msg = host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": "m-1", "method": "vivy.runtime/ask",
                "params": {"prompt": "bạn là ai"},
            }))
        assert msg is not None and "error" not in msg
        receipt = msg["receipt"]
        # Nhãn do HOST gán theo sổ năng lực — plugin không tự khai.
        assert receipt["source"] == "model"
        assert receipt["organ"] == "both"
        assert receipt["command"] == "vivy.runtime/ask"
        assert msg["result"]["answer"] == "tôi là ViVy, linh hồn của Cautreo"

    def test_server_model_name_reaches_the_caller(self):
        with StubModelServer(names=("tên-từ-server",)) as stub:
            host = self._bus_with_stub(stub)
            msg = host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": "m-2", "method": "vivy.runtime/ask",
                "params": {"prompt": "chào"},
            }))
        assert msg["result"]["detail"]["model"] == "tên-từ-server"

    def test_model_failure_becomes_plugin_error_with_no_result(self):
        """Server đang sống lúc probe nhưng chết lúc gọi — không bịa câu trả lời."""
        with StubModelServer(fail_with=503) as stub:
            host = self._bus_with_stub(stub)
            msg = host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": "m-3", "method": "vivy.runtime/ask",
                "params": {"prompt": "chào"},
            }))
        assert set(msg) == {"jsonrpc", "id", "error"}
        assert msg["error"]["code"] == -32002
        assert "result" not in msg
        assert "receipt" not in msg

    def test_no_model_backend_still_refuses_rather_than_invents(self):
        """Host không cắm model backend → ném thật, không trả chuỗi dự phòng."""
        host = Host(
            ui_dir=UI_DIR, plugins_dir=PLUGINS_DIR, workspace=REPO_ROOT,
            port=0, model_endpoint=None,
        )
        host.load_plugins()
        host.open_link()  # endpoint None → DEGRADED
        assert host.link.reason == "endpoint_unreachable"
        msg = host.bus.handle(json.dumps({
            "jsonrpc": "2.0", "id": "m-4", "method": "vivy.runtime/ask",
            "params": {"prompt": "chào"},
        }))
        assert "result" not in msg
        assert msg["error"]["code"] == -32005


# ---------------------------------------------------------------- tách kênh

# Đúng hình dạng đo được trên endpoint thật: kênh suy nghĩ mở bằng
# `<|channel>thought`, đóng bằng `<channel|>`, câu trả lời nằm sau đó.
RAW_WITH_THINKING = (
    "<|channel>thoughtThinking Process:\n"
    "1. người dùng chào mình\n"
    "2. mình là ViVy\n"
    "<channel|>"
    "Tôi là ViVy, linh hồn của Cautreo."
)


class TestThinkingIsSeparatedNotDiscarded:
    """Luồng tư duy tách khỏi câu trả lời — nhưng KHÔNG được mất chữ nào.

    Yêu cầu của người dùng: chỉ bày kết quả, phần suy nghĩ thu gọn lại, ai muốn
    thì bấm mở. Điều kiện kèm theo của Gate 9: thu gọn **không** được đồng nghĩa
    với vứt đi — chữ của model vẫn phải còn, và không được trộn vào câu trả lời.
    """

    def test_answer_is_only_the_closing_words(self):
        parts = split_model_channels(RAW_WITH_THINKING)
        assert parts["answer"] == "Tôi là ViVy, linh hồn của Cautreo."

    def test_thinking_holds_the_reasoning_verbatim(self):
        parts = split_model_channels(RAW_WITH_THINKING)
        assert parts["thinking"] == [
            "Thinking Process:\n1. người dùng chào mình\n2. mình là ViVy"
        ]

    def test_thinking_is_a_list_so_the_ui_can_show_each_block_in_turn(self):
        raw = "<|channel>thought bước một<channel|>trả lời<|channel>thought bước hai<channel|>!"
        parts = split_model_channels(raw)
        assert parts["thinking"] == ["bước một", "bước hai"]
        assert parts["answer"] == "trả lời\n\n!"

    def test_raw_comes_back_untouched(self):
        assert split_model_channels(RAW_WITH_THINKING)["raw"] == RAW_WITH_THINKING

    def test_no_content_word_is_lost(self):
        """Mọi chữ trong raw phải nằm trong answer hoặc thinking (trừ token)."""
        parts = split_model_channels(RAW_WITH_THINKING)
        haystack = parts["answer"] + "\n" + "\n".join(parts["thinking"])
        for word in (
            "Thinking Process:", "người dùng chào mình", "mình là ViVy",
            "Tôi là ViVy, linh hồn của Cautreo.",
        ):
            assert word in haystack

    def test_plain_text_has_no_thinking_block(self):
        parts = split_model_channels("xin chào, tôi nghe đây")
        assert parts == {
            "answer": "xin chào, tôi nghe đây",
            "thinking": [],
            "raw": "xin chào, tôi nghe đây",
        }

    def test_unrecognized_markup_goes_entirely_to_answer(self):
        """Không hiểu cấu trúc → bày hết ra. Tuyệt đối không giấu chữ."""
        weird = "<|widget>mở</|widget> phần còn lại"
        parts = split_model_channels(weird)
        assert parts["thinking"] == []
        assert parts["answer"] == weird

    def test_channel_name_glued_to_content_does_not_eat_the_content(self):
        """`thoughtThinking` phải tách ra `thought` + chữ `Thinking`."""
        parts = split_model_channels("<|channel>thoughtThinking Process:<channel|>Xong.")
        assert parts["thinking"] == ["Thinking Process:"]
        assert parts["answer"] == "Xong."

    def test_thinking_without_a_close_still_leaves_answer_visible(self):
        """Kênh suy nghĩ không đóng — vẫn phải thấy được chữ ở kênh mặc định."""
        parts = split_model_channels("trả lời trước<|channel>thought suy nghĩ dở dang")
        assert parts["answer"] == "trả lời trước"
        assert parts["thinking"] == ["suy nghĩ dở dang"]

    def test_answer_is_empty_when_the_model_only_thought(self):
        parts = split_model_channels("<|channel>thought toàn bộ là suy nghĩ<channel|>")
        assert parts["answer"] == ""
        assert parts["thinking"] == ["toàn bộ là suy nghĩ"]
        # raw vẫn giữ — người dùng không bị mất chữ, chỉ phải bấm mở rộng.
        assert "toàn bộ là suy nghĩ" in parts["raw"]

    @pytest.mark.parametrize("bad", [None, 42, ["x"], {"a": 1}])
    def test_non_string_input_is_emptied_not_guessed(self, bad):
        assert split_model_channels(bad) == {"answer": "", "thinking": [], "raw": ""}

    def test_complete_returns_the_split_beside_the_verbatim_text(self):
        with StubModelServer(reply=RAW_WITH_THINKING) as stub:
            out = ModelBackend(stub.endpoint).complete("chào")
        assert out["text"] == RAW_WITH_THINKING  # nguyên văn, không cắt
        assert out["answer"] == "Tôi là ViVy, linh hồn của Cautreo."
        assert out["thinking"] == ["Thinking Process:\n1. người dùng chào mình\n2. mình là ViVy"]


class TestAskShowsAnswerAndKeepsThinking:
    def _ask(self, reply: str) -> dict[str, Any]:
        with StubModelServer(reply=reply) as stub:
            host = Host(
                ui_dir=UI_DIR, plugins_dir=PLUGINS_DIR, workspace=REPO_ROOT,
                port=0, model_endpoint=stub.endpoint,
            )
            host.load_plugins()
            host.open_link()
            msg = host.bus.handle(json.dumps({
                "jsonrpc": "2.0", "id": "t-1", "method": "vivy.runtime/ask",
                "params": {"prompt": "chào"},
            }))
        assert msg is not None and "error" not in msg
        return msg["result"]

    def test_result_carries_answer_thinking_and_raw(self):
        result = self._ask(RAW_WITH_THINKING)
        assert result["answer"] == "Tôi là ViVy, linh hồn của Cautreo."
        assert result["thinking"] == [
            "Thinking Process:\n1. người dùng chào mình\n2. mình là ViVy"
        ]
        assert result["raw"] == RAW_WITH_THINKING

    def test_answer_does_not_smuggle_thinking_text(self):
        result = self._ask(RAW_WITH_THINKING)
        assert "Thinking Process" not in result["answer"]
        assert "người dùng chào mình" not in result["answer"]

    def test_plain_reply_yields_no_thinking_block(self):
        result = self._ask("chào bạn, tôi nghe đây")
        assert result["answer"] == "chào bạn, tôi nghe đây"
        assert result["thinking"] == []
        assert result["raw"] == "chào bạn, tôi nghe đây"

    def test_thinking_only_reply_does_not_fake_an_answer(self):
        """Model chỉ suy nghĩ, không ra câu trả lời → answer rỗng, không bịa."""
        result = self._ask("<|channel>thoughtnghĩ mãi chưa ra<channel|>")
        assert result["answer"] == ""
        assert result["thinking"] == ["nghĩ mãi chưa ra"]
