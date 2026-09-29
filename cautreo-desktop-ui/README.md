# Cautreo Desktop UI — bàn điều khiển cơ thể

Bản mẫu giao diện cho spec `docs/superpowers/specs/2026-09-25-cautreo-desktop-ui-design.md`.
**Greenfield** — không dựa trên `Vivy_final/desktop/` (xem D2).

```
index.html   cấu trúc 4 bề mặt + Thanh Thân thể
styles.css   token màu / chữ / thành phần
app.js       trạng thái, deep link, composer, đường ECG
```

Mở bằng cách mở `index.html` trong trình duyệt. Chưa nối IPC Bus — mọi dòng dữ liệu
trên màn hình là **dữ liệu mẫu**, có ghi rõ trong trang.

## Bốn bề mặt

| Đường dẫn | Bề mặt |
|:---|:---|
| *(mặc định)* | Giao tiếp 💬 |
| `?surface=nhiem-vu` | Nhiệm vụ ✓ |
| `?surface=he-thong` | Hệ thống ⚙ |
| `?surface=skill-plugin` | Skill / Plugin ◆ |

Trạng thái liên kết: `?link=online` · `?link=degraded` · `?link=offline`.
Gộp được: `?surface=he-thong&link=degraded`.

`#nhiem-vu` hay `#degraded` cũng chạy — nhưng **Chrome headless `--screenshot` rụng
`#hash`**, chỉ giữ `?query`. Muốn chụp màn hình thì dùng query, không dùng hash.
Deep link áp **ngay lúc nạp**, không đợi chuỗi boot.

## Nguyên tắc không được vi phạm

Những quy tắc này là lý do UI này có hình dạng hiện tại. Đừng "làm đẹp" mà phá chúng.

1. **Không bịa kết quả.** Không có receipt thì không nói đã làm. Khi `DEGRADED`,
   lệnh cần model bị **từ chối kèm lý do** — không có câu trả lời giả.
2. **Nhãn nguồn do host gán tại bus** — `model` · `cautreo` · `tool-local` · `derived`.
   Plugin không tự gắn được. Lời của người dùng **không** mang nhãn nguồn.
3. **Chưa đo thì ghi "chưa có số liệu".** Không viết số ước lượng vào meter,
   receipt, hay bộ đếm.
4. **Chip model phải tự thú.** `DEGRADED` → `gemma4-e4b · chưa nối`;
   `OFFLINE` → `model đã ngắt`. Không để chip đọc như đang dùng.
5. **`DEGRADED` ≠ `OFFLINE`.** Cái trước hệ thống tự rơi vào và **có lý do**
   (`endpoint_unreachable` · `model_mismatch` · `engine_unavailable` · `permission_denied`).
   Cái sau **người dùng tự chọn**. Không có đường `DEGRADED → OFFLINE`;
   từ `OFFLINE` bật lại phải đi `LINKING → ONLINE`.
6. **Chỉ một điểm nhấn:** đường ECG sống trong Thanh Thân thể. Không thêm animation
   trang trí. `prefers-reduced-motion` phải được tôn.

## Hệ màu

Bốn sắc cơ quan, mỗi sắc một nghĩa — không phải màu thương hiệu:

| Token | Hex | Nghĩa |
|:---|:---|:---|
| `--nerve` | `#7bc5b0` | sống · online |
| `--iris` | `#6fb6d9` | Mắt · nhận |
| `--ochre` | `#d9a05b` | Tay · làm |
| `--clot` | `#c25b4e` | hỏng · degraded |
| `--soul` | `#a99bd4` | linh hồn · model |

Chữ: **Be Vietnam Pro** (giao diện) + **Source Serif 4** (dòng suy nghĩ).
Serif chỉ cho thought-stream.

## Việc còn lại (ngoài phạm vi bản mẫu này)

Host (cửa sổ + Plugin Registry + IPC Bus), `plugin.toml` validation, `vivy.runtime`,
bốn workspace plugin, boot/degraded nối bus thật, nhãn nguồn tại bus, 5 bộ test.
Xem §8 của spec.
