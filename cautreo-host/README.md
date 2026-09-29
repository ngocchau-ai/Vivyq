# cautreo-host

Host mảnh cho Cautreo Desktop UI — đúng ba thứ theo spec §3: **cửa sổ · Plugin Registry · IPC Bus**.

Host không có logic nghiệp vụ. Việc nặng do plugin làm; host giữ vòng đời plugin,
giữ bus, và **gán nhãn nguồn** cho mọi kết quả đi qua.

---

## Chạy

```bash
cd cautreo-host
python -m cautreo_host --port 8751
```

Mở `http://127.0.0.1:8751/` — host sẽ tự mở trình duyệt cho bạn.

| Cờ | Mặc định | Nghĩa |
|:---|:---|:---|
| `--port` | `8751` | cổng HTTP + WebSocket |
| `--host` | `127.0.0.1` | địa chỉ lắng nghe |
| `--ui` | `../cautreo-desktop-ui` | thư mục UI tĩnh |
| `--plugins` | `./plugins` | thư mục plugin |
| `--model-endpoint` | `http://127.0.0.1:8080` | endpoint model để probe khi boot |
| `--offline` | tắt | vào thẳng `OFFLINE` — **người dùng chọn**, không phải do mất kết nối |
| `--no-browser` | tắt | không tự mở trình duyệt |

---

## "Cửa sổ" là trình duyệt — nói thẳng

Host phục vụ `cautreo-desktop-ui/` qua HTTP **trên cùng process** với WebSocket của bus,
rồi mở trình duyệt hệ thống. Đó là cửa sổ.

**Không có webview native nào ở đây.** `pywebview` không cài được trong môi trường này,
và host **không giả vờ** có: không có lớp nào mạo danh webview, không có "desktop window"
nào được dựng lên để trông cho giống app native. Nếu sau này cài được webview thật thì
chỉ phần mở cửa sổ thay đổi — HTTP + WS + registry + bus giữ nguyên.

Chạy hai host cùng lúc trên cùng một workspace sẽ bị từ chối: host giữ **khóa file ở mức
hệ điều hành** (`msvcrt.locking` trên Windows, `fcntl.flock` trên POSIX). Tiến trình chết
thì khóa tự nhả — không để khóa mồ côi.

---

## Ba mảnh của host

### 1 · Cửa sổ
Phục vụ UI tĩnh, mở trình duyệt, giữ khóa single-instance. Không biết plugin là gì.

### 2 · Plugin Registry
Vòng đời:

```
discovered → validated → loaded → activated ⇄ deactivated → unloaded
```

Hot-swap = `deactivated → unloaded → loaded → activated`. Lệnh đang bay khi hot-swap nhận
`plugin_reloading` — host không sập.

`deactivate()` **phải nhả mọi tài nguyên đang giữ** (handle ctypes, kết nối, timer).
Python chạy in-process (`cautreo_binding.py` là C-ABI direct memory) nên không có process
boundary nào cứu được nếu plugin quên nhả.

### 3 · IPC Bus
JSON-RPC 2.0 qua WebSocket tại `/bus`. Bốn điều bus này **không** làm:

1. **Không nhận nhãn nguồn từ client.** Client gửi `source` thì bị gỡ trước khi chạm plugin.
2. **Không sinh `result` khi lỗi.** Lỗi chỉ có `error`. Không có receipt nào tự nhận đã làm.
3. **Không bịa câu trả lời thay model.** Link không `ONLINE` thì lệnh cần model bị từ chối kèm lý do thật.
4. **Không nuốt lỗi plugin.** Lỗi trả `-32002` kèm `plugin_id` và `method`.

| code | message | khi nào |
|---:|:---|:---|
| -32001 | `permission_denied` | thiếu grant |
| -32002 | `plugin_error` | plugin ném lỗi |
| -32003 | `plugin_reloading` | lệnh gửi tới khi đang hot-swap |
| -32004 | `plugin_unavailable` | method chưa đăng ký / plugin chưa activated |
| -32005 | `model_unavailable` | cần model nhưng link không phải ONLINE |

Thông báo (không có `id`): `host.state`, `host.receipt`, `registry.changed`.
**Phản hồi gửi trước thông báo** — client đọc một frame vẫn lấy được đúng reply của mình.

---

## Bản đồ thân thể — tự dựng từ registry, không tự viết

Trước khi có bản đồ này, model nhận mỗi câu hỏi đúng **một** tin nhắn `user`, không system
prompt, không danh sách năng lực. Hỏi "bạn là ai" trên máy thật thì nó trả *"I am not Vivy…
I have no access to 91sh"* — nó nói **đúng** những gì nó được nói (chẳng có gì), và người
dùng hiểu nhầm thành ViVy mất trí.

`cautreo_host/bodymap.py` dựng bản đồ từ **bằng chứng có sẵn trong host**:

| Trường bản đồ | Lấy từ đâu |
|:---|:---|
| `id` · `version` · `kind` · `organ` · `grants` | `PluginRecord.manifest` |
| `methods` | `PluginRecord.methods` — **chỉ khi plugin đang `activated`** |
| `state` · `error` | `PluginRecord.state` / `.error` |
| `host_methods` | `Bus._host_methods` |

Ba bất biến giữ bằng test (`tests/test_bodymap.py`):

1. **Không dòng nào trong bản đồ là lời mô tả tự viết.** Registry nói có thì bản đồ nói có;
   registry nói không thì bản đồ nói thẳng là **chưa có**.
2. **Không liệt kê method mà bus sẽ từ chối.** Plugin chưa `activated` thì `methods: []` —
   nói "có method này" khi không gọi được là bịa năng lực. Thứ không gọi được vẫn hiện ra,
   nhưng ghi rõ `method: không gọi được khi chưa activated`.
3. **`broken` và `organs` không trộn vào nhau.** Record mang lỗi nằm trong `broken` kèm lý
   do, không được bày như một cơ quan khoẻ mạnh. `load()` ghi `rec.error` trước khi ném
   tiếp, để bản đồ nói được "thứ này hỏng vì…" thay vì im lặng biến mất.

Skill **không** là một `kind` của contract (`VALID_KINDS = {workspace, panel, tool, runtime}`).
Một skill là một cơ quan của cơ thể (spec §5.1), nên nó được đếm theo namespace `skill.`
và khi chưa có thì bản đồ nói thẳng `hiện **chưa có** skill nào được nạp`.

### Tự dựng lại khi có thay đổi

`PluginRegistry.on_change` là một hook, không phải lời nhắc phải nhớ gọi tay:

```
_move() / discover() / hot_swap()  →  _notify()  →  Bus.sync_registry()
                                                ├─ dựng lại bảng method
                                                └─ dựng lại bản đồ + system prompt
```

`hot_swap` dùng `_quiet()` để gom bốn lần đổi trạng thái thành **một** lần báo.

### Ba cửa vào bản đồ

| Cửa | Dùng cho |
|:---|:---|
| `build_body_map(records, host_methods)` | cấu trúc dữ liệu |
| `render_body_prompt(body_map)` | system prompt nạp vào model |
| `host.body-map` qua bus | giao diện · **không cần model**, `DEGRADED` vẫn đọc được |

Bản đồ đẩy thẳng vào model qua `ModelBackend.set_system()` — host gọi lại sau mỗi lần registry
đổi, nên ViVy thấy đúng cơ quan đang có **ngay tại thời điểm được hỏi**.

Bằng chứng trên máy thật (`:8751` host + `:8080` model `gemma4-e4b`):

```
hỏi "bạn là ai"   → "Tôi là ViVy, linh hồn ngự trong cơ thể Cautreo."
hỏi "liệt kê method" → tool.fs-read · tool.fs-write · vivy.runtime/ask
                       · vivy.runtime/digest · vivy.runtime/recall · host.body-map
```

---

## Nhãn nguồn — host gán, plugin không tự gắn được

Đây là điểm chốt của cả kiến trúc (spec §7.1), và nó là cơ chế, không phải quy ước.

Host trao cho mỗi plugin một `ctx` có các **handle năng lực**:

```
ctx.model    → cần grant model.connect
ctx.cautreo  → cần grant cautreo.access
ctx.fs       → cần grant fs.workspace
ctx.local    → cần grant tool.local
```

Handle nào được **chạm** trong lúc chạy method thì host ghi vào sổ. Nhãn suy ra từ sổ đó:

| Sổ ghi nhận | Nhãn |
|:---|:---|
| có `ctx.derive_from(receipt_id)` | `derived` |
| đã chạm `ctx.model` | `model` |
| đã chạm `ctx.cautreo` | `cautreo` |
| còn lại | `tool-local` |

Kết quả trả về **không bao giờ bị bóc để tìm nhãn**. Plugin có trả `{"source": "model"}`
mà không hề chạm `ctx.model` thì bus vẫn gán `tool-local` — và `tests/test_provenance.py`
khẳng định đúng điều đó.

Khi backend chưa được cắm, `ctx.model` / `ctx.cautreo` **ném lỗi** thay vì trả stub.
Tự trả một câu "giả" ở đây chính là bịa.

**Host cắm ba backend:** `fs` (hệ file workspace, đã jail), `local` (vài phép nội
bộ), và `model` — một **máy khách HTTP** tới `--model-endpoint`. Host không tự viết
câu trả lời nào: `ModelBackend.complete()` chuyển tiếp prompt sang
`/v1/chat/completions` của endpoint và trả về **đúng lời server nói**, kèm tên model
lấy từ thân phản hồi — không tự khai tên.

Không có endpoint → không có backend `model`, và `ctx.model.complete()` ném lỗi thật.
Có endpoint nhưng server chết giữa chừng → lỗi HTTP ném lên, bus trả `plugin_error`
**không kèm `result`**. Không có câu trả lời dự phòng nào trong mọi nhánh.

`cautreo` thì host **không** có — host không biết Cautreo là gì (D3). Backend đó do
plugin runtime tự cắm vào qua `CallContext(_backends=...)`.

### Luồng tư duy — tách ra, thu gọn, không vứt đi

Model ở endpoint này viết lập luận vào kênh `thought` rồi mới ra câu trả lời:

```
<|channel>thought Thinking Process: 1. … <channel|> Tôi là ViVy, …
```

`split_model_channels()` tách ba mặt — **tách cấu trúc, không viết lại chữ**:

| Khóa | Là gì |
|:---|:---|
| `answer` | câu trả lời — phần **được bày ra trước mặt** |
| `thinking` | danh sách các đoạn lập luận, để bày **lần lượt** |
| `raw` | **nguyên vẹn** đúng chuỗi server trả về |

Bất biến có test giữ:

- `raw` luôn bằng đúng đầu vào — không mất chữ nào.
- Không nhận diện được cấu trúc kênh thì **toàn bộ** nằm ở `answer`. Không bao giờ
  đẩy chữ sang `thinking` rồi để đó cho người dùng không thấy.
- Tên kênh dính liền chữ (`thoughtThinking`) phải bóc được `Thinking` trả lại —
  regex tham ăn mà ăn mất chữ là hỏng.

Trên giao diện, mỗi đoạn `thinking` là một khối `<details>` **tự thu gọn**
(không có `open` sẵn). Bấm vào dòng tóm tắt là mở. Model chỉ sinh suy nghĩ mà
không ra câu trả lời thì giao diện **nói thẳng điều đó** — không lấy
`summary` ("đã hỏi model") ra giả làm câu trả lời.

---

## Receipt — đơn vị tin cậy

Mọi lời gọi thành công sinh đúng một receipt:

```json
{
  "id": "rc-0002",
  "organ": "eye",
  "command": "tool.fs-read",
  "result": "đã đọc cautreo-host/pyproject.toml (744 ký tự)",
  "at": "2026-09-25T10:43:48.637Z",
  "source": "tool-local"
}
```

**Không có receipt thì không được nói đã làm.** Lỗi không có `result`, không có `receipt`.

---

## Trạng thái liên kết

```
BOOTING → LINKING → ONLINE ⇄ DEGRADED
                  ↘ OFFLINE ↗
```

`OFFLINE` là **người dùng chọn** — vào thẳng từ/to `ONLINE`, không đi qua `DEGRADED`.
Không có đường `DEGRADED → OFFLINE`.

| Khóa lý do | Nghĩa |
|:---|:---|
| `endpoint_unreachable` | không nối được endpoint |
| `model_mismatch` | model không khớp |
| `engine_unavailable` | engine chưa sẵn sàng |
| `permission_denied` | thiếu quyền |

Khi `DEGRADED`, ô nhập vẫn nhận lệnh nhưng **chỉ lệnh không cần model được chạy**.
Lệnh cần model bị từ chối kèm lý do thật.

**Ô nhập điều hướng ra sao** (`cautreo-desktop-ui/app.js`):

| Bạn gõ | Đi đâu |
|:---|:---|
| `đọc <path>` | `tool.fs-read` |
| `ghi <path> <nội dung>` | `tool.fs-write` |
| `tra <khoá>` | `vivy.runtime/recall` |
| `tool.fs-read {"path":"..."}` | đúng method đó, tham số JSON |
| **còn lại** | `vivy.runtime/ask` — coi là lời nói với ViVy |

Câu "chào Vivy" đi thẳng tới model. Kết quả về sẽ mang nhãn `model` do **host** gán,
nên bạn thấy rõ câu đã đi đâu — không có dòng nào do giao diện tự viết ra.
Bạn chỉ thấy **câu trả lời**; luồng tư duy nằm trong khối thu gọn bên dưới
(xem *Luồng tư duy* ở trên).

Chỉ tên method **có namespace** (chứa `.` hoặc `/`, đúng contract `id = "namespace.tên"`)
mới được coi là method. Nhờ vậy từ `hello` không bị hiểu nhầm thành tên method.

---

## Plugin — `plugin.toml`

```toml
[plugin]
id = "tool.fs-read"        # namespace.tên
version = "1.0.0"          # semver
api = 1                    # lệch là từ chối, host không dịch
kind = "tool"              # workspace | panel | tool | runtime
organ = "eye"              # eye | hand | both — BẮT BUỘC với tool/runtime,
                           # phải TRỐNG với workspace/panel

[entry]
logic = "logic/main.py"    # ít nhất một trong ui / logic

[permissions]
grant = ["fs.workspace"]   # không xin thì không có quyền
```

Logic face khai `method_grants` — mỗi method nói nó cần quyền gì. Khai vượt manifest
là trượt contract: host chặn ở **hai biên**, một ở biên method, một ở biên handle.

Plugin mẫu trong `plugins/`:

| Plugin | Organ | Làm gì |
|:---|:---|:---|
| `tool.fs-read` | eye | đọc file trong workspace |
| `tool.fs-write` | hand | ghi file; có `based_on` để minh hoạ nhãn `derived` |
| `vivy.runtime` | both | runtime, đăng ký động `ask` / `recall` / `digest` |

---

## Kiểm thử

```bash
python -m pytest tests/ -q --basetemp=_pytest_tmp
ruff check .
mypy cautreo_host/ --ignore-missing-imports
```

Năm bộ test theo spec §7.3:

| File | Chốt cái gì |
|:---|:---|
| `test_contract.py` | manifest schema, version, bus từ chối thiếu quyền |
| `test_lifecycle.py` | 100 lần hot-swap không rò handle, không sót surface, lệnh đang bay nhận `plugin_reloading` |
| `test_boot_degraded.py` | mất model → đúng lý do, **không bịa trả lời** |
| `test_provenance.py` | plugin không tự gắn nhãn được |
| `test_ui_smoke.py` | 4 bề mặt mở được, Body Bar đọc đúng state thật |
| `test_model_backend.py` | tên model **đọc từ server** (không hardcode); backend ném lỗi chứ không trả câu dự phòng; tách kênh suy nghĩ **không mất chữ** |
| `test_testkit.py` | bộ chấm cho plugin bên thứ ba có răng |

`tests/testkit.py` là bộ chấm dùng chung — plugin bên thứ ba chấm bằng đúng bộ này
thay vì chép test của host:

```python
from testkit import assert_plugin_ok

def test_contract():
    assert_plugin_ok(Path(__file__).parent / "my-plugin")
```

---

## Thiết kế đầy đủ

`docs/superpowers/specs/2026-09-25-cautreo-desktop-ui-design.md` — 9 quyết định D1–D9,
contract plugin, state machine, bốn lớp xử lý lỗi, và ranh giới phạm vi.
